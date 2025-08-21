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

def login_block():
    st.header("👋 Welcome Back, Commander!")

    username = st.text_input("🛰️ Enter Your Call Sign",
                             key="login_username",
                             help="🛸 Case-sensitive: 'StarLord' and 'starlord' are different.")

    password = st.text_input("🔐 Enter Your Secret Code", type="password", key="login_password")

    cols = st.columns([3, 1])
    with cols[1]:
        st.markdown(
            """
            <style>
            div[data-testid="column"]:nth-child(2) button:first-of-type {
                background: none !important;
                border: none !important;
                box-shadow: none !important;
                color: #3384ff !important;
                text-decoration: underline !important;
                font-size: 0.85rem !important;
                padding: 0 !important;
                min-width: 0 !important;
                height: 24px !important;
                margin-top: -12px;
                margin-bottom: 12px;
                float: right;
                cursor: pointer;
            }
            div[data-testid="column"]:nth-child(2) button:first-of-type:hover {
                color: #0059cc !important;
                text-decoration: underline;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        forgot_click = st.button("Forgot your code?", key="forgot_code_small")

    if forgot_click:
        st.session_state.forgot_mode = True
        st.experimental_rerun()

    # Global button size adjustment
    st.markdown("""
    <style>
    .stButton > button {
        font-size: 0.87rem !important;
        padding: 0.25rem 0.6rem !important;
        min-width: 140px !important;
        height: 30px !important;
        border-radius: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("🚀 Launch Mission Control", key="launch_mc_small"):
        if not username or not password:
            st.error("Please enter your Call Sign and Secret Code.")
            return
        if not username_exists(username):
            st.error("Unknown Call Sign.")
            return
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error("Incorrect Secret Code.")
            return
        st.session_state.user = username
        st.session_state.logged_in = True
        st.experimental_rerun()

SECURITY_QUESTIONS = [
    "What is your favorite spacecraft?",
    "What planet would you visit first?",
    "What was your childhood nickname?",
    "Who is your favorite hero?",
    "Custom question",
]

def signup_block():
    st.header("🛠️ Create Your Commander Profile")

    if st.session_state.get("registration_success"):
        st.success("Profile created! Ready to launch.")
        if st.button("Back to Login", key="back_to_login_post_signup"):
            st.session_state.registration_success = False
            st.session_state.show_register_form = False
            st.experimental_rerun()
        return

    username = st.text_input("🏷️ Choose your call sign:",
                             key="signup_username",
                             help="Case-sensitive.")

    password = st.text_input("🔑 Choose Secret Code:",
                             type="password",
                             key="signup_password")

    confirm_password = st.text_input("🔑 Confirm Secret Code:",
                                    type="password",
                                    key="signup_confirm_password")

    question = st.selectbox("🛡️ Security question:", options=SECURITY_QUESTIONS)
    if question == "Custom question":
        question = st.text_input("Your custom question:")

    answer = st.text_input("Answer:",
                          type="password",
                          key="signup_answer")

    st.markdown(
        "<span style='color:orange; font-weight:bold;'>"
        "Save your security question & answer carefully — it's your only way to recover access."
        "</span>", unsafe_allow_html=True)

    if st.button("Create Profile", key="signup_create"):
        if not username or not password or not confirm_password or not answer:
            st.error("Please complete all fields.")
            return
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
        if username_exists(username):
            st.error("That call sign is taken.")
            return
        if not is_strong_password(password):
            st.error("Password must be 8+ chars with uppercase, lowercase, digit, and symbol.")
            return
        
        table.create({
            "User": username,
            "PasswordHash": hash_password(password),
            "SecurityQuestion": question,
            "PasswordHash": hash_password(password),
            "SecurityAnswer": hash_answer(answer),
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Task": "[User Created]",
            "Completed": True,
        })

        st.session_state.registration_success = True
        st.session_state.show_register_form = True
        st.experimental_rerun()

def forgot_password_flow():
    st.header("🔑 Reset your Secret Code")

    if "security_verified" not in st.session_state:
        st.session_state.security_verified = False
    if "reset_username" not in st.session_state:
        st.session_state.reset_username = ""
    if "user_record" not in st.session_state:
        st.session_state.user_record = None

    username = st.text_input("Enter your Call Sign:", key="reset_username")

    if st.button("Verify Identity", key="verify_identity"):
        if not username:
            st.error("Enter your Call Sign.")
            return
        if not username_exists(username):
            st.error("Unknown Call Sign.")
            return
        
        all_records = table.all()
        user_record = next((r for r in all_records if r.get("fields", {}).get("User") == username), None)
        if not user_record or "SecurityQuestion" not in user_record.get("fields"):
            st.error("No security question setup.")
            return

        st.session_state.reset_username = username
        st.session_state.user_record = user_record
        st.session_state.security_verified = False
        st.experimental_rerun()

    if st.session_state.reset_username and not st.session_state.security_verified:
        question = st.session_state.user_record['fields']["SecurityQuestion"]
        answer_hash = st.session_state.user_record['fields'].get("SecurityAnswer", "")

        answer = st.text_input(f"Answer the question: *{question}*", type="password", key="security_answer")

        if st.button("Verify Answer", key="verify_answer"):
            if not answer:
                st.error("Answer is required.")
                return
            if hash_answer(answer) != answer_hash:
                st.error("Incorrect answer.")
                return
            st.session_state.security_verified = True
            st.experimental_rerun()

    if st.session_state.security_verified:
        new_password = st.text_input("Enter new Secret Code:", type="password", key="new_password")
        confirm_password = st.text_input("Confirm new Secret Code:", type="password", key="confirm_new_password")
        st.caption("Minimum 8 characters, uppercase, lowercase, digit, and symbol.")

        if st.button("Reset Secret Code", key="reset_code_button"):
            if not new_password or not confirm_password:
                st.error("Complete all fields.")
                return
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
            if not is_strong_password(new_password):
                st.error("Password does not meet criteria.")
                return
            if reset_user_password(st.session_state.reset_username, new_password):
                st.success("Secret Code reset successful!")
                st.session_state.security_verified = False
                st.session_state.reset_username = ""
                st.session_state.user_record = None
                if st.button("Return to Login"):
                    st.session_state.forgot_mode = False
                    st.experimental_rerun()
            else:
                st.error("Reset failed. Contact support.")

def logout():
    st.session_state.user = ""
    st.session_state.logged_in = False
    st.experimental_rerun()

# Initialize session state variables
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

st.sidebar.title("🚀 Command Center")

if not st.session_state.logged_in:
    if st.session_state.forgot_mode:
        forgot_password_flow()
        if st.button("Back to Login"):
            st.session_state.forgot_mode = False
            st.experimental_rerun()
        st.stop()
    else:
        login_block()
        if not st.session_state.show_register_form and not st.session_state.registration_success:
            if st.button("Forgot your code?"):
                st.session_state.forgot_mode = True
                st.experimental_rerun()
            if st.button("New Commander? Enlist here"):
                st.session_state.show_register_form = True
                st.experimental_rerun()
        if st.session_state.show_register_form:
            st.markdown("---")
            signup_block()
            if st.button("Back to Login"):
                st.session_state.show_register_form = False
                st.experimental_rerun()
        st.stop()

st.sidebar.title(f"Commander {st.session_state.user}")
if st.sidebar.button("Abort Mission"):
    logout()

selected_date = st.sidebar.date_input("Mission Date", datetime.today())
selected_date_str = selected_date.strftime("%Y-%m-%d")

st.markdown("""
<style>
.stButton > button {
    font-size: 0.85rem !important;
    padding: 0.25rem 0.6rem !important;
    min-width: 140px !important;
    height: 32px !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state.user}'s Mission Control")

tasks = get_tasks_for_date_and_user(selected_date_str, st.session_state.user)

if not tasks:
    st.info("No missions for today! Add your command.")

for task in tasks:
    completed = task["completed"]
    label = f"✅ {task['task']}" if completed else f"☐ {task['task']}"

    cols = st.columns([9, 1])
    with cols[0]:
        new_completed = st.checkbox("", value=completed, key=f"chk_{task['id']}")
        st.write(label)
        if new_completed != completed:
            update_task_completion(task['id'], new_completed)
            st.experimental_rerun()
    with cols[1]:
        if st.button("🗑️", key=f"del_{task['id']}"):
            delete_task(task['id'])
            st.experimental_rerun()

new_task = st.text_input("New Mission:")
if st.button("Add Mission"):
    if new_task.strip():
        add_task(new_task.strip(), selected_date_str, st.session_state.user)
        st.success("Mission added!")
        st.experimental_rerun()
