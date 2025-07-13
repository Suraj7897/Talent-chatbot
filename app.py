# app.py (Improved with Full Data Awareness)
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
from difflib import get_close_matches
from database import save_to_db, load_from_db, db_table_exists
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

st.set_page_config(page_title="🧠 Talent Intelligence Hub (AI)", page_icon="🧠", layout="wide")

# Session state
for key, default in {
    "df": None,
    "text": "",
    "chat_history": [],
    "last_file_type": None,
    "file_source": "Upload File",
    "file_link_input": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Column inference
def infer_column(query, columns):
    words = re.findall(r'\w+', query.lower())
    best_match = get_close_matches(' '.join(words), columns, n=1, cutoff=0.3)
    if best_match:
        return best_match[0]
    for word in words:
        best_match = get_close_matches(word, columns, n=1, cutoff=0.6)
        if best_match:
            return best_match[0]
    return None

def query_llama(prompt):
    try:
        system_prompt = """
You are an expert AI analyst with strong natural language skills.
- Understand uploaded datasets or documents quickly
- Provide clear, structured, and smart answers in markdown
- Explain insights like a human data analyst would
- Never return code — only human-readable explanations
"""
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
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
            return io.BytesIO(response.content), response.headers.get("Content-Type", "")
    except Exception as e:
        st.warning(f"⚠️ Could not fetch file: {e}")
    return None, None

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
    else:
        st.session_state.text = full_text

# Chat logic
if st.session_state.df is not None:
    df = st.session_state.df
    st.subheader("📊 Uploaded Talent Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("💬 Ask AI about the data")
    user_query = st.text_input("Ask me any question regarding your file")

    if user_query:
        try:
            stats_preview = df.describe(include='all').to_string()
            preview = df.head(10).to_markdown(index=False)
            full_cols = ", ".join(df.columns.tolist())
            total_rows = len(df)

            prompt = f"""
You are analyzing a dataset with {total_rows} rows and the following columns: {full_cols}.

Here is a preview of the first 10 rows:
{preview}

Descriptive statistics:
{stats_preview}

Now answer this user query:
{user_query.strip()}

Please:
- Consider the full dataset even though preview only shows 10 rows.
- Mention any relevant insights from the whole data.
- If useful, suggest pie/bar charts.
- Do not return Python code.
"""

            response = query_llama(prompt)
            st.session_state.chat_history.append((user_query, response))
            save_chat(user_query, response)

            st.markdown(f"""
<div class='chat-box'>
<strong>🧑‍🏫 You:</strong> {user_query}

**🧠 AI:** {response}
</div>
""", unsafe_allow_html=True)

            if any(x in user_query.lower() for x in ["chart", "distribution", "pie", "bar", "graph"]):
                inferred_col = infer_column(user_query, df.columns.tolist())
                if inferred_col:
                    chart_data = df[inferred_col].value_counts()
                    fig, ax = plt.subplots()
                    if "pie" in user_query.lower():
                        ax.pie(chart_data, labels=chart_data.index, autopct='%1.1f%%', startangle=90)
                        ax.axis("equal")
                        ax.set_title(f"{inferred_col.title()} Distribution")
                    elif "bar" in user_query.lower():
                        chart_data.plot(kind='bar', ax=ax)
                        ax.set_title(f"{inferred_col.title()} Count")
                        ax.set_ylabel("Count")
                        ax.set_xlabel(inferred_col.title())
                    st.pyplot(fig)
                else:
                    st.info("ℹ️ Couldn't infer which column to chart. Try mentioning a clearer field like 'Department' or 'Status'.")

        except Exception as e:
            st.warning(f"⚠️ Failed to answer: {e}")

    show_chat_history()

elif st.session_state.text:
    st.subheader("📄 Uploaded Document Preview")
    st.text_area("Extracted Text from File", st.session_state.text[:3000], height=300)

    st.subheader("💬 Ask AI about the document")
    user_query = st.text_input("Ask me any question regarding your file")

    if user_query:
        try:
            prompt = f"""
Document snippet:
{st.session_state.text[:18000]}

Now answer this:
{user_query.strip()}

Give a clear and concise answer using markdown, suggest 2–3 follow-up questions, and do not return code.
"""
            response = query_llama(prompt)
            st.session_state.chat_history.append((user_query, response))
            save_chat(user_query, response)

            st.markdown(f"""
<div class='chat-box'>
<strong>🧑‍🏫 You:</strong> {user_query}

**🧠 AI:** {response}
</div>
""", unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"⚠️ Failed to answer: {e}")

    show_chat_history()

else:
    st.info("🗕 Upload an Excel, PDF, or DOCX file or paste a Drive link to start asking questions.")