import streamlit as st

from db import get_conn
from service import apply_to_team, cast_vote, has_pending, is_closed


def get_teams():
    rows = get_conn().execute(
        "select t.id, t.name, m.student_id, s.name, s.main_role, "
        "coalesce(array_agg(r.role) filter (where r.role is not null), '{}') "
        "from tf_teams t "
        "left join tf_members m on m.team_id = t.id "
        "left join tf_students s on s.id = m.student_id "
        "left join tf_student_sub_roles r on r.student_id = s.id "
        "group by t.id, t.name, m.slot_no, m.student_id, s.name, s.main_role "
        "order by t.id, m.slot_no"
    ).fetchall()

    teams = {}
    for team_id, team_name, student_id, name, main_role, subs in rows:
        team = teams.setdefault(team_id, {"id": team_id, "name": team_name, "members": []})
        if student_id is not None:
            team["members"].append(
                {"id": student_id, "name": name, "main_role": main_role, "sub_roles": subs}
            )
    return list(teams.values())


def show_teams(user, result_box):
    teams = get_teams()

    my_team_id = None
    for team in teams:
        if any(m["id"] == user["id"] for m in team["members"]):
            my_team_id = team["id"]

    cannot_apply = my_team_id is not None or has_pending(user["id"]) or is_closed()

    st.subheader("팀 목록")
    for team in teams:
        number = team["name"].replace("팀", "")
        title = team["name"] + (" (내 팀)" if team["id"] == my_team_id else "")
        with st.container(key=f"team_{number}", border=True):
            st.markdown("**" + title + "**")
            if not team["members"]:
                st.write("아직 팀원이 없음")
            for m in team["members"]:
                subs = ", ".join(m["sub_roles"]) if m["sub_roles"] else "없음"
                st.write(f"{m['name']} - 주 역할: {m['main_role']} / 보조 역할: {subs}")

            if team["id"] == my_team_id:
                show_votes(user, team)

            if not user["is_admin"]:
                if st.button("지원", key=f"apply_{number}", disabled=cannot_apply):
                    status, reason = apply_to_team(user["id"], team["id"])
                    st.session_state.result_msg = f"{status}: {reason}"
                    st.rerun()

    message = st.session_state.get("result_msg")
    if message:
        with result_box:
            st.write(message)

    if not user["is_admin"] and my_team_id is None:
        st.info("아직 팀이 없음")

def show_votes(user, team):
    rows = get_conn().execute(
        "select a.id, s.student_no, s.name, s.main_role, v.vote "
        "from tf_applications a "
        "join tf_students s on s.id = a.student_id "
        "left join tf_votes v on v.application_id = a.id and v.voter_id = %s "
        "where a.team_id = %s and a.status = '대기' "
        "order by a.created_at, a.id",
        (user["id"], team["id"]),
    ).fetchall()

    for app_id, student_no, name, main_role, my_vote in rows:
        st.write(f"지원자: {name} (주 역할: {main_role}) - 대기 중")
        if my_vote:
            st.write(f"내 투표: {my_vote}")
            continue
        col_yes, col_no = st.columns(2)
        if col_yes.button("찬성", key=f"vote_yes_{student_no}"):
            status, reason = cast_vote(user["id"], app_id, "찬성")
            st.session_state.result_msg = f"{status}: {reason}"
            st.rerun()
        if col_no.button("거부", key=f"vote_no_{student_no}"):
            status, reason = cast_vote(user["id"], app_id, "거부")
            st.session_state.result_msg = f"{status}: {reason}"
            st.rerun()