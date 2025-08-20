import streamlit as st

st.title("AI-powered To Do List")

if "tasks" not in st.session_state:
    st.session_state["tasks"] = []

task = st.text_input("Add a new task:")
if st.button("Add Task"):
    if task:
        st.session_state["tasks"].append(task)
        st.success(f"Added: {task}")

st.write("### Your Tasks:")
for i, t in enumerate(st.session_state["tasks"]):
    if st.checkbox(t, key=i):
        st.session_state["tasks"].pop(i)
        st.experimental_rerun()
