import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Load environment variables
load_dotenv()

# Fetch Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
   GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# FIREBASE INITIALIZATION (SAFE SECRETS / FILE PATH)
# ==========================================
db = None

if not firebase_admin._apps:
    try:
        # 1. First check if Firebase credentials exist in Streamlit Secrets (for Cloud Deployment)
        if "FIREBASE_CREDENTIALS" in st.secrets:
            cred_dict = dict(st.secrets["FIREBASE_CREDENTIALS"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
        else:
            # 2. Fallback to local json file (for Local Development)
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            KEY_PATH = os.path.join(BASE_DIR, "firebase_key.json")
            if not os.path.exists(KEY_PATH):
                KEY_PATH = os.path.join(BASE_DIR, "firebase_key.json.json")

            if os.path.exists(KEY_PATH):
                cred = credentials.Certificate(KEY_PATH)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
            else:
                st.warning("⚠️ Firebase credentials not configured in Streamlit Secrets or local file.")
    except Exception as e:
        st.error(f"Error initializing Firebase: {e}")
else:
    db = firestore.client()

# Page Configuration
st.set_page_config(
    page_title="Internee.pk AI Tutor", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CUSTOM CSS FOR PROFESSIONAL BLUE THEME
# ==========================================
st.markdown("""
<style>
    /* Main Background & Fonts */
    .main {
        background-color: #f8f9fa;
        font-family: 'Inter', sans-serif;
    }
    
    /* Primary Color Overrides */
    :root {
        --primary-color: #1e3c72 !important;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }
    .main-header p {
        color: #e0e6ed;
        margin-top: 5px;
        font-size: 1rem;
    }

    /* Badge Pills */
    .badge-container {
        display: flex;
        gap: 12px;
        margin-top: 12px;
    }
    .badge {
        background: rgba(255, 255, 255, 0.2);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        backdrop-filter: blur(5px);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* Sidebar Customization */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    
    /* Custom Blue Radio Buttons & Selections */
    div[role="radiogroup"] label[data-baseweb="radio"] div[aria-checked="true"] {
        background-color: #1e3c72 !important;
    }

    /* Custom Blue Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%) !important;
        box-shadow: 0 4px 10px rgba(30, 60, 114, 0.3) !important;
    }

    /* Custom Blue Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%) !important;
        box-shadow: 0 4px 10px rgba(30, 60, 114, 0.3) !important;
    }

    /* Chat Message Styling */
    .stChatMessage {
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# SIDEBAR SETUP
# ==========================================
st.sidebar.title("Control Panel")
st.sidebar.caption("Personalized Learning Settings")

# 1. Mode Switcher
app_mode = st.sidebar.radio(
    " Choose Feature Mode:",
    [" AI Chat Tutor", " Smart Quiz Generator"]
)

st.sidebar.divider()

# 2. Domain Selection
domain = st.sidebar.selectbox(
    " Select Learning Track:",
    ["Data Science & AI", "Python Programming", "Web Development", "Machine Learning", "Cyber Security"]
)

# 3. Difficulty Level
difficulty = st.sidebar.radio(
    " Select Skill Level:",
    ["Beginner", "Intermediate", "Advanced"]
)

st.sidebar.divider()

# 4. SECURE DOWNLOAD NOTES GENERATOR
chat_export = f"=========================================\n"
chat_export += f"       INTERNEE.PK STUDY NOTES          \n"
chat_export += f"=========================================\n"
chat_export += f"Track: {domain}\nLevel: {difficulty}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
chat_export += f"-----------------------------------------\n\n"

if st.session_state.messages:
    for msg in st.session_state.messages:
        role = "Student" if msg["role"] == "user" else "AI Smart Tutor"
        content = msg['content']
        
        # Security sanitization: Remove API keys if present
        if GEMINI_API_KEY and GEMINI_API_KEY in content:
            content = content.replace(GEMINI_API_KEY, "[REDACTED_API_KEY]")
        
        chat_export += f"[{role}]:\n{content}\n\n" + "-"*40 + "\n\n"
else:
    chat_export += "No active conversation history found yet.\n"

st.sidebar.download_button(
    label="📥 Download Study Notes",
    data=chat_export,
    file_name=f"Internee_Notes_{domain.replace(' ', '_')}.txt",
    mime="text/plain",
    use_container_width=True
)

# 5. Clear Conversation Button
if st.sidebar.button("🗑️ Clear Conversation", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# ==========================================
# MAIN DASHBOARD HEADER
# ==========================================
db_status = "Connected" if db else "Disconnected"
st.markdown(f"""
<div class="main-header">
    <h1>🎓 Internee.pk Smart AI Tutor</h1>
    <p>Your interactive personalized learning workspace</p>
    <div class="badge-container">
        <span class="badge"> Track: {domain}</span>
        <span class="badge"> Level: {difficulty}</span>
        <span class="badge">⚙️ Mode: {app_mode.split()[1]}</span>
        <span class="badge">🔥 DB: {db_status}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# FEATURE MODES
# ==========================================

# ------------------------------------------
# MODE 1: CHAT TUTOR
# ------------------------------------------
if app_mode == " AI Chat Tutor":
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question or enter a topic..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("AI Tutor is thinking..."):
                try:
                    system_instruction = f"""
                    You are a highly skilled Smart AI Tutor at Internee.pk.
                    User's current Track/Domain: {domain}
                    User's Skill Level: {difficulty}

                    Rules for response:
                    1. Keep explanations clear, engaging, and tailored specifically to the {difficulty} level.
                    2. Provide formatted markdown code blocks with helpful comments for programming examples.
                    3. Always conclude with 📌 Key Takeaways and a 🏋️ Practice Challenge.
                    4. Respond in professional English unless explicitly asked otherwise by the user.
                    """

                    full_prompt = f"{system_instruction}\n\nUser Query: {prompt}"

                    model = genai.GenerativeModel('gemini-3.8-flash')
                    response = model.generate_content(full_prompt)
                    
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})

                    # Save to Firebase Firestore
                    if db:
                        try:
                            db.collection("chat_history").add({
                                "user_query": prompt,
                                "ai_response": response.text,
                                "domain": domain,
                                "difficulty": difficulty,
                                "timestamp": datetime.now()
                            })
                        except Exception as db_err:
                            st.caption(f"Note: Firebase sync issue: {db_err}")

                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "Quota" in err_msg:
                        st.warning("⚠️ Free tier limit reached. Please wait 30 seconds before retrying.")
                    else:
                        st.error(f"An error occurred: {err_msg}")

# ------------------------------------------
# MODE 2: QUIZ GENERATOR
# ------------------------------------------
elif app_mode == " Smart Quiz Generator":
    st.subheader(f"⚡ Practice Quiz for {domain} ({difficulty})")
    st.write("Click the 'Generate New Quiz' button below to test your knowledge.")

    if st.button(" Generate New Quiz"):
        with st.spinner("Generating personalized quiz..."):
            try:
                quiz_prompt = f"""
                You are an AI Examiner at Internee.pk.
                Topic Track: {domain}
                Difficulty Level: {difficulty}

                Task:
                Generate 3 Multiple Choice Questions (MCQs).
                Each question must have 4 options (A, B, C, D).
                Include an 'Answer Key' section at the end.
                Format everything in clean markdown.
                Respond in English.
                """
                
                model = genai.GenerativeModel('gemini-3.8-flash')
                quiz_response = model.generate_content(quiz_prompt)
                
                st.markdown(quiz_response.text)

                # Save Quiz to Firebase Firestore
                if db:
                    try:
                        db.collection("quiz_history").add({
                            "quiz_content": quiz_response.text,
                            "domain": domain,
                            "difficulty": difficulty,
                            "timestamp": datetime.now()
                        })
                    except Exception as db_err:
                        st.caption(f"Note: Firebase sync issue: {db_err}")

            except Exception as e:
                st.error(f"Error generating quiz: {e}")