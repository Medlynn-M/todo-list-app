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

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def hash_answer(answer):
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"\W", password):
        return False
    return True

# User functions
def username_exists(username):
    records = table.all()
    return any(record['fields'].get('User') == username for record in records)

def get_user_password_hash(username):
    records = table.all()
    for record in records:
        if record['fields'].get('User') == username:
            return record['fields'].get('PasswordHash')
    return None

def reset_user_password(username, new_password):
    records = table.all()
    for record in records:
        if record['fields'].get('User') == username:
            table.update(record['id'], {'PasswordHash': hash_password(new_password)})
            return True
    return False

# Task functions
def get_tasks_for_user_and_date(user, date_str):
    tasks = []
    seen = set()
    records = table.all()
    for record in records:
        fields = record.get('fields', {})
        if (fields.get('User') == user and fields.get('Date') == date_str and 
                fields.get('Task') != '[User Created]'):
            task_text = fields.get('Task')
            task_lower = task_text.lower()
            if task_lower not in seen:
                seen.add(task_lower)
                tasks.append({'id': record['id'], 'task': task_text, 'completed': fields.get('Completed', False)})
    return sorted(tasks, key=lambda x: x['task'])

def update_task_completion(record_id, completed):
    table.update(record_id, {"Completed": completed})

def add_task(task, date_str, user):
    table.create({"Task": task, "Date": date_str, "Completed": False, "User": user})

def delete_task(record_id):
    table.delete(record_id)

# Login UI
def login_ui():
    st.header("🚀 Commander Access Portal")
    username = st.text_input('🛰️ Enter your Call Sign', key='login_username', help='Captain, your unique ID is Case Sensitive.')
    password = st.text_input('🛡️ Enter your Secret Code', key='login_password', type='password')
    
    # "Forgot Code?" button - right aligned below password input
    cols = st.columns([3,1])
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
        if st.button('Forgot Code?', key='forgot_code_btn'):
            st.session_state['forgot_mode'] = True
            st.rerun()
    
    # Button styling for smaller buttons globally
    st.markdown("""
        <style>
        .stButton > button {
            padding: 0.25rem 0.6rem !important;
            font-size: 0.88rem !important;
            min-width: 140px !important;
            height: 32px !important;
            border-radius: 6px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if st.button('🎮 Launch Mission Control', key='launch_mission'):
        if not username or not password:
            st.error('⚠️ Enter your Call Sign and Secret Code.')
            return
        if not username_exists(username):
            st.error('🚫 Call Sign not found.')
            return
        pw_hash = get_user_password_hash(username)
        if pw_hash != hash_password(password):
            st.error('🛑 Incorrect Secret Code.')
            return
        st.session_state['user'] = username
        st.session_state['logged_in'] = True
        st.rerun()

# Signup UI
SECURITY_QUESTIONS = [
    "Which starship did you command?",
    "Favorite planet to conquer?",
    "Your childhood nickname?",
    "Who inspires you most in the fleet?",
    "Add your own",
]

def signup_ui():
    st.header("🛠️ Create Your Commander Profile")
    if st.session_state.get('registration_success', False):
        st.success('🎉 Profile successfully created! Prepare for launch.')
        if st.button('🛸 Return to Launchpad'):
            st.session_state['registration_success'] = False
            st.session_state['show_register_form'] = False
            st.rerun()
        return
    
    username = st.text_input('🪐 Choose your Call Sign:', key='signup_username', help='Make it unique and Case Sensitive.')
    password = st.text_input('🔐 Set your Secret Code:', key='signup_password', type='password')
    confirm_password = st.text_input('🔐 Confirm your Secret Code:', key='signup_confirm_password', type='password')
    question = st.selectbox('🛡️ Select your Security Question:', options=SECURITY_QUESTIONS)
    if question == 'Add your own':
        question = st.text_input('Enter your custom question')
    answer = st.text_input('Security Answer:', key='signup_answer', type='password')
    
    st.markdown("""
        <span style="color:#30d6ff; font-size:0.9em;">
            🔒 <b>Your Secret Code must be:</b>
            8+ characters, with at least one uppercase letter,
            one lowercase letter, one number, and one symbol 
            (e.g., <code>P@ssword1!</code>)
        </span>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <span style="color:orange; font-size:0.9em;">
            ⚠️ Remember your security question and answer - this is the only way to recover access if you forget your code.
        </span>
    """, unsafe_allow_html=True)
    
    if st.button('🖋️ Enlist as Commander'):
        if not username or not password or not confirm_password or not answer:
            st.error('⚠️ All fields are required.')
            return
        if password != confirm_password:
            st.error('🚨 Secret Codes do not match.')
            return
        if username_exists(username):
            st.error('🚫 Call Sign already taken.')
            return
        if not is_strong_password(password):
            st.error('⚠️ Secret Code does not meet requirements.')
            return
        
        table.create({
            'User': username,
            'PasswordHash': hash_password(password),
            'SecurityQuestion': question,
            'PasswordHash': hash_password(password),
            'SecurityAnswer': hash_answer(answer),
            'Date': datetime.today().strftime('%Y-%m-%d'),
            'Task': '[User Created]',
            'Completed': True,
        })
        st.session_state['registration_success'] = True
        st.session_state['show_register_form'] = True
        st.rerun()

# Password Reset UI
def forgot_password_ui():
    st.header("🛡 Verify Your Identity")
    if 'security_verified' not in st.session_state:
        st.session_state['security_verified'] = False
    if 'reset_username' not in st.session_state:
        st.session_state['reset_username'] = ''
    if 'user_record' not in st.session_state:
        st.session_state['user_record'] = None

    username = st.text_input("Enter your Call Sign:", key="reset_username")
    if st.button("🚨 Verify Identity"):
        if not username:
            st.error("Enter your Call Sign")
            return
        if not username_exists(username):
            st.error("Call Sign not found")
            return
        records = table.all()
        record = next((r for r in records if r['fields'].get("User") == username), None)
        if not record or "SecurityQuestion" not in record['fields']:
            st.error("No Security Question found")
            return
        st.session_state['reset_username'] = username
        st.session_state['user_record'] = record
        st.session_state['security_verified'] = False
        st.rerun()

    if st.session_state['reset_username'] and not st.session_state['security_verified']:
        question = st.session_state['user_record']['fields']['SecurityQuestion']
        expected_hash = st.session_state['user_record']['fields'].get('SecurityAnswer', '')

        answer = st.text_input(f"Answer to '{question}':", key="security_answer", type='password')

        if st.button("✅ Submit Answer"):
            if not answer:
                st.error("Answer is required.")
                return
            if hash_answer(answer) != expected_hash:
                st.error("Incorrect answer.")
                return
            st.session_state['security_verified'] = True
            st.rerun()

    if st.session_state['security_verified']:
        new_password = st.text_input("Enter New Secret Code:", key="new_password", type='password')
        confirm_password = st.text_input("Confirm New Secret Code:", key="confirm_password", type='password')
        st.caption("Minimum 8 chars, including uppercase, lowercase, number & symbol.")
        if st.button("🛡 Reset Secret Code"):
            if not new_password or not confirm_password:
                st.error("All fields are required.")
                return
            if new_password != confirm_password:
                st.error("Secret Codes do not match.")
                return
            if not is_strong_password(new_password):
                st.error("Secret Code does not meet requirements.")
                return
            if reset_user_password(st.session_state['reset_username'], new_password):
                st.success("Secret Code reset successful! Please sign in.")
                st.session_state['security_verified'] = False
                st.session_state['reset_username'] = ''
                st.session_state['user_record'] = None
                if st.button("⬅ Return to Sign In"):
                    st.session_state['forgot_mode'] = False
                    st.rerun()

# Logout function
def logout():
    st.session_state['user'] = ''
    st.session_state['logged_in'] = False
    st.rerun()

# Initialize session states
for key, default in {
    'user': '',
    'logged_in': False,
    'mode': 'login',
    'show_register_form': False,
    'registration_success': False,
    'forgot_mode': False,
    'security_verified': False,
    'reset_username': '',
    'user_record': None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.sidebar.title("🚀 Command Center")

# Navigation logic
if not st.session_state['logged_in']:
    if st.session_state['forgot_mode']:
        forgot_password_ui()
        if st.button('⬅ Back to Sign In'):
            st.session_state['forgot_mode'] = False
            st.rerun()
        st.stop()
    else:
        login_ui()
        if (not st.session_state['show_register_form'] and not st.session_state['registration_success']):
            if st.button('🌟 New Commander? Enlist Here'):
                st.session_state['show_register_form'] = True
                st.rerun()
        if st.session_state['show_register_form']:
            signup_ui()
            if st.button('⬅ Back to Sign In'):
                st.session_state['show_register_form'] = False
                st.rerun()
        st.stop()

# Main dashboard after login
st.sidebar.title(f"Commander {st.session_state['user']}")
if st.sidebar.button("🚪 Abort Mission"):
    logout()

selected_date = st.sidebar.date_input("Select Mission Date", datetime.today())
date_str = selected_date.strftime("%Y-%m-%d")

# Button Styling
st.markdown("""
    <style>
    .stButton > button {
        padding: 0.25rem 0.6rem !important;
        font-size: 0.88rem !important;
        min-width: 140px !important;
        height: 32px !important;
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title(f"Commander {st.session_state['user']}'s Mission Control")

tasks = get_tasks_for_user_and_date(st.session_state['user'], date_str)
if not tasks:
    st.info("No missions today. Prepare your objectives.")

for task in tasks:
    cols = st.columns([9, 1])
    with cols[0]:
        label = f"✅ {task['task']}" if task['completed'] else f"⬜ {task['task']}"
        checkbox = st.checkbox(label, value=task['completed'], key=f"task_{task['id']}")
        if checkbox != task['completed']:
            update_task_completion(task['id'], checkbox)
            st.rerun()
    with cols[1]:
        if st.button("🗑", key=f"del_{task['id']}", help="Delete mission"):
            delete_task(task['id'])
            st.rerun()

new_task = st.text_input("Add new mission")
if st.button("🚀 Submit Mission"):
    if new_task.strip():
        add_task(new_task.strip(), date_str, st.session_state['user'])
        st.success("Mission added")
        st.rerun()
