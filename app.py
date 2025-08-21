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
        and re.search(r'[A-Z]', password)
        and re.search(r'[a-z]', password)
        and re.search(r'\d', password)
        and re.search(r'\W', password)
    )

def username_exists(username):
    records = table.all()
    return any(r['fields'].get("User") == username for r in records)

def get_user_hash(username):
    records = table.all()
    for r in records:
        if r['fields'].get("User") == username:
            return r['fields'].get("PasswordHash")
    return None

def reset_user_password(username, new_password):
    records = table.all()
    for r in records:
        if r['fields'].get("User") == username:
            table.update(r['id'], {"PasswordHash": hash_password(new_password)})
            return True
    return False

def get_tasks(user, date_str):
    records = table.all()
    tasks = []
    seen = set()
    for r in records:
        f = r['fields']
        if f.get('User') == user and f.get('Date') == date_str and f.get('Task') != "[User Created]":
            task = f.get('Task')
            if task and task.lower() not in seen:
                seen.add(task.lower())
                tasks.append({
                    'id': r['id'],
                    'task': task,
                    'completed': f.get('Completed', False),
                    'time_slot': f.get('TimeSlot', '')
                })
    return sorted(tasks, key=lambda x: (x['time_slot'], x['task']))

def update_task(id, completed):
    table.update(id, {"Completed": completed})

def add_task(text, date_str, time_str, user):
    table.create({
        "User": user,
        "Task": text,
        "Date": date_str,
        "TimeSlot": time_str,
        "Completed": False,
    })

def delete_task(id):
    table.delete(id)


def login_ui():
    st.header("🚀 Commander Access")
    username = st.text_input("🛰️ Call Sign", key="login_username")
    password = st.text_input("🛡️ Secret Code", key="login_password", type="password")

    # Launch button first with unique key
    if st.button("🎮 Launch", key="login_launch_btn"):
        if not username or not password:
            st.error("Enter your Sign and Code")
            return
        if not username_exists(username):
            st.error("Unknown Sign")
            return
        if get_user_hash(username) != hash_password(password):
            st.error("Wrong Code")
            return
        st.session_state['user'] = username
        st.session_state['logged_in'] = True
        st.rerun()

    cols = st.columns([3,1])
    with cols[1]:
        st.markdown("""
            <style>
            div[data-testid="column"]:nth-child(2) > button:first-of-type {
                background:none!important;
                border:none!important;
                box-shadow:none!important;
                color:#209cee!important;
                text-decoration:underline!important;
                font-size:0.85rem!important;
                padding:0!important;
                min-width:0!important;
                height:28px!important;
                margin:-12px 0 8px 0;
                float:right;
                cursor:pointer;
            }
            div[data-testid="column"]:nth-child(2) > button:first-of-type:hover {
                color:#1479cc!important;
            }
            </style>
        """, unsafe_allow_html=True)
        if st.button("Forgot Code?", key="login_forgot_btn"):
            st.session_state['forgot_mode'] = True
            st.rerun()


SECURITY_QUESTIONS = [
    'Which starship did you command?',
    'Favorite planet',
    'Childhood nickname',
    'Who inspires you',
    'Add your own',
]

def signup_ui():
    st.header("🛠️ Create Commander Profile")
    if st.session_state.get('registration_success', False):
        st.success("Profile created")
        if st.button("Back", key="signup_back_btn"):
            st.session_state['registration_success'] = False
            st.session_state['show_register_form'] = False
            st.rerun()
        return

    username = st.text_input("Call Sign", key="signup_username")
    password = st.text_input("Secret Code", key="signup_password", type="password")
    st.markdown('<span style="color:#30A8B8;">Password must be 8+ chars, uppercase, lowercase, digit & symbol</span>', unsafe_allow_html=True)
    confirm_password = st.text_input("Confirm Code", key="signup_confirm_password", type="password")
    question = st.selectbox("Security Question", options=SECURITY_QUESTIONS, key="signup_question")
    if question == 'Add your own':
        question = st.text_input("Custom Question", key="signup_custom_question")
    answer = st.text_input("Answer", key="signup_answer", type="password")
    st.markdown('<span style="color:#E2681E;">Save your security question and answer—only way to recover your account</span>', unsafe_allow_html=True)

    if st.button("Enlist", key="signup_enlist_btn"):
        if not username or not password or not confirm_password or not answer:
            st.error("Complete all fields")
            return
        if password != confirm_password:
            st.error("Codes do not match")
            return
        if username_exists(username):
            st.error("Call Sign taken")
            return
        if not is_strong_password(password):
            st.error("Password too weak")
            return
        table.create({
            "User": username,
            "PasswordHash": hash_password(password),
            "SecurityQuestion": question,
            "SecurityAnswerHash": hash_answer(answer),
            "Date": datetime.today().strftime('%Y-%m-%d'),
            "Task": "[User Created]",
            "Completed": True,
        })
        st.session_state['registration_success'] = True
        st.session_state['show_register_form'] = True
        st.rerun()


def forgot_password_ui():
    st.header("Commander Code Recovery")

    if 'forgot_stage' not in st.session_state or st.session_state['forgot_stage'] is None:
        st.session_state['forgot_stage'] = 'username'

    if st.session_state['forgot_stage'] == 'username':
        uname = st.text_input("Commander Sign", key="reset_username")
        if st.button("Verify", key="forgot_ver_btn"):
            if not uname:
                st.error("Enter your Commander Sign")
            elif not username_exists(uname):
                st.error("Commander Sign not found")
            else:
                record = next((r for r in table.all() if r['fields'].get('User') == uname))
                if not record or 'SecurityQuestion' not in record['fields']:
                    st.error("Security question not found")
                else:
                    st.session_state['reset_record'] = record
                    st.session_state['username_for_reset'] = uname
                    st.session_state['forgot_stage'] = 'security'
                    st.rerun()

    elif st.session_state['forgot_stage'] == 'security':
        record = st.session_state['reset_record']
        question = record['fields']['SecurityQuestion']
        expected_answer = record['fields'].get('SecurityAnswerHash', '')
        ans = st.text_input(f"Security Question: {question}", key="security_answer", type="password")
        if st.button("Submit", key="forgot_sec_submit_btn"):
            if not ans:
                st.error("Please provide an answer")
            elif hash_answer(ans) != expected_answer:
                st.error("Incorrect answer")
            else:
                st.session_state['forgot_stage'] = 'reset'
                st.rerun()
        if st.button("Back", key="forgot_sec_back_btn"):
            st.session_state['forgot_stage'] = 'username'
            st.rerun()

    elif st.session_state['forgot_stage'] == 'reset':
        new_pw = st.text_input("New Secret Code", key="reset_new_password", type="password")
        confirm_pw = st.text_input("Confirm Secret Code", key="reset_confirm_password", type="password")
        st.caption("Password must be 8+ characters with uppercase, lowercase, digit, and symbol")
        if st.button("Reset Password", key="forgot_reset_submit_btn"):
            if not new_pw or not confirm_pw:
                st.error("Please fill all fields")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match")
            elif not is_strong_password(new_pw):
                st.error("Password too weak")
            else:
                uname = st.session_state['username_for_reset']
                if reset_user_password(uname, new_pw):
                    st.success("Password reset successful! Please login.")
                    for k in ['forgot_stage', 'reset_record', 'username_for_reset']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.session_state['forgot_mode'] = False
                    st.rerun()
        if st.button("Back", key="forgot_reset_back_btn"):
            st.session_state['forgot_stage'] = 'security'
            st.rerun()

    st.markdown("---")
    if st.button("Back to Login", key="forgot_final_back_btn"):
        st.session_state['forgot_mode'] = False
        for k in ['forgot_stage', 'reset_record', 'username_for_reset']:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()


def logout():
    st.session_state['user'] = ''
    st.session_state['logged_in'] = False
    st.rerun()


for key, default in {
    'user': '',
    'logged_in': False,
    'mode': 'login',
    'show_register_form': False,
    'registration_success': False,
    'forgot_mode': False,
    'forgot_stage': None,
    'reset_record': None,
    'username_for_reset': None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


st.sidebar.title("Mission Control")

if not st.session_state['logged_in']:
    if st.session_state['forgot_mode']:
        forgot_password_ui()
        st.stop()
    else:
        login_ui()
        if not st.session_state['show_register_form'] and not st.session_state['registration_success']:
            if st.button("New? Enlist", key="main_enlist_btn"):
                st.session_state['show_register_form'] = True
                st.rerun()
        if st.session_state['show_register_form']:
            signup_ui()
            if st.button("Back to Login", key="signup_back_to_login_btn"):
                st.session_state['show_register_form'] = False
                st.rerun()
        st.stop()

st.sidebar.title(f"Commander {st.session_state['user']}")
if st.sidebar.button("Abort Mission", key="sidebar_abort_btn"):
    logout()

selected_date = st.sidebar.date_input("Select Date", datetime.today())
date_str = selected_date.strftime('%Y-%m-%d')

st.markdown("""
<style>
.stButton > button {
    padding: 0.25rem 0.6rem!important;
    font-size: 0.9rem!important;
    min-width: 120px!important;
    height: 32px!important;
    border-radius: 6px!important;
}
</style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state['user']}'s Mission Control")

tasks = get_tasks(st.session_state['user'], date_str)
if not tasks:
    st.info("No missions today.")

for idx, task in enumerate(tasks):
    cols = st.columns([9, 1])
    with cols[0]:
        label = f"{'✅' if task['completed'] else '⬜'} {task['task']} {task.get('time_slot','')}"
        checked = st.checkbox(label, key=f"task_checkbox_{task['id']}", value=task['completed'])
        if checked != task['completed']:
            update_task(task['id'], checked)
            st.rerun()
    with cols[1]:
        if st.button("🗑", key=f"delete_task_btn_{task['id']}", help="Delete task"):
            delete_task(task['id'])
            st.rerun()

time_input = st.text_input("Enter mission time (e.g. 3:15 PM or 15:15)", key="mission_time_input")

def validate_time(t):
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(t.strip(), fmt).strftime("%I:%M %p")
        except:
            continue
    return None

time_val = None
if time_input:
    time_val = validate_time(time_input)
    if not time_val:
        st.error("Invalid time format. Use '3:15 PM' or '15:15'.")
else:
    time_val = "12:00 PM"

new_task = st.text_input("Add new mission", key="new_task_input")
if st.button("Launch Mission", key="launch_mission_btn"):
    if new_task.strip() and time_val:
        add_task(new_task.strip(), date_str, time_val, st.session_state['user'])
        st.success(f"Mission scheduled at {time_val} added.")
        st.rerun()
