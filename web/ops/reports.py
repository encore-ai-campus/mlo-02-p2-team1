"""관리자 페이지에 보여줄 결과 읽기: 파이프라인 출력 파일(data/03_cleaned, data/04_reports)과 MySQL 적재 상태.

파일이 없거나 테이블이 아직 없으면 예외 대신 {"missing": 사유}를 돌려 화면에 안내한다.
"""
from __future__ import annotations

import csv, json, re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from django.db import connection, DatabaseError

from .steps import ROOT

REPORTS = ROOT / "data" / "04_reports" / "quality"
VALIDATION = ROOT / "data" / "04_reports" / "validation"
INT_COLS = {"rows", "issue_count", "repaired_cells", "repaired_rows", "open_issues", "quarantined_rows", "detected",
            "repaired", "accepted", "open", "residual_after_repair", "fail_count", "total_count", "raw_rows",
            "unchanged_rows", "removed_rows", "processed_sum", "difference", "cleaned_rows", "analysis_rows"}
SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def _read_csv(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in INT_COLS & r.keys():
            try:
                r[k] = int(float(r[k])) if r[k] != "" else None
            except ValueError:
                pass
    return rows


def _mtime(path: Path):
    return datetime.fromtimestamp(path.stat().st_mtime)


def _guard(fn):
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except FileNotFoundError as e:
            return {"missing": f"결과 파일 없음: {Path(e.filename).relative_to(ROOT) if e.filename else e} — 해당 단계를 먼저 실행하세요."}
        except DatabaseError as e:
            return {"missing": f"DB 조회 실패: {e.args[-1] if e.args else e} — DB 적재 단계를 먼저 실행하세요."}
        except (ValueError, KeyError, csv.Error, json.JSONDecodeError) as e:
            return {"missing": f"결과 파일 형식 오류: {e}"}
    return wrapper


@_guard
def recovery_summary():
    path = REPORTS / "run_result.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"data": data, "updated": _mtime(path), "report": REPORTS / "quality_report.html"}


@_guard
def error_analysis():
    files = _read_csv(REPORTS / "repair_summary.csv")
    dq = _read_csv(REPORTS / "dq_summary.csv")
    dq.sort(key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), -(r["detected"] or 0)))

    by_type = defaultdict(lambda: Counter())
    for r in dq:
        t = by_type[r["error_type_korean"] or r["error_type"]]
        for k in ("detected", "repaired", "accepted", "open", "residual_after_repair"):
            t[k] += r[k] or 0
    types = sorted(({"name": k, **v} for k, v in by_type.items()), key=lambda r: -r["detected"])
    max_detected = max((t["detected"] for t in types), default=0) or 1
    for t in types:
        t["bar"] = round(100 * t["detected"] / max_detected, 1)
        t["fixed_pct"] = round(100 * (t["repaired"] + t["accepted"]) / t["detected"], 1) if t["detected"] else 0

    status = Counter()
    open_samples = []
    with open(REPORTS / "validation_issues.csv", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            status[r["status"]] += 1
            if r["status"] in ("OPEN", "QUARANTINED") and len(open_samples) < 40:
                open_samples.append(r)
    totals = {k: sum(r[k] or 0 for r in files) for k in ("rows", "issue_count", "repaired_cells", "open_issues", "quarantined_rows")}
    return {"files": files, "dq": dq, "types": types, "status": status.most_common(), "open_samples": open_samples,
            "totals": totals, "updated": _mtime(REPORTS / "dq_summary.csv")}


@_guard
def pandas_validation():
    rows = _read_csv(VALIDATION / "validation_result.csv")
    recon = _read_csv(VALIDATION / "row_reconciliation.csv")
    return {"counts": _status_counts(rows), "issues": [r for r in rows if r["status"] in ("FAIL", "WARN")],
            "recon": recon, "rows": rows, "updated": _mtime(VALIDATION / "validation_result.csv"),
            "report": VALIDATION / "validation_report.html"}


def _status_counts(rows):
    c = Counter(r["status"] for r in rows)
    return [(s, c.get(s, 0)) for s in ("FAIL", "WARN", "PASS", "INFO")]


LOAD_PAIRS = [("session", "stg_sessions"), ("session_driver", "stg_drivers"), ("lap", "stg_laps"),
              ("stint", "stg_stints"), ("pit_event", "stg_pit"), ("weather", "stg_weather"),
              ("starting_grid", "stg_starting_grid"), ("session_result", "stg_session_result"),
              ("position_event", "stg_position"), ("race_control_event", "stg_race_control"),
              ("interval_event", "stg_intervals"), ("quality_issue", "stg_validation_issues"),
              ("repair_detail", "stg_repair_detail")]


def _existing_tables(cur):
    cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")
    return {r[0] for r in cur.fetchall()}


@_guard
def mysql_integrity():
    with connection.cursor() as cur:
        tables = _existing_tables(cur)
        load = []
        for table, stg in LOAD_PAIRS:  # 이름은 고정 목록에서만 사용
            staged = loaded = None
            if stg in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{stg}`")
                staged = cur.fetchone()[0]
            if table in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                loaded = cur.fetchone()[0]
            diff = loaded - staged if staged is not None and loaded is not None else None
            load.append({"table": table, "staged": staged, "loaded": loaded, "diff": diff,
                         "status": "PASS" if diff == 0 else ("MISSING" if diff is None else "FAIL")})

        checks = []
        if {"vc_result", "ref_validation_check"} <= tables:
            cur.execute("""
                SELECT r.check_id, c.korean_category, c.check_name, r.target, c.severity, r.fail_count, r.total_count,
                       CASE WHEN c.severity = 'INFO' THEN 'INFO' WHEN r.fail_count = 0 THEN 'PASS'
                            WHEN c.severity = 'ERROR' THEN 'FAIL' ELSE 'WARN' END, r.note, c.description
                FROM vc_result r JOIN ref_validation_check c ON c.check_id = r.check_id ORDER BY r.check_id, r.id""")
            keys = ["check_id", "korean_category", "check_name", "target", "severity", "fail_count", "total_count",
                    "status", "note", "description"]
            checks = [dict(zip(keys, r)) for r in cur.fetchall()]

        points = []
        if {"v_race_outcome", "v_team_race_points"} <= tables:
            cur.execute("""
                SELECT year, SUM(race_base_points),
                       (SELECT SUM(race_base_points) FROM v_team_race_points t WHERE t.year = o.year)
                FROM v_race_outcome o GROUP BY year ORDER BY year""")
            points = [{"year": y, "driver": d, "team": t, "ok": d == t} for y, d, t in cur.fetchall()]

    if not any(r["staged"] is not None for r in load) and not checks:
        return {"missing": "MySQL에 적재된 데이터가 없습니다 — 'DB 적재'를 먼저 실행하세요."}
    return {"load": load, "load_ok": all(r["status"] == "PASS" for r in load), "checks": checks,
            "counts": _status_counts(checks), "issues": [c for c in checks if c["status"] in ("FAIL", "WARN")],
            "points": points, "points_ok": bool(points) and all(p["ok"] for p in points)}


def compare_validation(pandas_v, mysql_v):
    """같은 검사 ID·대상의 위반 건수가 pandas와 MySQL에서 같은지."""
    if "missing" in pandas_v or "missing" in mysql_v or not mysql_v.get("checks"):
        return None
    p = {(r["check_id"], r["target"]): r["fail_count"] for r in pandas_v["rows"]}
    m = {(r["check_id"], r["target"]): r["fail_count"] for r in mysql_v["checks"]}
    diffs = [{"check_id": k[0], "target": k[1], "pandas": p.get(k), "mysql": m.get(k)}
             for k in sorted(p.keys() | m.keys()) if p.get(k) != m.get(k)]
    return {"total": len(p.keys() | m.keys()), "diffs": diffs}


ERROR_LINE = re.compile(r"^ERROR \d+|Error:|Exception|Traceback|\[오류\]|실패")


def log_errors(run, limit=40):
    """실패한 실행 로그에서 오류로 보이는 줄과 앞뒤 문맥."""
    try:
        lines = run.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []
    hits = []
    for i, line in enumerate(lines):
        if ERROR_LINE.search(line) and not line.startswith("-----"):
            hits.append({"no": i + 1, "text": line, "before": lines[max(0, i - 2):i]})
    return hits[-limit:]


def log_tail(run, lines=200):
    try:
        with open(run.log_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 64 * 1024))
            text = f.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    return "\n".join(text.splitlines()[-lines:])
