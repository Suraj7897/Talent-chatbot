# app.py (Bug-fixed version with dynamic file reload support)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
import fitz  # PyMuPDF for PDF
import docx
from dotenv import load_dotenv
from database import save_to_db, load_from_db, db_table_exists
import re
import datetime

load_dotenv()

st.set_page_config(page_title="🌟 Talent Intelligence Hub", page_icon="📊", layout="wide")

# Inject CSS styles
st.markdown("""
    <style>
    .main { background-color: #f4f8fb; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .stButton>button { background-color: #0066cc; color: white; border-radius: 5px; font-weight: 600; }
    .stDownloadButton>button {
        background-color: #34d399;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        border: 2px solid #059669;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        font-size: 1rem;
        margin-top: 1rem;
        transition: all 0.3s ease-in-out;
    }
    .stDownloadButton>button:hover {
        background-color: #10b981;
        transform: scale(1.03);
    }
    .stTextInput>div>input, .stTextArea textarea { border-radius: 5px; border: 1px solid #ccc; }
    .welcome-banner {
        background: linear-gradient(to right, #003366, #006699);
        padding: 2rem; border-radius: 10px; color: white; text-align: center;
    }
    .sidebar-upload {
        background-color: #ffffff; padding: 1rem; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='welcome-banner'>
    <h1>👋 Welcome to the Talent Intelligence Hub</h1>
    <p>Empowering decisions through smart talent insights</p>
</div>
""", unsafe_allow_html=True)

with st.expander("💡 What can I ask?"):
    st.markdown("""
    - Who is on bench?
    - Talent_3 is in which department?
    - Email of Talent_4
    - Show pie chart of department
    - Who completed SEER training?
    - Show training status chart
    - Export list of deployed talents
    """)

with st.sidebar:
    st.markdown("""
    <div class='sidebar-upload'>
        <h4>📂 Upload Your Talent File</h4>
        <p><small>Supported formats: Excel, CSV, PDF, DOCX</small></p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Drag & drop or browse file", type=["xlsx", "xls", "csv", "pdf", "docx"])

# Helpers
@st.cache_data

def convert_df_to_excel(df_result):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name='Filtered Results')
    output.seek(0)
    return output

CHAT_LOG_FILE = "chat_log.txt"
def save_chat(query, response):
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as log:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"[{now}]\nQ: {query}\nA: {response}\n\n")

def show_chat_history():
    if os.path.exists(CHAT_LOG_FILE):
        with st.expander("📜 Chat History (Local)"):
            with open(CHAT_LOG_FILE, "r", encoding="utf-8") as log:
                st.text_area("Chat History", value=log.read(), height=300)

# Load and update df
raw_text = None
if uploaded_file:
    file_name = uploaded_file.name.lower()
    if file_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    elif file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif file_name.endswith(".pdf"):
        raw_text = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        df = None
    elif file_name.endswith(".docx"):
        raw_text = docx.Document(uploaded_file)
        df = None
    else:
        df = None

    if df is not None:
        df.columns = df.columns.str.strip().str.lower()
        if 'talent name' in df.columns:
            df['talent name'] = df['talent name'].str.strip()
        save_to_db(df)
        st.session_state.df = df
else:
    if db_table_exists():
        st.session_state.df = load_from_db()

df = st.session_state.get("df")

if df is not None:
    st.subheader("📊 Talent Summary Dashboard")
    try:
        training_in_progress = df[df['training status'].str.lower() == "training in progress"].shape[0]
        completed_seer = df[df['training status'].str.lower() == "completed seer training"].shape[0]
        not_started = df[df['training status'].str.lower() == "not started"].shape[0]
        on_bench = df[df['deployment status'].str.lower() == "on bench"].shape[0]
        deployed = df[df['deployment status'].str.lower() == "deployed in project"].shape[0]
        rolling_off = df[df['deployment status'].str.lower() == "rolling off"].shape[0]

        col1, col2, col3 = st.columns(3)
        col4, col5, col6 = st.columns(3)

        col1.metric("🧐 In Training", training_in_progress)
        col2.metric("🎓 SEER Completed", completed_seer)
        col3.metric("🕒 Not Started", not_started)
        col4.metric("🪑 On Bench", on_bench)
        col5.metric("🧑‍💼 Deployed", deployed)
        col6.metric("🚪 Rolling Off", rolling_off)

        with st.expander("🔍 Preview Uploaded Table"):
            st.dataframe(df)

        st.subheader("💬 Ask a Question")
        query = st.text_input("Type a question about the data:")

        result = None
        response = ""
        matched = False

        if query:
            query = query.lower().strip()
            talent_match = re.search(r"talent[_\s]?(\d+)", query)
            talent_name = f"talent_{talent_match.group(1)}" if talent_match else None

            if "on bench" in query:
                result = df[df['deployment status'].str.lower() == "on bench"]
                response = f"🪑 {len(result)} talents are on bench."
                matched = True
            elif "deployed" in query:
                result = df[df['deployment status'].str.lower() == "deployed in project"]
                response = f"🧑‍💼 {len(result)} talents are deployed."
                matched = True
            elif "rolling off" in query:
                result = df[df['deployment status'].str.lower() == "rolling off"]
                response = f"📄 {len(result)} talents are rolling off."
                matched = True
            elif "completed seer" in query:
                result = df[df['training status'].str.lower() == "completed seer training"]
                response = f"🎓 {len(result)} talents completed SEER training."
                matched = True
            elif "not started" in query:
                result = df[df['training status'].str.lower() == "not started"]
                response = f"⏳ {len(result)} haven't started training."
                matched = True
            elif "training in progress" in query:
                result = df[df['training status'].str.lower() == "training in progress"]
                response = f"🧐 {len(result)} talents are currently in training."
                matched = True
            elif "pie chart of department" in query:
                chart_data = df['department'].value_counts()
                st.subheader("📊 Department-wise Distribution")
                fig, ax = plt.subplots()
                chart_data.plot.pie(autopct='%1.1f%%', ax=ax)
                ax.set_ylabel("")
                st.pyplot(fig)
                matched = True
            elif "training status chart" in query:
                chart_data = df['training status'].value_counts()
                st.subheader("📊 Training Status Distribution")
                fig, ax = plt.subplots()
                chart_data.plot.pie(autopct='%1.1f%%', ax=ax)
                ax.set_ylabel("")
                st.pyplot(fig)
                matched = True
            elif "bar chart of deployment" in query:
                chart_data = df['deployment status'].value_counts()
                st.subheader("📊 Deployment Status")
                st.bar_chart(chart_data)
                matched = True
            elif "talents name with the department" in query:
                result = df[['talent name', 'department']]
                response = "📋 Talent names and their departments:"
                matched = True
            elif talent_name:
                row = df[df['talent name'].str.lower() == talent_name]
                if "department" in query and 'department' in df.columns:
                    response = f"🏢 {talent_name.title()} is in the {row.iloc[0]['department']} department." if not row.empty else f"❌ Talent '{talent_name}' not found."
                    matched = True
                elif "email" in query and 'email' in df.columns:
                    response = f"📧 Email of {talent_name.title()}: {row.iloc[0]['email']}" if not row.empty else f"❌ Email not found for {talent_name}."
                    matched = True

        if response:
            st.text_area("🧠 Bot Response", value=response, height=150)
            save_chat(query, response)

        if result is not None:
            st.dataframe(result)
            st.markdown("""
            <div style='background-color:#e0f2f1; padding:1rem; border-radius:8px; margin-top:1.5rem; margin-bottom:1rem;'>
                <h4>📁 Export Filtered Data</h4>
            </div>
            """, unsafe_allow_html=True)
            st.download_button("⬇️ Download Excel", data=convert_df_to_excel(result), file_name="filtered_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        elif not matched:
            default_response = "🧠 Sorry, I couldn’t understand that question. Try asking about training, deployment, or departments."
            st.text_area("🧠 Bot Response", value=default_response, height=150)
            save_chat(query, default_response)

        show_chat_history()

    except Exception as e:
        st.warning(f"⚠️ Dashboard couldn't load due to: {e}")

elif raw_text:
    st.subheader("📄 Text Extracted from Document")
    st.text_area("File Content Preview", raw_text[:3000])
else:
    st.info("📌 Upload a file or rely on the existing database.")
