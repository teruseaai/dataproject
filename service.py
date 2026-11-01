from auth import hash_password
from rules import seats_ok
from db import get_conn
from roster import parse_roster


def start_scenario(file_bytes, team_count):
    students = parse_roster(file_bytes)
    conn = get_conn()
    password_hash = hash_password("1234")

    with conn.transaction():
        conn.execute("delete from tf_votes")
        conn.execute("delete from tf_applications")
        conn.execute("delete from tf_members")
        conn.execute("delete from tf_teams")
        conn.execute("delete from tf_students where is_admin = false")
        conn.execute("delete from tf_settings")

        for s in students:
            row = conn.execute(
                "insert into tf_students (student_no, name, main_role, password_hash) "
                "values (%s, %s, %s, %s) returning id",
                (s["student_no"], s["name"], s["main_role"], password_hash),
            ).fetchone()
            for role in s["sub_roles"]:
                conn.execute(
                    "insert into tf_student_sub_roles (student_id, role) values (%s, %s)",
                    (row[0], role),
                )

        for i in range(1, team_count + 1):
            conn.execute("insert into tf_teams (name) values (%s)", (f"팀{i}",))

        conn.execute("insert into tf_settings (key, value) values ('closed', 'false')")

    return len(students)

def get_setting(key):
    row = get_conn().execute("select value from tf_settings where key = %s", (key,)).fetchone()
    return row[0] if row else None


def is_closed():
    return get_setting("closed") == "true"


def apply_to_team(student_id, team_id):
    conn = get_conn()
    with conn.transaction():
        if is_closed():
            return "막힘", "모집이 마감됨"

        if conn.execute("select 1 from tf_members where student_id = %s", (student_id,)).fetchone():
            return "막힘", "이미 팀이 있음"

        if conn.execute(
            "select 1 from tf_applications where student_id = %s and status = '대기'", (student_id,)
        ).fetchone():
            return "막힘", "결과를 기다리는 지원이 있음"

        members = conn.execute(
            "select m.student_id, s.main_role from tf_members m "
            "join tf_students s on s.id = m.student_id where m.team_id = %s",
            (team_id,),
        ).fetchall()
        if len(members) >= 4:
            return "막힘", "팀이 꽉 참"

        my_role = conn.execute(
            "select main_role from tf_students where id = %s", (student_id,)
        ).fetchone()[0]
        if any(role == my_role for _, role in members):
            return "막힘", "같은 주 역할의 팀원이 있음"

        if not seats_ok(_team_people(conn, team_id) + [_person(conn, student_id)]):
            return "막힘", "필수 포함 역할을 맡을 학생의 자리가 모자람"

        if not members:
            conn.execute(
                "insert into tf_members (team_id, slot_no, student_id) values (%s, 1, %s)",
                (team_id, student_id),
            )
            conn.execute(
                "insert into tf_applications (team_id, student_id, status) values (%s, %s, '승인')",
                (team_id, student_id),
            )
            return "승인", "빈 팀이라 바로 승인됨"

        conn.execute(
            "insert into tf_applications (team_id, student_id, status) values (%s, %s, '대기')",
            (team_id, student_id),
        )
        return "대기", "팀원의 투표를 기다림"

def has_pending(student_id):
    row = get_conn().execute(
        "select 1 from tf_applications where student_id = %s and status = '대기'",
        (student_id,),
    ).fetchone()
    return row is not None

def cast_vote(voter_id, application_id, vote):
    conn = get_conn()
    with conn.transaction():
        app = conn.execute(
            "select team_id, student_id, status from tf_applications where id = %s for update",
            (application_id,),
        ).fetchone()
        if app is None:
            return "막힘", "지원을 찾을 수 없음"
        team_id, applicant_id, status = app

        if is_closed():
            return "막힘", "모집이 마감됨"
        if status != "대기":
            return status, "이미 결과가 나온 지원임"

        members = [
            r[0]
            for r in conn.execute(
                "select student_id from tf_members where team_id = %s", (team_id,)
            ).fetchall()
        ]
        if voter_id not in members:
            return "막힘", "이 팀의 팀원이 아님"
        if conn.execute(
            "select 1 from tf_votes where application_id = %s and voter_id = %s",
            (application_id, voter_id),
        ).fetchone():
            return "대기", "이미 투표함"

        conn.execute(
            "insert into tf_votes (application_id, voter_id, vote) values (%s, %s, %s)",
            (application_id, voter_id, vote),
        )

        if vote == "거부":
            conn.execute(
                "update tf_applications set status = '거절', reason = '팀원의 거부' where id = %s",
                (application_id,),
            )
            return "거절", "팀원의 거부로 거절됨"

        yes = conn.execute(
            "select count(*) from tf_votes "
            "where application_id = %s and vote = '찬성' and voter_id = any(%s)",
            (application_id, members),
        ).fetchone()[0]
        if yes >= len(members):
            problem = reject_if_invalid(conn, application_id, team_id, applicant_id)
            if problem:
                return "거절", problem
        if yes < len(members):
            return "대기", "다른 팀원의 투표를 기다림"

        if len(members) >= 4:
            conn.execute(
                "update tf_applications set status = '거절', reason = '팀이 꽉 참' where id = %s",
                (application_id,),
            )
            return "거절", "팀이 꽉 차서 거절됨"

        used = {
            r[0]
            for r in conn.execute(
                "select slot_no from tf_members where team_id = %s", (team_id,)
            ).fetchall()
        }
        slot = min(set(range(1, 5)) - used)
        conn.execute(
            "insert into tf_members (team_id, slot_no, student_id) values (%s, %s, %s)",
            (team_id, slot, applicant_id),
        )
        conn.execute(
            "update tf_applications set status = '승인' where id = %s", (application_id,)
        )
        return "승인", "모든 팀원이 찬성해 승인됨"

def close_recruitment():
    conn = get_conn()
    with conn.transaction():
        if is_closed():
            return "막힘", "이미 모집이 마감됨"
        conn.execute(
            "update tf_applications set status = '거절', reason = '모집 마감' where status = '대기'"
        )
        conn.execute(
            "delete from tf_members where team_id in "
            "(select team_id from tf_members group by team_id having count(*) = 1)"
        )
        conn.execute(
            "insert into tf_settings (key, value) values ('closed', 'true') "
            "on conflict (key) do update set value = 'true'"
        )
    return "승인", "모집을 마감함"


def get_unassigned():
    rows = get_conn().execute(
        "select s.name from tf_students s "
        "where s.is_admin = false "
        "and not exists (select 1 from tf_members m where m.student_id = s.id) "
        "order by s.student_no"
    ).fetchall()
    return [r[0] for r in rows]


def load_state():
    conn = get_conn()

    students = {}
    for db_id, student_no, name, main_role in conn.execute(
        "select id, student_no, name, main_role from tf_students where is_admin = false"
    ).fetchall():
        students[db_id] = {"id": student_no, "name": name, "main_role": main_role, "sub_roles": []}

    for db_id, role in conn.execute("select student_id, role from tf_student_sub_roles").fetchall():
        if db_id in students:
            students[db_id]["sub_roles"].append(role)

    teams = {}
    placed = set()
    for team_name, db_id in conn.execute(
        "select t.name, m.student_id from tf_teams t "
        "left join tf_members m on m.team_id = t.id "
        "order by t.id, m.slot_no"
    ).fetchall():
        teams.setdefault(team_name, [])
        if db_id is not None:
            teams[team_name].append(students[db_id])
            placed.add(db_id)

    unassigned = [s for db_id, s in students.items() if db_id not in placed]
    unassigned.sort(key=lambda s: s["id"])
    return teams, unassigned

def _run_ai(progress=None):
    from ai import run_with_fallback
    from assign import build_prompt, make_check, parse_response
    from config import MODELS

    teams, unassigned = load_state()
    if not unassigned:
        return None, None, ["팀이 없는 학생이 없음"]

    prompt = build_prompt(teams, unassigned)
    text, number, log = run_with_fallback(MODELS, prompt, make_check(teams, unassigned), progress=progress)
    if text is None:
        return None, None, log
    return parse_response(text), number, log

def confirm_assignment(assignment):
    from rules import validate_assignment

    conn = get_conn()
    with conn.transaction():
        if not is_closed():
            return "막힘", "먼저 모집을 마감해야 함"

        teams, unassigned = load_state()
        problems = validate_assignment(teams, unassigned, assignment)
        if problems:
            return "막힘", problems[0]

        for team_name, student_nos in assignment.items():
            team_id = conn.execute(
                "select id from tf_teams where name = %s", (team_name,)
            ).fetchone()[0]
            used = {
                r[0]
                for r in conn.execute(
                    "select slot_no from tf_members where team_id = %s", (team_id,)
                ).fetchall()
            }
            for student_no in student_nos:
                slot = min(set(range(1, 5)) - used)
                used.add(slot)
                conn.execute(
                    "insert into tf_members (team_id, slot_no, student_id) "
                    "select %s, %s, id from tf_students where student_no = %s",
                    (team_id, slot, student_no),
                )
    return "승인", "배정안을 확정함"

def run_assignment(progress=None):
    from solver import explain_impossible, find_assignment

    teams, unassigned = load_state()
    if not unassigned:
        return None, None, ["팀이 없는 학생이 없음"], []

    own = find_assignment(teams, unassigned)
    if own is None:
        return None, None, ["규칙을 지키는 배정이 없음"], explain_impossible(teams, unassigned)

    assignment, number, log = _run_ai(progress)
    if assignment is None:
        return own, 0, log + ["3차 모델까지 실패하여 앱이 스스로 배정함"], []
    return assignment, number, log, []

def reject_if_invalid(conn, application_id, team_id, applicant_id):
    rows = conn.execute(
        "select s.main_role from tf_members m "
        "join tf_students s on s.id = m.student_id where m.team_id = %s",
        (team_id,),
    ).fetchall()
    roles = [r[0] for r in rows]
    my_role = conn.execute(
        "select main_role from tf_students where id = %s", (applicant_id,)
    ).fetchone()[0]

    reason = None
    if len(roles) >= 4:
        reason = "팀이 꽉 참"
    elif my_role in roles:
        reason = "같은 주 역할의 팀원이 있음"
    if reason is None and not seats_ok(_team_people(conn, team_id) + [_person(conn, applicant_id)]):
        reason = "필수 포함 역할을 맡을 학생의 자리가 모자람"
    if reason is None:
        return None

    conn.execute(
        "update tf_applications set status = '거절', reason = %s where id = %s",
        (reason, application_id),
    )
    return "승인 직전 검사에서 규칙을 어김(" + reason + ")"

def _person(conn, student_id):
    main_role = conn.execute(
        "select main_role from tf_students where id = %s", (student_id,)
    ).fetchone()[0]
    subs = [
        r[0]
        for r in conn.execute(
            "select role from tf_student_sub_roles where student_id = %s", (student_id,)
        ).fetchall()
    ]
    return {"main_role": main_role, "sub_roles": subs}


def _team_people(conn, team_id):
    ids = [
        r[0]
        for r in conn.execute(
            "select student_id from tf_members where team_id = %s", (team_id,)
        ).fetchall()
    ]
    return [_person(conn, i) for i in ids]