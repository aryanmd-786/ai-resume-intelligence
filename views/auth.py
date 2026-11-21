# views/auth.py
import streamlit as st
from services.auth_service import signup, login


def render_auth_page():
    # 🎨 Premium Custom CSS
    st.markdown(
        """
        <style>
            /* Hide Streamlit header/footer for a clean look */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}

            /* Style the main title with a nice gradient */
            .auth-title {
                text-align: center;
                font-size: 2.8rem;
                font-weight: 900;
                background: -webkit-linear-gradient(45deg, #4f46e5, #9333ea);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 2rem;
                padding-top: 3rem;
                letter-spacing: -1px;
            }

            /* Style the form container (Card Look) */
            [data-testid="stForm"] {
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                padding: 2.5rem 2rem;
                background-color: white;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
            }

            /* Style input fields */
            .stTextInput > div > div > input {
                border-radius: 8px;
                border: 1px solid #cbd5e1;
                padding: 12px 14px;
                background-color: #f8fafc;
                transition: all 0.2s;
                font-size: 1rem;
            }
            .stTextInput > div > div > input:focus {
                border-color: #4f46e5;
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
                background-color: white;
            }

            /* Style the submit button (Gradient) */
            .stFormSubmitButton > button {
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-weight: 700;
                font-size: 1.1rem;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
                margin-top: 15px;
                letter-spacing: 0.5px;
            }
            .stFormSubmitButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
                color: white;
            }

            /* ✨ FIXED TABS STYLING (No Glitches, Pure Bold) ✨ */
            .stTabs [data-baseweb="tab-list"] {
                gap: 3rem;
                justify-content: center;
                margin-bottom: 2rem;
                border-bottom: 2px solid #e2e8f0;
            }
            
            .stTabs [data-baseweb="tab"] {
                height: 60px;
                font-size: 1.5rem;       /* 🔥 Bada Font */
                font-weight: 800;        /* 🔥 Extra Bold */
                color: #94a3b8;
                letter-spacing: 0.5px;
                transition: all 0.3s ease;
                background-color: transparent !important;
                border: none !important; /* 🔥 Red lines hatane ke liye */
                outline: none !important; /* 🔥 Focus ring hatane ke liye */
                box-shadow: none !important;
                padding: 0 1rem;
            }

            .stTabs [data-baseweb="tab"]:hover {
                color: #4f46e5;
                transform: translateY(-2px); /* Hover par halka sa uthega */
            }

            .stTabs [aria-selected="true"] {
                color: #4f46e5 !important;
                font-weight: 900 !important; /* 🔥 Active tab sabse zyada bold */
            }

            /* Sirf active tab ke neeche ki line dikhe */
            .stTabs [data-baseweb="tab-highlight"] {
                background-color: #4f46e5 !important;
                height: 4px !important;
                border-radius: 4px 4px 0 0;
            }

            /* Streamlit ka default border hide karo */
            .stTabs [data-baseweb="tab-border"] {
                display: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 🎨 Custom Header
    st.markdown("<div class='auth-title'>🧠 AI Resume Intelligence</div>", unsafe_allow_html=True)

    # Center align the forms using columns
    _, center, _ = st.columns([1, 1.2, 1])
    
    with center:
        # 🔥 Tabs with Icons
        tab_login, tab_signup = st.tabs(["🔑 Login", "✨ Sign Up"])

        # ---------- LOGIN ----------
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### Welcome Back! 👋")
                ident = st.text_input("Username or Email", key="login_ident", placeholder="Enter your username or email")
                pwd = st.text_input("Password", type="password", key="login_pwd", placeholder="••••••••")
                submitted = st.form_submit_button("Login", use_container_width=True)

                if submitted:
                    res = login(ident, pwd)
                    if res["ok"]:
                        st.session_state.logged_in = True
                        st.session_state.user_id = res["user_id"]
                        st.session_state.username = res["username"]
                        st.session_state.full_name = res["full_name"]
                        st.success(f"✅ Welcome back, {res['full_name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {res['message']}")

        # ---------- SIGNUP ----------
        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                st.markdown("### Create an Account 🚀")
                full_name = st.text_input("Full Name", key="su_fullname", placeholder="John Doe")
                uname = st.text_input("Username", key="su_uname", placeholder="Choose a unique username")
                email = st.text_input("Email", key="su_email", placeholder="you@example.com")
                p1 = st.text_input("Password", type="password", key="su_p1", placeholder="Min 6 characters")
                p2 = st.text_input("Confirm Password", type="password", key="su_p2", placeholder="Re-enter password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)

                if submitted:
                    if p1 != p2:
                        st.error("❌ Passwords do not match.")
                    else:
                        res = signup(uname, email, p1, full_name)
                        if res["ok"]:
                            # 🔐 Auto-login after successful signup
                            login_res = login(uname, p1)
                            if login_res["ok"]:
                                st.session_state.logged_in = True
                                st.session_state.user_id = login_res["user_id"]
                                st.session_state.username = login_res["username"]
                                st.session_state.full_name = login_res["full_name"]
                                st.success("✅ Account created successfully! Welcome!")
                                st.rerun()
                            else:
                                st.success("✅ Account created! Please go to the Login tab.")
                        else:
                            st.error(f"❌ {res['message']}")