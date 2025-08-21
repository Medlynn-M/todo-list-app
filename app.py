import streamlit as st
from pyairtable import Table
from datetime import datetime
import hashlib
import re

# Airtable configuration (matches your schema!)
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_API_KEY = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def hash_answer(answer):
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()

def is_strong_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"\W", password)
    )

# User/account ops
def username_exists(username):
    for record in table.all():
        if record["fields"].get("User") == username:
            return True
    return False

def get_user_password_hash(username):
    for record in table.all():
        if record["fields"].get("User") == username:
            return record["fields"].get("PasswordHash")
    return None

def reset_user_password(username, new_password):
    for record in table.all():
        if record["fields"].get("User") == username:
            table.update(record["id"], {"PasswordHash": hash_password(new_password)})
            return True
    return False

# Task management
def get_tasks(user, date_str):
    tasks = []
    seen = set()
    for record in table.all():
        f = record["fields"]
        if (
            f.get("User") == user
            and f.get("Date") == date_str
            and f.get("Task") != "[User Created]"
        ):
            task_text = f.get("Task")
            if task_text and task_text.lower() not in seen:
                seen.add(task_text.lower())
                tasks.append(
                    {
                        "id": record["id"],
                        "task": task_text,
                        "completed": f.get("Completed", False),
                    }
                )
    return sorted(tasks, key=lambda x: x["task"])

def update_task(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(text, date_str, user):
    table.create(
        {
            "User": user,
            "Task": text,
            "Date": date_str,
            "Completed": False,
        }
    )

def delete_task(record_id):
    table.delete(record_id)

# Login UI
def login_ui():
    st.header("🚀 Commander Access Portal")
    username = st.text_input("🛰️ Call Sign", key="login_username", help="Case sensitive")
    password = st.text_input("🛡️ Secret Code", type="password", key="login_password")

    # Place "Forgot Code?" small link-like button right-aligned under password input
    cols = st.columns([3, 1])
    with cols[1]:
        st.markdown("""
            <style>
                div[data-testid="column"]:nth-child(2) > button:first-of-type {
                    background: none !important;
                    border: none !important;
                    box-shadow: none !important;
                    color: #209cee !important;
                    text-decoration: underline !important;
                    font-size: 0.85rem !important;
                    padding: 0 !important;
                    min-width: 0 !important;
                    height: 28px !important;
                    margin: -12px 0 8px 0;
                    float: right;
                    cursor: pointer;
                }
                div[data-testid="column"]:nth-child(2) > button:first-of-type:hover {
                    color: #1479cc !important;
                }
            </style>
        """, unsafe_allow_html=True)
        if st.button("Forgot Code?", key="forgot_code_btn"):
            st.session_state["forgot_mode"] = True
            st.rerun()

    st.markdown("""
    <style>
        .stButton > button {
            padding: 0.25rem 0.6rem !important;
            font-size: 0.88rem !important;
            min-width: 125px !important;
            height: 32px !important;
            border-radius: 6px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if st.button("🎮 Launch Mission", key="login_btn"):
        if not username or not password:
            st.error("🚧 Enter your Call Sign and Secret Code.")
            return
        if not username_exists(username):
            st.error("🚫 No such Call Sign registered, Commander.")
            return
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("🛑 Incorrect Secret Code. Try again or recover.")
            return
        st.session_state["user"] = username
        st.session_state["logged_in"] = True
        st.rerun()

SECURITY_QUESTIONS = [
    "Which starship did you command?",
    "Favorite planet to conquer?",
    "Your childhood nickname?",
    "Who inspires you most in the fleet?",
    "Add your own",
]

def signup_ui():
    st.header("🛠️ Create Your Commander Profile")
    if st.session_state.get("registration_success", False):
        st.success("🎉 Commander profile created. Prepare for launch!")
        if st.button("🛸 Return to Launchpad"):
            st.session_state["registration_success"] = False
            st.session_state["show_register_form"] = False
            st.rerun()
        return

    username = st.text_input("🪐 Call Sign", key="signup_username", help="Unique and case sensitive")
    password = st.text_input("🔐 Set your Secret Code", key="signup_password", type="password")

    # Themed password instruction below password field only
    st.markdown(
        "<span style='color:#30d6ff;'>"
        "🛡️ Secret Code for interstellar clearance: at least 8 characters, with uppercase, lowercase, a number, and a symbol (e.g. <code>P@ssw0rd!</code>)"
        "</span>", unsafe_allow_html=True)

    confirm_password = st.text_input("🔐 Confirm Secret Code", key="signup_confirm_password", type="password")
    question = st.selectbox("🛡️ Choose a Security Question", options=SECURITY_QUESTIONS)
    if question == "Add your own":
        question = st.text_input("Custom Security Question")
    answer = st.text_input("Security Answer", type="password", key="signup_answer")

    st.markdown(
        "<span style='color:orange;'>"
        "⚠️ Safeguard your security question and answer. It's your only backup if your code is lost in deep space."
        "</span>", unsafe_allow_html=True)

    if st.button("✍️ Enlist as Commander"):
        if not username or not password or not confirm_password or not answer:
            st.error("🚧 All fields must be completed to join the fleet.")
            return
        if password != confirm_password:
            st.error("🚫 Secret Codes do not match.")
            return
        if username_exists(username):
            st.error("🚫 Call Sign already in fleet logs.")
            return
        if not is_strong_password(password):
            st.error("🛑 Secret Code too weak for mission parameters.")
            return

        table.create({
            "User": username,
            "PasswordHash": hash_password(password),
            "SecurityQuestion": question,
            "SecurityAnswerHash": hash_answer(answer),
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Task": "[User Created]",
            "Completed": True,
        })
        st.session_state["registration_success"] = True
        st.session_state["show_register_form"] = True
        st.rerun()

def forgot_password_ui():
    st.header("🛡 Commander Code Recovery")
    if "security_verified" not in st.session_state:
        st.session_state["security_verified"] = False
    if "reset_username" not in st.session_state:
        st.session_state["reset_username"] = ""
    if "user_record" not in st.session_state:
        st.session_state["user_record"] = None

    username = st.text_input("Commander Call Sign", key="reset_username")
    if st.button("🚨 Verify Identity"):
        if not username:
            st.error("🚧 Enter your Call Sign.")
            return
        if not username_exists(username):
            st.error("🚫 Commander not found in base.")
            return
        records = table.all()
        record = next((r for r in records if r["fields"].get("User") == username), None)
        if not record or "SecurityQuestion" not in record["fields"]:
            st.error("No Security Question on record.")
            return
        st.session_state["reset_username"] = username
        st.session_state["user_record"] = record
        st.session_state["security_verified"] = False
        st.rerun()

    if st.session_state["reset_username"] and not st.session_state["security_verified"]:
        question = st.session_state["user_record"]["fields"]["SecurityQuestion"]
        expected_hash = st.session_state["user_record"]["fields"].get("SecurityAnswerHash", "")
        answer = st.text_input(f"Security Answer for Mission Clearance:\n{question}", key="security_answer", type="password")

        if st.button("✅ Submit Answer"):
            if not answer:
                st.error("Security answer required.")
                return
            if hash_answer(answer) != expected_hash:
                st.error("Incorrect answer.")
                return
            st.session_state["security_verified"] = True
            st.rerun()

    if st.session_state["security_verified"]:
        new_password = st.text_input("Set new Secret Code", key="new_password", type="password")
        confirm_password = st.text_input("Confirm new Secret Code", key="confirm_password", type="password")
        st.caption("Min 8 chars, with uppercase, lowercase, number and symbol.")
        if st.button("🛡 Reset Code"):
            if not new_password or not confirm_password:
                st.error("Complete all reset fields.")
                return
            if new_password != confirm_password:
                st.error("Secret Codes do not match.")
                return
            if not is_strong_password(new_password):
                st.error("New Secret Code does not meet mission readiness.")
                return
            if reset_user_password(st.session_state["reset_username"], new_password):
                st.success("Secret Code reset. Proceed to mission login.")
                st.session_state["security_verified"] = False
                st.session_state["reset_username"] = ""
                st.session_state["user_record"] = None
                if st.button("⬅ Return to Mission Login"):
                    st.session_state["forgot_mode"] = False
                    st.rerun()

def logout():
    st.session_state["user"] = ""
    st.session_state["logged_in"] = False
    st.rerun()

# Session state defaults
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

st.sidebar.title("🚀 Mission Command")

if not st.session_state["logged_in"]:
    if st.session_state["forgot_mode"]:
        forgot_password_ui()
        if st.button("⬅ Back to Login"):
            st.session_state["forgot_mode"] = False
            st.rerun()
        st.stop()
    else:
        login_ui()
        if not st.session_state["show_register_form"] and not st.session_state["registration_success"]:
            if st.button("🌟 New Commander?"):
                st.session_state["show_register_form"] = True
                st.rerun()
        if st.session_state["show_register_form"]:
            signup_ui()
            if st.button("⬅ Back to Login"):
                st.session_state["show_register_form"] = False
                st.rerun()
        st.stop()

st.sidebar.title(f"Commander {st.session_state['user']}")
if st.sidebar.button("🚪 Abort Mission"):
    logout()

selected_date = st.sidebar.date_input("Mission Date", datetime.today())
date_str = selected_date.strftime("%Y-%m-%d")

st.markdown("""
<style>
.stButton > button {
    padding: 0.25rem 0.6rem !important;
    font-size: 0.88rem !important;
    min-width: 125px !important;
    height: 32px !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state['user']}'s Mission Control")

tasks = get_tasks(st.session_state['user'], date_str)
if not tasks:
    st.info("No mission logs for today.")

for task in tasks:
    cols = st.columns([9, 1])
    with cols[0]:
        label = f"✅ {task['task']}" if task['completed'] else f"⬜ {task['task']}"
        checkbox = st.checkbox(label, value=task["completed"], key=f"task_{task['id']}")
        if checkbox != task["completed"]:
            update_task(task["id"], checkbox)
            st.rerun()
    with cols[1]:
        if st.button("🗑", key=f"del_{task['id']}", help="Delete mission"):
            delete_task(task["id"])
            st.rerun()

mission_input = st.text_input("Add new mission today:")
if st.button("🚀 Submit Mission"):
    if mission_input.strip():
        add_task(mission_input.strip(), date_str, st.session_state["user"])
        st.success("Mission uploaded to Control.")
        st.rerun()
