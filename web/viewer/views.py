from django.db import connection
from django.http import Http404
from django.shortcuts import render

PAGE_SIZE = 50
EXCLUDE_PREFIX = ("auth_", "django_")  # Django 기본 테이블은 목록에서 제외

# 테이블 이름 접두사로 묶어서 보여준다 (팀 SQL 01~06 구조)
GROUPS = [
    ("stg_", "스테이징 (정제 결과·추가 데이터 원문)"),
    ("ref_", "코드·규칙 테이블"),
    ("vc_", "검증 결과 (03_validate_cleaned)"),
    ("gold_board_", "Decision Board Gold (06_create_gold_board · 화면이 읽는 테이블)"),
    ("gold_", "이전 시안 Gold (build_gold)"),
    ("ops_", "파이프라인 실행 기록 (/ops/)"),
    ("v_", "뷰"),
]


def data_tables():
    with connection.cursor() as cur:
        cur.execute("""
            SELECT TABLE_NAME, TABLE_ROWS, TABLE_TYPE
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME
        """)
        return [r for r in cur.fetchall() if not r[0].startswith(EXCLUDE_PREFIX)]


def grouped(tables):
    out = {label: [] for _, label in GROUPS}
    out["설계 스키마 (04_create_schema)"] = []
    for name, rows, ttype in tables:
        label = next((lb for pf, lb in GROUPS if name.startswith(pf)), "설계 스키마 (04_create_schema)")
        if ttype == "VIEW":
            label = "뷰"
        out[label].append((name, rows, ttype))
    return [(k, v) for k, v in out.items() if v]


def table_list(request):
    return render(request, "viewer/table_list.html", {"groups": grouped(data_tables())})


def primary_key(name):
    with connection.cursor() as cur:
        cur.execute("""
            SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """, [name])
        return [r[0] for r in cur.fetchall()]


def table_detail(request, name):
    if name not in [t[0] for t in data_tables()]:  # 존재하는 테이블만 허용 (SQL 인젝션 방지)
        raise Http404("테이블이 없습니다.")

    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1
    offset = (page - 1) * PAGE_SIZE
    pk = primary_key(name)
    order = ("ORDER BY " + ", ".join(f"`{c}`" for c in pk)) if pk else ""

    with connection.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM `{name}`")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT * FROM `{name}` {order} LIMIT {PAGE_SIZE} OFFSET {offset}")
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()

    last_page = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return render(request, "viewer/table_detail.html", {
        "name": name, "cols": cols, "rows": rows, "total": total, "pk": pk,
        "page": page, "last_page": last_page,
        "prev": page - 1 if page > 1 else None,
        "next": page + 1 if page < last_page else None,
    })
