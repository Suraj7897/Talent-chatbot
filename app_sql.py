import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import io
import re

st.set_page_config(page_title="Live SQL Talent Chatbot", layout="wide")
st.title("🗃️ Talent Database Chatbot (No API)")

DB_FILE = "talents.db"
TABLE_NAME = "talents"

# Excel Export Helper
@st.cache_data
def convert_df_to_excel(df_result):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_result.to_excel(writer, index=False, sheet_name="Filtered Results")
    output.seek(0)
    return output

# Connect to DB
def fetch_query(sql):
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(sql, conn)

# Handle query
def handle_user_query(query):
    query = query.lower().strip()
    base_sql = f"SELECT * FROM {TABLE_NAME}"
    where = ""
    title = ""

    # Match common phrases
    if "on bench" in query:
        where = "deployment_status = 'on bench'"
        title = "🪑 Talents On Bench"

    elif "deployed" in query:
        where = "deployment_status = 'deployed in project'"
        title = "🧑‍💻 Deployed Talents"

    elif "rolling off" in query:
        where = "deployment_status = 'rolling off'"
        title = "🚪 Rolling Off Talents"

    elif "completed seer" in query:
        where = "training_status = 'completed seer training'"
        title = "🎓 Completed SEER Training"

    elif "not started" in query:
        where = "training_status = 'not started'"
        title = "🕒 Training Not Started"

    elif "training in progress" in query:
        where = "training_status = 'training in progress'"
        title = "🧠 Training In Progress"

    elif "department" in query and "pie" in query:
        df = fetch_query(f"SELECT department FROM {TABLE_NAME}")
        plot_pie(df["department"], "📊 Department-wise Distribution")
        return

    elif "deployment status" in query and "pie" in query:
        df = fetch_query(f"SELECT deployment_status FROM {TABLE_NAME}")
        plot_pie(df["deployment_status"], "📊 Deployment Status Chart")
        return

    elif "training status" in query and "bar" in query:
        df = fetch_query(f"SELECT training_status FROM {TABLE_NAME}")
        plot_bar(df["training_status"], "📊 Training Status Bar Chart")
        return

    elif "list all" in query or "show all" in query:
        title = "📋 All Talents"
        return fetch_query(base_sql), title

    # Department filter combo
    elif "completed seer" in query and "engineering" in query:
        where = "training_status = 'completed seer training' AND department = 'engineering'"
        title = "🎓 Completed SEER in Engineering"

    # Talent-specific (regex): e.g., "talent_3 department"
    talent_match = re.search(r"talent[_\s]?(\d+)", query)
    if talent_match:
        tid = talent_match.group(1)
        row = fetch_query(f"SELECT * FROM {TABLE_NAME} WHERE id = {tid}")
        if not row.empty:
            title = f"ℹ️ Talent_{tid} Info"
            return row, title
        else:
            return None, f"❌ Talent_{tid} not found"

    if where:
        full_sql = f"{base_sql} WHERE {where}"
        df = fetch_query(full_sql)
        return df, title

    return None, "❌ Sorry, I couldn’t understand your question."

# Charts
def plot_pie(data_series, title):
    st.subheader(title)
    fig, ax = plt.subplots()
    data_series.value_counts().plot.pie(autopct="%1.1f%%", ax=ax)
    ax.set_ylabel("")
    st.pyplot(fig)

def plot_bar(data_series, title):
    st.subheader(title)
    chart_data = data_series.value_counts()
    st.bar_chart(chart_data)

# Main UI
st.markdown("Ask a question like:")
st.code("Show talents on bench\nPie chart of department\nCompleted SEER in engineering")

user_query = st.text_input("💬 Your question:")

if user_query:
    result, title = handle_user_query(user_query)

    if isinstance(result, pd.DataFrame):
        st.subheader(title)
        st.dataframe(result)

        if not result.empty:
            excel_data = convert_df_to_excel(result)
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name="result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    elif isinstance(title, str):
        st.info(title)
