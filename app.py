# Sidebar and main app control
st.sidebar.title("🚀 Command Center")

if not st.session_state.logged_in:
    if st.session_state.forgot_mode:
        forgot_password_flow()
        if st.button("Back to Login"):
            st.session_state.forgot_mode = False
            st.experimental_rerun()
        st.stop()
    else:
        login_block()
        # Removed the duplicate forgot button here
        if not st.session_state.show_register_form and not st.session_state.registration_success:
            # Only "New Commander" button remains
            if st.button("New Commander", key="new_commander"):
                st.session_state.show_register_form = True
                st.experimental_rerun()
        if st.session_state.show_register_form:
            signup_block()
            if st.button("Back to Login", key="back_to_login_signup"):
                st.session_state.show_register_form = False
                st.experimental_rerun()
        st.stop()
