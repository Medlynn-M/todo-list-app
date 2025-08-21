import streamlit as st
from pyairtable import Table
from datetime import datetime
import hashlib
import random
import re  # for password validation

# Airtable config
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# Password hashing
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ✅ Strong password policy check
def is_strong_password(password: str) -> bool:
    """Check if password meets complexity requirements"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Uppercase
        return False
    if not re.search(r"[a-z]", password):  # Lowercase
        return False
    if not re.search(r"[0-9]", password):  # Digit
        return False
    if not re.search(r"[^A-Za-z0-9]", password):  # Special char
        return False
    return True

# ✅ Case-sensitive username check
def username_exists(username):
    all_records = table.all()
    usernames = {r.get("fields", {}).get("User", "") for r in all_records}
    return username in usernames   # exact match

def get_user_password_hash(username):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User", "") == username:  # exact match
            return fields.get("PasswordHash", None)
    return None

def get_tasks_for_date_and_user(date_str, user):
    all_records = table.all()
    seen = set()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        # ✅ exact match for user
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

# ---------------- LOGIN UI ----------------
def login_block():
    st.header("👋 Welcome Back, Commander!")
    username = st.text_input("🛰️ Enter Your Call Sign (Case-Sensitive Username)", key="login_username")
    password = st.text_input("🔐 Enter Your Secret Code (Password)", type="password", key="login_password")
    login_clicked = st.button("🚀 Launch Mission Control")
    if login_clicked:
        if not username or not password:
            st.error("⚠️ Mission Incomplete! Enter both your Call Sign and Secret Code to proceed.")
            return False
        if not username_exists(username):
            st.error("🛰️ Unknown Call Sign Detected! No Commander registered with that name.")
            return False
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("❌ Access Denied! Secret Code mismatch. Mission Control cannot authenticate this call sign.")
            return False
        st.session_state.user = username
        st.session_state.logged_in = True
        st.success(f"🌟 Access Granted! Welcome aboard, Commander {username}. Mission Control is now online!")
        st.rerun()
        return True
    return False

# ---------------- SIGNUP UI ----------------
def signup_block():
    st.header("🛠️ Launch New Mission: Create Your Commander Profile")

    if st.session_state.get("registration_success", False):
        st.success("🎉 Mission Success! Your Commander profile is now secured in Mission Control. Prepare for liftoff!")
        if st.button("🔑 Return to Launchpad"):
            st.session_state.registration_success = False
            st.session_state.show_register_form = False
            st.session_state.mode = "login"
            st.rerun()
        return

    username = st.text_input("🌌 Choose Your Call Sign (Case-Sensitive Username)", key="reg_username")
    password = st.text_input("🔐 Forge Your Secret Code (Password)", type="password", key="reg_password")
    st.caption("🛡️ Secret Code must be mission-grade: Minimum 8 characters, containing at least one uppercase star, one lowercase planet, a number for coordinates, and a special symbol to unlock hyperspace portals.")
    password_confirm = st.text_input("🔐 Confirm Your Secret Code", type="password", key="reg_password_confirm")

    if st.button("✨ Enlist Me, Mission Control!"):
        if not username or not password or not password_confirm:
            st.error("⚠️ Every input is mission critical, Commander. Complete all fields to proceed.")
            return
        if password != password_confirm:
            st.error("⚠️ Secret Codes don't match! Resynchronize your access key.")
            return
        if username_exists(username):
            st.error("❌ Call Sign already claimed by another Commander. Choose a unique identifier.")
            return
        if not is_strong_password(password):
            st.error("⚠️ Secret Code too weak! Your access key must be battle-ready: "
                     "at least 8 characters, include an UPPERCASE star, a lowercase planet, "
                     "a number for coordinates, and a special symbol to unlock hyperspace. 🌌")
            return

        # Save to Airtable
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

# ---------------- LOGOUT ----------------
def logout():
    st.session_state.user = ""
    st.session_state.logged_in = False
    st.rerun()

# ---------------- SESSION STATE INIT ----------------
if "user" not in st.session_state:
    st.session_state.user = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "mode" not in st.session_state:
    st.session_state.mode = "login"
if "show_register_form" not in st.session_state:
    st.session_state.show_register_form = False
if "registration_success" not in st.session_state:
    st.session_state.registration_success = False

# ---------------- SIDEBAR AUTH ----------------
st.sidebar.title("🛸 Commander Authentication Center")

if not st.session_state.logged_in:
    login_block()

    if not st.session_state.show_register_form and not st.session_state.registration_success:
        if st.button("✨ New here? Enlist your Call Sign"):
            st.session_state.show_register_form = True
            st.rerun()

    if st.session_state.show_register_form:
        st.markdown("---")
        signup_block()
        if not st.session_state.registration_success:
            if st.button("🔙 Already a Commander? Return to Launchpad"):
                st.session_state.show_register_form = False
                st.rerun()

    st.stop()

# ---------------- MAIN APP ----------------
st.sidebar.title(f"🧑‍🚀 Commander {st.session_state.user}")
if st.sidebar.button("⏹️ Abort Mission: Log Out"):
    logout()

selected_date = st.sidebar.date_input("🎯 Select Mission Date", datetime.today())
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

st.title(f"🧑‍🚀 Commander {st.session_state.user}'s Mission Control")
st.markdown("#### Every mission counts. Let’s conquer today’s challenges! 🚀")

tasks = get_tasks_for_date_and_user(selected_date_str, st.session_state.user)

if not tasks:
    st.info("🛰️ No missions logged for this date. Ready to add a new objective for your legacy, Commander?")

for task in tasks:
    completed = task.get("completed", False)
    label_text = task["task"]
    if completed:
        label = f"<span class='completed-label'>🌟 Completed: {label_text}</span>"
    else:
        label = f"<span class='incomplete-label'>💡 Pending: {label_text}</span>"

    col1, col2 = st.columns([9, 1])
    with col1:
        new_completed = st.checkbox("", value=completed, key=f"{task['id']}_checkbox")
        st.markdown(label, unsafe_allow_html=True)
        if new_completed != completed:
            update_task_completion(task["id"], new_completed)
            st.rerun()
    with col2:
        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
        if st.button("🗑️", key=f"{task['id']}_delete", help="Delete this mission objective"):
            delete_task(task["id"])
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### 📝 Set a new mission:")
new_task = st.text_input("What objective shall we pursue today, Commander?")

st.markdown('<div class="add-btn">', unsafe_allow_html=True)
if st.button("🚀 Accept Mission"):
    if new_task.strip():
        add_task(new_task.strip(), selected_date_str, st.session_state.user)
        st.success("✅ Mission accepted! Onward, Commander!")
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
---
**Tip:** Use ✅ to mark a mission complete, or 🗑️ to remove it.  
Stay sharp, Commander. The galaxy is counting on you! 🌌
""")
