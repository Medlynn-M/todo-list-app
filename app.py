from pyairtable import Table
import streamlit as st
from datetime import datetime

# Load Airtable config from secrets
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

# Connect to your Airtable table
table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def get_tasks_for_today():
    today_str = datetime.now().strftime("%Y-%m-%d")
    all_records = table.all()
    return [
        {
            "id": r["id"],
            "task": r["fields"].get("Task", "")
        }
        for r in all_records
        if r["fields"].get("Date") == today_str
    ]

def add_task(task_text):
    today_str = datetime.now().strftime("%Y-%m-%d")
    table.create({
        "Task": task_text,
        "Date": today_str
    })

def delete_task(record_id):
    table.delete(record_id)

st.title("🚀 Boost Your Day!")

new_task = st.text_input("🌟 Add an exciting mission:")

if st.button("🔥 Add Mission"):
    if new_task:
        add_task(new_task)
        st.success(f"Mission added: {new_task}")

tasks = get_tasks_for_today()

if tasks:
    choices = [t['task'] for t in tasks]
    selected_idx = st.radio("Select a mission to mark as done:", range(len(tasks)), format_func=lambda x: choices[x])

    if st.button("✅ Mark as Done!"):
        delete_task(tasks[selected_idx]['id'])
        st.info(f"Mission accomplished: {tasks[selected_idx]['task']}")
else:
    st.info("No missions for today. Add some to get started!")
