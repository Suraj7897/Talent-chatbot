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

load_dotenv()

st.set_page_config(page_title="🌟 Talent Intelligence Hub", page_icon="📊", layout="wide")

# Custom Styling and Welcome Header
st.markdown("""
    <style>
    .main {
        background-color: #f4f8fb;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .css-18e3th9 {
        padding: 1rem 2rem 2rem 2rem;
        border-radius: 12px;
        background-color: #ffffff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .stButton>button {
        background-color: #0066cc;
        color: white;
        border-radius: 5px;
        font-weight: 600;
    }
    .stDownloadButton>button {
        background-color: #10b981;
        color: white;
        border-radius: 5px;
        font-weight: 600;
    }
    .stTextInput>div>input {
        border-radius: 5px;
        border: 1px solid #ccc;
    }
    .stTextArea textarea {
        border-radius: 6px;
        border: 1px solid #ccc;
    }
    .welcome-banner {
        background: linear-gradient(to right, #003366, #006699);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='welcome-banner'>
    <h1>👋 Welcome to the Talent Intelligence Hub</h1>
    <p>Empowering decisions through smart talent insights</p>
</div>
""", unsafe_allow_html=True)

# 📘 Help Box
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

# 📁 Sidebar Header (Replaced image with emoji)
st.sidebar.markdown("### 📂 Talent File Uploader")
uploaded_file = st.sidebar.file_uploader("Supported formats: Excel, CSV, PDF, DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])

# File Load
raw_text = None
df = None
if uploaded_file:
    file_name = uploaded_file.name.lower()
    if file_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        if 'talent name' in df.columns:
            df['talent name'] = df['talent name'].str.strip()
        save_to_db(df)
    elif file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        if 'talent name' in df.columns:
            df['talent name'] = df['talent name'].str.strip()
        save_to_db(df)
    elif file_name.endswith(".pdf"):
        raw_text = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    elif file_name.endswith(".docx"):
        raw_text = docx.Document(uploaded_file)

elif db_table_exists():
    df = load_from_db()
    st.success("📦 Data loaded from existing database.")

@st.cache_data
def convert_df_to_excel(df_result):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name='Filtered Results')
    output.seek(0)
    return output

# 🧠 Smart Query Area
if df is not None:
    st.subheader("📊 Talent Summary Dashboard")

    try:
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
                response = f"🧑‍💻 {len(result)} talents are deployed."
                matched = True

            elif "rolling off" in query:
                result = df[df['deployment status'].str.lower() == "rolling off"]
                response = f"📤 {len(result)} talents are rolling off."
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
                response = f"🧠 {len(result)} talents are currently in training."
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
                    if not row.empty:
                        response = f"🏢 {talent_name.title()} is in the {row.iloc[0]['department']} department."
                    else:
                        response = f"❌ Talent '{talent_name}' not found."
                    matched = True

                elif "email" in query and 'email' in df.columns:
                    if not row.empty:
                        response = f"📧 Email of {talent_name.title()}: {row.iloc[0]['email']}"
                    else:
                        response = f"❌ Email not found for {talent_name}."
                    matched = True

        if response:
            st.text_area("🤖 Bot Response", value=response, height=150)

        if result is not None:
            st.dataframe(result)
            st.download_button(
                label="📥 Download Filtered Results as Excel",
                data=convert_df_to_excel(result),
                file_name="filtered_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        elif not matched:
            st.text_area("🤖 Bot Response", value="🤖 Sorry, I couldn’t understand that question. Try asking about training, deployment, or departments.", height=150)

    except Exception as e:
        st.warning(f"⚠️ Dashboard couldn't load due to: {e}")

elif raw_text:
    st.subheader("📄 Text Extracted from Document")
    st.text_area("File Content Preview", raw_text[:3000])

else:
    st.info("📌 Upload a file or rely on the existing database.")
