PL = "기획자"
WP = "웹 프로그래머"


def can_do(student, role):
    return student["main_role"] == role or role in student["sub_roles"]


def has_required_roles(members):
    for a in members:
        for b in members:
            if a is not b and can_do(a, PL) and can_do(b, WP):
                return True
    return False


def validate_assignment(teams, unassigned, assignment):
    """
    teams: {"팀1": [학생, ...]}  지금 팀 구성
    unassigned: [학생, ...]  팀이 없는 학생
    assignment: {"팀1": [학생 id, ...]}  배정안
    학생은 {"id", "name", "main_role", "sub_roles"} 꼴
    문제가 없으면 빈 목록, 있으면 문제 설명의 목록을 돌려줌
    """
    problems = []
    by_id = {s["id"]: s for s in unassigned}

    count = {}
    for team_name, ids in assignment.items():
        if team_name not in teams:
            problems.append(f"없는 팀: {team_name}")
        for sid in ids:
            if sid not in by_id:
                problems.append(f"배정 대상이 아닌 학생: {sid}")
            count[sid] = count.get(sid, 0) + 1

    for sid, s in by_id.items():
        if sid not in count:
            problems.append(f"배정되지 않은 학생: {s['name']}")

    for sid, n in count.items():
        if n > 1 and sid in by_id:
            problems.append(f"여러 번 배정된 학생: {by_id[sid]['name']}")

    for team_name, current in teams.items():
        added = [by_id[sid] for sid in assignment.get(team_name, []) if sid in by_id]
        members = list(current) + added

        if not 2 <= len(members) <= 4:
            problems.append(f"{team_name}: 인원이 {len(members)}명임(2~4명이어야 함)")

        roles = [m["main_role"] for m in members]
        for role in sorted(set(roles)):
            if roles.count(role) > 1:
                problems.append(f"{team_name}: 주 역할이 같은 학생이 둘 이상임({role})")

        if not has_required_roles(members):
            problems.append(f"{team_name}: 기획자와 웹 프로그래머를 서로 다른 학생이 맡을 수 없음")

    return problems

def missing_required(members):
    can_pl = [can_do(m, PL) for m in members]
    can_wp = [can_do(m, WP) for m in members]
    for i in range(len(members)):
        for j in range(len(members)):
            if i != j and can_pl[i] and can_wp[j]:
                return 0
    if any(can_pl) or any(can_wp):
        return 1
    return 2


def seats_ok(members_after):
    return 4 - len(members_after) >= missing_required(members_after)