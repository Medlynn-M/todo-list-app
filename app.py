from pyairtable import Table
import streamlit as st
from datetime import datetime, time

# Airtable config from secrets
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def parse_time(t_str):
    try:
        return datetime.strptime(t_str, "%H:%M").time()
    except:
        return None

def get_tasks_for_date(date_str):
    all_records = table.all()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("Date") == date_str:
            tasks.append({
                "id": r["id"],
                "task": fields.get("Task", ""),
                "completed": fields.get("Completed", False),
                "time": fields.get("Time", "")  # Make sure you have a "Time" field in Airtable
            })

    # Sort by time if available; otherwise by task alphabetically
    def sort_key(task):
        task_time = parse_time(task.get("time", ""))
        return (task_time if task_time else time.max, task["task"].lower())

    return sorted(tasks, key=sort_key)

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

# ---- THE ENGAGING INTERFACE ----

# Sidebar date selector
selected_date = st.sidebar.date_input("🎯 Pick your day!", datetime.today())
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.sidebar.markdown(f"#### 📅 Missions for {selected_date_str}")

st.markdown("""
    <style>
        .completed-label {color: #43ea54; font-weight: bold;}
        .incomplete-label {color: #fa4372; font-weight: bold;}
        .delete-btn button {background: #fa2656;}
        .add-btn button {background: #ffe766; color: black;}
    </style>
    """, unsafe_allow_html=True
)

st.title("🧑‍🚀 Your Daily Mission Companion!")

st.markdown("#### Every day is a new adventure. Let's crush it together! 🚀")

tasks = get_tasks_for_date(selected_date_str)

if not tasks:
    st.info("No missions yet for this day. Ready to conquer something new? 🥷")

# Display missions (sorted by time then alphabetically) with colorful icons and playful messages
for task in tasks:
    completed = task.get("completed", False)
    label_text = task["task"]
    # Companion-style label
    if completed:
        label = f"<span class='completed-label'>🌟 Great job! {label_text}</span>"
    else:
        label = f"<span class='incomplete-label'>💡 Let's do: {label_text}</span>"

    col1, col2 = st.columns([9,1])
    with col1:
        # Companion-style checkbox
        new_completed = st.checkbox(
            "", value=completed, key=f"{task['id']}_checkbox"
        )
        st.markdown(label, unsafe_allow_html=True)
        if new_completed != completed:
            update_task_completion(task["id"], new_completed)
            st.rerun()
    with col2:
        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
        if st.button("🗑️", key=f"{task['id']}_delete", help="Delete this mission"):
            delete_task(task["id"])
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# Add new mission input & creative call to action
st.markdown("### ✨ New quest for the day:")
new_task = st.text_input("What powerful mission should we tackle together today?")

st.markdown('<div class="add-btn">', unsafe_allow_html=True)
if st.button("⚡ Add Mission"):
    if new_task.strip():
        add_task(new_task.strip(), selected_date_str)
        st.success("Your new mission is ready for liftoff! 🚀")
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
---
**Tip:** Click the check to mark a mission completed, or 🗑️ to delete it.  
Keep coming back to see your super progress! 🌈

#### Your companion awaits powerful new adventures every day!
""")
