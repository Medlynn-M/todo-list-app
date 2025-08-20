from pyairtable import Table
import streamlit as st
from datetime import datetime
import random

# Airtable config from secrets
AIRTABLE_BASE_ID = "appf3qCx67knSZq16"
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# Helper functions for username management
def username_exists(username):
    all_records = table.all()
    usernames = {r.get("fields", {}).get("User", "").lower() for r in all_records}
    return username.lower() in usernames

def suggest_usernames(base_name):
    suggestions = []
    for i in range(1, 10):
        suggestions.append(f"{base_name}{i}")
        suggestions.append(f"{base_name}_{random.randint(10,99)}")
    return suggestions

# User login / registration flow
if "user" not in st.session_state:
    st.session_state.user = ""
if "user_available" not in st.session_state:
    st.session_state.user_available = False
if "user_to_confirm" not in st.session_state:
    st.session_state.user_to_confirm = ""

current_user = st.session_state.user.strip()

if current_user == "":
    st.header("🚀 Set up your Companion Profile")
    new_username = st.text_input("Choose your unique username:", value="")

    if st.button("Check Availability") and new_username.strip():
        name = new_username.strip()
        if username_exists(name):
            st.session_state.user_available = False
            st.error(f"Sorry, '{name}' is already taken. Try one of these:")
            for sug in suggest_usernames(name):
                st.write(f"- {sug}")
        else:
            st.session_state.user_available = True
            st.session_state.user_to_confirm = name
            st.success(f"'{name}' is available! 🎉 Please confirm below.")

    if st.session_state.user_available and st.session_state.user_to_confirm:
        if st.button("Confirm username"):
            st.session_state.user = st.session_state.user_to_confirm
            st.session_state.user_to_confirm = ""
            st.experimental_rerun()

    st.stop()  # Wait until username confirmed

def get_tasks_for_date_and_user(date_str, user):
    all_records = table.all()
    seen = set()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("Date") == date_str and fields.get("User", "").strip().lower() == user.lower():
            task_text = fields.get("Task", "")
            if task_text.lower() not in seen:
                seen.add(task_text.lower())
                tasks.append({
                    "id": r["id"],
                    "task": task_text,
                    "completed": fields.get("Completed", False)
                })
    # Alphabetical order by task text
    return sorted(tasks, key=lambda x: x["task"].lower())

def update_task_completion(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(task_text, date_str, user):
    table.create({
        "Task": task_text,
        "Date": date_str,
        "Completed": False,
        "User": user
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

st.title(f"🧑‍🚀 {current_user}'s Daily Mission Companion!")

st.markdown("#### Every day is a new adventure. Let's crush it together! 🚀")

tasks = get_tasks_for_date_and_user(selected_date_str, current_user)

if not tasks:
    st.info("No missions yet for this day. Ready to conquer something new? 🥷")

# Display missions alphabetically with colorful icons and playful messages
for task in tasks:
    completed = task.get("completed", False)
    label_text = task["task"]
    if completed:
        label = f"<span class='completed-label'>🌟 Great job! {label_text}</span>"
    else:
        label = f"<span class='incomplete-label'>💡 Let's do: {label_text}</span>"

    col1, col2 = st.columns([9,1])
    with col1:
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
        add_task(new_task.strip(), selected_date_str, current_user)
        st.success("Your new mission is ready for liftoff! 🚀")
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
---
**Tip:** Click the check to mark a mission completed, or 🗑️ to delete it.  
Keep coming back to see your super progress! 🌈

#### Your companion awaits powerful new adventures every day!
""")
