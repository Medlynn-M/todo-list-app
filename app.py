from pyairtable import Table
import streamlit as st
from datetime import datetime

AIRTABLE_BASE_ID = "https://airtable.com/appf3qCx67knSZq16/api/docs"
AIRTABLE_TABLE_NAME = "Tasks"
AIRTABLE_TOKEN = "pat2bTPrIC5qNJtLx.d474703680c5b0464dc0171b402574fc5721f5ee1a831927e8a1e881511dbf89"

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def get_tasks_for_today():
    today_str = datetime.now().strftime("%Y-%m-%d")
    all_records = table.all()
    return [
        {
            "id": r["id"],
            "task": r["fields"].get("Task", ""),
            "alarm": r["fields"].get("Alarm", ""),
        }
        for r in all_records
        if r["fields"].get("Date") == today_str
    ]

def add_task(task_text, alarm_time):
    today_str = datetime.now().strftime("%Y-%m-%d")
    table.create({
        "Task": task_text,
        "Alarm": alarm_time,
        "Date": today_str
    })

def delete_task(record_id):
    table.delete(record_id)

st.title("🚀 Boost Your Day!")

new_task = st.text_input("🌟 Add an exciting mission:")
new_alarm = st.text_input("⏰ Set alarm time (HH:MM) - optional")

if st.button("🔥 Add Mission"):
    if new_task:
        add_task(new_task, new_alarm)
        st.success(f"Mission added: {new_task} with alarm {new_alarm}")

tasks = get_tasks_for_today()

if tasks:
    choices = [f"{t['task']} (Alarm: {t['alarm']})" if t['alarm'] else t['task'] for t in tasks]
    selected_idx = st.radio("Select a mission to mark as done:", range(len(tasks)), format_func=lambda x: choices[x])

    if st.button("✅ Mark as Done!"):
        delete_task(tasks[selected_idx]['id'])
        st.info(f"Mission accomplished: {tasks[selected_idx]['task']}")
else:
    st.info("No missions for today. Add some to get started!")
