import streamlit as st

st.markdown("<h1 style='color: #FF8C00; text-align: center;'>🚀 Boost Your Day!</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='color: #FFD700;'>✨ What awesome thing will you do next?</h2>", unsafe_allow_html=True)

# Initialize tasks
if "tasks" not in st.session_state:
    st.session_state["tasks"] = []

new_task = st.text_input("🌟 Add an exciting mission:")

if st.button("🔥 Add Mission"):
    if new_task:
        st.session_state["tasks"].append(new_task)
        st.success(f"Mission added: {new_task}")

st.markdown("## 📝 Today's Missions")

delete_task = st.radio(
    "Select a mission you completed and click 'Mark as Done!':",
    st.session_state["tasks"] if st.session_state["tasks"] else ["Nothing yet!"],
    key="complete_task"
)

# Button to complete task
if st.button("✅ Mark as Done!"):
    if delete_task and delete_task in st.session_state["tasks"]:
        st.session_state["tasks"].remove(delete_task)
        st.info(f"Mission accomplished: {delete_task}")

# If no tasks, show motivational message
if not st.session_state["tasks"]:
    st.markdown("<div style='text-align:center; color:#00CED1;'>No missions left! You're on fire today! 🎉</div>", unsafe_allow_html=True)
