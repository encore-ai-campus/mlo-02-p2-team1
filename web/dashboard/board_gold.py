"""Decision Board Gold ↔ MySQL.

화면(/)은 이 모듈의 read_board()로 MySQL의 gold_board_* 테이블을 읽는다.
적재 원천은 분석 결과 내보내기 파일 data/05_gold/decision_board.json이다
(이 수치를 만든 분석 코드는 저장소에 없으므로, 재계산 대신 결과를 그대로 정규화해 적재한다).

    sql/06_create_gold_board.sql                                 # 테이블 생성 (컬럼 정의는 이 SQL이 기준)
    venv\\Scripts\\python.exe web\\manage.py load_board_gold     # 파일 → MySQL (관리자 화면 'Gold 갱신'에 포함)

기획서 Gold 9개 마트와의 대응
    gold_board_driver_profile  ≈ 1 driver_performance + 5 driver_profile (시즌 × 드라이버 소속 구간)
    gold_board_team_profile    ≈ 6 team_profile + 7 team_pit_benchmark (시즌 × 팀)
    gold_board_team_race       팀 × 경기 상대 페이스 (6의 경기 단위 근거)
    gold_board_race_outcome    ≈ 3 race_outcome (경기 × 드라이버, 본경기 기본 포인트)
    gold_board_driver_team_fit ≈ 8 driver_team_fit (팀 자리 × 타 팀 후보, 판정)
      gold_board_fit_race        후보 판정의 공통 경기별 차이
      gold_board_fit_scenario    후보 판정의 정제 조건 11가지별 결과
    gold_board_data_quality    ≈ 9 data_quality
    gold_board_coverage        경기별 원천 커버리지
    gold_board_source          원천 11종 매니페스트
    gold_board_meta            기준일·조건·임계값·방법론·요약 (1행)
아직 별도 테이블이 없는 마트: 2 tyre_performance(스틴트 단위), 4 pit_strategy(피트 이벤트 단위) — 팀 단위 집계만 team_profile에 있음.
"""
from __future__ import annotations

import hashlib, json, math
from datetime import datetime
from pathlib import Path

import pandas as pd
from django.conf import settings
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

SNAPSHOT = Path(settings.BASE_DIR).parent / "data" / "05_gold" / "decision_board.json"
P = "gold_board_"

# 스냅샷 키 → 테이블. 행 순서를 지키려고 seq를 둔다.
FLAT = {
    "profiles": "driver_profile", "teams": "team_profile", "team_races": "team_race", "outcomes": "race_outcome",
    "coverage": "coverage", "quality": "data_quality", "source_counts": "source",
}
BOOL_COLS = {"eligible", "current_segment", "pit_source_present", "special_strategy", "own_faster"}  # TINYINT(1) → bool
META_JSON = ["years", "variants", "thresholds", "summary", "methodology"]
CASE_SCALARS = ["year", "seat", "candidate", "status", "delta", "low", "high", "common_races", "faster", "missing",
                "own_negative", "own_missing", "first", "second", "loo_min", "loo_max", "tyre_races", "tyre_delta",
                "tyre_low", "tyre_high", "iqr_delta", "iqr_low", "iqr_high"]
RACE_COLS = ["session_key", "delta_pct", "candidate_rel_pct", "seat_rel_pct"]          # common[i]
SCEN_COLS = ["delta_pct", "common_races", "own_teammate_delta_sec", "own_faster"]      # scenarios[i] (variants 순서)


class BoardNotLoaded(Exception):
    pass


def engine():
    db = settings.DATABASES["default"]
    url = URL.create("mysql+pymysql", username=db["USER"], password=db["PASSWORD"], host=db["HOST"] or "127.0.0.1",
                     port=int(db["PORT"] or 3306), database=db["NAME"], query={"charset": "utf8mb4"})
    return create_engine(url, pool_pre_ping=True)


TABLES = list(FLAT.values()) + ["driver_team_fit", "fit_race", "fit_scenario", "meta"]


def _write(conn, name, df):
    """sql/06이 만든 테이블에 적재한다. 컬럼이 테이블 정의와 다르면 멈춘다."""
    table_cols = {c["name"] for c in inspect(conn).get_columns(P + name)}
    extra = set(df.columns) - table_cols
    if extra:
        raise ValueError(f"{P}{name}에 없는 컬럼 {sorted(extra)} — sql/06_create_gold_board.sql을 데이터에 맞게 고치세요")
    df.to_sql(P + name, conn, if_exists="append", index=False, chunksize=2000, method="multi")


def load_board(source: Path = SNAPSHOT) -> dict:
    """스냅샷 파일을 gold_board_* 테이블에 다시 채운다 (테이블은 sql/06이 만든다). 적재 행 수를 반환."""
    raw = source.read_bytes()
    data = json.loads(raw)
    counts = {}
    with engine().begin() as conn:
        missing = [P + t for t in TABLES if not inspect(conn).has_table(P + t)]
        if missing:
            raise BoardNotLoaded(f"테이블 없음: {', '.join(missing)} — 먼저 sql/06_create_gold_board.sql을 실행하세요")
        for t in TABLES:
            conn.execute(text(f"DELETE FROM `{P}{t}`"))  # 트랜잭션 안에서 비우고 다시 채움 (실패하면 이전 데이터 유지)
        for key, name in FLAT.items():
            df = pd.DataFrame(data[key])
            df.insert(0, "seq", range(len(df)))
            _write(conn, name, df)
            counts[name] = len(df)

        cases, races, scens = [], [], []
        for seq, (case_id, c) in enumerate(data["cases"].items()):
            cases.append({"seq": seq, "case_id": case_id, **{k: c[k] for k in CASE_SCALARS}, "reasons": json.dumps(c["reasons"], ensure_ascii=False)})
            races += [{"case_id": case_id, "seq": i, **dict(zip(RACE_COLS, v))} for i, v in enumerate(c["common"])]
            scens += [{"case_id": case_id, "seq": i, "variant": data["variants"][i], **dict(zip(SCEN_COLS, v))} for i, v in enumerate(c["scenarios"])]
        _write(conn, "driver_team_fit", pd.DataFrame(cases))
        _write(conn, "fit_race", pd.DataFrame(races))
        _write(conn, "fit_scenario", pd.DataFrame(scens))
        counts.update(driver_team_fit=len(cases), fit_race=len(races), fit_scenario=len(scens))

        meta = {"seq": 0, "created": data["created"], "cutoff": data["cutoff"], **{k: json.dumps(data[k], ensure_ascii=False) for k in META_JSON},
                "source_file": source.name, "source_sha256": hashlib.sha256(raw).hexdigest(), "loaded_at": datetime.now().isoformat(timespec="seconds")}
        _write(conn, "meta", pd.DataFrame([meta]))
        counts["meta"] = 1
    _cache.clear()
    return counts


# ───────── 읽기 ─────────
_cache: dict = {}


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if hasattr(v, "item"):  # numpy 스칼라
        v = v.item()
        if isinstance(v, float) and math.isnan(v):
            return None
    return v


def _records(df):
    rows = []
    for rec in df.drop(columns=["seq"], errors="ignore").to_dict("records"):
        rows.append({k: (bool(v) if k in BOOL_COLS and _clean(v) is not None else _clean(v)) for k, v in rec.items()})
    return rows


def read_board() -> dict:
    """MySQL gold_board_*에서 화면용 데이터(스냅샷과 같은 구조)를 만든다. 적재 시각이 바뀔 때만 다시 읽는다."""
    eng = engine()
    with eng.connect() as conn:
        if not inspect(conn).has_table(P + "meta"):
            raise BoardNotLoaded("gold_board_meta 없음")
        meta = conn.execute(text(f"SELECT * FROM {P}meta")).mappings().first()
        if meta is None:
            raise BoardNotLoaded("gold_board_meta 비어 있음")
        if _cache.get("loaded_at") == meta["loaded_at"]:
            return _cache["data"]

        q = lambda name: pd.read_sql(text(f"SELECT * FROM {P}{name} ORDER BY seq"), conn)
        out = {"created": meta["created"], "cutoff": meta["cutoff"]}
        out["years"], out["variants"] = json.loads(meta["years"]), json.loads(meta["variants"])
        for key, name in FLAT.items():
            out[key] = _records(q(name))

        races = {}
        for r in _records(pd.read_sql(text(f"SELECT * FROM {P}fit_race ORDER BY case_id, seq"), conn)):
            races.setdefault(r["case_id"], []).append([r[c] for c in RACE_COLS])
        scens = {}
        for r in _records(pd.read_sql(text(f"SELECT * FROM {P}fit_scenario ORDER BY case_id, seq"), conn)):
            scens.setdefault(r["case_id"], []).append([r[c] for c in SCEN_COLS])
        cases = {}
        for r in _records(q("driver_team_fit")):
            cid = r.pop("case_id")
            reasons = json.loads(r.pop("reasons") or "[]")
            row = {k: r[k] for k in ("year", "seat", "candidate", "status", "delta", "low", "high", "common_races")}
            row["common"] = races.get(cid, [])
            row.update({k: r[k] for k in ("faster", "missing", "own_negative", "own_missing", "first", "second", "loo_min", "loo_max")})
            row["scenarios"] = scens.get(cid, [])
            row.update({k: r[k] for k in ("tyre_races", "tyre_delta", "tyre_low", "tyre_high", "iqr_delta", "iqr_low", "iqr_high")})
            row["reasons"] = reasons
            cases[cid] = row
        out["cases"] = cases
        for k in ("summary", "thresholds", "methodology"):
            out[k] = json.loads(meta[k])
        out["source"] = {"table_prefix": P, "loaded_at": meta["loaded_at"], "source_file": meta["source_file"], "source_sha256": meta["source_sha256"]}

    text_json = json.dumps(out, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")  # </script> 방지
    _cache.update(loaded_at=meta["loaded_at"], data={"payload": out, "json": text_json})
    return _cache["data"]


def diff_against(source: Path = SNAPSHOT, tol=1e-9) -> list[str]:
    """DB에서 읽은 데이터가 원천 파일과 같은지 비교한다 (숫자는 허용 오차). 다른 경로 목록을 반환."""
    expected = json.loads(source.read_text(encoding="utf-8"))
    got = read_board()["payload"]
    diffs = []

    def walk(a, b, path):
        if len(diffs) > 20:
            return
        if isinstance(a, dict):
            if not isinstance(b, dict) or set(a) - set(b):
                diffs.append(f"{path}: 키 누락 {sorted(set(a) - set(b if isinstance(b, dict) else {}))[:5]}")
                return
            for k in a:
                walk(a[k], b[k], f"{path}.{k}")
        elif isinstance(a, list):
            if not isinstance(b, list) or len(a) != len(b):
                diffs.append(f"{path}: 길이 {len(a)} ≠ {len(b) if isinstance(b, list) else type(b).__name__}")
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]")
        elif isinstance(a, bool) or isinstance(b, bool):
            if a != b:
                diffs.append(f"{path}: {a!r} ≠ {b!r}")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not math.isclose(a, b, rel_tol=tol, abs_tol=tol):
                diffs.append(f"{path}: {a} ≠ {b}")
        elif a != b:
            diffs.append(f"{path}: {a!r} ≠ {b!r}")

    walk(expected, got, "$")
    return diffs
