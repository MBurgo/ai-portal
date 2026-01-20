import os
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st
from utils import apply_branding, configure_openai, configure_gemini

# ────────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & SETUP
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Foolish Persona Portal", layout="centered", page_icon="🔬")
apply_branding()

# 1. Init AI Clients
# NOTE: We grab the clients here once
openai_client = configure_openai()
gemini_client = configure_gemini()

# 2. HELPER FUNCTIONS
DASH_CHARS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

def normalize_dashes(s: str) -> str:
    return re.sub(f"[{DASH_CHARS}]", "-", s or "")

def extract_json_object(text: str) -> Optional[dict]:
    if not text: return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start: return None
    blob = text[start : end + 1]
    try:
        return json.loads(blob)
    except Exception:
        return None

# --- AI WRAPPERS (UPDATED) ---
def query_openai(messages, model="gpt-4o", temperature=0.7):
    try:
        # Use the global client instance
        resp = openai_client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def query_gemini(prompt):
    # Try Gemini first if available
    if gemini_client:
        try:
            model = gemini_client.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            st.warning(f"Gemini Error: {e}. Falling back to OpenAI.")
    
    # Fallback to OpenAI
    return query_openai([{"role": "user", "content": prompt}])

# ────────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_personas():
    root_path = Path("personas.json")
    if not root_path.exists():
        return [], []

    with open(root_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    segments = raw.get("segments", [])
    flat = []
    for seg in segments:
        seg_lbl = seg.get("label", "Unknown")
        for p in seg.get("personas", []):
            p['segment_label'] = seg_lbl
            p['uid'] = p['id']
            flat.append(p)
    return segments, flat

segments_data, all_personas_flat = load_personas()

# ────────────────────────────────────────────────────────────────────────────────
# PROMPT LOGIC
# ────────────────────────────────────────────────────────────────────────────────
def build_persona_system_prompt(core):
    return (
        f"You are {core.get('name')}, {core.get('age')} years old, {core.get('occupation')}.\n"
        f"Bio: {core.get('narrative')}\n"
        f"Values: {', '.join(core.get('values', []))}\n"
        f"Concerns: {', '.join(core.get('concerns', []))}\n"
        "Respond in character. Be specific. Keep answers under 140 words."
    )

def moderator_prompt(transcript, creative):
    return f"""
    You are a Direct Response Copy Chief. Analyze this focus group debate.
    
    TRANSCRIPT:
    {transcript}
    
    CREATIVE:
    {creative}
    
    Output JSON only:
    {{
        "executive_summary": "...",
        "key_objections": ["..."],
        "actionable_fixes": ["..."],
        "rewrite": {{
            "headline": "...",
            "body": "..."
        }}
    }}
    """

# ────────────────────────────────────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────────────────────────────────────
st.title("🧠 The Foolish Synthetic Audience")

st.session_state.setdefault("fg_last_run", None)

# 1. GOLDEN THREAD CHECK
default_creative = ""
if 'draft_for_validation' in st.session_state:
    st.success("✍️ Draft loaded from Creation Tool.")
    default_creative = st.session_state['draft_for_validation']

# 2. INPUTS
c1, c2, c3 = st.columns(3)
with c1:
    p1_uid = st.selectbox("Skeptic", [p['uid'] for p in all_personas_flat], index=0)
with c2:
    p2_uid = st.selectbox("Believer", [p['uid'] for p in all_personas_flat], index=1)
with c3:
    copy_type = st.selectbox("Format", ["Email", "Ads", "Sales Page"])

creative_input = st.text_area("Creative to Test", value=default_creative, height=250)

# 3. RUN LOGIC
if st.button("🚀 Start Debate", type="primary"):
    if not creative_input:
        st.warning("Please enter creative text.")
        st.stop()
        
    p1 = next(p for p in all_personas_flat if p['uid'] == p1_uid)
    p2 = next(p for p in all_personas_flat if p['uid'] == p2_uid)
    
    # We use st.status to show real-time progress
    with st.status("Running Focus Group Simulation...", expanded=True) as status:
        
        # Step 1
        st.write(f"🤔 {p1['core']['name']} (Skeptic) is reading...")
        sys_1 = build_persona_system_prompt(p1['core']) + "\nSTANCE: Skeptical. Look for flaws."
        msg_1 = query_openai([
            {"role": "system", "content": sys_1},
            {"role": "user", "content": f"Review this creative:\n{creative_input}"}
        ])
        st.write("✅ Skeptic has spoken.")
        
        # Step 2
        st.write(f"🤩 {p2['core']['name']} (Believer) is responding...")
        sys_2 = build_persona_system_prompt(p2['core']) + "\nSTANCE: Optimistic. Look for opportunity."
        msg_2 = query_openai([
            {"role": "system", "content": sys_2},
            {"role": "user", "content": f"Review this creative:\n{creative_input}\n\nThe Skeptic said: {msg_1}\nRespond to them."}
        ])
        st.write("✅ Believer has spoken.")
        
        # Step 3
        st.write("👨‍⚖️ Moderator is analyzing the transcript...")
        transcript = f"{p1['core']['name']}: {msg_1}\n{p2['core']['name']}: {msg_2}"
        mod_analysis = query_gemini(moderator_prompt(transcript, creative_input))
        
        status.update(label="Validation Complete! Reloading...", state="complete", expanded=False)

    # Save results
    st.session_state.fg_last_run = {
        "transcript": transcript,
        "analysis": mod_analysis
    }
    st.rerun()

# 4. RESULTS DISPLAY
if st.session_state.fg_last_run:
    st.divider()
    st.subheader("Debate Transcript")
    st.text(st.session_state.fg_last_run["transcript"])
    
    st.divider()
    st.subheader("Moderator Analysis")
    
    an_json = extract_json_object(st.session_state.fg_last_run["analysis"])
    if an_json:
        st.write("**Executive Summary:**", an_json.get("executive_summary"))
        st.write("**Fixes:**")
        for fix in an_json.get("actionable_fixes", []):
            st.write(f"- {fix}")
        
        with st.expander("✨ See Rewrite Suggestion"):
            st.write(an_json.get("rewrite"))
    else:
        st.write(st.session_state.fg_last_run["analysis"])
