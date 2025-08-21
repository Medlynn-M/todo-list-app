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

# -----------------------------------------------------
# 🔒 Utility functions
# -----------------------------------------------------
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def hash_answer(ans):
    return hashlib.sha256(ans.strip().lower().encode()).hexdigest()

def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True

# -----------------------------------------------------
# 👨‍🚀 User account utilities
# -----------------------------------------------------
def username_exists(username):
    all_records = table.all()
    usernames = {r.get("fields", {}).get("User", "") for r in all_records}
    return username in usernames

def get_user_password_hash(username):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User", "") == username:
            return fields.get("PasswordHash", None)
    return None

def reset_user_password(username, new_password):
    all_records = table.all()
    for r in all_records:
        fields = r.get("fields", {})
        if fields.get("User", "") == username:
            table.update(r["id"], {"PasswordHash": hash_password(new_password)})
            return True
    return False

# -----------------------------------------------------
# 📋 Task utilities
# -----------------------------------------------------
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

# -----------------------------------------------------
# 🔐 Login UI
# -----------------------------------------------------
def login_block():
    st.header("👋 Welcome Back, Commander!")

    username = st.text_input(
        "🛰️ Enter Your Call Sign",
        key="login_username",
        help="🛸 Case-Sensitive: 'StarCaptain' and 'starcaptain' are different Commanders. Choose wisely."
    )

    password = st.text_input("🔐 Enter Your Secret Code (Password)", type="password", key="login_password")

    # Right-align: place 'Forgot Secret Code?' link beneath the password input
    cols = st.columns([3, 1])
    with cols[1]:
        forgot_clicked = st.button("❓ Forgot Secret Code?", key="forgot_text_inline")
        st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(2) button {
            color: #ff4b4b !important;
            background: none !important;
            box-shadow: none !important;
            border: none !important;
            text-decoration: underline !important;
            font-size: 0.98em !important;
            padding-left: 0;
            padding-right: 0;
            margin-top: -6px;
            margin-bottom: 0px;
            float: right;
        }
        </style>
        """, unsafe_allow_html=True)
    if forgot_clicked:
        st.session_state.forgot_mode = True
        st.experimental_rerun()

    # Global small button styling
    st.markdown("""
    <style>
    .stButton button {
        padding: 0.3em 0.8em !important;
        font-size: 0.92em !important;
        border-radius: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("🚀 Launch Mission Control", key="launchmc_small"):
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

# -----------------------------------------------------
# 🛠️ Signup UI
# -----------------------------------------------------
SECURITY_QUESTIONS = [
    "What is your favorite spacecraft?",
    "What planet would you visit first?",
    "What is your childhood nickname?",
    "Who is your all-time hero?",
    "Custom (type your own!)"
]

def signup_block():
    st.header("🛠️ Launch New Mission: Create Your Commander Profile")

    if st.session_state.get("registration_success", False):
        st.success("🎉 Mission Success! Your Commander profile is now secured in Mission Control. Prepare for liftoff!")
        if st.button("🔑 Return to Launchpad", key="return_launchpad_small"):
            st.session_state.registration_success = False
            st.session_state.show_register_form = False
            st.session_state.mode = "login"
            st.rerun()
        return

    username = st.text_input(
        "🌌 Choose Your Call Sign",
        key="reg_username",
        help="🛸 Case-Sensitive: 'StarCaptain' and 'starcaptain' are different Commanders. Choose wisely."
    )

    password = st.text_input("🔐 Forge Your Secret Code (Password)", type="password", key="reg_password")
    st.caption("🛡️ Secret Code must be mission-grade: ≥8 chars, with an UPPERCASE star, a lowercase planet, a number for coordinates, and a special symbol to unlock hyperspace portals.")

    password_confirm = st.text_input("🔐 Confirm Your Secret Code", type="password", key="reg_password_confirm")

    security_q = st.selectbox("🛡️ Choose a Security Question for Emergencies", SECURITY_QUESTIONS)
    if security_q == "Custom (type your own!)":
        security_q = st.text_input("📝 Enter Your Custom Security Question")

    security_ans = st.text_input("🔑 Secret Answer (case-insensitive, for password reset)", type="password")

    st.markdown(
        "<span style='color: orange; font-weight: bold;'>"
        "⚠️ Secure Your Access: This is your ONLY lifeline to reset your Secret Code if forgotten. "
        "Record your Security Question and Answer somewhere safe! "
        "If lost, Mission Control cannot recover your access.</span>",
        unsafe_allow_html=True
    )

    if st.button("✨ Enlist Me, Mission Control!", key="enlist_small"):
        if not username or not password or not password_confirm or not security_ans:
            st.error("⚠️ Every input is mission critical, Commander. Complete all fields to proceed.")
            return
        if password != password_confirm:
            st.error("⚠️ Secret Codes don't match! Resynchronize your access key.")
            return
        if username_exists(username):
            st.error("❌ Call Sign already claimed by another Commander. Choose a unique identifier.")
            return
        if not is_strong_password(password):
            st.error("⚠️ Secret Code too weak! Battle-ready keys require ≥8 chars, "
                     "an UPPERCASE star, a lowercase planet, a number, and a special hyperspace symbol. 🌌")
            return

        # Save to Airtable
        table.create({
            "User": username,
            "Task": "[User Created]",
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Completed": True,
            "PasswordHash": hash_password(password),
            "SecurityQuestion": security_q,
            "SecurityAnswerHash": hash_answer(security_ans)
        })
        st.session_state.registration_success = True
        st.session_state.show_register_form = True
        st.rerun()

# -----------------------------------------------------
# 🔑 Forgot Password / Reset UI
# -----------------------------------------------------
def forgot_password_block():
    st.header("🔑 Reset Your Secret Code")

    if "security_verified" not in st.session_state:
        st.session_state.security_verified = False
    if "reset_username" not in st.session_state:
        st.session_state.reset_username = ""
    if "user_record" not in st.session_state:
        st.session_state.user_record = None

    username = st.text_input("🌌 Enter Your Call Sign", key="reset_username_input")

    if st.button("📡 Verify Commander Identity", key="verify_identity"):
        if not username:
            st.error("⚠️ Enter your Call Sign to proceed.")
        elif not username_exists(username):
            st.error("🛰️ Unknown Call Sign! No Commander registered with that identity.")
        else:
            all_records = table.all()
            user_record = next((r for r in all_records if r.get("fields", {}).get("User", "") == username), None)
            if not user_record or "SecurityQuestion" not in user_record.get("fields", {}):
                st.error("⚠️ No security question set for this account.")
            else:
                st.session_state.reset_username = username
                st.session_state.user_record = user_record
                st.session_state.security_verified = False
                st.experimental_rerun()

    if st.session_state.reset_username and not st.session_state.security_verified:
        sec_q = st.session_state.user_record['fields']["SecurityQuestion"]
        sec_ans_hash = st.session_state.user_record['fields'].get("SecurityAnswerHash", "")

        ans = st.text_input(f"🛡️ Answer your Security Question:\n*{sec_q}*", type="password", key="sec_answer")

        if st.button("🔓 Verify Security Answer", key="verify_answer"):
            if not ans:
                st.error("⚠️ You must answer the security question.")
            elif hash_answer(ans) != sec_ans_hash:
                st.error("❌ Incorrect answer! Unable to reset Secret Code.")
            else:
                st.session_state.security_verified = True
                st.experimental_rerun()

    if st.session_state.security_verified:
        new_pw = st.text_input("🔐 Enter New Secret Code", type="password", key="new_pw")
        confirm_pw = st.text_input("🔐 Confirm New Secret Code", type="password", key="confirm_pw")
        st.caption("🛡️ Must be mission-grade: ≥8 chars, uppercase, lowercase, numeral, symbol.")

        if st.button("✅ Reset Secret Code", key="reset_pw"):
            if not new_pw or not confirm_pw:
                st.error("⚠️ All fields required, Commander!")
            elif new_pw != confirm_pw:
                st.error("❌ Codes don’t match! Check your entries.")
            elif not is_strong_password(new_pw):
                st.error("⚠️ Secret Code too weak! Must be ≥8 chars, include uppercase, lowercase, number, and symbol.")
            elif reset_user_password(st.session_state.reset_username, new_pw):
                st.success("🎉 Secret Code reset successful! Back to Launchpad to login.")
                st.session_state.security_verified = False
                st.session_state.reset_username = ""
                st.session_state.user_record = None
                if st.button("🚀 Back to Launchpad"):
                    st.session_state.mode = "login"
                    st.session_state.forgot_mode = False
                    st.experimental_rerun()
            else:
                st.error("⚠️ Error: Could not reset password. Contact Mission Control.")

# -----------------------------------------------------
# 🔓 Logout
# -----------------------------------------------------
def logout():
    st.session_state.user = ""
    st.session_state.logged_in = False
    st.rerun()

# -----------------------------------------------------
# 🌌 App Core - Session Init
# -----------------------------------------------------
for key in ["user", "logged_in", "mode", "show_register_form", "registration_success", "forgot_mode", "security_verified", "reset_username", "user_record"]:
    if key not in st.session_state:
        if key == "user":
            st.session_state[key] = ""
        elif key == "logged_in":
            st.session_state[key] = False
        elif key == "mode":
            st.session_state[key] = "login"
        elif key == "show_register_form":
            st.session_state[key] = False
        elif key == "registration_success":
            st.session_state[key] = False
        elif key == "forgot_mode":
            st.session_state[key] = False
        elif key == "security_verified":
            st.session_state[key] = False
        elif key == "reset_username":
            st.session_state[key] = ""
        elif key == "user_record":
            st.session_state[key] = None

# -----------------------------------------------------
# 🛸 Auth Sidebar
# -----------------------------------------------------
st.sidebar.title("🛸 Commander Authentication Center")

if not st.session_state.logged_in:
    if st.session_state.forgot_mode:
        forgot_password_block()
        if st.button("🔙 Back to Login", key="back_to_login_small"):
            st.session_state.forgot_mode = False
            st.rerun()
        st.stop()
    else:
        login_block()

        if not st.session_state.show_register_form and not st.session_state.registration_success:
            # Forgot Secret Code? button ABOVE New user registration button
            if st.button("❓ Forgot Secret Code?", key="forgot_small_button"):
                st.session_state.forgot_mode = True
                st.rerun()
            if st.button("✨ New here? Enlist your Call Sign", key="enlist_small_button"):
                st.session_state.show_register_form = True
                st.rerun()

        if st.session_state.show_register_form:
            st.markdown("---")
            signup_block()
            if not st.session_state.registration_success:
                if st.button("🔙 Already a Commander? Return to Launchpad", key="return_launchpad_small"):
                    st.session_state.show_register_form = False
                    st.rerun()

        st.stop()

# -----------------------------------------------------
# 🌠 Main Mission Control
# -----------------------------------------------------
st.sidebar.title(f"🧑‍🚀 Commander {st.session_state.user}")
if st.sidebar.button("⏹️ Abort Mission: Log Out", key="logout_small_button"):
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
        /* Make all buttons smaller across the whole app */
        .stButton button {
            padding: 0.3em 0.75em !important;
            font-size: 0.90em !important;
            border-radius: 6px;
        }
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
if st.button("🚀 Accept Mission", key="accept_mission"):
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
