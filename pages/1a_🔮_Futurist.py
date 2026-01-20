import streamlit as st
from utils import apply_branding

# 1. Page Config
st.set_page_config(page_title="Futurist Agent", page_icon="🔮", layout="wide")
apply_branding()

st.title("🔮 The Futurist")
st.markdown("Interact with the AgentKit Web Agent below to identify high-growth themes.")

# 2. The Iframe (Window to your Next.js App)
# REPLACE THIS URL with your deployed Next.js URL (e.g., https://your-vercel-app.vercel.app)
AGENT_URL = "http://localhost:3000" 

st.components.v1.iframe(src=AGENT_URL, height=600, scrolling=True)

# 3. The "Manual Bridge" (The Golden Thread)
st.divider()
st.markdown("### 🚀 Ready to build a campaign?")
st.info("When the Agent finds a winning theme, paste the summary below to send it to the Copywriter.")

# The user manually copies the insight from the iframe into this box
insight_input = st.text_area("Paste the Futurist's Insight here:", height=150)

if st.button("Draft Campaign from this Insight"):
    if not insight_input:
        st.warning("Please paste the insight first.")
    else:
        # Save to session state
        st.session_state['intelligence_brief'] = insight_input
        st.session_state['intelligence_source'] = "Futurist Agent (Web)"
        
        # Navigate to Creation Tool
        st.switch_page("pages/2_✍️_Creation.py")
