import streamlit as st
import datetime as dt
from utils import get_gspread_client, apply_branding
from data_retrieval_storage_news_engine import main as retrieve_and_store_data
from step2_summarisation_with_easier_reading import generate_summary

# 1. Page Setup
st.set_page_config(page_title="Intelligence | Briefing", page_icon="🧠")
apply_branding()

# 2. Connect to Sheets using our new utils
client = get_gspread_client()
spreadsheet_id = "1BzTJgX7OgaA0QNfzKs5AgAx2rvZZjDdorgAz0SD9NZg"
sheet = client.open_by_key(spreadsheet_id)

# --- Helper Functions ---
def get_last_run_info(sheet_obj):
    metadata_ws = sheet_obj.worksheet("Metadata")
    last_run_time_str = metadata_ws.cell(2, 1).value
    last_summary_text = metadata_ws.cell(2, 2).value
    if last_run_time_str:
        naive_dt = dt.datetime.strptime(last_run_time_str, "%Y-%m-%d %H:%M:%S")
        last_run_utc = naive_dt.replace(tzinfo=dt.timezone.utc)
    else:
        last_run_utc = None
    return last_run_utc, last_summary_text

def set_last_run_info(sheet_obj, summary_text):
    metadata_ws = sheet_obj.worksheet("Metadata")
    now_utc = dt.datetime.now(dt.timezone.utc)
    run_time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")
    metadata_ws.update_cell(2, 1, run_time_str)
    metadata_ws.update_cell(2, 2, summary_text)

def parse_briefs(summary_text):
    """
    Splits the AI's giant text block into individual briefs.
    Based on your prompt's separator: '--------------------------------------------------'
    """
    sections = summary_text.split("--------------------------------------------------")
    briefs = []
    for section in sections:
        clean_sec = section.strip()
        # Filter for sections that look like actual briefs
        if len(clean_sec) > 100 and ("1. *Synopsis*" in clean_sec or "*Brief Title*" in clean_sec):
            briefs.append(clean_sec)
    return briefs

def run_all_cooldown(sheet_obj, cooldown_hours=3):
    now_utc = dt.datetime.now(dt.timezone.utc)
    last_run_utc, last_summary = get_last_run_info(sheet_obj)

    if last_run_utc is not None:
        elapsed_hours = (now_utc - last_run_utc).total_seconds() / 3600.0
    else:
        elapsed_hours = 9999

    if elapsed_hours < cooldown_hours:
        st.warning(f"⏳ Cooldown active. Briefs were last run {elapsed_hours:.1f} hours ago.")
        st.write("Here is the existing summary from that run:")
        return last_summary
    else:
        with st.status("🤖 AI Agents working...", expanded=True) as status:
            st.write("Step 1: Scrape Google Trends & News...")
            retrieve_and_store_data()
            st.write("Step 2: OpenAI Analysis & Summarization...")
            summary_text = generate_summary()
            set_last_run_info(sheet_obj, summary_text)
            status.update(label="Briefing Complete!", state="complete", expanded=False)
        return summary_text

# --- Main Page UI ---
st.title("Daily Market Intelligence")
st.markdown("### what is the market focusing on?")

# 1. State Management (The Fix)
if "briefing_report" not in st.session_state:
    st.session_state.briefing_report = None

# 2. Generation Button (Only runs logic, doesn't hold UI)
if st.button("Generate Briefing"):
    # Run scraping logic
    full_summary = run_all_cooldown(sheet, cooldown_hours=3)
    # Save to session state so it persists
    st.session_state.briefing_report = full_summary

# 3. Display Logic (Checks State, not the Button)
if st.session_state.briefing_report:
    full_summary = st.session_state.briefing_report
    
    # Parse results
    individual_briefs = parse_briefs(full_summary)
    
    st.success(f"Report Ready: {len(individual_briefs)} Opportunities Found")
    
    # Display Card Selection
    for idx, brief in enumerate(individual_briefs):
        with st.expander(f"📢 Opportunity #{idx+1} (Click to View)", expanded=False):
            st.markdown(brief)
            
            # THE GOLDEN THREAD BUTTON
            # This is now safe because it's outside the first button's scope
            if st.button(f"🚀 Draft Campaign for Opp #{idx+1}", key=f"btn_{idx}"):
                st.session_state['intelligence_brief'] = brief
                st.session_state['intelligence_source'] = "Daily Briefing"
                st.switch_page("pages/2_✍️_Creation.py")

    # Fallback for full text
    with st.expander("📄 View Full Raw Report"):
        st.markdown(full_summary)
