import os

from auth import check_password, hash_password
from db import get_conn


def ensure_admin():
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("ADMIN_PASSWORD가 없음")
    get_conn().execute(
        "insert into tf_students (student_no, name, password_hash, is_admin) "
        "values ('admin', '관리자', %s, true) "
        "on conflict (student_no) do update "
        "set password_hash = excluded.password_hash, is_admin = true",
        (hash_password(password),),
    )


def login(student_no, password):
    row = get_conn().execute(
        "select id, student_no, name, password_hash, is_admin "
        "from tf_students where student_no = %s",
        (student_no.strip(),),
    ).fetchone()
    if row is None or not check_password(password, row[3]):
        return None
    return {"id": row[0], "student_no": row[1], "name": row[2], "is_admin": row[4]}