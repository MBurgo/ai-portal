import time, json, pathlib
from io import BytesIO
from textwrap import dedent
import streamlit as st
from docx import Document
from utils import apply_branding, configure_openai

# 1. Config & Styling
st.set_page_config(page_title="✍️ Foolish AI Copywriter", initial_sidebar_state="expanded")
apply_branding()

# 2. Init OpenAI
client = configure_openai()
OPENAI_MODEL = "gpt-4-turbo" # Or your preferred model

# 3. Load Traits
try:
    TRAIT_CFG = json.loads(pathlib.Path("traits_config.json").read_text())
except FileNotFoundError:
    st.error("Error: 'traits_config.json' not found. Please ensure it is in the root folder.")
    st.stop()

# 4. Globals & Helpers
LENGTH_RULES = {
    "📏 Short (100–200 words)":        (100, 220),
    "📐 Medium (200–500 words)":       (200, 550),
    "📖 Long (500–1500 words)":        (500, 1600),
    "📚 Extra Long (1500–3000 words)": (1500, 3200),
}
COUNTRY_RULES = {
    "Australia":      "Use Australian English, prices in AUD, reference the ASX.",
    "United Kingdom": "Use British English, prices in GBP, reference the FTSE.",
    "Canada":         "Use Canadian English, prices in CAD, reference the TSX.",
    "United States":  "Use American English, prices in USD, reference the S&P 500.",
}

if "generated_copy" not in st.session_state: st.session_state.generated_copy = ""
if "internal_plan" not in st.session_state: st.session_state.internal_plan = ""

def line(label, value):
    return f"- {label}: {value}\n" if value.strip() else ""

def trait_rules(traits):
    out = []
    for name, score in traits.items():
        cfg = TRAIT_CFG.get(name)
        if not cfg: continue
        if score >= cfg["high_threshold"]: out.append(cfg["high_rule"])
        elif score <= cfg["low_threshold"]: out.append(cfg["low_rule"])
        else:
            if cfg.get("mid_rule"): out.append(cfg["mid_rule"])
    return out

# --- UI START ---
st.title("✍️ Foolish AI Copywriter")

# Check for Golden Thread Data
default_details = ""
if 'intelligence_brief' in st.session_state:
    st.success(f"💡 Imported Insight from {st.session_state.get('intelligence_source', 'Intelligence Tool')}")
    default_details = st.session_state['intelligence_brief']

tab_gen, tab_adapt = st.tabs(["✍️ Generate Copy", "🌐 Adapt Copy"])

with tab_gen:
    with st.sidebar.expander("🎚️ Linguistic Trait Intensity", True):
        with st.form("trait_form"):
            trait_scores = {
                "Urgency": st.slider("Urgency", 1, 10, 8),
                "Data_Richness": st.slider("Data Richness", 1, 10, 7),
                "Social_Proof": st.slider("Social Proof", 1, 10, 6),
                "Comparative_Framing": st.slider("Comparative Framing", 1, 10, 6),
                "Imagery": st.slider("Imagery", 1, 10, 7),
                "Conversational_Tone": st.slider("Conversational Tone", 1, 10, 8),
                "FOMO": st.slider("FOMO", 1, 10, 7),
                "Repetition": st.slider("Repetition", 1, 10, 5),
            }
            st.form_submit_button("Update Settings")

    country = st.selectbox("🌐 Target Country", list(COUNTRY_RULES))
    copy_type = st.selectbox("Copy Type", ["📧 Email", "📝 Sales Page"])
    length_choice = st.selectbox("Desired Length", list(LENGTH_RULES))

    st.subheader("Campaign Brief")
    hook = st.text_area("🪝 Campaign Hook")
    details = st.text_area("📦 Product / Offer Details (or Paste Brief)", value=default_details, height=200)

    # Simple Generation Logic
    if st.button("✨ Generate Copy"):
        with st.spinner("Writing..."):
            rules = trait_rules(trait_scores)
            prompt = f"""
            You are a Copy Chief. Write a {copy_type} for the {country} market.
            
            CONTEXT/DETAILS:
            {details}
            
            HOOK:
            {hook}
            
            GUIDELINES:
            {chr(10).join(rules)}
            
            Return ONLY the copy.
            """
            
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            st.session_state.generated_copy = resp.choices[0].message.content

    if st.session_state.generated_copy:
        st.markdown("### Generated Draft")
        st.markdown(st.session_state.generated_copy)
        
        # GOLDEN THREAD OUTPUT
        st.divider()
        if st.button("🔬 Test this Draft in Focus Group"):
            st.session_state['draft_for_validation'] = st.session_state.generated_copy
            st.switch_page("pages/3_🔬_Validation.py")
