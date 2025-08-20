import streamlit as st
from pyairtable import Table
from datetime import datetime
import hashlib
import random

# Airtable config
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def username_exists(username):
    all_records = table.all()
    usernames = {r.get("fields", {}).get("User", "").lower() for r in all_records}
    return username.lower() in usernames

def get_user_password_hash(username):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User", "").lower() == username.lower():
            return fields.get("PasswordHash", None)
    return None

def suggest_usernames(base_name):
    suggestions = []
    for i in range(1, 10):
        suggestions.append(f"{base_name}{i}")
        suggestions.append(f"{base_name}_{random.randint(10,99)}")
    return suggestions

def get_tasks_for_date_and_user(date_str, user):
    all_records = table.all()
    seen = set()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("Date") == date_str and fields.get("User", "").strip().lower() == user.lower() and fields.get("Task", "") != "[User Created]":
            task_text = fields.get("Task", "")
            if task_text.lower() not in seen:
                seen.add(task_text.lower())
                tasks.append({
                    "id": r["id"],
                    "task": task_text,
                    "completed": fields.get("Completed", False)
                })
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

def login():
    st.header("🔐 Welcome back! Please log in")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Log In"):
        if not username or not password:
            st.error("Please enter both username and password.")
            return
        if not username_exists(username):
            st.error("Username does not exist. Please register.")
            return
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("Incorrect password. Please try again.")
            return
        st.session_state.user = username
        st.session_state.logged_in = True
        st.success(f"Welcome back, {username}!")
        st.experimental_rerun()

def register():
    st.header("📝 Create your Companion Profile")
    username = st.text_input("Choose a username", key="reg_username")
    password = st.text_input("Choose a password", type="password", key="reg_password")
    password_confirm = st.text_input("Confirm password", type="password", key="reg_password_confirm")
    if st.button("Register"):
        if not username or not password or not password_confirm:
            st.error("Please fill all fields.")
            return
        if password != password_confirm:
            st.error("Passwords do not match.")
            return
        if username_exists(username):
            st.error("Username taken. Try another one or log in.")
            return
        table.create({
            "User": username,
            "Task": "[User Created]",
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Completed": True,
            "PasswordHash": hash_password(password)
        })
        st.success("Registration successful! Please log in now.")
        st.session_state.mode = "login"
        st.experimental_rerun()

def logout():
    st.session_state.user = ""
    st.session_state.logged_in = False
    st.experimental_rerun()

# Session state defaults
if "user" not in st.session_state:
    st.session_state.user = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "mode" not in st.session_state:
    st.session_state.mode = "login"

# User selects login or register mode
st.sidebar.title("User Authentication")
mode_option = st.sidebar.radio("Select mode:", ["Log In", "Register"])
st.session_state.mode = mode_option.lower()

# Show login/register or main app depending on login state
if not st.session_state.logged_in:
    if st.session_state.mode == "login":
        login()
    else:
        register()
    st.stop()  # Stop here if not logged in, wait for login/registration
else:
    st.sidebar.title(f"Hello, {st.session_state.user}!")
    if st.sidebar.button("Log Out"):
        logout()

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
        """, unsafe_allow_html=True)

    st.title(f"🧑‍🚀 {st.session_state.user}'s Daily Mission Companion!")
    st.markdown("#### Every day is a new adventure. Let's crush it together! 🚀")

    tasks = get_tasks_for_date_and_user(selected_date_str, st.session_state.user)

    if not tasks:
        st.info("No missions yet for this day. Ready to conquer something new? 🥷")

    for task in tasks:
        completed = task.get("completed", False)
        label_text = task["task"]
        if completed:
            label = f"<span class='completed-label'>🌟 Great job! {label_text}</span>"
        else:
            label = f"<span class='incomplete-label'>💡 Let's do: {label_text}</span>"

        col1, col2 = st.columns([9, 1])
        with col1:
            new_completed = st.checkbox("", value=completed, key=f"{task['id']}_checkbox")
            st.markdown(label, unsafe_allow_html=True)
            if new_completed != completed:
                update_task_completion(task["id"], new_completed)
                st.rerun()
        with col2:
            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
            if st.button("🗑️", key=f"{task['id']}_delete", help="Delete this mission"):
                delete_task(task["id"])
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### ✨ New quest for the day:")
    new_task = st.text_input("What powerful mission should we tackle together today?")

    st.markdown('<div class="add-btn">', unsafe_allow_html=True)
    if st.button("⚡ Add Mission"):
        if new_task.strip():
            add_task(new_task.strip(), selected_date_str, st.session_state.user)
            st.success("Your new mission is ready for liftoff! 🚀")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    ---
    **Tip:** Click the check to mark a mission completed, or 🗑️ to delete it.  
    Keep coming back to see your super progress! 🌈

    #### Your companion awaits powerful new adventures every day!
    """)
