import json

from rules import validate_assignment


def _describe(student):
    subs = ", ".join(student["sub_roles"]) if student["sub_roles"] else "없음"
    return f"{student['id']} ({student['name']}, 주 역할: {student['main_role']}, 보조 역할: {subs})"


def build_prompt(teams, unassigned):
    lines = [
        "팀이 없는 학생을 팀에 배정하라. 아래 규칙을 모두 지켜야 한다.",
        "",
        "규칙:",
        "1. 팀이 없는 학생만 팀에 넣는다. 이미 팀에 있는 학생은 옮기지 않는다.",
        "2. 팀이 없는 학생은 한 명도 빠뜨리지 않고 모두 배정하며, 한 학생은 한 팀에만 넣는다.",
        "3. 배정이 끝난 뒤 모든 팀은 2명 이상 4명 이하여야 한다.",
        "4. 한 팀에 주 역할이 같은 학생이 2명 이상이면 안 된다. 보조 역할은 이 판단에 쓰지 않는다.",
        "5. 모든 팀에는 기획자를 맡을 수 있는 학생과 웹 프로그래머를 맡을 수 있는 학생이 서로 다른 사람으로 1명씩 있어야 한다. 주 역할이나 보조 역할로 맡을 수 있다.",
        "",
        "지금의 팀 구성:",
    ]
    for team_name, members in teams.items():
        if members:
            lines.append(f"- {team_name}: " + "; ".join(_describe(m) for m in members))
        else:
            lines.append(f"- {team_name}: (빈 팀)")
    lines.append("")
    lines.append("팀이 없는 학생:")
    for s in unassigned:
        lines.append("- " + _describe(s))
    lines.append("")
    lines.append("답은 JSON만 쓴다. 다른 설명은 쓰지 않는다.")
    lines.append("모든 팀 이름을 키로 쓰고, 값은 그 팀에 새로 넣을 학생의 학번 목록이다. 넣을 학생이 없으면 빈 목록이다.")
    lines.append('예: {"팀1": ["2026001"], "팀2": []}')
    return "\n".join(lines)


def parse_response(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("JSON을 찾을 수 없음")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON이 객체가 아님")
    result = {}
    for team, ids in data.items():
        if not isinstance(ids, list):
            raise ValueError("학번 목록이 아님")
        result[str(team)] = [str(i) for i in ids]
    return result


def make_check(teams, unassigned):
    def check(text):
        try:
            assignment = parse_response(text)
        except ValueError:
            return False, "JSON으로 읽을 수 없음"
        problems = validate_assignment(teams, unassigned, assignment)
        if problems:
            return False, problems[0]
        return True, ""

    return check