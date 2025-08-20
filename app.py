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
    # Reverse order: most recently added tasks first
    return tasks[::-1]

def update_task_completion(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(task_text, date_str):
    table.create({
        "Task": task_text,
        "Date": date_str,
        "Completed": False
    })

def delete_task(record_id):
    table.delete(record_id)

st.title("🚀 Boost Your Day!")

# Sidebar date selection
selected_date = st.sidebar.date_input("Select date", datetime.today())
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.sidebar.markdown(f"### Tasks for {selected_date_str}")

tasks = get_tasks_for_date(selected_date_str)

if not tasks:
    st.write("No missions for this day. Add some below!")

# Show tasks in reverse order with delete option
for task in tasks:
    completed = task.get("completed", False)
    label_text = task["task"]
    label = f"✅ {label_text}" if completed else f"❌ {label_text}"

    col1, col2 = st.columns([9,1])
    with col1:
        # Checkbox for completion status
        new_completed = st.checkbox(label, value=completed, key=f"{task['id']}_checkbox")
        if new_completed != completed:
            update_task_completion(task["id"], new_completed)
            st.rerun()
    with col2:
        # Delete button for each mission
        if st.button("🗑️", key=f"{task['id']}_delete", help="Delete this mission"):
            delete_task(task["id"])
            st.rerun()

# Add new mission
new_task = st.text_input("🌟 Add a new mission:")
if st.button("🔥 Add Mission"):
    if new_task.strip():
        add_task(new_task.strip(), selected_date_str)
        st.success(f"Added new mission for {selected_date_str}!")
        st.rerun()
