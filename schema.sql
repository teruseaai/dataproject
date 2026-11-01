-- 학생과 관리자
create table if not exists tf_students (
    id bigserial primary key,
    student_no text unique not null,
    name text not null,
    main_role text check (main_role in ('기획자', '웹 프로그래머', '프론트엔드 디자이너', '테스터', '보고서 작성자', '발표자')),
    password_hash text not null,
    is_admin boolean not null default false
);

-- 보조 역할 (학생 1명에 0~2행)
create table if not exists tf_student_sub_roles (
    student_id bigint not null references tf_students(id) on delete cascade,
    role text not null check (role in ('기획자', '웹 프로그래머', '프론트엔드 디자이너', '테스터', '보고서 작성자', '발표자')),
    primary key (student_id, role)
);

-- 팀
create table if not exists tf_teams (
    id bigserial primary key,
    name text unique not null
);
-- 팀원 (팀마다 자리 1~4)
create table if not exists tf_members (
    team_id bigint not null references tf_teams(id) on delete cascade,
    slot_no int not null check (slot_no between 1 and 4),
    student_id bigint not null unique references tf_students(id) on delete cascade,
    primary key (team_id, slot_no)
);

-- 지원
create table if not exists tf_applications (
    id bigserial primary key,
    team_id bigint not null references tf_teams(id) on delete cascade,
    student_id bigint not null references tf_students(id) on delete cascade,
    status text not null default '대기' check (status in ('대기', '승인', '거절')),
    reason text,
    created_at timestamptz not null default now()
);

-- 투표
create table if not exists tf_votes (
    application_id bigint not null references tf_applications(id) on delete cascade,
    voter_id bigint not null references tf_students(id) on delete cascade,
    vote text not null check (vote in ('찬성', '거부')),
    primary key (application_id, voter_id)
);

-- 설정 (모집 마감 여부 등)
create table if not exists tf_settings (
    key text primary key,
    value text
);