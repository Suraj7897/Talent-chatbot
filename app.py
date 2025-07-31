import streamlit as st
import pandas as pd
import io
import os
import re
import datetime
import requests
import matplotlib.pyplot as plt
from difflib import get_close_matches
import fitz  # PyMuPDF
import docx
from dotenv import load_dotenv
from groq import Groq

# --- Load Environment Variables and API Key ---
load_dotenv()
st.set_page_config(page_title="🧠 Talent Intelligence Hub (AI)", page_icon="🧠", layout="wide")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is not set. Please add it to your .env file to proceed.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# --- Session State Initialization ---
for key, default in {
    "df": None,
    "text": "",
    "chat_history": [],
    "file_source": "Upload File",
    "file_link_input": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- AI and Data Processing Functions ---
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

def query_llama(prompt, chat_history):
    try:
        system_prompt = """
You are an expert AI analyst with strong natural language skills.
- Analyze the FULL uploaded dataset or document, not just a sample.
- Provide clear, structured, and smart answers in markdown format.
- Explain insights as a human data analyst would.
- Never return Python code — only human-readable explanations and insights.
- If asked about a person or topic not found, say so clearly.
"""
        messages = [{"role": "system", "content": system_prompt.strip()}]
        for user_msg, ai_msg in chat_history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_msg})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model="llama3-8b-8192", messages=messages)
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Groq Error: {e}"

# --- UI Styling ---
st.markdown("""
<style>
    body, .main { background-color: #f4f8fb !important; color: #1f2937; }
    .stApp { background-color: #f4f8fb; }
    .stTextInput > div > div > input, .stTextArea > div > textarea { background-color: white; color: #111827; border-radius: 8px; }
    .stButton>button { background-color: #2563eb; color: white; border-radius: 8px; font-weight: 600; border: none; }
    .stDownloadButton>button { background-color: #10b981; color: white; font-weight: 600; border-radius: 8px; border: none; }
    .welcome-banner { background: linear-gradient(to right, #1e3a8a, #2563eb); padding: 2rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem; }
    .chat-box { background-color: white; color: #111827; border-radius: 10px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class='welcome-banner'>
    <h1>🧠 Talent Intelligence Hub (AI-Powered)</h1>
    <p>Upload your document or paste a link and ask anything — powered by LLaMA3 via Groq</p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar File Input ---
with st.sidebar:
    st.header("📂 Choose File Source")
    file_source = st.radio("Select Source", ["Upload File", "Paste Link"], key="file_source_selector")
    uploaded_file = None
    if file_source == "Upload File":
        uploaded_file = st.file_uploader("Upload Excel, CSV, PDF, or DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])
    else:
        file_link_input = st.text_input("📌 Paste a public link (e.g., Google Drive, Dropbox)", key="file_link_input")
        if file_link_input:
            try:
                r = requests.get(file_link_input)
                if r.status_code == 200:
                    file_data = io.BytesIO(r.content)
                    file_data.name = file_link_input.split("/")[-1]
                    uploaded_file = file_data
            except:
                st.error("Could not load file from link.")

# --- File Processing ---
@st.cache_data
def process_file(file_object):
    filename = file_object.name.lower()
    df, text = None, ""
    try:
        if filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_object)
        elif filename.endswith(".csv"):
            df = pd.read_csv(file_object)
        elif filename.endswith(".pdf"):
            with fitz.open(stream=file_object.read(), filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
        elif filename.endswith(".docx"):
            doc = docx.Document(file_object)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if df is not None:
            df.columns = [col.strip().replace(" ", "_") for col in df.columns]
        return df, text
    except Exception as e:
        st.error(f"❌ File processing error: {e}")
        return None, ""

if uploaded_file:
    df, text = process_file(uploaded_file)
    st.session_state.df = df
    st.session_state.text = text

# --- Main Chat Interface ---
# --- Main Chat Interface ---
if st.session_state.df is not None:
    df = st.session_state.df
    st.subheader("📊 Uploaded Data Preview")
    st.dataframe(df.head(), use_container_width=True)

    st.subheader("💬 Ask Anything About the Data")
    query = st.text_input("Ask a question about the uploaded dataset", key="data_query")
    
    if query:
        # --- START OF THE FIX V2 ---
        # Create a more efficient summary to avoid exceeding the API token limit.
        column_summary = {}
        for col in df.columns:
            if df[col].dtype == 'object':
                unique_values = df[col].nunique()
                # If a column has too many unique values, only show the top 5.
                if unique_values > 50:
                    column_summary[col] = {
                        "summary_type": "High Cardinality",
                        "unique_values_count": unique_values,
                        "top_5_values": df[col].value_counts().head(5).to_dict()
                    }
                else:
                    # Otherwise, show all value counts.
                    column_summary[col] = df[col].value_counts().to_dict()
            else:
                # Numeric columns are summarized as before.
                column_summary[col] = {
                    "mean": df[col].mean(),
                    "min": df[col].min(),
                    "max": df[col].max(),
                    "non_null_count": df[col].count()
                }

        # Create the robust prompt with the efficient data summary.
        prompt = f"""
You are an expert data analyst. Your task is to analyze a dataset based on the following JSON summary and answer the user's question.

- The dataset has {len(df)} rows.
- **NEVER** make up information. Only use the data provided in the summary below.
- For columns with many unique values, a summary is provided instead of a full list.
- If the answer isn't in the data, state that clearly.

**Data Summary:**
{column_summary}

**User's Question:**
{query}
"""
        # --- END OF THE FIX V2 ---

        answer = query_llama(prompt, st.session_state.chat_history)
        st.session_state.chat_history.append((query, answer))
        
        # Display chat history
        st.markdown(f"""
        <div class='chat-box'>
            <p><strong>You:</strong> {query}</p><hr>
            <p><strong>🧠 AI Analyst:</strong></p>{answer}
        </div>
        """, unsafe_allow_html=True)

        # Charting logic (remains the same)
        if any(x in query.lower() for x in ["chart", "distribution", "pie", "bar", "plot"]):
            inferred = infer_column(query, df.columns.tolist())
            if inferred and inferred in df.columns and pd.api.types.is_string_dtype(df[inferred]):
                try:
                    st.success(f"Found column **'{inferred}'** to generate a chart.")
                    chart_data = df[inferred].value_counts()
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    if "pie" in query.lower():
                        # For pie charts, it's better to show fewer slices
                        chart_data = chart_data.head(10)
                        ax.pie(chart_data, labels=chart_data.index, autopct='%1.1f%%', startangle=90)
                        ax.set_title(f"Distribution of '{inferred}' (Top 10)")
                        ax.axis("equal")
                    else:
                        # For bar charts, we can show more categories
                        chart_data = chart_data.head(20)
                        chart_data.plot(kind='bar', ax=ax, color='#2563eb')
                        ax.set_title(f"Value Counts for '{inferred}' (Top 20)")
                        ax.set_ylabel("Count")
                        ax.set_xlabel(inferred)
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()

                    st.pyplot(fig)
                except Exception as e:
                    st.error(f"Could not generate chart for '{inferred}'. Error: {e}")

elif st.session_state.text:
    st.subheader("📄 Uploaded Document Preview")
    st.text_area("Extracted Text", st.session_state.text[:3000], height=300)
    st.subheader("💬 Ask Anything About the Document")
    query = st.text_input("Ask a question about the document", key="doc_query")
    if query:
        prompt = f"""You are an expert document analyst. Please answer the following question based ONLY on the document provided.

Document Content (partial):
{st.session_state.text[:18000]}

Question:
{query}"""
        answer = query_llama(prompt, st.session_state.chat_history)
        st.session_state.chat_history.append((query, answer))
        st.markdown(f"""
        <div class='chat-box'>
            <p><strong>You:</strong> {query}</p><hr>
            <p><strong>🧠 AI Analyst:</strong></p>{answer}
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("📄 Please upload a file or paste a public link to begin.")