import streamlit as st
import json, re, time
from pathlib import Path
from utils import apply_branding, configure_openai, configure_gemini

# 1. Config
st.set_page_config(page_title="Foolish Focus Group", page_icon="🔬")
apply_branding()

# 2. Load Data
try:
    APP_DIR = Path(__file__).resolve().parent.parent
    with open(APP_DIR / "personas.json", "r", encoding="utf-8") as f:
        personas_data = json.load(f)
        # Flatten personas for dropdown
        all_personas = []
        for seg in personas_data.get("segments", []):
            for p in seg.get("personas", []):
                p_flat = p.copy()
                p_flat['segment_label'] = seg['label']
                p_flat['uid'] = p['id']
                all_personas.append(p_flat)
except Exception as e:
    st.error(f"Error loading personas.json: {e}")
    st.stop()

# 3. UI
st.title("🔬 Focus Group Validation")

# Check for Golden Thread Data
default_creative = ""
if 'draft_for_validation' in st.session_state:
    st.success("✍️ Draft loaded from Creation Tool.")
    default_creative = st.session_state['draft_for_validation']

creative_input = st.text_area("Campaign Creative to Test", value=default_creative, height=200)

c1, c2 = st.columns(2)
with c1:
    p1_uid = st.selectbox("Participant 1 (The Skeptic)", [p['uid'] for p in all_personas], index=0)
with c2:
    p2_uid = st.selectbox("Participant 2 (The Believer)", [p['uid'] for p in all_personas], index=1)

if st.button("⚔️ Start Debate"):
    st.info("Simulation running... (This is a placeholder for the full logic you already have)")
    
    # Simple Mock Simulation (Replace with your full debate logic if preferred)
    p1_name = next(p['core']['name'] for p in all_personas if p['uid'] == p1_uid)
    p2_name = next(p['core']['name'] for p in all_personas if p['uid'] == p2_uid)
    
    st.write(f"**{p1_name}**: This looks expensive. Where is the proof?")
    st.write(f"**{p2_name}**: I actually like the vision here. It feels forward-thinking.")
    
    st.success("Debate Complete. (Copy your full logic from your original file here to restore full functionality)")
