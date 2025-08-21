import streamlit as st
from pyairtable import Table
from datetime import datetime
import hashlib
import re

# Airtable configuration
AIRTABLE_BASE_ID = st.secrets["airtable"]["base_id"]
AIRTABLE_TABLE_NAME = st.secrets["airtable"]["table_name"]
AIRTABLE_API_KEY = st.secrets["airtable"]["token"]

table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# Helper functions
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

def username_exists(username):
    records = table.all()
    return any(r["fields"].get("User") == username for r in records)

def get_user_password_hash(username):
    records = table.all()
    for r in records:
        if r["fields"].get("User") == username:
            return r["fields"].get("PasswordHash")
    return None

def reset_user_password(username, new_password):
    records = table.all()
    for r in records:
        if r["fields"].get("User") == username:
            table.update(r["id"], {"PasswordHash": hash_password(new_password)})
            return True
    return False

def get_tasks(user, date_str):
    records = table.all()
    tasks = []
    seen = set()
    for r in records:
        f = r["fields"]
        if f.get("User") == user and f.get("Date") == date_str and f.get("Task") != "[User Created]":
            task = f.get("Task")
            if task and task.lower() not in seen:
                seen.add(task.lower())
                tasks.append({
                    "id": r["id"],
                    "task": task,
                    "completed": f.get("Completed", False),
                    "time_slot": f.get("TimeSlot", "")
                })
    return sorted(tasks, key=lambda x: (x["time_slot"], x["task"]))

def update_task(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(text, date_str, time_str, user):
    table.create({
        "User": user,
        "Task": text,
        "Date": date_str,
        "TimeSlot": time_str,
        "Completed": False,
    })

def delete_task(record_id):
    table.delete(record_id)


def login_ui():
    st.header("🚀 Commander Access")
    username = st.text_input("🛰️ Call Sign", key="login_username", help="Case sensitive")
    password = st.text_input("🛡️ Secret Code", key="login_password", type="password")

    # Launch button first, with key
    if st.button("🎮 Launch", key="login_launch_btn"):
        if not username or not password:
            st.error("🚧 Enter your Sign and Code.")
            return
        if not username_exists(username):
            st.error("🚫 Unknown Sign.")
            return
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("🛑 Wrong Code.")
            return
        st.session_state["user"] = username
        st.session_state["logged_in"] = True
        st.rerun()

    # Forgot Code? button aligned right below password input
    cols = st.columns([3, 1])
    with cols[1]:
        st.markdown(
            """
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
            """,
            unsafe_allow_html=True,
        )
        if st.button("Forgot Code?", key="login_forgot_code_btn"):
            st.session_state["forgot_mode"] = True
            st.rerun()

    st.markdown(
        """
    <style>
    .stButton > button {
        padding: 0.25rem 0.6rem !important;
        font-size: 0.88rem !important;
        min-width: 125px !important;
        height: 32px !important;
        border-radius: 6px !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


SECURITY_QUESTIONS = [
    "Which starship did you command?",
    "Favorite planet to conquer?",
    "Your childhood nickname?",
    "Who inspires you most?",
    "Add your own",
]

def signup_ui():
    st.header("🛠️ Create Commander Profile")
    if st.session_state.get("registration_success", False):
        st.success("🎉 Profile created")
        if st.button("🛸 Back", key="signup_back_btn"):
            st.session_state["registration_success"] = False
            st.session_state["show_register_form"] = False
            st.rerun()
        return
    username = st.text_input("🪐 Call Sign", key="signup_username", help="Unique & case sensitive")
    password = st.text_input("🔐 Set Code", key="signup_password", type="password")
    st.markdown(
        "<span style='color:#30d6ff'>🛡️ 8+ chars, uppercase, lowercase, number & symbol e.g. <code>P@ssw0rd!</code></span>",
        unsafe_allow_html=True,
    )
    confirm_password = st.text_input(
        "🔐 Confirm Code", key="signup_confirm_password", type="password"
    )
    question = st.selectbox("🛡 Choose Question", options=SECURITY_QUESTIONS, key="signup_selectbox_q")
    if question == "Add your own":
        question = st.text_input("Custom Question", key="signup_custom_question")
    answer = st.text_input("Answer", key="signup_answer", type="password")
    st.markdown(
        "<span style='color:orange'>⚠️ Save question & answer! Only recovery method.</span>",
        unsafe_allow_html=True,
    )
    if st.button("✍️ Enlist", key="signup_enlist_btn"):
        if not username or not password or not confirm_password or not answer:
            st.error("Complete all fields")
            return
        if password != confirm_password:
            st.error("Codes mismatch")
            return
        if username_exists(username):
            st.error("Sign taken")
            return
        if not is_strong_password(password):
            st.error("Weak code")
            return
        table.create(
            {
                "User": username,
                "PasswordHash": hash_password(password),
                "SecurityQuestion": question,
                "SecurityAnswerHash": hash_answer(answer),
                "Date": datetime.today().strftime("%Y-%m-%d"),
                "Task": "[User Created]",
                "Completed": True,
            }
        )
        st.session_state["registration_success"] = True
        st.session_state["show_register_form"] = True
        st.rerun()

def forgot_password_ui():
    st.header("🛡 Commander Code Recovery")
    if "forgot_stage" not in st.session_state or st.session_state["forgot_stage"] is None:
        st.session_state["forgot_stage"] = "username"
    if st.session_state["forgot_stage"] == "username":
        username_in = st.text_input("Commander Sign", key="reset_username")
        if st.button("🚨 Verify", key="forgot_verify_btn"):
            if not username_in:
                st.error("Enter your Sign!")
            elif not username_exists(username_in):
                st.error("Sign not found!")
            else:
                record = next(
                    r for r in table.all() if r["fields"].get("User") == username_in
                )
                if not record or "SecurityQuestion" not in record["fields"]:
                    st.error("No security question found.")
                else:
                    st.session_state["reset_record"] = record
                    st.session_state["username_for_reset"] = username_in
                    st.session_state["forgot_stage"] = "security"
                    st.rerun()
    elif st.session_state["forgot_stage"] == "security":
        record = st.session_state["reset_record"]
        question = record["fields"]["SecurityQuestion"]
        expected_hash = record["fields"].get("SecurityAnswerHash", "")
        answer_in = st.text_input(
            f"Answer: {question}", key="security_answer", type="password"
        )
        if st.button("✅ Submit", key="forgot_submit_answer_btn"):
            if not answer_in:
                st.error("Answer required.")
            elif hash_answer(answer_in) != expected_hash:
                st.error("Wrong answer.")
            else:
                st.session_state["forgot_stage"] = "reset"
                st.rerun()
        if st.button("⬅ Back", key="forgot_back_btn_security"):
            st.session_state["forgot_stage"] = "username"
            st.rerun()
    elif st.session_state["forgot_stage"] == "reset":
        new_pw = st.text_input("New Code", key="new_password", type="password")
        confirm_pw = st.text_input("Confirm Code", key="confirm_password", type="password")
        st.caption("Min 8 chars, uppercase, lowercase, digit & symbol.")
        if st.button("🛡 Reset", key="forgot_reset_btn"):
            if not new_pw or not confirm_pw:
                st.error("Complete all fields.")
            elif new_pw != confirm_pw:
                st.error("Codes mismatch.")
            elif not is_strong_password(new_pw):
                st.error("Code too weak.")
            else:
                username = st.session_state["username_for_reset"]
                if reset_user_password(username, new_pw):
                    st.success("Code reset! Please login.")
                    for key in ["forgot_stage", "reset_record", "username_for_reset"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state["forgot_mode"] = False
                    st.rerun()
        if st.button("⬅ Back", key="forgot_back_btn_reset"):
            st.session_state["forgot_stage"] = "security"
            st.rerun()

    st.markdown("---")
    if st.button("⬅ Back to Login", key="forgot_back_to_login_btn"):
        st.session_state["forgot_mode"] = False
        for key in ["forgot_stage", "reset_record", "username_for_reset"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

def logout():
    st.session_state["user"] = ""
    st.session_state["logged_in"] = False
    st.rerun()

for key, default in {
    "user": "",
    "logged_in": False,
    "mode": "login",
    "show_register_form": False,
    "registration_success": False,
    "forgot_mode": False,
    "forgot_stage": None,
    "reset_record": None,
    "username_for_reset": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.sidebar.title("🚀 Mission Command")

if not st.session_state["logged_in"]:
    if st.session_state["forgot_mode"]:
        forgot_password_ui()
        if st.button("⬅ Back to Login", key="forgot_outer_back_to_login_btn"):
            st.session_state["forgot_mode"] = False
            for key in ["forgot_stage", "reset_record", "username_for_reset"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.stop()
    else:
        login_ui()
        if not st.session_state["show_register_form"] and not st.session_state["registration_success"]:
            if st.button("🌟 New Commander?", key="main_new_commander_btn"):
                st.session_state["show_register_form"] = True
                st.rerun()
        if st.session_state["show_register_form"]:
            signup_ui()
            if st.button("⬅ Back to Login", key="signup_back_to_login_btn"):
                st.session_state["show_register_form"] = False
                st.rerun()
        st.stop()

st.sidebar.title(f"Commander {st.session_state['user']}")
if st.sidebar.button("🚪 Abort Mission", key="sidebar_abort_btn"):
    logout()

selected_date = st.sidebar.date_input("Select Mission Date", datetime.today())
date_str = selected_date.strftime("%Y-%m-%d")

st.markdown(
    """
<style>
.stButton > button {
    padding: 0.25rem 0.6rem !important;
    font-size: 0.88rem !important;
    min-width: 125px !important;
    height: 32px !important;
    border-radius: 6px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title(f"Commander {st.session_state['user']}'s Mission Control")

tasks = get_tasks(st.session_state["user"], date_str)
if not tasks:
    st.info("No missions recorded for today.")

for idx, task in enumerate(tasks):
    cols = st.columns([9, 1])
    with cols[0]:
        label = f"{'✅' if task['completed'] else '⬜'} {task['task']} {task.get('time_slot', '')}"
        checked = st.checkbox(label, value=task["completed"], key=f"task_checkbox_{task['id']}")
        if checked != task["completed"]:
            update_task(task["id"], checked)
            st.rerun()
    with cols[1]:
        if st.button("🗑", key=f"del_btn_{task['id']}", help="Delete mission"):
            delete_task(task["id"])
            st.rerun()

time_input = st.text_input("Enter mission time (e.g., 3:15 pm or 15:15)", key="main_time_input")

def validate_time(t):
    for fmt in ["%I:%M %p", "%H:%M"]:
        try:
            return datetime.strptime(t.strip(), fmt).strftime("%I:%M %p")
        except:
            pass
    return None

time_str = "12:00 PM"
if time_input:
    val = validate_time(time_input)
    if val:
        time_str = val
    else:
        st.error("Enter valid time in 12-hour (3:15 PM) or 24-hour (15:15) format.")

new_task = st.text_input("Add new mission", key="main_new_task")
if st.button("🚀 Submit Mission", key="main_submit_btn"):
    if new_task.strip() and time_str:
        add_task(new_task.strip(), date_str, time_str, st.session_state["user"])
        st.success(f"Mission scheduled at {time_str} added.")
        st.rerun()
