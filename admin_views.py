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

def show_assign():
    from service import is_closed, load_state, run_assignment

    box = st.container(key="assign_status")

    if st.button("AI 배정", key="admin_assign"):
        if not is_closed():
            st.session_state.result_msg = "막힘: 먼저 모집을 마감해야 함"
            st.session_state.proposal = None
            st.rerun()

        line = box.empty()

        def progress(n):
            line.write(f"AI가 생각하는 중: {n}차 모델의 응답을 기다리는 중")

        assignment, number, log, reasons = run_assignment(progress)
        _, unassigned = load_state()
        st.session_state.proposal = {
            "assignment": assignment,
            "number": number,
            "log": log + reasons,
            "people": {s["id"]: s for s in unassigned},
        }
        if assignment is None:
            st.session_state.result_msg = "막힘: 규칙을 지키는 배정이 없음"
        else:
            st.session_state.result_msg = (f"승인: {number}차 모델의 배정안이 검사를 통과함" if number else "승인: 앱이 스스로 배정안을 만듦")
        st.rerun()

    proposal = st.session_state.get("proposal")
    if proposal:
        with box:
            for text in proposal["log"]:
                st.write(text)
            if proposal["assignment"]:
                for team, ids in proposal["assignment"].items():
                    people = [proposal["people"][i] for i in ids if i in proposal["people"]]
                    names = ", ".join(f"{p['name']}({p['main_role']})" for p in people)
                    st.write(f"{team}: {names if names else '추가 없음'}")

def show_confirm():
    from service import confirm_assignment

    if st.button("배정안 확정", key="admin_confirm"):
        proposal = st.session_state.get("proposal")
        if not proposal or not proposal["assignment"]:
            st.session_state.result_msg = "막힘: 확정할 배정안이 없음"
        else:
            status, reason = confirm_assignment(proposal["assignment"])
            st.session_state.result_msg = f"{status}: {reason}"
            if status == "승인":
                st.session_state.proposal = None
        st.rerun()