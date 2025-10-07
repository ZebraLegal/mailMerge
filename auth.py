"""
Enhanced authentication system for the mail merge application.
Supports multiple authentication methods: password, secrets, and environment variables.
"""

import streamlit as st
import hashlib
import os
from typing import Optional, Dict, Any


class AuthManager:
    """Manages authentication for the Streamlit application."""
    
    def __init__(self):
        self.session_key = "password_correct"
        self.password_key = "password"
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_password_from_secrets(self) -> Optional[str]:
        """Get password from Streamlit secrets."""
        try:
            return st.secrets.get("password")
        except Exception:
            return None
    
    def get_password_from_env(self) -> Optional[str]:
        """Get password from environment variable."""
        return os.getenv("MAILMERGE_PASSWORD")
    
    def get_password_from_config(self) -> Optional[str]:
        """Get password from config file (for development)."""
        # You can add a config file here if needed
        return None
    
    def get_stored_password(self) -> Optional[str]:
        """Get the stored password from various sources."""
        # Priority order: secrets > environment > config
        password = self.get_password_from_secrets()
        if password:
            return password
        
        password = self.get_password_from_env()
        if password:
            return password
        
        return self.get_password_from_config()
    
    def check_password(self, entered_password: str) -> bool:
        """Check if the entered password matches the stored password."""
        stored_password = self.get_stored_password()
        if not stored_password:
            # If no password is set, allow access (development mode)
            return True
        
        # Compare hashed passwords
        entered_hash = self.hash_password(entered_password)
        stored_hash = self.hash_password(stored_password)
        
        return entered_hash == stored_hash
    
    def password_entered(self):
        """Callback function when password is entered."""
        entered_password = st.session_state.get(self.password_key, "")
        
        if self.check_password(entered_password):
            st.session_state[self.session_key] = True
            del st.session_state[self.password_key]  # Don't store password
        else:
            st.session_state[self.session_key] = False
    
    def show_login_form(self) -> bool:
        """Show the login form and return True if authenticated."""
        if st.session_state.get(self.session_key, False):
            return True
        
        st.markdown("## 🔐 Authentication Required")
        st.markdown("Please enter the password to access the Mail Merge application.")
        
        st.text_input(
            "Password",
            type="password",
            on_change=self.password_entered,
            key=self.password_key,
            help="Enter the application password"
        )
        
        if self.session_key in st.session_state and not st.session_state[self.session_key]:
            st.error("😕 Password incorrect. Please try again.")
        
        return False
    
    def logout(self):
        """Logout the user."""
        if self.session_key in st.session_state:
            del st.session_state[self.session_key]
        if self.password_key in st.session_state:
            del st.session_state[self.password_key]


# Global auth manager instance
auth_manager = AuthManager()


def require_auth(func):
    """Decorator to require authentication for a function."""
    def wrapper(*args, **kwargs):
        if not auth_manager.show_login_form():
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def show_logout_button():
    """Show a logout button in the sidebar."""
    with st.sidebar:
        if st.button("🚪 Logout"):
            auth_manager.logout()
            st.rerun()


# Simple function for basic authentication
def check_password() -> bool:
    """
    Simple password check function.
    Returns True if the user is authenticated.
    """
    return auth_manager.show_login_form()


# Usage examples:
"""
# Method 1: Simple authentication
if not check_password():
    st.stop()

# Method 2: Decorator authentication
@require_auth
def my_protected_function():
    st.write("This is protected content")

# Method 3: Manual authentication with logout
if not check_password():
    st.stop()

show_logout_button()  # Add logout button to sidebar
"""