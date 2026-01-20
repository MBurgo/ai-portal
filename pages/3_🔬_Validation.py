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
configure_gemini() # Sets up Google GenAI if key exists
configure_openai() # Sets up OpenAI

# 2. HELPER FUNCTIONS (Preserved from your original code)
DASH_CHARS = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

def normalize_dashes(s: str) -> str:
    return re.sub(f"[{DASH_CHARS}]", "-", s or "")

def slugify(s: str) -> str:
    s = normalize_dashes(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")

def _ensure_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _ensure_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []

def word_count(text: str) -> int:
    if not text: return 0
    return len(re.findall(r"\S+", text))

def estimate_tokens(text: str) -> int:
    return int(word_count(text) * 1.45)

def truncate_words(text: str, max_words: int) -> str:
    if not text: return ""
    words = re.findall(r"\S+", text)
    if len(words) <= max_words: return text
    return " ".join(words[:max_words]).strip()

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

def claim_risk_flags(text: str) -> List[str]:
    if not text or not text.strip(): return []
    t = text.lower()
    patterns = {
        "Guaranteed": ["guaranteed", "can't lose", "risk-free", "100%"],
        "Urgency": ["act now", "limited time", "today only", "last chance"],
        "Hype": ["will double", "next nvidia", "explosive"],
        "Absolutes": ["always", "never", "everyone", "no one"],
    }
    hits = []
    for label, toks in patterns.items():
        if any(tok in t for tok in toks): hits.append(label)
    return hits

def safe_option(default: str, options: List[str]) -> str:
    return default if default in options else options[0]

# --- AI WRAPPERS ---
def query_openai(messages, model="gpt-4o", temperature=0.7):
    try:
        import openai
        resp = openai.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def query_gemini(prompt):
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Fallback to OpenAI if Gemini fails or isn't set up
        return query_openai([{"role": "user", "content": prompt}])

# ────────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_personas():
    # Look for personas.json in the root directory (parent of 'pages')
    root_path = Path(__file__).resolve().parent.parent / "personas.json"
    if not root_path.exists():
        # Fallback to current directory
        root_path = Path("personas.json")
    
    if not root_path.exists():
        return [], []

    with open(root_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Simplified loader assuming new schema
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
# SESSION STATE
# ────────────────────────────────────────────────────────────────────────────────
st.session_state.setdefault("chat_history", {})
st.session_state.setdefault("selected_persona_uid", None)
st.session_state.setdefault("fg_last_run", None)

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

def participant_task(copy_type):
    return (
        "Answer in 4 bullets:\n1) Click/Read or Ignore?\n2) Credibility reaction\n3) Biggest doubt\n4) One fix"
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

tab1, tab2 = st.tabs(["🗣️ Individual Interview", "⚔️ Focus Group Debate"])

# --- TAB 1: INDIVIDUAL ---
with tab1:
    st.subheader("Interview a Persona")
    
    # Selection
    cols = st.columns(3)
    for i, p in enumerate(all_personas_flat):
        with cols[i % 3]:
            if st.button(f"{p['core']['name']}\n({p['segment_label']})", key=f"sel_{p['uid']}"):
                st.session_state.selected_persona_uid = p['uid']
    
    if st.session_state.selected_persona_uid:
        p_data = next((p for p in all_personas_flat if p['uid'] == st.session_state.selected_persona_uid), None)
        st.info(f"Talking to: **{p_data['core']['name']}**")
        
        # Chat
        uid = p_data['uid']
        if uid not in st.session_state.chat_history: st.session_state.chat_history[uid] = []
        
        for q, a in st.session_state.chat_history[uid]:
            st.markdown(f"**You:** {q}")
            st.markdown(f"**{p_data['core']['name']}:** {a}")
            st.divider()
            
        q_input = st.text_input("Ask a question:", key="q_individual")
        if st.button("Ask", key="btn_ask_ind"):
            if q_input:
                sys = build_persona_system_prompt(p_data['core'])
                ans = query_openai([
                    {"role": "system", "content": sys},
                    {"role": "user", "content": q_input}
                ])
                st.session_state.chat_history[uid].append((q_input, ans))
                st.rerun()

# --- TAB 2: FOCUS GROUP (THE GOLDEN THREAD) ---
with tab2:
    st.header("⚔️ Focus Group Debate")
    
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
        
        with st.status("Running Simulation...", expanded=True) as status:
            
            # Turn 1: Skeptic
            st.write(f"🤔 {p1['core']['name']} is reviewing...")
            sys_1 = build_persona_system_prompt(p1['core']) + "\nSTANCE: Skeptical. Look for flaws."
            msg_1 = query_openai([
                {"role": "system", "content": sys_1},
                {"role": "user", "content": f"Review this creative:\n{creative_input}"}
            ])
            
            # Turn 2: Believer
            st.write(f"🤩 {p2['core']['name']} is reviewing...")
            sys_2 = build_persona_system_prompt(p2['core']) + "\nSTANCE: Optimistic. Look for opportunity."
            msg_2 = query_openai([
                {"role": "system", "content": sys_2},
                {"role": "user", "content": f"Review this creative:\n{creative_input}\n\nThe Skeptic said: {msg_1}\nRespond to them."}
            ])
            
            # Turn 3: Moderator
            st.write("👨‍⚖️ Moderator is analyzing...")
            transcript = f"{p1['core']['name']}: {msg_1}\n{p2['core']['name']}: {msg_2}"
            mod_analysis = query_gemini(moderator_prompt(transcript, creative_input))
            
            status.update(label="Validation Complete", state="complete", expanded=False)

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
        
        # Try to parse JSON, else show raw
        try:
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
        except:
            st.write(st.session_state.fg_last_run["analysis"])
            
        # LOOP BACK TO CREATION
        st.divider()
        if st.button("🔄 Send Feedback to Copywriter"):
             st.info("Feedback loop coming in v2!")
