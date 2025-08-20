import streamlit as st
from datetime import datetime

st.markdown("<h1 style='color: #FF8C00; text-align: center;'>🚀 Boost Your Day!</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='color: #FFD700;'>✨ What awesome thing will you do next?</h2>", unsafe_allow_html=True)

if "tasks" not in st.session_state:
    # Store tasks as list of dicts with 'task' and optional 'alarm'
    st.session_state["tasks"] = []

# Input task and optional alarm time
new_task = st.text_input("🌟 Add an exciting mission:")
new_alarm = st.time_input("⏰ Set alarm time (optional)", value=None)

if st.button("🔥 Add Mission"):
    if new_task:
        alarm_str = new_alarm.strftime("%H:%M") if new_alarm else None
        st.session_state.tasks.append({"task": new_task, "alarm": alarm_str})
        st.success(f"Mission added: {new_task}" + (f" with alarm at {alarm_str}" if alarm_str else ""))

st.markdown("## 📝 Today's Missions")

# Display tasks with alarms and option to mark done
to_remove = None
for idx, entry in enumerate(st.session_state.tasks):
    task_text = entry["task"]
    alarm = entry.get("alarm")
    alert = ""

    # Check if alarm time is passed or now (simple alert)
    if alarm:
        now_str = datetime.now().strftime("%H:%M")
        if now_str >= alarm:
            alert = " ⏰ Alarm!"

    if st.radio(
        f"{task_text}{alert}  (Alarm at {alarm})" if alarm else task_text,
        options=[""],
        key=f"task_radio_{idx}",
    ):
        to_remove = idx

if st.button("✅ Mark as Done!"):
    if to_remove is not None:
        accomplished = st.session_state.tasks.pop(to_remove)
        st.info(f"Mission accomplished: {accomplished['task']}")

if not st.session_state.tasks:
    st.markdown("<div style='text-align:center; color:#00CED1;'>No missions left! You're on fire today! 🎉</div>", unsafe_allow_html=True)
