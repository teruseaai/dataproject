import streamlit as st

from accounts import ensure_admin, login
from admin_views import show_admin, show_assign, show_confirm
from views import show_teams

st.set_page_config(page_title="팀 편성 앱")


@st.cache_resource
def init():
    ensure_admin()
    return True


init()

if "user" not in st.session_state:
    st.session_state.user = None

st.title("팀 편성 앱")

if st.session_state.user is None:
    with st.form("login_form"):
        student_no = st.text_input("학번", key="login_student_no")
        password = st.text_input("비밀번호", type="password", key="login_password")
        submitted = st.form_submit_button("로그인", key="login_submit")

    if submitted:
        user = login(student_no, password)
        if user is None:
            with st.container(key="result"):
                st.write("막힘: 학번 또는 비밀번호가 틀림")
        else:
            st.session_state.user = user; st.session_state.result_msg = None; st.session_state.result_msg = None
            st.rerun()
else:
    user = st.session_state.user
    with st.container(key="whoami"):
        st.write(f"{user['name']} ({user['student_no']})님으로 로그인함")
    if st.button("로그아웃"):
        st.session_state.user = None
        st.rerun()
    show_teams(user, st.container(key="result"))
    if user["is_admin"]:
        show_admin()
        show_assign()
        show_confirm()
