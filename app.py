# app.py (GPT-style question handling without GPT API, updated fallback handling and improved Talent_X query recognition)

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

st.set_page_config(page_title="Universal Talent Dashboard", layout="wide")
st.title("📂 Universal Talent Dashboard")

@st.cache_data
def convert_df_to_excel(df_result):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False, sheet_name='Filtered Results')
    output.seek(0)
    return output

def extract_text_from_pdf(uploaded_pdf):
    text = ""
    with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(uploaded_docx):
    doc = docx.Document(uploaded_docx)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip() != ""])

# Upload section
st.sidebar.markdown("### 📁 Upload a new file")
uploaded_file = st.sidebar.file_uploader("Upload Excel, CSV, PDF, or DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])

df = None
raw_text = None

if uploaded_file:
    file_name = uploaded_file.name.lower()

    if file_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        df['talent name'] = df['talent name'].str.strip()
        save_to_db(df)
        st.success("✅ New Excel file uploaded and saved to DB.")

    elif file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        df['talent name'] = df['talent name'].str.strip()
        save_to_db(df)
        st.success("✅ New CSV file uploaded and saved to DB.")

    elif file_name.endswith(".pdf"):
        raw_text = extract_text_from_pdf(uploaded_file)

    elif file_name.endswith(".docx"):
        raw_text = extract_text_from_docx(uploaded_file)

elif db_table_exists():
    df = load_from_db()
    st.success("📦 Data loaded from existing database.")

# Show dashboard
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

        col1.metric("🧠 In Training", training_in_progress)
        col2.metric("🎓 SEER Completed", completed_seer)
        col3.metric("🕒 Not Started", not_started)
        col4.metric("🪑 On Bench", on_bench)
        col5.metric("🧑‍💻 Deployed", deployed)
        col6.metric("🚪 Rolling Off", rolling_off)

        with st.expander("🔍 Preview Uploaded Table"):
            st.dataframe(df)

        with st.expander("📥 Export Filtered Data"):
            excel_data = convert_df_to_excel(df)
            st.download_button("📥 Download Full Data as Excel", data=excel_data, file_name="talent_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Simple keyword-based question handling
        st.subheader("💬 Ask a Question")
        query = st.text_input("Your question:")

        if query:
            query = query.lower()
            result = None
            chart_data = None
            response = ""
            matched = False

            # Preprocess Talent_X detection
            talent_match = re.search(r"talent[_\s]?(\d+)", query)
            talent_name = f"talent_{talent_match.group(1)}" if talent_match else None

            if "on bench" in query:
                result = df[df['deployment status'].str.lower() == "on bench"]
                response = f"🪑 {len(result)} talents on bench."
                matched = True

            elif "deployed in project" in query or "who is deployed" in query:
                result = df[df['deployment status'].str.lower() == "deployed in project"]
                response = f"🧑‍💻 {len(result)} talents deployed in project."
                matched = True

            elif "rolling off" in query:
                result = df[df['deployment status'].str.lower() == "rolling off"]
                response = f"🚪 {len(result)} talents rolling off."
                matched = True

            elif "completed seer" in query:
                result = df[df['training status'].str.lower() == "completed seer training"]
                response = f"🎓 {len(result)} talents completed SEER training."
                matched = True

            elif "not started" in query:
                result = df[df['training status'].str.lower() == "not started"]
                response = f"🕒 {len(result)} talents haven't started training."
                matched = True

            elif "training in progress" in query:
                result = df[df['training status'].str.lower() == "training in progress"]
                response = f"🧠 {len(result)} talents currently in training."
                matched = True

            elif "talents name with the department" in query:
                result = df[['talent name', 'department']]
                response = f"📋 Showing all talents with departments."
                matched = True

            elif talent_name and "department" in query:
                row = df[df['talent name'].str.lower() == talent_name]
                if not row.empty:
                    response = f"🏢 {talent_name.title()} is in the {row.iloc[0]['department']} department."
                else:
                    response = f"❌ Sorry, I couldn’t find {talent_name.title()} in the data."
                matched = True

            elif talent_name and "email" in query:
                row = df[df['talent name'].str.lower() == talent_name]
                if not row.empty:
                    response = f"📧 Email of {talent_name.title()}: {row.iloc[0]['email']}"
                else:
                    response = f"❌ Sorry, I couldn’t find {talent_name.title()} in the data."
                matched = True

            elif "pie chart of department" in query or "department-wise distribution" in query:
                chart_data = df['department'].value_counts()
                st.subheader("📊 Department-wise Distribution")
                fig, ax = plt.subplots()
                chart_data.plot.pie(autopct='%1.1f%%', ax=ax)
                ax.set_ylabel("")
                st.pyplot(fig)
                matched = True

            elif "training status chart" in query or "pie chart of training" in query:
                chart_data = df['training status'].value_counts()
                st.subheader("📊 Training Status Chart")
                fig, ax = plt.subplots()
                chart_data.plot.pie(autopct='%1.1f%%', ax=ax)
                ax.set_ylabel("")
                st.pyplot(fig)
                matched = True

            elif "bar chart of deployment" in query or "deployment status chart" in query:
                chart_data = df['deployment status'].value_counts()
                st.subheader("📊 Deployment Status Chart")
                st.bar_chart(chart_data)
                matched = True

            if response:
                st.text_area("🤖 Bot Response", value=response, height=150)
            elif not matched:
                st.text_area("🤖 Bot Response", value="🤖 Sorry, I couldn’t understand that question. Try asking about training, deployment, or specific talents.", height=150)
            if result is not None:
                st.dataframe(result)

    except Exception:
        st.warning("Summary dashboard not shown. Check column names in uploaded data.")

elif raw_text:
    st.subheader("📄 Uploaded Text Content Preview")
    st.text_area("Text Extracted:", raw_text[:3000])

else:
    st.info("📌 Upload a file or rely on the existing database.")
