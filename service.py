from auth import hash_password
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