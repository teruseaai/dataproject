import streamlit as st

from service import close_recruitment, get_unassigned, start_scenario


def show_admin():
    st.subheader("관리자")

    file = st.file_uploader("명단 CSV", type=["csv"], key="admin_roster_file")
    team_count = st.number_input(
        "팀 수", min_value=1, max_value=10, value=3, step=1, key="admin_team_count"
    )

    if st.button("명단으로 처음 상태 만들기", key="admin_start"):
        if file is None:
            message = "막힘: 명단 CSV를 먼저 올려야 함"
        else:
            try:
                n = start_scenario(file.getvalue(), int(team_count))
                message = f"승인: 학생 {n}명, 팀 {int(team_count)}개로 처음 상태를 만듦"
            except ValueError as e:
                message = f"막힘: {e}"
            except Exception:
                message = "막힘: 명단 CSV를 처리하지 못함"
        st.session_state.result_msg = message
        st.rerun()

    if st.button("모집 마감", key="admin_close"):
        status, reason = close_recruitment()
        st.session_state.result_msg = f"{status}: {reason}"
        st.rerun()

    with st.container(key="unassigned"):
        names = get_unassigned()
        st.write("팀이 없는 학생: " + (", ".join(names) if names else "없음"))