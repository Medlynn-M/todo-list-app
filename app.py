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
        f = record['fields']
        if f.get('User') == user and f.get('Date') == date_str and f.get('Task') != "[User Created]":
            task = f.get('Task')
            if task and task.lower() not in seen:
                seen.add(task.lower())
                tasks.append({
                    'id': record['id'],
                    'task': task,
                    'completed': f.get('Completed', False),
                    'time_slot': f.get('Time', ''),
                })
    return sorted(tasks, key=lambda x: (x['time_slot'], x['task']))

def update_task(id, completed):
    table.update(id, {"Completed": completed})

def add_task(text, date_str, time_str, user):
    table.create({
        "User": user,
        "Task": text,
        "Date": date_str,
        "Time": time_str,
        "Completed": False,
    })

def delete_task(id):
    table.delete(id)

def login_ui():
    st.header("Login")
    username = st.text_input("Call Sign", key="login_username")
    password = st.text_input("Password", key="login_password", type="password")

    if st.button("Launch", key="login_launch"):
        if not username or not password:
            st.error("Enter Call Sign and Password")
            return
        if not username_exists(username):
            st.error("Call Sign not found")
            return
        if get_user_hash(username) != hash_password(password):
            st.error("Incorrect Password")
            return
        st.session_state['user'] = username
        st.session_state['logged_in'] = True
        st.rerun()

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
            font-size:0.85!important;
            padding:0!important;
            min-width:0!important;
            height:28!important;
            margin:-12 0 8 0;
            float:right;
            cursor:pointer;
        }
        div[data-testid="column"]:nth-child(2) > button:first-of-type:hover {
            color:#147cc!important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("Forgot Password?", key="forgot_password_btn"):
            st.session_state['forgot_mode'] = True
            st.rerun()

SECURITY_QUESTIONS = [
    "Your first pet's name?",
    "Mother's maiden name?",
    "Favorite color?",
    "Make your own",
]

def signup_ui():
    st.header("Create Account")
    if st.session_state.get('registration_success', False):
        st.success("Account created")
        if st.button("Back to Login", key="signup_back"):
            st.session_state['registration_success'] = False
            st.session_state['show_register'] = False
            st.rerun()
        return
    username = st.text_input("Call Sign", key="signup_username")
    password = st.text_input("Password", key="signup_password", type="password")
    st.markdown('<span style="color:blue;">Password must be at least 8 characters and include uppercase, lowercase, numbers, and symbols</span>', unsafe_allow_html=True)
    confirm_password = st.text_input("Confirm Password", key="signup_confirm", type="password")
    question = st.selectbox("Choose Security Question", options=SECURITY_QUESTIONS, key="signup_question")
    if question == "Make your own":
        question = st.text_input("Custom Security Question", key="signup_custom_question")
    answer = st.text_input("Answer", key="signup_answer", type="password")
    st.markdown('<span style="color:red;">Save your question and answer for future recovery</span>', unsafe_allow_html=True)
    if st.button("Sign Up", key="signup_submit"):
        if not username or not password or not confirm_password or not answer:
            st.error("All fields are required")
            return
        if password != confirm_password:
            st.error("Passwords do not match")
            return
        if not is_strong_password(password):
            st.error("Password is too weak")
            return
        if username_exists(username):
            st.error("Call Sign already taken")
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
        st.session_state['show_register'] = True
        st.rerun()

def forgot_password_ui():
    st.header("Password Recovery")
    if 'forgot_stage' not in st.session_state or st.session_state['forgot_stage'] is None:
        st.session_state['forgot_stage'] = 'username'

    # stage: username
    if st.session_state['forgot_stage'] == 'username':
        uname = st.text_input("Enter your Call Sign", key='recover_username')
        if st.button("Verify", key='recover_verify'):
            if not uname:
                st.error("Please enter your Call Sign")
            elif not username_exists(uname):
                st.error("Call Sign not found")
            else:
                record = next((r for r in table.all() if r['fields'].get('User')==uname and r['fields'].get('Task')=='[User Created]' and r['fields'].get('SecurityQuestion')), None)
                if not record:
                    st.error("No security question set for this account.")
                else:
                    st.session_state['recover_record'] = record
                    st.session_state['recover_stage_username'] = uname  # new session key, not the text_input's key
                    st.session_state['forgot_stage'] = 'security'
                    st.rerun()
    if st.session_state['forgot_stage']=='security':
        record = st.session_state['recover_record']
        question = record['fields']['SecurityQuestion']
        expected_answer_hash = record['fields']['SecurityAnswerHash']
        ans = st.text_input(f"Security Question: {question}", key='recover_answer', type='password')
        if st.button("Submit", key='recover_submit'):
            if not ans:
                st.error("Please provide answer")
            elif hash_answer(ans)!=expected_answer_hash:
                st.error("Incorrect answer")
            else:
                st.session_state['forgot_stage'] = 'reset'
                st.rerun()
        if st.button("Back", key='recover_back_to_username'):
            st.session_state['forgot_stage'] = 'username'
            st.rerun()
    if st.session_state['forgot_stage']=='reset':
        new_password = st.text_input("New Password", key='recover_new_password', type='password')
        confirm_password = st.text_input("Confirm Password", key='recover_confirm_password', type='password')
        st.caption("Password must be at least 8 characters including uppercase, lowercase, digit and symbol")
        if st.button("Reset", key='recover_reset'):
            if not new_password or not confirm_password:
                st.error("All fields are required")
            elif new_password!=confirm_password:
                st.error("Passwords do not match")
            elif not is_strong_password(new_password):
                st.error("Password is too weak")
            else:
                # Use recover_stage_username, not recover_username from text_input
                if reset_user_password(st.session_state['recover_stage_username'], new_password):
                    st.success("Password reset successful! Please login")
                    for key in ['forgot_stage','recover_record','recover_stage_username']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state['forgot_mode'] = False
                    st.rerun()
        if st.button("Back", key='recover_back_to_security'):
            st.session_state['forgot_stage'] = 'security'
            st.rerun()
    st.markdown("---")
    if st.button("Back to Login", key='recover_back_to_login'):
        st.session_state['forgot_mode'] = False
        for key in ['forgot_stage','recover_record','recover_stage_username']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

def logout():
    st.session_state['user'] = ''
    st.session_state['logged_in'] = False
    st.rerun()

for key, default in {
    'user': '',
    'logged_in': False,
    'mode': 'login',
    'show_register': False,
    'registration_success': False,
    'forgot_mode': False,
    'forgot_stage': None,
    'recover_record': None,
    'recover_stage_username': None,
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
        if not st.session_state['show_register'] and not st.session_state['registration_success']:
            if st.button("Sign Up", key='signup_show'):
                st.session_state['show_register'] = True
                st.rerun()
        if st.session_state['show_register']:
            signup_ui()
            if st.button("Back to Login", key='signup_back'):
                st.session_state['show_register'] = False
                st.rerun()
        st.stop()

st.sidebar.title(f"Commander {st.session_state['user']}")
if st.sidebar.button("Abort Mission", key='logout'):
    logout()

selected_date = st.sidebar.date_input("Mission Date", datetime.today())
date_str = selected_date.strftime('%Y-%m-%d')

st.markdown("""
<style>
.stButton button {
    padding: 8px 16px;
    font-size: 14px;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state['user']}'s Control")

tasks = get_tasks(st.session_state['user'], date_str)
if not tasks:
    st.info("No missions recorded")

for idx, task in enumerate(tasks):
    cols = st.columns([10,1])
    with cols[0]:
        label = f"{'✅' if task['completed'] else '⬜'} {task['task']} {task.get('time_slot','')}"
        checked = st.checkbox(label, key=f'task_{task["id"]}', value=task['completed'])
        if checked != task['completed']:
            update_task(task['id'], checked)
            st.rerun()
    with cols[1]:
        if st.button("Delete", key=f'del_{task["id"]}'):
            delete_task(task['id'])
            st.rerun()

time_input = st.text_input("Enter mission time (e.g. 3:15 PM or 15:15)", key='time_input')

def validate_time(t):
    for fmt in ['%I:%M %p', '%H:%M']:
        try:
            return datetime.strptime(t.strip(), fmt).strftime('%I:%M %p')
        except:
            pass
    return None

time_value = '12:00 PM'
if time_input:
    tv = validate_time(time_input)
    if tv:
        time_value = tv
    else:
        st.error("Please enter valid time format e.g. 3:15 PM or 15:15")

new_task = st.text_input('Add new mission', key='new_task')

if st.button('Add Mission', key='add_mission_btn'):
    if new_task.strip():
        add_task(new_task.strip(), date_str, time_value, st.session_state['user'])
        st.success(f'Mission scheduled at {time_value} added.')
        st.rerun()
