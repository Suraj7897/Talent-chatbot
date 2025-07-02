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

# Custom Styling
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
    </style>
""", unsafe_allow_html=True)

st.title("📂 Talent Intelligence Dashboard")
st.markdown("<h4 style='color: #333;'>Empowering decisions through smart talent insights</h4>", unsafe_allow_html=True)

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
st.sidebar.image("https://img.icons8.com/ios-filled/50/upload--v1.png", width=40)
st.sidebar.markdown("### 📁 Upload Your Talent File")
uploaded_file = st.sidebar.file_uploader("Supported formats: Excel, CSV, PDF, DOCX", type=["xlsx", "xls", "csv", "pdf", "docx"])

df = None
raw_text = None

if uploaded_file:
    file_name = uploaded_file.name.lower()

    if file_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        if 'talent name' in df.columns:
            df['talent name'] = df['talent name'].str.strip()
        try:
            save_to_db(df)
        except Exception as e:
            st.warning(f"⚠️ Failed to save to DB: {e}")
        st.success("✅ New Excel file uploaded and saved to DB.")

    elif file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        if 'talent name' in df.columns:
            df['talent name'] = df['talent name'].str.strip()
        try:
            save_to_db(df)
        except Exception as e:
            st.warning(f"⚠️ Failed to save to DB: {e}")
        st.success("✅ New CSV file uploaded and saved to DB.")

    elif file_name.endswith(".pdf"):
        raw_text = extract_text_from_pdf(uploaded_file)

    elif file_name.endswith(".docx"):
        raw_text = extract_text_from_docx(uploaded_file)

elif db_table_exists():
    df = load_from_db()
    st.success("📦 Data loaded from existing database.")

if df is not None:
    st.subheader("📊 Talent Summary Dashboard")

    try:
        df_cols = df.columns.tolist()

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

            if any(x in df.columns for x in ['deployment status', 'training status']):

                if 'deployment status' in df.columns:
                    if "on bench" in query or "bench talents" in query:
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

                if 'training status' in df.columns:
                    if "completed seer" in query:
                        result = df[df['training status'].str.lower() == "completed seer training"]
                        response = f"🎓 {len(result)} talents completed SEER training."
                        matched = True

                    elif "haven't started" in query or "not started" in query:
                        result = df[df['training status'].str.lower() == "not started"]
                        response = f"🕒 {len(result)} talents haven't started training."
                        matched = True

                    elif "training in progress" in query or "are in training" in query:
                        result = df[df['training status'].str.lower() == "training in progress"]
                        response = f"🧠 {len(result)} talents currently in training."
                        matched = True

                    elif "training status chart" in query or "pie chart of training" in query:
                        chart_data = df['training status'].value_counts()
                        st.subheader("📊 Training Status Chart")
                        fig, ax = plt.subplots()
                        chart_data.plot.pie(autopct='%1.1f%%', ax=ax)
                        ax.set_ylabel("")
                        st.pyplot(fig)
                        matched = True

                if 'department' in df.columns:
                    if "pie chart of department" in query or "department-wise distribution" in query:
                        chart_data = df['department'].value_counts()
                        st.subheader("📊 Department-wise Distribution")
                        fig, ax = plt.subplots()
                        chart_data.plot.pie(autopct='%1.1f%%', ax=ax)
                        ax.set_ylabel("")
                        st.pyplot(fig)
                        matched = True

                    if "talents name with the department" in query:
                        result = df[['talent name', 'department']] if 'talent name' in df.columns else df[['department']]
                        response = "📋 Showing all talents with departments."
                        matched = True

                if 'deployment status' in df.columns and ("bar chart of deployment" in query or "deployment status chart" in query):
                    chart_data = df['deployment status'].value_counts()
                    st.subheader("📊 Deployment Status Chart")
                    st.bar_chart(chart_data)
                    matched = True

            if talent_name:
                if "department" in query and 'talent name' in df.columns and 'department' in df.columns:
                    row = df[df['talent name'].str.lower() == talent_name]
                    if not row.empty:
                        response = f"🏢 {talent_name.title()} is in the {row.iloc[0]['department']} department."
                    else:
                        response = f"❌ Sorry, I couldn’t find {talent_name.title()} in the data."
                    matched = True

                elif "email" in query and 'talent name' in df.columns and 'email' in df.columns:
                    row = df[df['talent name'].str.lower() == talent_name]
                    if not row.empty:
                        response = f"📧 Email of {talent_name.title()}: {row.iloc[0]['email']}"
                    else:
                        response = f"❌ Sorry, I couldn’t find {talent_name.title()} in the data."
                    matched = True

            if response:
                st.text_area("🤖 Bot Response", value=response, height=150)
            elif not matched:
                st.text_area("🤖 Bot Response", value="🤖 Sorry, I couldn’t understand that question. Try asking about training, deployment, or specific talents.", height=150)

            if result is not None:
                st.dataframe(result)
                excel_data = convert_df_to_excel(result)
                st.download_button(
                    label="📥 Download Filtered Results as Excel",
                    data=excel_data,
                    file_name="filtered_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.warning(f"Summary dashboard not shown. Error: {e}")

elif raw_text:
    st.subheader("📄 Uploaded Text Content Preview")
    st.text_area("Text Extracted:", raw_text[:3000])

else:
    st.info("📌 Upload a file or rely on the existing database.")
