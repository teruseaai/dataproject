from rules import PL, WP, can_do, has_required_roles, validate_assignment


def find_assignment(teams, unassigned):
    names = list(teams.keys())
    by_id = {s["id"]: s for s in unassigned}
    assignment = {name: [] for name in names}

    def members(name):
        return list(teams[name]) + [by_id[i] for i in assignment[name]]

    def search(k):
        if k == len(unassigned):
            return validate_assignment(teams, unassigned, assignment) == []
        student = unassigned[k]
        for name in names:
            current = members(name)
            if len(current) >= 4:
                continue
            if any(m["main_role"] == student["main_role"] for m in current):
                continue
            assignment[name].append(student["id"])
            if search(k + 1):
                return True
            assignment[name].pop()
        return False

    if search(0):
        return {name: list(ids) for name, ids in assignment.items()}
    return None

def explain_impossible(teams, unassigned):
    reasons = []
    total = sum(len(m) for m in teams.values()) + len(unassigned)
    if total < 2 * len(teams):
        reasons.append("학생 수가 모자라 모든 팀을 2명 이상으로 만들 수 없음")
    if total > 4 * len(teams):
        reasons.append("학생 수가 많아 모든 팀을 4명 이하로 만들 수 없음")

    for name, current in teams.items():
        pool = list(current) + (list(unassigned) if len(current) < 4 else [])
        no_wp = not any(can_do(s, WP) for s in pool)
        no_pl = not any(can_do(s, PL) for s in pool)
        if no_wp:
            reasons.append(f"{name}에 웹 프로그래머를 맡을 학생이 없음")
        if no_pl:
            reasons.append(f"{name}에 기획자를 맡을 학생이 없음")
        if not no_wp and not no_pl and not has_required_roles(pool):
            reasons.append(f"{name}에 기획자와 웹 프로그래머를 서로 다른 학생이 맡을 수 없음")

    if not reasons:
        reasons.append("모든 경우를 따져 봤지만 규칙을 지키는 배정이 없음")
    return reasons