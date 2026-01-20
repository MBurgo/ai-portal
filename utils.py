import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# --- 1. Shared Styling ---
def apply_branding():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css?family=Oswald:400,700');
    h1, .stTitle { font-family: 'Oswald', sans-serif; color: #f9423a; }
    .stButton>button { background-color: #43b02a; color: white; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Shared Google Sheets Auth ---
def get_gspread_client():
    if "gspread_client" not in st.session_state:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            if "service_account" not in st.secrets:
                st.error("🚨 Secret 'service_account' missing.")
                st.stop()
            
            creds_dict = st.secrets["service_account"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            st.session_state.gspread_client = gspread.authorize(creds)
        except Exception as e:
            st.error(f"🚨 Google Sheets Error: {e}")
            st.stop()
    return st.session_state.gspread_client

# --- 3. Shared OpenAI Auth (UPDATED FOR v1.0+) ---
def configure_openai():
    if "openai" not in st.secrets:
        st.error("🚨 Secret '[openai]' section is missing.")
        st.stop()
    
    # Return a proper Client Instance
    return OpenAI(api_key=st.secrets["openai"]["api_key"])

# --- 4. Shared Gemini Auth ---
def configure_gemini():
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai
    return None
