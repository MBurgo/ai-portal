import streamlit as st
from utils import apply_branding

# 1. Page Config
st.set_page_config(
    page_title="Marketing Intelligence Portal",
    page_icon="🚀",
    layout="centered"
)

# 2. Apply Brand Styles
apply_branding()

# 3. The Welcome Screen
st.title("Marketing Intelligence Portal")
st.markdown("### Welcome, Team.")
st.markdown("Select your goal below to enter the workflow.")

st.divider()

# --- Pillar 1: Intelligence ---
st.subheader("🧠 Intelligence & Strategy")
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("#### 📰 Daily Briefing")
        st.caption("Source: Google News & Trends")
        st.markdown("Scan today's market headlines to find immediate hooks and opportunities.")
        if st.button("Open Briefing Tool", use_container_width=True):
            st.switch_page("pages/1_🧠_Intelligence.py")

with col2:
    with st.container(border=True):
        st.markdown("#### 🔮 The Futurist")
        st.caption("Source: Deep Web Agent")
        st.markdown("Deep-dive research into emerging technologies and future investment themes.")
        if st.button("Chat with Futurist", use_container_width=True):
            st.switch_page("pages/1a_🔮_Futurist.py")

st.divider()

# --- Pillar 2 & 3: Creation & Validation ---
col3, col4 = st.columns(2)

with col3:
    st.subheader("✍️ Creation")
    with st.container(border=True):
        st.markdown("#### AI Copywriter")
        st.caption("Modes: Email, Ads, Sales Pages")
        st.markdown("Turn insights into compliant campaign assets using our copywriting principles.")
        if st.button("Start Writing", use_container_width=True):
            st.switch_page("pages/2_✍️_Creation.py")

with col4:
    st.subheader("🔬 Validation")
    with st.container(border=True):
        st.markdown("#### Focus Group")
        st.caption("Personas: Skeptic, Believer, Retiree")
        st.markdown("Stress-test your creative against synthetic personas before publishing.")
        if st.button("Start Testing", use_container_width=True):
            st.switch_page("pages/3_🔬_Validation.py")

# Footer
st.divider()
st.caption("v1.0 | Marketing Intelligence Portal")
