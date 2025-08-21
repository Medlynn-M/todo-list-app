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
    return any(r['fields'].get("User") == username for r in records)

def get_user_hash(username):
    records = table.all()
    for record in records:
        if record['fields'].get("User") == username:
            return record['fields'].get("PasswordHash")
    return None

def reset_user_password(username, new_password):
    records = table.all()
    for record in records:
        if record['fields'].get("User") == username:
            table.update(record['id'], {"PasswordHash": hash_password(new_password)})
            return True
    return False

def get_tasks(user, date_str):
    records = table.all()
    tasks = []
    seen = set()
    for record in records:
        fields = record['fields']
        if fields.get('User') == user and fields.get('Date') == date_str and fields.get('Task') != "[User Created]":
            task = fields.get('Task')
            if task and task.lower() not in seen:
                seen.add(task.lower())
                tasks.append({
                    'id': record['id'],
                    'task': task,
                    'completed': fields.get('Completed', False),
                    'time_slot': fields.get('Time', ''),
                })
    return sorted(tasks, key=lambda x: (x['time_slot'], x['task']))

def update_task(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(text, date_str, time_str, user):
    table.create({
        "User": user,
        "Task": text,
        "Date": date_str,
        "Time": time_str,
        "Completed": False,
    })

def delete_task(record_id):
    table.delete(record_id)

def login_ui():
    st.header("🚀 Login")
    username = st.text_input("Call Sign", key="login_username")
    password = st.text_input("Secret Code", key="login_password", type="password")

    if st.button("Launch", key="login_launch"):
        if not username or not password:
            st.error("Enter Call Sign and Code")
            return
        if not username_exists(username):
            st.error("Call Sign not found")
            return
        if get_user_hash(username) != hash_password(password):
            st.error("Incorrect Code")
            return
        st.session_state['user'] = username
        st.session_state['logged_in'] = True
        st.experimental_rerun()

    col1, col2 = st.columns([3, 1])
    with col2:
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
        if st.button("Forgot Code?", key="login_forgot"):
            st.session_state['forgot_mode'] = True
            st.experimental_rerun()

SECURITY_QUESTIONS = [
    "Which starship did you command?",
    "Favorite planet",
    "Childhood nickname",
    "Who inspires you",
    "Add your own",
]

def signup_ui():
    st.header("Create Account")
    if st.session_state.get('registration_success', False):
        st.success("Account created")
        if st.button("Back to Login", key="signup_back"):
            st.session_state['registration_success'] = False
            st.session_state['show_register'] = False
            st.experimental_rerun()
        return

    username = st.text_input("Call Sign", key="signup_username")
    password = st.text_input("Password", key="signup_password", type="password")
    st.markdown("<span style='color:#30A8B8;'>Password requires 8+ chars, uppercase, lowercase, digit & symbol</span>", unsafe_allow_html=True)
    confirm_password = st.text_input("Confirm Password", key="signup_confirm", type="password")
    question = st.selectbox("Security question", options=SECURITY_QUESTIONS, key="signup_question")
    if question == "Add your own":
        question = st.text_input("Custom question", key="signup_custom_question")
    answer = st.text_input("Security answer", key="signup_answer", type="password")
    st.markdown("<span style='color:#E2681E;'>Save your question and answer! These are required for recovery.</span>", unsafe_allow_html=True)
    
    if st.button("Sign Up", key="signup_submit"):
        if not username or not password or not confirm_password or not answer:
            st.error("All fields required")
            return
        if password != confirm_password:
            st.error("Passwords do not match")
            return
        if username_exists(username):
            st.error("Call Sign already taken")
            return
        if not is_strong_password(password):
            st.error("Password too weak")
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
        st.session_state['registration_success'] = True
        st.session_state['show_register'] = True
        st.experimental_rerun()

def forgot_password_ui():
    st.header("Commander Code Recovery")
    if 'forgot_stage' not in st.session_state or st.session_state['forgot_stage'] is None:
        st.session_state['forgot_stage'] = 'username'

    if st.session_state['forgot_stage'] == 'username':
        username_input = st.text_input("Commander Sign", key="forgot_username")
        if st.button("Verify", key="forgot_verify"):
            if not username_input:
                st.error("Please enter your Commander Sign")
            elif not username_exists(username_input):
                st.error("Commander Sign not found")
            else:
                record = next(
                    (r for r in table.all() 
                        if r['fields'].get('User') == username_input 
                        and r['fields'].get('Task') == '[User Created]'
                        and r['fields'].get('SecurityQuestion')),
                    None)
                if not record:
                    st.error("Security question missing for this account. Please contact support.")
                else:
                    st.session_state['reset_record'] = record
                    st.session_state['username_for_reset'] = username_input
                    st.session_state['forgot_stage'] = 'security'
                    st.experimental_rerun()

    elif st.session_state['forgot_stage'] == 'security':
        record = st.session_state['reset_record']
        question = record['fields']['SecurityQuestion']
        expected = record['fields']['SecurityAnswerHash']
        answer_input = st.text_input(f"Security question: {question}", key="forgot_answer", type="password")
        if st.button("Submit", key="forgot_submit"):
            if not answer_input:
                st.error("Please provide an answer")
            elif hash_answer(answer_input) != expected:
                st.error("Incorrect answer")
            else:
                st.session_state['forgot_stage'] = 'reset'
                st.experimental_rerun()
        if st.button("Back", key="forgot_back_to_username"):
            st.session_state['forgot_stage'] = 'username'
            st.experimental_rerun()

    elif st.session_state['forgot_stage'] == 'reset':
        new_password = st.text_input("New Password", key="forgot_new_password", type="password")
        confirm_password = st.text_input("Confirm Password", key="forgot_confirm_password", type="password")
        st.caption("Password must be at least 8 characters with uppercase, lowercase, digit and symbol.")
        if st.button("Reset", key="forgot_reset"):
            if not new_password or not confirm_password:
                st.error("Please fill all fields")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            elif not is_strong_password(new_password):
                st.error("Password too weak")
            else:
                username = st.session_state['username_for_reset']
                if reset_user_password(username, new_password):
                    st.success("Password reset successful! Please log in.")
                    for k in ['forgot_stage','reset_record','username_for_reset']:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.session_state['forgot_mode'] = False
                    st.experimental_rerun()
        if st.button("Back", key="forgot_back_to_security"):
            st.session_state['forgot_stage'] = 'security'
            st.experimental_rerun()

    st.markdown("---")
    if st.button("Back to Login", key="forgot_back_to_login"):
        st.session_state['forgot_mode'] = False
        for k in ['forgot_stage','reset_record','username_for_reset']:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()


def logout():
    st.session_state['user'] = ''
    st.session_state['logged_in'] = False
    st.experimental_rerun()


for k,v in {
    'user':'',
    'logged_in':False,
    'mode':'login',
    'show_register':False,
    'registration_success':False,
    'forgot_mode':False,
    'forgot_stage':None,
    'reset_record':None,
    'username_for_reset':None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


st.sidebar.title("Mission Control")

if not st.session_state['logged_in']:
    if st.session_state['forgot_mode']:
        forgot_password_ui()
        st.stop()
    else:
        login_ui()
        if not st.session_state['show_register'] and not st.session_state['registration_success']:
            if st.button("Sign Up", key="btn_signup"):
                st.session_state['show_register'] = True
                st.experimental_rerun()
        if st.session_state['show_register']:
            signup_ui()
            if st.button("Back to Login", key="btn_back_login"):
                st.session_state['show_register'] = False
                st.experimental_rerun()
        st.stop()

st.sidebar.title(f"Commander {st.session_state['user']}")
if st.sidebar.button("Abort", key="btn_abort"):
    logout()

selected_date = st.sidebar.date_input("Mission Date", datetime.today())
date_str = selected_date.strftime('%Y-%m-%d')

st.markdown("""
<style>
.stButton > button {
    padding: 0.3rem 0.6rem !important;
    font-size: 1.0rem !important;
    border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state['user']}'s Mission Control")

tasks = get_tasks(st.session_state['user'], date_str)
if not tasks:
    st.info("No missions logged for today.")

for idx, task in enumerate(tasks):
    cols = st.columns([10,1])
    with cols[0]:
        label = f"{'✅' if task['completed'] else '⬜'} {task['task']} {task.get('time_slot','')}"
        checked = st.checkbox(label, key=f"task_checkbox_{task['id']}", value=task['completed'])
        if checked != task['completed']:
            update_task(task['id'], checked)
            st.experimental_rerun()
    with cols[1]:
        if st.button("Delete", key=f"btn_del_{task['id']}", help="Delete task"):
            delete_task(task['id'])
            st.experimental_rerun()

time_input = st.text_input("Enter mission time (e.g., 3:15 PM or 15:15)", key="text_time_input")

def validate_time(t):
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(t.strip(), fmt).strftime("%I:%M %p")
        except:
            pass
    return None

time_value = "12:00 PM"
if time_input:
    val = validate_time(time_input)
    if val:
        time_value = val
    else:
        st.error("Invalid time format. Use 3:15 PM or 15:15.")

new_task = st.text_input("Add new mission", key="text_new_task")
if st.button("Add Mission", key="btn_add_mission"):
    if new_task.strip():
        add_task(new_task.strip(), date_str, time_value, st.session_state['user'])
        st.success(f"Mission scheduled for {time_value} added.")
        st.experimental_rerun()
