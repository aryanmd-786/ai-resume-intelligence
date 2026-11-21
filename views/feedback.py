"""
views/feedback.py
-----------------
User Feedback page.
"""

import streamlit as st
import config
from database import database
from utils.helpers import section_header

def render() -> None:
    # 🔐 User authentication check
    uid = st.session_state.get("user_id")
    if not uid:
        st.error("Session expire. Dobara login karo.")
        st.stop()

    # 🎨 Custom CSS for Feedback Form (To match Login Page style)
    st.markdown(
        """
        <style>
            /* Style the form container (Card Look) */
            [data-testid="stForm"] {
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                padding: 2rem;
                background-color: white;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
            }

            /* Style the submit button (Gradient matching Auth page) */
            .stFormSubmitButton > button {
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: 700;
                font-size: 1.1rem;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
                margin-top: 10px;
            }
            .stFormSubmitButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
                color: white;
            }
            
            /* Style text area */
            .stTextArea textarea {
                border-radius: 8px;
                border: 1px solid #cbd5e1;
                background-color: #f8fafc;
            }
            .stTextArea textarea:focus {
                border-color: #4f46e5;
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
                background-color: white;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<h1 class="page-title">💬 Feedback</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-sub">We would love to hear your thoughts about AI Resume Intelligence.</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(section_header("Rate Your Experience"), unsafe_allow_html=True)
        
        with st.form("feedback_form", clear_on_submit=True):
            # Rating Slider (1 to 5)
            rating = st.slider("How would you rate this platform?", min_value=1, max_value=5, value=5)
            
            # Emoji feedback based on rating
            if rating == 5:
                st.caption("⭐⭐⭐⭐⭐ Excellent! We're glad you liked it.")
            elif rating == 4:
                st.caption("⭐⭐⭐⭐ Very Good!")
            elif rating == 3:
                st.caption("⭐⭐⭐ Good, but we can do better.")
            elif rating == 2:
                st.caption("⭐⭐ Needs Improvement.")
            else:
                st.caption("⭐ Poor. We are sorry to hear that.")

            comments = st.text_area(
                "Any suggestions or comments?",
                placeholder="Tell us what you loved, or what we can improve...",
                height=120,
            )

            submitted = st.form_submit_button("Submit Feedback 🚀", use_container_width=True)

            if submitted:
                success = database.save_feedback(user_id=uid, rating=rating, comments=comments)
                if success:
                    st.success("✅ Thank you! Your feedback has been saved.")
                else:
                    st.error("❌ Could not save feedback. Please try again.")

    with col2:
        # Ek chhota sa visual panel
        st.markdown(section_header("Why give feedback?"), unsafe_allow_html=True)
        st.info(
            "Your feedback helps us improve the AI models, user interface, "
            "and overall experience of the platform. We read every single response!"
        )
        
        st.markdown(
            f"""
            <div class="info-panel" style="margin-top: 20px; padding: 20px; border-radius: 12px; background-color: #f8fafc; border: 1px solid #e2e8f0;">
                <div style="font-size: 2.5rem; text-align: center;">🤝</div>
                <div style="text-align: center; font-weight: 700; font-size: 1.1rem; margin-top: 10px; color: #1e293b;">
                    Built for students, by students.
                </div>
                <div style="text-align: center; color: #64748b; font-size: 0.9rem; margin-top: 8px;">
                    Thank you for using {config.APP_NAME} <b>v{config.APP_VERSION}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )