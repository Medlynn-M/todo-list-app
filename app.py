from pyairtable import Table
import streamlit as st
from datetime import datetime

# Load Airtable config from secrets
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

# Connect to Airtable table
table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def get_tasks_for_date(date_str):
    all_records = table.all()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("Date") == date_str:
            tasks.append({
                "id": r["id"],
                "task": fields.get("Task", ""),
                "completed": fields.get("Completed", False)
            })
    return tasks

def update_task_completion(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(task_text, date_str):
    table.create({
        "Task": task_text,
        "Date": date_str,
        "Completed": False
    })

st.title("🚀 Boost Your Day!")

# Sidebar date selection
selected_date = st.sidebar.date_input("Select date", datetime.today())
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.sidebar.markdown(f"### Tasks for {selected_date_str}")

tasks = get_tasks_for_date(selected_date_str)

if not tasks:
    st.write("No missions for this day. Add some below!")

# Display tasks with persistent checkbox and color indicators
for task in tasks:
    completed = task.get("completed", False)
    label_text = task["task"]
    # Show green check emoji for completed, red cross for incomplete
    label = f"✅ {label_text}" if completed else f"❌ {label_text}"

    # Checkbox to toggle completion state
    new_completed = st.checkbox(label, value=completed, key=task["id"])
    if new_completed != completed:
        update_task_completion(task["id"], new_completed)
        st.experimental_rerun()

# Input to add new task to selected date
new_task = st.text_input("🌟 Add a new mission:")
if st.button("🔥 Add Mission"):
    if new_task.strip():
        add_task(new_task.strip(), selected_date_str)
        st.success(f"Added new mission for {selected_date_str}!")
        st.rerun()
