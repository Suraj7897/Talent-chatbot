# app.py (Enhanced ChatGPT-style Talent Intelligence App)

import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import docx
import os
import io
import re
import datetime
import time
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from database import save_to_db, load_from_db, db_table_exists
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

# ----- Streamlit Config -----
st.set_page_config(page_title="🤖 Talent Intelligence Hub", page_icon="🧠", layout="wide")

if "df" not in st.session_state: st.session_state.df = None
if "text" not in st.session_state: st.session_state.text = ""
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# ----- Styling -----
st.markdown("""
<style>
    .main { background-color: #f4f8fb; }
    .stButton>button, .stDownloadButton>button {
        font-weight: 600; border-radius: 8px; color: white;
    }
    .stButton>button { background-color: #2563eb; }
    .stDownloadButton>button { background-color: #10b981; }
    .welcome-banner {
        background: linear-gradient(to right, #1e3a8a, #2563eb);
        padding: 2rem; border-radius: 10px; color: white; text-align: center;
    }
    .chat-box {
        background-color: white; border-radius: 10px; padding: 1rem;
        margin-bottom: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='welcome-banner'>
    <h1>🤖 Talent Intelligence Hub (AI-Powered)</h1>
    <p>Upload your file and ask anything — powered by LLaMA3 via Groq</p>
</div>
""", unsafe_allow_html=True)

# ----- Sidebar -----
with st.sidebar:
    st.header("📂 Upload Talent File")
    uploaded_file = st.file_uploader("Upload Excel/CSV/PDF/DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])
    model_choice = st.radio("🤖 Choose LLM Engine", ["Groq (LLaMA3)", "OpenAI GPT (Coming Soon)", "Ollama (Local - Coming Soon)"])

# ----- Chat Log File -----
CHAT_LOG_FILE = "chat_log.txt"

def save_chat(q, a):
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}]\nQ: {q}\nA: {a}\n\n")

def show_chat_history():
    if os.path.exists(CHAT_LOG_FILE):
        with st.expander("🕘 Chat History"):
            with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
                st.text_area("Chat Log", f.read(), height=300)

# ----- File Processing -----
raw_text = ""
df = None
if uploaded_file:
    filename = uploaded_file.name.lower()
    if filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    elif filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith(".pdf"):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        raw_text = "\n".join([page.get_text() for page in doc])
    elif filename.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        raw_text = "\n".join([para.text for para in doc.paragraphs])

    if df is not None:
        df.columns = df.columns.str.strip().str.lower()
        save_to_db(df)
        st.session_state.df = df
        st.session_state.text = ""
        st.session_state.chat_history = []
    else:
        st.session_state.df = None
        st.session_state.text = raw_text
        st.session_state.chat_history = []

# ----- LLM Logic -----
def query_groq(prompt):
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Groq Error: {e}"

def run_llm(prompt):
    if model_choice.startswith("Groq"):
        return query_groq(prompt)
    elif model_choice.startswith("OpenAI"):
        return "🔒 OpenAI GPT integration coming soon"
    elif model_choice.startswith("Ollama"):
        return "🔒 Local Ollama model coming soon"
    else:
        return "❓ Unknown LLM selected"

# ----- Main Chat UI -----
df = st.session_state.df
text = st.session_state.text

if df is not None:
    st.subheader("📊 Uploaded Talent Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("💬 Ask AI about the data")
    user_query = st.text_input("Ask a question like: 'How many completed SEER training?'")

    if user_query:
        preview = df.to_markdown(index=False)[:18000]
        prompt = f"""You are a helpful assistant. A user has uploaded a dataset and asked a question.

Here is a preview of the data:
{preview}

Now answer this:
{user_query.strip()}

Instructions:
- Give exact numbers
- Mention names or departments if relevant
- Use **markdown**
- Suggest a chart if useful
"""
        start = time.time()
        ai_response = run_llm(prompt)
        elapsed = time.time() - start

        st.session_state.chat_history.append((user_query, ai_response))
        save_chat(user_query, ai_response)

        st.info(f"⚡ Response generated in {elapsed:.2f} seconds")

    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"""
<div class='chat-box'>
<strong>🧑‍💼 You:</strong> {q}

**🤖 AI:** {a}
</div>
""", unsafe_allow_html=True)

        # Auto-detect and render simple charts
        if "bar chart" in a.lower() and df is not None:
            st.subheader("📊 Suggested Bar Chart")
            try:
                fig, ax = plt.subplots()
                df.iloc[:, 0].value_counts().plot(kind='bar', ax=ax)
                st.pyplot(fig)
            except Exception as e:
                st.warning(f"❌ Couldn't render chart: {e}")

    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, "rb") as f:
            st.download_button("⬇️ Download Chat Log", data=f, file_name="chat_history.txt")

    show_chat_history()

elif text:
    st.subheader("📄 Document Preview")
    st.text_area("Extracted Text from File", text[:3000])
else:
    st.info("📥 Upload a document or spreadsheet to get started.")
