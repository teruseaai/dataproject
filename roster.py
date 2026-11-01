import csv
import io

ROLES = ["기획자", "웹 프로그래머", "프론트엔드 디자이너", "테스터", "보고서 작성자", "발표자"]


def parse_roster(file_bytes):
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    students = []
    for row in reader:
        main_role = row["main_role"].strip()
        sub_roles = [s.strip() for s in (row["sub_roles"] or "").split(";") if s.strip()]

        if main_role not in ROLES:
            raise ValueError("알 수 없는 역할: " + main_role)
        for role in sub_roles:
            if role not in ROLES:
                raise ValueError("알 수 없는 보조 역할: " + role)
        if len(sub_roles) > 2:
            raise ValueError("보조 역할이 3개 이상임: " + row["student_no"])

        students.append({
            "student_no": row["student_no"].strip(),
            "name": row["name"].strip(),
            "main_role": main_role,
            "sub_roles": sub_roles,
        })
    return students