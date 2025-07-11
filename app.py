# app.py (Enhanced: Support file link input via Google Drive, OneDrive, Dropbox, Google Sheets)
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def query_llama(prompt):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use NLP to understand the user's intent and give specific, concise answers only."},
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
    st.header("📂 Upload or Link Talent File")
    uploaded_file = st.file_uploader("Upload Excel/CSV/PDF/DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])
    file_link = st.text_input("📌 Or paste Google Drive / Dropbox / OneDrive / Sheets link")

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

if uploaded_file or file_link:
    file_data, content_type = (uploaded_file, None) if uploaded_file else load_file_from_link(file_link)
    if file_data:
        if uploaded_file:
            filename = uploaded_file.name.lower()
        else:
            # Infer file type from content-type
            if "sheet" in content_type:
                filename = "temp.xlsx"
            elif "csv" in content_type:
                filename = "temp.csv"
            elif "pdf" in content_type:
                filename = "temp.pdf"
            elif "word" in content_type:
                filename = "temp.docx"
            else:
                filename = "temp.xlsx"

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
else:
    st.session_state.df = None
    st.session_state.text = ""

df = st.session_state.df
full_text = st.session_state.text

if df is not None:
    st.subheader("📊 Uploaded Talent Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("💬 Ask AI about the data")
    user_query = st.text_input("Ask me any question regarding your file", key="user_query_input")

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
- Use markdown formatting (bullets, **bold**)
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

            chart_placeholder = st.empty()
            matched_column = None
            lowered_query = user_query.lower()

            chart_keywords = ["chart", "graph", "distribution", "pie", "bar"]
            if any(word in lowered_query for word in chart_keywords):
                smart_targets = ["status", "type", "category", "department"]
                for col in df.columns:
                    if any(key in col.lower() for key in smart_targets):
                        matched_column = col
                        break
                if not matched_column:
                    for col in df.columns:
                        if df[col].dtype == "object" or df[col].nunique() < len(df) / 2:
                            matched_column = col
                            break

            if matched_column:
                data = df[matched_column].value_counts()
                labels = [f"{label} ({value} | {value / data.sum() * 100:.1f}%)" for label, value in zip(data.index, data.values)]

                fig, ax = plt.subplots()
                if "pie" in lowered_query:
                    ax.pie(data, labels=labels, startangle=90)
                    ax.set_title(f"Pie Chart: {matched_column.title()} Distribution")
                    ax.axis("equal")
                else:
                    ax.bar(data.index, data.values, color="#4f46e5")
                    ax.set_title(f"Bar Chart: {matched_column.title()} Distribution")
                    ax.set_xlabel(matched_column.title())
                    ax.set_ylabel("Count")
                    plt.xticks(rotation=45)

                chart_placeholder.pyplot(fig)

                chart_buf = io.BytesIO()
                fig.savefig(chart_buf, format='png')
                st.download_button("🗕️ Download Chart", data=chart_buf.getvalue(), file_name="chart.png", mime="image/png")

        except Exception as e:
            st.warning(f"⚠️ Failed to answer: {e}")

    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, "rb") as f:
            st.download_button("⬇️ Export Chat as TXT", data=f, file_name="chat_history.txt")

    show_chat_history()

elif full_text:
    st.subheader("📄 Uploaded Document Preview")
    st.text_area("Extracted Text from File", full_text[:3000])
else:
    st.info("🗕 Upload an Excel, PDF, or DOCX file or paste a Drive link to start asking questions.")
