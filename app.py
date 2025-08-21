import streamlit as st
from pyairtable import Table
from datetime import datetime
import hashlib
import random
import re  # <-- for regex password validation

# Airtable config
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ✅ Case-sensitive username check (removed .lower())
def username_exists(username):
    all_records = table.all()
    usernames = {r.get("fields", {}).get("User", "") for r in all_records}
    return username in usernames

def get_user_password_hash(username):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User", "") == username:  # ✅ case-sensitive match
            return fields.get("PasswordHash", None)
    return None

def get_tasks_for_date_and_user(date_str, user):
    all_records = table.all()
    seen = set()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("Date") == date_str and fields.get("User", "").strip() == user and fields.get("Task", "") != "[User Created]":
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

def suggest_usernames(base_name):
    suggestions = []
    for i in range(1, 10):
        suggestions.append(f"{base_name}{i}")
        suggestions.append(f"{base_name}_{random.randint(10,99)}")
    return suggestions

# ✅ Strong password policy function
def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Uppercase
        return False
    if not re.search(r"[a-z]", password):  # Lowercase
        return False
    if not re.search(r"[0-9]", password):  # Digit
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):  # Special char
        return False
    return True

def login_block():
    st.header("👋 Welcome Back, Commander!")
    username = st.text_input("Your Call Sign (Username)", key="login_username")
    password = st.text_input("Secret Code (Password)", type="password", key="login_password")
    login_clicked = st.button("Launch Mission Control")
    if login_clicked:
        if not username or not password:
            st.error("Please enter both your call sign and secret code.")
            return False
        if not username_exists(username):
            st.error("Stranger alert! Call sign not found. Ready to enroll?")
            return False
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("Invalid secret code. Please try again.")
            return False
        st.session_state.user = username
        st.session_state.logged_in = True
        st.success(f"Welcome aboard, Commander {username}!")
        st.rerun()
        return True
    return False

def signup_block():
    st.header("🛠️ Launch New Mission: Create Your Commander Profile")

    if st.session_state.get("registration_success", False):
        st.success("🎉 Congratulations, Commander! Your profile is locked and loaded. Return to the Launchpad to start your mission.")
        if st.button("Back to Login"):
            st.session_state.registration_success = False
            st.session_state.show_register_form = False
            st.session_state.mode = "login"
            st.rerun()
        return

    username = st.text_input("Pick Your Call Sign (Username)", key="reg_username")
    password = st.text_input("Choose a Secret Code (Password)", type="password", key="reg_password")
    password_confirm = st.text_input("Confirm Secret Code", type="password", key="reg_password_confirm")

    if st.button("Enroll Me!"):
        if not username or not password or not password_confirm:
            st.error("All fields are mission critical. Fill them all.")
            return
        if password != password_confirm:
            st.error("Codes don't match. Recheck your secret code.")
            return
        if username_exists(username):
            st.error("Call sign already taken by another commander. Choose a different one.")
            return
        # ✅ Password strength validation
        if not is_strong_password(password):
            st.error("Secret code too weak! Must be at least 8 chars & include uppercase, lowercase, number, and symbol.")
            return
        table.create({
            "User": username,
            "Task": "[User Created]",
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Completed": True,
            "PasswordHash": hash_password(password)
        })
        st.session_state.registration_success = True
        st.session_state.show_register_form = True
        st.rerun()
