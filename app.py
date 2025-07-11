# app.py (Improved Pie Chart + Smart Chart Detection + File Switching Fix)
import streamlit as st
import pandas as pd
import io
import os
import fitz  # PyMuPDF
import docx
import re
import datetime
import requests
import mimetypes
import matplotlib.pyplot as plt
from database import save_to_db, load_from_db, db_table_exists
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

st.set_page_config(page_title="🧠 Talent Intelligence Hub (AI)", page_icon="🧠", layout="wide")

if "df" not in st.session_state:
    st.session_state.df = None
if "text" not in st.session_state:
    st.session_state.text = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_file_type" not in st.session_state:
    st.session_state.last_file_type = None
if "file_source" not in st.session_state:
    st.session_state.file_source = "Upload File"
if "file_link_input" not in st.session_state:
    st.session_state.file_link_input = ""

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def query_llama(prompt):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use NLP to understand the user's intent and give specific, clear answers with optional visualizations. Format your response in markdown. Include a pie or bar chart if asked. Only return natural language summaries, never return Python code."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Groq Error: {e}"

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

st.markdown("""
<div class='welcome-banner'>
    <h1>🧠 Talent Intelligence Hub (AI-Powered)</h1>
    <p>Upload your document or paste a link and ask anything — powered by LLaMA3 via Groq</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Choose File Source")
    file_source = st.radio("Select Source", ["Upload File", "Paste Link"], index=0)

    uploaded_file = None
    file_link_input_value = ""

    if file_source == "Upload File":
        uploaded_file = st.file_uploader("Upload Excel/CSV/PDF/DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])
        if uploaded_file:
            st.session_state.file_link_input = ""
    else:
        file_link_input_value = st.text_input("📌 Paste Google Drive / Dropbox / OneDrive / Sheets link", key="file_link_input")
        if file_link_input_value:
            uploaded_file = None

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

def load_file_from_link(link):
    try:
        if "drive.google.com" in link:
            file_id = re.search(r"/d/([\w-]+)|id=([\w-]+)", link)
            file_id = file_id.group(1) if file_id.group(1) else file_id.group(2)
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        elif "dropbox.com" in link:
            download_url = link.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        elif "onedrive.live.com" in link:
            download_url = link.replace("redir?resid=", "download.aspx?resid=").replace("&authkey=", "")
        elif "docs.google.com/spreadsheets" in link:
            sheet_id = re.search(r"/d/([\w-]+)", link).group(1)
            download_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        else:
            download_url = link

        response = requests.get(download_url)
        if response.status_code == 200:
            response.content_type = response.headers.get("Content-Type", "")
            return io.BytesIO(response.content), response.content_type
    except Exception as e:
        st.warning(f"⚠️ Could not fetch file: {e}")
    return None, None

raw_text = None
full_text = ""
df = None

file_data, content_type = None, None

if uploaded_file:
    file_data = uploaded_file
    content_type = mimetypes.guess_type(uploaded_file.name)[0]
    st.session_state.file_link_input = ""
elif st.session_state.file_link_input:
    file_data, content_type = load_file_from_link(st.session_state.file_link_input)
    uploaded_file = None

if file_data:
    filename = uploaded_file.name.lower() if uploaded_file else "temp.xlsx"
    if content_type and "sheet" in content_type:
        filename = "temp.xlsx"
    elif content_type and "csv" in content_type:
        filename = "temp.csv"
    elif content_type and "pdf" in content_type:
        filename = "temp.pdf"
    elif content_type and "word" in content_type:
        filename = "temp.docx"

    if filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_data)
    elif filename.endswith(".csv"):
        df = pd.read_csv(file_data)
    elif filename.endswith(".pdf"):
        doc = fitz.open(stream=file_data.read(), filetype="pdf")
        full_text = "\n".join([page.get_text() for page in doc])
    elif filename.endswith(".docx"):
        doc = docx.Document(file_data)
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

df = st.session_state.df
full_text = st.session_state.text

if df is not None:
    st.subheader("📊 Uploaded Talent Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("💬 Ask AI about the data")
    user_query = st.text_input("Ask me any question regarding your file")

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
- Give a helpful summary in markdown
- If the question is about quantity or grouping, create a pie or bar chart using Streamlit
- Conclude with 2–3 follow-up questions the user can ask next
Only return natural language answers — never include Python code in your response.
"""
            response = query_llama(prompt)
            st.session_state.chat_history.append((user_query, response))
            save_chat(user_query, response)

            st.markdown(f"""
<div class='chat-box'>
<strong>🧑‍🏬 You:</strong> {user_query}

**🧠 AI:** {response}
</div>
""", unsafe_allow_html=True)

            if any(chart in user_query.lower() for chart in ["pie chart", "bar chart"]):
                matched_cols = [col for col in df.columns if df[col].nunique() < 20 and df[col].dtype == "object"]
                if matched_cols:
                    col = matched_cols[0]
                    chart_data = df[col].value_counts()
                    fig, ax = plt.subplots()
                    if "pie" in user_query.lower():
                        ax.pie(chart_data, labels=chart_data.index, autopct='%1.1f%%', startangle=90)
                        ax.axis('equal')
                    elif "bar" in user_query.lower():
                        chart_data.plot(kind='bar', ax=ax)
                        ax.set_ylabel("Count")
                        ax.set_xlabel(col.title())
                    st.pyplot(fig)

        except Exception as e:
            st.warning(f"⚠️ Failed to answer: {e}")

    show_chat_history()

elif full_text:
    st.subheader("📄 Uploaded Document Preview")
    st.text_area("Extracted Text from File", full_text[:3000], height=300)

    st.subheader("💬 Ask AI about the document")
    user_query = st.text_input("Ask me any question regarding your file")

    if user_query:
        try:
            prompt = f"""
You are a helpful assistant. A user uploaded a document and asked a question.

Document snippet:
{full_text[:18000]}

Now answer this:
{user_query.strip()}

Please:
- Give a clear and concise answer
- Use markdown if needed
- Suggest 2–3 follow-up questions the user can explore next
Only return natural language answers — never include Python code in your response.
"""
            response = query_llama(prompt)
            st.session_state.chat_history.append((user_query, response))
            save_chat(user_query, response)

            st.markdown(f"""
<div class='chat-box'>
<strong>🧑‍🏬 You:</strong> {user_query}

**🧠 AI:** {response}
</div>
""", unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"⚠️ Failed to answer: {e}")

    show_chat_history()

else:
    st.info("🗕 Upload an Excel, PDF, or DOCX file or paste a Drive link to start asking questions.")