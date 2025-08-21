import streamlit as st
from pyairtable import Table
from datetime import datetime
import hashlib
import random
import re  # for regex validation

# Airtable config
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_TOKEN = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# Utility functions for hashing and password checks
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def hash_answer(ans):
    return hashlib.sha256(ans.strip().lower().encode()).hexdigest()

def is_strong_password(pw):
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"[a-z]", pw):
        return False
    if not re.search(r"[0-9]", pw):
        return False
    if not re.search(r"[^A-Za-z0-9]", pw):
        return False
    return True

# Checking user existence and fetching data
def username_exists(username):
    all_records = table.all()
    usernames = {r.get("fields", {}).get("User", "") for r in all_records}
    return username in usernames

def get_user_password_hash(username):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User") == username:
            return fields.get("PasswordHash", None)
    return None

def reset_user_password(username, new_password):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User") == username:
            table.update(r['id'], {"PasswordHash": hash_password(new_password)})
            return True
    return False

# Task handling
def get_tasks_for_date_and_user(date_str, user):
    all_records = table.all()
    seen = set()
    tasks = []
    for r in all_records:
        fields = r.get("fields", {})
        if (fields.get("Date") == date_str and 
            fields.get("User") == user and 
            fields.get("Task") != "[User Created]"):
            task_text = fields.get("Task", "")
            if task_text.lower() not in seen:
                seen.add(task_text.lower())
                tasks.append({
                    "id": r['id'],
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
        "User": user,
    })

def delete_task(record_id):
    table.delete(record_id)

# Login UI
def login_block():
    st.header("👋 Welcome Back, Commander!")

    username = st.text_input(
        "🛰️ Enter Your Call Sign",
        key="login_username",
        help="🛸 Case-sensitive: 'StarLord' and 'starlord' are different."
    )
    password = st.text_input("🔐 Enter Your Secret Code", type="password", key="login_password")

    # Layout for "Forgot Secret Code?" aligned right below password input
    cols = st.columns([3, 1])
    with cols[1]:
        st.markdown("""
            <style>
            .forgot-link {
                font-size: 0.85em;
                color: #ff4b4b;
                text-decoration: underline;
                cursor: pointer;
                padding-top: 0;
                margin-top: -12px;
                display: block;
                float: right;
            }
            .forgot-link:hover {
                color: #cc0000;
            }
            </style>
            <a class="forgot-link" href="#">❓ Forgot Secret Code?</a>
            """, unsafe_allow_html=True)
        if st.button(" ", key="forgot_button", help="Click to reset your secret code"):
            st.session_state.forgot_mode = True
            st.experimental_rerun()

    # Global button style for smaller buttons
    st.markdown("""
        <style>
        .stButton>button {
            font-size: 0.85rem !important;
            padding: 0.25rem 0.6rem !important;
            min-width: 140px;
            border-radius: 6px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("🚀 Launch Mission Control", key="login_launch"):
        if not username or not password:
            st.error("⚠️ Enter your Call Sign and Secret Code.")
            return
        if not username_exists(username):
            st.error("🛰️ Unknown Call Sign.")
            return
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("❌ Secret Code mismatch.")
            return
        st.session_state.user = username
        st.session_state.logged_in = True
        st.success(f"Welcome aboard, Commander {username}!")
        st.experimental_rerun()

# Signup UI
SECURITY_QUESTIONS = [
    "What is your favorite spacecraft?",
    "What planet would you visit first?",
    "What was your childhood nickname?",
    "Who is your all-time hero?",
    "Custom (type your own)",
]

def signup_block():
    st.header("🛠️ Launch New Mission: Create Your Commander Profile")

    if st.session_state.get("registration_success"):
        st.success("🎉 Profile created! Prepare for launch.")
        if st.button("Back to Login", key="signup_back"):
            st.session_state.registration_success = False
            st.session_state.show_register_form = False
            st.experimental_rerun()
        return

    username = st.text_input("🌌 Choose Your Call Sign",
                             key="signup_username",
                             help="Case-sensitive.")

    password = st.text_input("🔐 Choose Your Secret Code", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Secret Code", type="password", key="signup_password_confirm")

    question = st.selectbox("🛡️ Security Question", options=SECURITY_QUESTIONS)
    if question == "Custom (type your own)":
        question = st.text_input("Enter your custom security question")

    answer = st.text_input("Security Answer (case-insensitive)", type="password", key="signup_answer")

    st.markdown("""<span style="color:orange; font-weight:bold;">⚠️ Save your security question and answer! It’s the only way to recover your access.</span>""", unsafe_allow_html=True)

    if st.button("✨ Enlist Commander", key="signup_submit"):
        if not username or not password or not confirm_password or not answer:
            st.error("Complete all fields.")
            return
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
        if username_exists(username):
            st.error("Username already taken.")
            return
        if not is_strong_password(password):
            st.error("Password must be at least 8 chars with uppercase, lowercase, digit, and symbol.")
            return

        table.create({
            "User": username,
            "PasswordHash": hash_password(password),
            "SecurityQuestion": question,
            "PasswordHash": hash_password(password),
            "SecurityAnswerHash": hash_answer(answer),
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Task": "[User Created]",
            "Completed": True,
        })
        st.session_state.registration_success = True
        st.session_state.show_register_form = True
        st.experimental_rerun()

# Forgot Password UI
def forgot_password_block():
    st.header("🔑 Reset Your Secret Code")

    if "security_verified" not in st.session_state:
        st.session_state.security_verified = False
    if "reset_username" not in st.session_state:
        st.session_state.reset_username = ""
    if "user_record" not in st.session_state:
        st.session_state.user_record = None

    username = st.text_input("🌌 Enter Your Call Sign", key="reset_username")

    if st.button("📡 Verify Identity", key="verify_identity"):
        if not username:
            st.error("Enter username")
            return
        if not username_exists(username):
            st.error("Unknown username")
            return
        all_records = table.all()
        user_record = next((r for r in all_records if r.get("fields", {}).get("User") == username), None)
        if not user_record or "SecurityQuestion" not in user_record.get("fields"):
            st.error("No security question set.")
            return
        st.session_state.reset_username = username
        st.session_state.user_record = user_record
        st.session_state.security_verified = False
        st.experimental_rerun()

    if st.session_state.reset_username and not st.session_state.security_verified:
        question = st.session_state.user_record['fields']["SecurityQuestion"]
        answer_hash = st.session_state.user_record['fields'].get("SecurityAnswerHash", "")

        answer = st.text_input(f"Answer the security question:\n*{question}*", type="password", key="security_answer")

        if st.button("🔓 Verify Answer", key="verify_answer"):
            if not answer:
                st.error("Answer required.")
                return
            if hash_answer(answer) != answer_hash:
                st.error("Incorrect answer.")
                return
            st.session_state.security_verified = True
            st.experimental_rerun()

    if st.session_state.security_verified:
        new_password = st.text_input("New Secret Code", type="password", key="new_password")
        confirm_password = st.text_input("Confirm New Secret Code", type="password", key="confirm_new_password")
        st.caption("Must be min 8 chars with uppercase, lowercase, digit, and symbol.")

        if st.button("Reset Secret Code", key="reset_password"):
            if not new_password or not confirm_password:
                st.error("Complete all fields.")
                return
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
            if not is_strong_password(new_password):
                st.error("Password does not meet requirements.")
                return
            if reset_user_password(st.session_state.reset_username, new_password):
                st.success("Password reset successful! Return to login.")
                st.session_state.security_verified = False
                st.session_state.reset_username = ""
                st.session_state.user_record = None
                if st.button("Back to Login", key="back_to_login"):
                    st.session_state.forgot_mode = False
                    st.experimental_rerun()
            else:
                st.error("Error resetting password, contact support.")

# Logout
def logout():
    st.session_state.user = ""
    st.session_state.logged_in = False
    st.experimental_rerun()

# Session initialization defaults
for key, default in {
    "user": "",
    "logged_in": False,
    "mode": "login",
    "show_register_form": False,
    "registration_success": False,
    "forgot_mode": False,
    "security_verified": False,
    "reset_username": "",
    "user_record": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Sidebar and main app control
st.sidebar.title("🛸 Commander Authentication Center")

if not st.session_state.logged_in:
    if st.session_state.forgot_mode:
        forgot_password_block()
        if st.button("Back to Login", key="back_to_login_sidebar"):
            st.session_state.forgot_mode = False
            st.experimental_rerun()
        st.stop()
    else:
        login_block()
        if not st.session_state.show_register_form and not st.session_state.registration_success:
            # Put forgot before enlist button
            if st.button("❓ Forgot Secret Code?", key="forgot_code_name_sidebar"):
                st.session_state.forgot_mode = True
                st.experimental_rerun()
            if st.button("✨ New here? Enlist your Call Sign", key="enlist_name_sidebar"):
                st.session_state.show_register_form = True
                st.experimental_rerun()
        if st.session_state.show_register_form:
            st.markdown("---")
            signup_block()
            if not st.session_state.registration_success:
                if st.button("Back to Login", key="back_to_login_signup"):
                    st.session_state.show_register_form = False
                    st.experimental_rerun()
        st.stop()

# Main App after login
st.sidebar.title(f"🧑‍🚀 Commander {st.session_state.user}")
if st.sidebar.button("Abort Mission", key="logout_button"):
    logout()

selected_date = st.sidebar.date_input("Choose Mission Date", datetime.today())
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.sidebar.markdown(f"#### 🗓️ Missions for {selected_date_str}")

st.markdown("""
<style>
.stButton > button {
    font-size: 0.85rem !important;
    padding: 5px 15px !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state.user}'s Mission Control")
st.markdown("Let’s conquer today’s challenges!")

tasks = get_tasks_for_date_and_user(selected_date_str, st.session_state.user)

if not tasks:
    st.info("No missions for today. Add a new objective!")

for task in tasks:
    completed = task["completed"]
    label = f"✅ {task['task']}" if completed else f"🔲 {task['task']}"

    cols = st.columns([9,1])
    with cols[0]:
        new_completed = st.checkbox("", value=completed, key=f"cb_{task['id']}")
        st.write(label)
        if new_completed != completed:
            update_task_completion(task['id'], new_completed)
            st.experimental_rerun()
    with cols[1]:
        if st.button("🗑️", key=f"del_{task['id']}", help="Delete mission"):
            delete_task(task['id'])
            st.experimental_rerun()

new_task = st.text_input("Set a new mission:")
if st.button("Add Mission"):
    if new_task.strip():
        add_task(new_task.strip(), selected_date_str, st.session_state.user)
        st.success("Mission added!")
        st.experimental_rerun()
