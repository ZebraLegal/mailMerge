"""
Mail Merge Application with Authentication - Example Integration
This shows how to add authentication to your main mailMerge.py
"""

import streamlit as st
import locale
from pathlib import Path

# Robust locale selection with fallbacks
for _loc in ('nl_NL.UTF-8', 'nl_NL', 'nl_NL.utf8'):
    try:
        locale.setlocale(locale.LC_ALL, _loc)
        break
    except locale.Error:
        continue

# Import our custom modules
from ui_pages import (
    render_template_upload_page,
    render_data_upload_page,
    render_preview_page,
    render_output_settings_page,
    render_single_document_page
)

# Import authentication
from auth import check_password, show_logout_button

# Configure Streamlit page
st.set_page_config(layout="centered")

# AUTHENTICATION CHECK - Add this line to enable authentication
if not check_password():
    st.stop()

# Show logout button in sidebar
show_logout_button()

# Initialize session state for multi-page effect
if "page" not in st.session_state:
    st.session_state.page = 1

# Main application logic
if st.session_state.page == 1:
    render_template_upload_page()
elif st.session_state.page == 2:
    render_data_upload_page()
elif st.session_state.page == 3:
    render_preview_page()
elif st.session_state.page == 4:
    render_output_settings_page()
elif st.session_state.page == "single":
    render_single_document_page()
else:
    st.error("Onbekende pagina. Ga terug naar de startpagina.")
    if st.button("⬅️ Terug naar start"):
        st.session_state.page = 1
        st.rerun()

