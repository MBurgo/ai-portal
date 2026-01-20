import time, json, pathlib
from textwrap import dedent
import streamlit as st
from docx import Document
from io import BytesIO
from utils import apply_branding, configure_openai

# 1. Config & Styling
st.set_page_config(page_title="✍️ Foolish AI Copywriter", initial_sidebar_state="expanded")
apply_branding()

# 2. Init OpenAI
client = configure_openai()
# Use a model that supports complex instructions well
OPENAI_MODEL = "gpt-4o" 

# 3. Load Traits
try:
    TRAIT_CFG = json.loads(pathlib.Path("traits_config.json").read_text())
except FileNotFoundError:
    st.error("Error: 'traits_config.json' not found. Please ensure it is in the root folder.")
    st.stop()

# 4. Globals & Definitions (Restoring your original logic)
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

# --- Restoring Your Original Prompts ---
SYSTEM_PROMPT = dedent("""
You are The Motley Fool’s senior direct‑response copy chief.

• Voice: plain English, optimistic, inclusive, lightly playful but always expert.
• Draw from Ogilvy clarity, Sugarman narrative, Halbert urgency, Cialdini persuasion.
• Use **Markdown headings** (##, ###) and standard `-` bullets for lists.
• Never promise guaranteed returns; keep compliance in mind.
• The reference examples are for inspiration only — do NOT reuse phrases verbatim.
• Return ONLY the requested copy – no meta commentary.

{country_rules}

At the very end of the piece, append this italic line (no quotes):
*Past performance is not a reliable indicator of future results.*
""").strip()

TRAIT_EXAMPLES = {
    "Urgency": [
        "This isn't a drill — once midnight hits, your chance is gone.",
        "Time’s ticking — when the clock hits zero tonight, you’re out of luck.",
        "You have exactly one shot. Miss today’s deadline, and it's gone."
    ],
    "Data_Richness": [
        "Last year alone, our recommendations averaged returns higher than the market.",
        "Our analysis has identified returns higher than the average ASX investor.",
        "More than 85% of our recommended stocks outperformed the market."
    ],
    "Social_Proof": [
        "Thousands of investors trust Motley Fool every year.",
        "Australia’s leading financial experts have rated us highly.",
        "Join over 125,000 smart investors who rely on our advice."
    ],
    "Comparative_Framing": [
        "Think back to those who seized early opportunities in the smartphone revolution.",
        "Imagine being among the first to see Netflix’s potential in 2002.",
        "Just like the early days of Tesla, these stocks could define your success."
    ],
    "Imagery": [
        "When that switch flips, the next phase could accelerate even faster.",
        "Think of it as a snowball rolling downhill—small at first, but soon unstoppable.",
        "Like a rocket on the launch pad, the countdown has begun."
    ],
    "Conversational_Tone": [
        "Look — investing can feel complicated, but what if it didn't have to be?",
        "We get it—investing can seem overwhelming.",
        "Here’s the truth: investing doesn’t have to be complicated."
    ],
    "FOMO": [
        "Opportunities like these pass quickly — and regret can last forever.",
        "Don’t be the one who has to tell their friends, ‘I missed out.’",
        "By tomorrow, your chance to act will be history."
    ],
    "Repetition": [
        "This offer is for today only. Today only means exactly that: today only.",
        "Act now. This offer expires tonight. Again, it expires tonight.",
        "This is a limited-time deal. Limited-time means exactly that."
    ],
}

EMAIL_STRUCT = """
### Subject Line
### Greeting
### Body (benefits, urgency, proofs)
### Call‑to‑Action
### Sign‑off
"""

SALES_STRUCT = """
## Headline
### Introduction
### Key Benefit Paragraphs
### Detailed Body
### Call‑to‑Action
"""

# 5. Helpers
if "generated_copy" not in st.session_state: st.session_state.generated_copy = ""

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

def trait_guide(traits):
    out = []
    for i, (name, score) in enumerate(traits.items(), 1):
        shots = 3 if score >= 8 else 2 if score >= 4 else 1
        examples = " / ".join(f"“{s}”" for s in TRAIT_EXAMPLES.get(name, [])[:shots])
        out.append(f"{i}. {name.replace('_',' ')} ({score}/10) — e.g. {examples}")
    return "\n".join(out)

def build_prompt(copy_type, copy_struct, traits, brief, length_choice):
    hard_list = trait_rules(traits)
    hard_block = "#### Hard Requirements\n" + "\n".join(hard_list) if hard_list else ""
    
    min_len, max_len = LENGTH_RULES[length_choice]
    length_block = (f"#### Length Requirement\nWrite between **{min_len} and {max_len} words**." 
                    if max_len else f"#### Length Requirement\nWrite **at least {min_len} words**.")

    return f"""
{trait_guide(traits)}

#### Structure to Follow
{copy_struct}

{hard_block}

#### Campaign Brief
{line('Hook', brief['hook'])}
{line('Details', brief['details'])}

{length_block}

IMPORTANT:
- Do NOT invent fake names, fake doctors, or specific numbers (e.g. "5.7%") unless explicitly provided in the Brief. 
- If you need a number, use a placeholder like "[Insert % Return]".
- Focus on the *psychology* of the sale, not manufacturing evidence.

### END INSTRUCTIONS
""".strip()

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

    # --- Robust Generation Logic ---
    if st.button("✨ Generate Copy"):
        if not details and not hook:
            st.warning("Please provide a hook or details.")
        else:
            with st.spinner("Writing compliant copy..."):
                
                # 1. Build the Brief Object
                brief_obj = {"hook": hook, "details": details}
                struct = EMAIL_STRUCT if "Email" in copy_type else SALES_STRUCT
                
                # 2. Build the System & User Prompts using your original logic
                sys_msg = SYSTEM_PROMPT.format(country_rules=COUNTRY_RULES[country])
                user_msg = build_prompt(copy_type, struct, trait_scores, brief_obj, length_choice)
                
                # 3. Call OpenAI
                resp = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg}
                    ]
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
