# app.py (Updated with Pie/Bar Chart + Download Support + Auto Chart Detection)
import streamlit as st
import pandas as pd
import io
import os
import fitz  # PyMuPDF
import docx
import re
import datetime
import requests
import matplotlib.pyplot as plt
from database import save_to_db, load_from_db, db_table_exists
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

st.set_page_config(page_title="🤖 Talent Intelligence Hub (AI)", page_icon="🧠", layout="wide")

# Initialize session state
if "df" not in st.session_state:
    st.session_state.df = None
if "text" not in st.session_state:
    st.session_state.text = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Load API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

def query_llama(prompt):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Groq Error: {e}"

# UI Styling
st.markdown("""
<style>
    .main { background-color: #f4f8fb; }
    .stButton>button { background-color: #2563eb; color: white; border-radius: 5px; font-weight: 600; }
    .stDownloadButton>button { background-color: #10b981; color: white; font-weight: 600; border-radius: 8px; }
    .welcome-banner {
        background: linear-gradient(to right, #1e3a8a, #2563eb);
        padding: 2rem; border-radius: 10px; color: white; text-align: center;
    }
    .chat-box {
        background-color: white; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class='welcome-banner'>
    <h1>🤖 Talent Intelligence Hub (AI-Powered)</h1>
    <p>Upload your document and ask anything — powered by LLaMA3 via Groq</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📂 Upload Talent File")
    uploaded_file = st.file_uploader("Upload Excel/CSV/PDF/DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])

# Chat Log
CHAT_LOG_FILE = "chat_log.txt"
def save_chat(query, response):
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as log:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"[{now}]\nQ: {query}\nA: {response}\n\n")

def show_chat_history():
    if os.path.exists(CHAT_LOG_FILE):
        with st.expander("🕘 Chat History"):
            with open(CHAT_LOG_FILE, "r", encoding="utf-8") as log:
                st.text_area("Chat Log", value=log.read(), height=300)

# File Processing
raw_text = None
full_text = ""
df = None
if uploaded_file:
    filename = uploaded_file.name.lower()
    if filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    elif filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith(".pdf"):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = "\n".join([page.get_text() for page in doc])
    elif filename.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        full_text = "\n".join([para.text for para in doc.paragraphs])

    if df is not None:
        df.columns = df.columns.str.strip().str.lower()
        save_to_db(df)
        st.session_state.df = df
        st.session_state.text = ""
        st.session_state.chat_history = []
    else:
        st.session_state.df = None
        st.session_state.text = full_text
        st.session_state.chat_history = []
else:
    st.session_state.df = None
    st.session_state.text = ""

# -------------------- MAIN UI -------------------- #
df = st.session_state.df
full_text = st.session_state.text

if df is not None:
    st.subheader("📊 Uploaded Talent Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("💬 Ask AI about the data")
    user_query = st.text_input("Ask a question like 'How many completed SEER training?'", key="user_query_input")

    if user_query:
        try:
            snippet = df.to_markdown(index=False)[:18000]
            prompt = f"""
You are a helpful assistant. A user has uploaded a dataset and asked a question.

Here is a preview of the data:
{snippet}

Now answer this:
{user_query.strip()}

Please:
- Provide exact counts when applicable
- Mention relevant names or departments
- Use markdown formatting (bullets, bold)
- Suggest a chart (if useful)
"""
            response = query_llama(prompt)
            st.session_state.chat_history.append((user_query, response))
            save_chat(user_query, response)
            st.markdown(response)

            # Chart rendering based on query
            chart_placeholder = st.empty()
            col_match = None
            if any(x in user_query.lower() for x in ["pie chart", "distribution", "percentage"]):
                col_match = [col for col in df.columns if "department" in col.lower() or "category" in col.lower()]
                if col_match:
                    data = df[col_match[0]].value_counts()
                    fig, ax = plt.subplots()
                    ax.pie(data, labels=data.index, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    chart_placeholder.pyplot(fig)

            elif any(x in user_query.lower() for x in ["bar chart", "comparison", "count"]):
                col_match = [col for col in df.columns if "department" in col.lower() or "role" in col.lower()]
                if col_match:
                    data = df[col_match[0]].value_counts()
                    fig, ax = plt.subplots()
                    ax.bar(data.index, data.values, color="#4f46e5")
                    ax.set_xlabel(col_match[0].capitalize())
                    ax.set_ylabel("Count")
                    ax.set_title("Bar Chart")
                    plt.xticks(rotation=45)
                    chart_placeholder.pyplot(fig)

            if col_match:
                # Chart download button
                chart_buf = io.BytesIO()
                fig.savefig(chart_buf, format='png')
                st.download_button("📥 Download Chart", data=chart_buf.getvalue(), file_name="chart.png", mime="image/png")

        except Exception as e:
            st.warning(f"⚠️ Failed to answer: {e}")

    for i, (q, a) in enumerate(reversed(st.session_state.chat_history)):
        with st.container():
            st.markdown(f"""
<div class='chat-box'>
<strong>🧑‍💼 You:</strong> {q}

**🤖 AI:** {a}
</div>
""", unsafe_allow_html=True)

    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, "rb") as f:
            st.download_button("⬇️ Export Chat as TXT", data=f, file_name="chat_history.txt")

    show_chat_history()

elif full_text:
    st.subheader("📄 Uploaded Document Preview")
    st.text_area("Extracted Text from File", full_text[:3000])
else:
    st.info("📥 Upload an Excel, PDF, or DOCX file to start asking questions.")
