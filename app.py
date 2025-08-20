import streamlit as st
from datetime import datetime

st.markdown("<h1 style='color: #FF8C00; text-align: center;'>🚀 Boost Your Day!</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='color: #FFD700;'>✨ What awesome thing will you do next?</h2>", unsafe_allow_html=True)

if "tasks" not in st.session_state:
    st.session_state["tasks"] = []

# Add new task with optional alarm
new_task = st.text_input("🌟 Add an exciting mission:")
new_alarm = st.time_input("⏰ Set alarm time (optional)", value=None)

if st.button("🔥 Add Mission"):
    if new_task:
        alarm_str = new_alarm.strftime("%H:%M") if new_alarm else None
        st.session_state.tasks.append({"task": new_task, "alarm": alarm_str})
        st.success(f"Mission added: {new_task}" + (f" with alarm at {alarm_str}" if alarm_str else ""))

st.markdown("## 📝 Today's Missions")

now_str = datetime.now().strftime("%H:%M")

# Show each task, highlight if alarm is matched, and allow just one to be marked as done
if st.session_state.tasks:
    choices = []
    display_texts = []
    for i, entry in enumerate(st.session_state.tasks):
        alarm = entry.get("alarm")
        alert = ""
        if alarm and now_str >= alarm:
            alert = " ⏰ **ALARM!**"
        label = entry["task"] + (f' (Alarm at {alarm})' if alarm else '') + alert
        display_texts.append(label)
        choices.append(str(i))

    selected = st.radio(
        "Select a mission to mark as done:",
        choices,
        format_func=lambda x: display_texts[int(x)]
    )

    if st.button("✅ Mark as Done!"):
        removed = st.session_state.tasks.pop(int(selected))
        st.info(f"Mission accomplished: {removed['task']}")
else:
    st.markdown("<div style='text-align:center; color:#00CED1;'>No missions left! You're on fire today! 🎉</div>", unsafe_allow_html=True)
