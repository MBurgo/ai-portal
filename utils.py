import streamlit as st
import openai
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
            # Check if secrets exist
            if "service_account" not in st.secrets:
                st.error("🚨 Secret 'service_account' missing. Please check secrets.toml.")
                st.stop()
                
            creds_dict = st.secrets["service_account"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            st.session_state.gspread_client = gspread.authorize(creds)
        except Exception as e:
            st.error(f"🚨 Google Sheets Error: {e}")
            st.stop()
    return st.session_state.gspread_client

# --- 3. Shared OpenAI Auth ---
def configure_openai():
    # Debugging: Check if the key exists
    if "openai" not in st.secrets:
        st.error("🚨 Secret '[openai]' section is missing.")
        # Print available keys to help debug (safe keys only)
        st.write("Available Top-Level Keys:", list(st.secrets.keys()))
        st.stop()
        
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        return openai
    except KeyError:
        st.error("🚨 Secret found [openai], but 'api_key' is missing inside it.")
        st.stop()

# --- 4. Shared Gemini Auth ---
def configure_gemini():
    # We check if the key exists, but don't stop the app if it doesn't (optional)
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai
    return None
