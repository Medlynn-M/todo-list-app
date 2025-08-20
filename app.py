import streamlit as st

st.title("AI-powered To Do List")

# Initialize the list if not present
if "tasks" not in st.session_state:
    st.session_state["tasks"] = []

# Input for new task
task = st.text_input("Add a new task:")
if st.button("Add Task"):
    if task:
        st.session_state["tasks"].append(task)
        st.success(f"Added: {task}")

st.write("### Your Tasks:")

to_remove = []
for i, t in enumerate(st.session_state["tasks"]):
    if st.checkbox(t, key=f"task_{i}"):
        to_remove.append(i)

# Remove checked tasks after checkboxes are rendered
if to_remove:
    for idx in sorted(to_remove, reverse=True):
        st.session_state["tasks"].pop(idx)
    # No need to use st.experimental_set_query_params or st.query_params

