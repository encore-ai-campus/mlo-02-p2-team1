"""정제 후 데이터 검증 (pandas).

파이프라인이 만든 정제 결과(repaired/)와 미오염 추가 데이터 5종을 읽어
결측·중복·참조·범위·정합성·포인트·대사·JOIN 행 증폭을 검사한다.
검사 항목 정의는 data/02_reference/standard_dictionary/validation_checks.csv(VC01~VC71)이며,
같은 ID로 sql/03_validate_cleaned.sql 도 같은 검사를 수행한다.

실행(저장소 루트):
    python -m pipeline.validate_cleaned
    python -m pipeline.validate_cleaned --cleaned data/03_cleaned --extra data/01_raw/f1_extra_data.zip

출력(--out, 기본 data/04_reports/validation):
    validation_result.csv    검사ID × 대상 파일별 위반 건수·상태(PASS/FAIL/WARN/INFO)
    validation_samples.csv   위반 행 샘플(검사·대상별 최대 --samples 행)
    null_profile.csv         파일·컬럼별 공백 건수와 비율
    validation_report.html   요약·항목별 결과·위반 샘플·결측 프로파일 HTML 리포트
    validation_report.md     요약(마크다운)
종료 코드: ERROR 등급 위반이 있으면 1, 없으면 0.
"""
import argparse, html, io, re, sys, zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DICT = ROOT / "data" / "02_reference" / "standard_dictionary"

ORIGINAL = ["sessions", "drivers", "laps", "stints", "weather", "pit"]
EXTRA = ["starting_grid", "session_result", "position", "race_control", "intervals"]
MANAGEMENT = {"source_file", "repair_status", "repair_method", "repair_confidence", "repair_reason", "dq_codes", "quarantine_flag"}

KEYS = {
    "sessions": ["session_key"],
    "drivers": ["session_key", "driver_number"],
    "laps": ["session_key", "driver_number", "lap_number"],
    "stints": ["session_key", "driver_number", "stint_number"],
    "weather": ["session_key", "date"],
    "pit": ["session_key", "driver_number", "lap_number"],
    "starting_grid": ["session_key", "driver_number"],
    "session_result": ["session_key", "driver_number"],
    "position": ["session_key", "driver_number", "date"],
    "intervals": ["session_key", "driver_number", "date"],
    "race_control": [],  # 자연키 없음 → VC11 완전 중복으로 검사
}
NUMERIC = {
    "sessions": ["circuit_key", "country_key", "meeting_key", "session_key", "year"],
    "drivers": ["driver_number", "meeting_key", "session_key"],
    "laps": ["driver_number", "duration_sector_1", "duration_sector_2", "duration_sector_3", "i1_speed", "i2_speed",
             "st_speed", "lap_duration", "lap_number", "meeting_key", "session_key"],
    "stints": ["driver_number", "lap_end", "lap_start", "meeting_key", "session_key", "stint_number", "tyre_age_at_start"],
    "weather": ["air_temperature", "humidity", "meeting_key", "pressure", "session_key", "track_temperature",
                "wind_direction", "wind_speed"],
    "pit": ["driver_number", "lane_duration", "lap_number", "meeting_key", "pit_duration", "session_key", "stop_duration"],
    "starting_grid": ["position", "driver_number", "lap_duration", "meeting_key", "session_key"],
    "session_result": ["position", "driver_number", "number_of_laps", "points", "duration", "meeting_key", "session_key"],
    "position": ["session_key", "meeting_key", "driver_number", "position"],
    "race_control": ["meeting_key", "session_key", "driver_number", "lap_number", "sector", "qualifying_phase"],
    "intervals": ["session_key", "meeting_key", "driver_number"],
}
GAP_COLUMNS = {"session_result": ["gap_to_leader"], "intervals": ["interval", "gap_to_leader"]}
GAP_TEXT = re.compile(r"^\+\d+ LAPS?$")
DATES = {"sessions": ["date_start", "date_end"], "laps": ["date_start"], "pit": ["date"], "weather": ["date"],
         "position": ["date"], "race_control": ["date"], "intervals": ["date"]}
# (파일, 컬럼): (최소, 최대, 최소 포함 여부)
RANGES = {
    ("sessions", "year"): (2023, 2026, True),
    ("laps", "lap_duration"): (0, None, False), ("laps", "duration_sector_1"): (0, None, False),
    ("laps", "duration_sector_2"): (0, None, False), ("laps", "duration_sector_3"): (0, None, False),
    ("laps", "i1_speed"): (0, None, True), ("laps", "i2_speed"): (0, None, True), ("laps", "st_speed"): (0, None, True),
    ("laps", "lap_number"): (1, None, True),
    ("stints", "stint_number"): (1, None, True), ("stints", "lap_start"): (1, None, True),
    ("stints", "lap_end"): (0, None, True), ("stints", "tyre_age_at_start"): (0, None, True),
    ("pit", "lane_duration"): (0, None, True), ("pit", "pit_duration"): (0, None, True),
    ("pit", "stop_duration"): (0, None, True), ("pit", "lap_number"): (1, None, True),
    ("weather", "humidity"): (0, 100, True), ("weather", "wind_direction"): (0, 360, True),
    ("weather", "wind_speed"): (0, None, True), ("weather", "pressure"): (0, None, False),
    ("weather", "air_temperature"): (-20, 60, True), ("weather", "track_temperature"): (-20, 80, True),
    ("starting_grid", "position"): (1, 30, True), ("starting_grid", "lap_duration"): (0, None, False),
    ("session_result", "position"): (1, 30, True), ("session_result", "number_of_laps"): (0, None, True),
    ("session_result", "points"): (0, 26, True), ("session_result", "duration"): (0, None, True),
    ("position", "position"): (1, 30, True),
    ("race_control", "lap_number"): (0, None, True), ("race_control", "sector"): (1, None, True),
}
ZERO_IMPUTATION = {"laps": ["lap_duration", "duration_sector_1", "duration_sector_2", "duration_sector_3",
                            "i1_speed", "i2_speed", "st_speed"],
                   "pit": ["lane_duration", "pit_duration", "stop_duration"],
                   "stints": ["tyre_age_at_start"]}


# ---------- 읽기 ----------
def read_csv(src, name, category_cols=()):
    dtype = {c: "category" for c in category_cols}
    df = pd.read_csv(src, dtype=dtype, keep_default_na=False, encoding="utf-8-sig", low_memory=False)
    for col in df.columns:
        if col not in dtype:
            df[col] = df[col].astype(str)
    return df


def load_extra(path):
    path = Path(path)
    tables = {}
    cats = {"intervals": ["session_key", "meeting_key", "driver_number"],
            "position": ["session_key", "meeting_key", "driver_number"]}
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = {Path(n).stem: n for n in zf.namelist() if n.endswith(".csv")}
            for name in EXTRA:
                if name in names:
                    tables[name] = read_csv(io.BytesIO(zf.read(names[name])), name, cats.get(name, ()))
    else:
        for name in EXTRA:
            file = path / f"{name}.csv"
            if file.exists():
                tables[name] = read_csv(file, name, cats.get(name, ()))
    return tables


def business_columns(df):
    return [c for c in df.columns if not c.startswith("original_") and c not in MANAGEMENT]


def blank(s):
    return s.astype(str).str.strip() == ""


def num(s):
    s = s.astype(str)
    return pd.to_numeric(s.where(s.str.strip() != ""), errors="coerce")


def ts(s):
    s = s.astype(str)
    return pd.to_datetime(s.where(s.str.strip() != ""), format="ISO8601", utc=True, errors="coerce")


# ---------- 결과 기록 ----------
class Result:
    def __init__(self, catalogue, samples):
        self.catalogue = catalogue
        self.rows, self.sample_frames = [], []
        self.samples = samples

    def add(self, check_id, target, fail, total, sample=None, note=""):
        meta = self.catalogue.loc[check_id]
        fail = int(fail)
        if meta["severity"] == "INFO":
            status = "INFO"
        elif fail == 0:
            status = "PASS"
        else:
            status = "FAIL" if meta["severity"] == "ERROR" else "WARN"
        self.rows.append({"check_id": check_id, "category": meta["category"], "korean_category": meta["korean_category"],
                          "check_name": meta["check_name"], "target": target, "severity": meta["severity"],
                          "fail_count": fail, "total_count": int(total), "status": status,
                          "description": meta["description"], "note": note})
        if sample is not None and len(sample):
            s = sample.head(self.samples).astype(str)
            detail = s.apply(lambda r: "; ".join(f"{k}={v}" for k, v in r.items()), axis=1)
            self.sample_frames.append(pd.DataFrame({"check_id": check_id, "target": target, "detail": detail}))

    def frame(self):
        return pd.DataFrame(self.rows)

    def sample_frame(self):
        return pd.concat(self.sample_frames, ignore_index=True) if self.sample_frames else \
            pd.DataFrame(columns=["check_id", "target", "detail"])


# ---------- 검사 ----------
def check_missing(T, R):
    profile = []
    for name, df in T.items():
        cols = KEYS[name] + (["meeting_key"] if "meeting_key" in df.columns and "meeting_key" not in KEYS[name] else [])
        if name == "race_control":
            cols = ["session_key", "meeting_key", "date", "category"]
        mask = pd.concat([blank(df[c]) for c in cols], axis=1).any(axis=1)
        R.add("VC01", name, mask.sum(), len(df), df.loc[mask, cols])
        total_blank = 0
        for col in business_columns(df):
            n = int(blank(df[col]).sum())
            total_blank += n
            profile.append({"table": name, "column": col, "rows": len(df), "blank": n,
                            "blank_rate": round(n / len(df), 6) if len(df) else 0})
        R.add("VC02", name, total_blank, len(df) * len(business_columns(df)), note="null_profile.csv 참고")
    for name, cols in ZERO_IMPUTATION.items():
        df = T[name]
        if "original_" + cols[0] not in df.columns:
            continue
        mask = pd.Series(False, index=df.index)
        for col in cols:
            mask |= blank(df["original_" + col]) & (num(df[col]) == 0)
        R.add("VC03", name, mask.sum(), len(df), df.loc[mask, KEYS[name]])
    if "session_result" in T:
        sr = T["session_result"]
        mask = blank(sr["position"]) & (sr["dnf"] != "True") & (sr["dns"] != "True") & (sr["dsq"] != "True")
        R.add("VC04", "session_result", mask.sum(), len(sr), sr.loc[mask, ["session_key", "driver_number", "number_of_laps", "gap_to_leader"]])
    return pd.DataFrame(profile)


def check_duplicates(T, R):
    for name, df in T.items():
        if KEYS[name]:
            mask = df.duplicated(KEYS[name], keep=False)
            extra = df.duplicated(KEYS[name]).sum()
            R.add("VC10", name, extra, len(df), df.loc[mask, KEYS[name]])
        cols = business_columns(df)
        mask = df.duplicated(cols, keep=False)
        R.add("VC11", name, df.duplicated(cols).sum(), len(df), df.loc[mask, cols[:6]])
    for name in ["session_result", "starting_grid"]:
        if name in T:
            df = T[name]
            ranked = df[~blank(df["position"])]
            mask = ranked.duplicated(["session_key", "position"], keep=False)
            R.add("VC12", name, ranked.duplicated(["session_key", "position"]).sum(), len(ranked),
                  ranked.loc[mask, ["session_key", "position", "driver_number"]])
    drivers = T["drivers"]
    for col in ["full_name", "name_acronym"]:
        d = drivers[~blank(drivers[col])]
        n = d.groupby(["session_key", col])["driver_number"].nunique()
        bad = n[n > 1].reset_index()
        R.add("VC13", f"drivers.{col}", len(bad), d.groupby(["session_key", col]).ngroups, bad)


def check_references(T, R):
    sessions, drivers = T["sessions"], T["drivers"]
    session_keys = set(sessions["session_key"])
    driver_keys = pd.MultiIndex.from_frame(drivers[["session_key", "driver_number"]])
    meeting = sessions.set_index("session_key")["meeting_key"]
    for name, df in T.items():
        if name in ("sessions", "starting_grid"):
            continue
        sk = df["session_key"].astype(str)
        mask = ~sk.isin(session_keys)
        R.add("VC20", name, mask.sum(), len(df), df.loc[mask, ["session_key"]].drop_duplicates())
        mk = sk.map(meeting)
        mask = mk.notna() & (mk != df["meeting_key"].astype(str))
        R.add("VC22", name, mask.sum(), len(df), df.loc[mask, ["session_key", "meeting_key"]].assign(expected=mk[mask]).drop_duplicates())
    for name in ["laps", "stints", "pit", "session_result", "position", "intervals", "race_control"]:
        if name not in T:
            continue
        df = T[name]
        sub = df if name != "race_control" else df[~blank(df["driver_number"])]
        pairs = pd.MultiIndex.from_arrays([sub["session_key"].astype(str), sub["driver_number"].astype(str)])
        mask = ~pairs.isin(driver_keys)
        R.add("VC21", name, mask.sum(), len(sub), sub.loc[mask, ["session_key", "driver_number"]].drop_duplicates())

    races = sessions[sessions["session_type"] == "Race"]
    race_by_meeting = races.groupby("meeting_key")["session_key"]
    if "starting_grid" in T:
        grid = T["starting_grid"]
        uses_race_key = grid["session_key"].isin(set(races["session_key"]))
        race_count = grid["meeting_key"].map(race_by_meeting.nunique()).fillna(0)
        grid_sessions = grid.groupby("meeting_key")["session_key"].transform("nunique")
        mask = uses_race_key | (race_count != 1) | (grid_sessions != 1)
        R.add("VC23", "starting_grid", mask.sum(), len(grid), grid.loc[mask, ["meeting_key", "session_key", "driver_number"]],
              note="Qualifying session_key → meeting_key → Race session_key")
        if "session_result" in T:
            result = T["session_result"]
            g = grid.assign(race_session_key=grid["meeting_key"].map(race_by_meeting.first()))
            res_keys = pd.MultiIndex.from_frame(result[["session_key", "driver_number"]])
            g_keys = pd.MultiIndex.from_frame(g[["race_session_key", "driver_number"]].astype(str))
            mask = ~g_keys.isin(res_keys)
            R.add("VC24", "starting_grid", mask.sum(), len(g), g.loc[mask, ["meeting_key", "session_key", "race_session_key", "driver_number"]])
            mask = ~res_keys.isin(g_keys)
            R.add("VC25", "session_result", mask.sum(), len(result),
                  result.loc[mask, ["meeting_key", "session_key", "driver_number", "position", "dns"]],
                  note="그리드 없는 Race 결과(피트레인 출발 등)")

    laps, pit, stints = T["laps"], T["pit"], T["stints"]
    lap_no = num(laps["lap_number"])
    max_lap = laps.assign(n=lap_no).groupby(["session_key", "driver_number"])["n"].max()
    pit_max = pd.MultiIndex.from_frame(pit[["session_key", "driver_number"]]).map(lambda k: max_lap.get(k))
    pit_max = pd.Series(pit_max, index=pit.index, dtype="float")
    mask = num(pit["lap_number"]) > pit_max
    R.add("VC26", "pit", mask.sum(), len(pit), pit.loc[mask, ["session_key", "driver_number", "lap_number"]].assign(max_lap=pit_max[mask]))

    # 랩 ↔ 스틴트 범위 JOIN: 매칭 0건(VC27), 2건 이상(VC71)
    st = stints.assign(ls=num(stints["lap_start"]), le=num(stints["lap_end"]))[["session_key", "driver_number", "stint_number", "ls", "le"]]
    lp = laps.assign(n=lap_no)[["session_key", "driver_number", "lap_number", "n"]].reset_index()
    joined = lp.merge(st, on=["session_key", "driver_number"], how="left")
    hit = (joined["n"] >= joined["ls"]) & (joined["n"] <= joined["le"])
    matches = hit.groupby(joined["index"]).sum().reindex(lp["index"]).fillna(0).values
    mask = matches == 0
    R.add("VC27", "laps", mask.sum(), len(lp), lp.loc[mask, ["session_key", "driver_number", "lap_number"]])
    mask = matches > 1
    R.add("VC71", "laps×stints", mask.sum(), len(lp), lp.loc[mask, ["session_key", "driver_number", "lap_number"]],
          note="경계 랩이 앞뒤 스틴트에 모두 속함")


def check_ranges(T, R, codes):
    for name, cols in NUMERIC.items():
        if name not in T:
            continue
        df = T[name]
        fail, sample = 0, []
        for col in cols:
            raw = df[col].astype(str)
            bad = (raw.str.strip() != "") & num(raw).isna()
            fail += int(bad.sum())
            if bad.any():
                sample.append(df.loc[bad, [col]].rename(columns={col: "value"}).assign(column=col))
        for col in GAP_COLUMNS.get(name, []):
            raw = df[col].astype(str)
            bad = (raw.str.strip() != "") & num(raw).isna() & ~raw.str.match(GAP_TEXT)
            fail += int(bad.sum())
            if bad.any():
                sample.append(df.loc[bad, [col]].rename(columns={col: "value"}).assign(column=col))
        R.add("VC30", name, fail, len(df), pd.concat(sample) if sample else None)

    by_table = {}
    for (name, col), (lo, hi, inclusive) in RANGES.items():
        if name not in T:
            continue
        v = num(T[name][col])
        bad = pd.Series(False, index=v.index)
        if lo is not None:
            bad |= (v < lo) if inclusive else (v <= lo)
        if hi is not None:
            bad |= v > hi
        by_table.setdefault(name, []).append((col, bad, v))
    for name, items in by_table.items():
        fail = sum(int(b.sum()) for _, b, _ in items)
        sample = [pd.DataFrame({"column": c, "value": v[b]}) for c, b, v in items if b.any()]
        R.add("VC31", name, fail, len(T[name]), pd.concat(sample) if sample else None)
    for name in ["intervals", "session_result"]:
        if name in T:
            for col in GAP_COLUMNS[name]:
                v = num(T[name][col])
                R.add("VC31", f"{name}.{col}", (v < 0).sum(), len(v), pd.DataFrame({"value": v[v < 0]}))

    group = lambda g: set(codes.loc[codes["code_group"] == g, "code"])
    domains = {("sessions", "session_type"): group("SESSION_TYPE"), ("sessions", "is_cancelled"): group("BOOLEAN"),
               ("laps", "is_pit_out_lap"): group("BOOLEAN"), ("weather", "rainfall"): {"0", "1"},
               ("stints", "compound"): group("COMPOUND"),
               ("session_result", "dnf"): group("BOOLEAN"), ("session_result", "dns"): group("BOOLEAN"),
               ("session_result", "dsq"): group("BOOLEAN"),
               ("race_control", "category"): group("RACE_CONTROL_CATEGORY"),
               ("race_control", "flag"): group("RACE_CONTROL_FLAG"),
               ("race_control", "scope"): group("RACE_CONTROL_SCOPE")}
    by_table = {}
    for (name, col), allowed in domains.items():
        if name not in T:
            continue
        s = T[name][col].astype(str)
        nullable = (name, col) in {("race_control", "flag"), ("race_control", "scope"), ("laps", "is_pit_out_lap"),
                                   ("weather", "rainfall")}
        bad = ~s.isin(allowed) & ~((s.str.strip() == "") & nullable)
        by_table.setdefault(name, []).append((col, bad, s))
    for name, items in by_table.items():
        fail = sum(int(b.sum()) for _, b, _ in items)
        sample = [pd.DataFrame({"column": c, "value": s[b]}).drop_duplicates() for c, b, s in items if b.any()]
        R.add("VC32", name, fail, len(T[name]), pd.concat(sample) if sample else None)

    for name, cols in DATES.items():
        if name not in T:
            continue
        df = T[name]
        fail, sample = 0, []
        for col in cols:
            raw = df[col].astype(str)
            bad = (raw.str.strip() != "") & ts(raw).isna()
            fail += int(bad.sum())
            if bad.any():
                sample.append(df.loc[bad, [col]].rename(columns={col: "value"}).assign(column=col))
        if name == "sessions":
            bad = ts(df["date_end"]) < ts(df["date_start"])
            fail += int(bad.sum())
            if bad.any():
                sample.append(df.loc[bad, ["session_key", "date_start", "date_end"]])
        R.add("VC33", name, fail, len(df), pd.concat(sample) if sample else None)

    if "session_result" in T:
        sr = T["session_result"]
        flags = (sr[["dnf", "dns", "dsq"]] == "True").sum(axis=1)
        mask = flags > 1
        R.add("VC34", "session_result", mask.sum(), len(sr), sr.loc[mask, ["session_key", "driver_number", "dnf", "dns", "dsq"]])


def check_consistency(T, R):
    drivers, sessions, laps, pit, stints = T["drivers"], T["sessions"], T["laps"], T["pit"], T["stints"]
    d = drivers[~blank(drivers["team_name"])]
    n = d.groupby(["session_key", "team_name"])["driver_number"].nunique()
    bad = n[n != 2].reset_index(name="drivers")
    R.add("VC40", "drivers", len(bad), len(n), bad)

    year = sessions.set_index("session_key")["year"]
    d = drivers.assign(year=drivers["session_key"].map(year))
    n = d.groupby(["year", "driver_number"])["full_name"].nunique()
    bad = n[n > 1].reset_index(name="names")
    if len(bad):
        names = d.groupby(["year", "driver_number"])["full_name"].agg(lambda s: "|".join(sorted(set(s))))
        bad["full_names"] = [names[(y, k)] for y, k in zip(bad["year"], bad["driver_number"])]
    R.add("VC41", "drivers", len(bad), len(n), bad)

    s1, s2, s3, lap = (num(laps[c]) for c in ["duration_sector_1", "duration_sector_2", "duration_sector_3", "lap_duration"])
    diff = (s1 + s2 + s3 - lap).abs()
    mask = diff > 0.5
    R.add("VC42", "laps", mask.sum(), int(diff.notna().sum()),
          laps.loc[mask, ["session_key", "driver_number", "lap_number"]].assign(diff=diff[mask].round(3)))

    lane, pitd = num(pit["lane_duration"]), num(pit["pit_duration"])
    q = pit["quarantine_flag"] == "Y" if "quarantine_flag" in pit else False
    mask = lane.notna() & pitd.notna() & (lane != pitd) & ~q
    R.add("VC43", "pit", mask.sum(), len(pit), pit.loc[mask, ["session_key", "driver_number", "lap_number", "lane_duration", "pit_duration"]],
          note=f"격리 행 {int(q.sum()) if hasattr(q, 'sum') else 0}건 제외")

    if "session_result" in T:
        sr = T["session_result"]
        max_lap = laps.assign(n=num(laps["lap_number"])).groupby(["session_key", "driver_number"])["n"].max()
        m = sr.merge(max_lap.rename("max_lap").reset_index(), on=["session_key", "driver_number"], how="left")
        diff = (num(m["number_of_laps"]) - m["max_lap"]).abs()
        mask = diff > 1
        R.add("VC44", "session_result", mask.sum(), int(diff.notna().sum()),
              m.loc[mask, ["session_key", "driver_number", "number_of_laps", "max_lap"]])

    st = stints.assign(n=num(stints["stint_number"]), ls=num(stints["lap_start"]), le=num(stints["lap_end"]))
    st = st.sort_values(["session_key", "driver_number", "n"])
    prev_end = st.groupby(["session_key", "driver_number"])["le"].shift()
    mask = st["ls"] < prev_end
    R.add("VC45", "stints", mask.sum(), len(st), st.loc[mask, ["session_key", "driver_number", "stint_number", "lap_start"]].assign(prev_lap_end=prev_end[mask]))


def race_points(T):
    """session_result에 race_base_points·team_at_race를 붙인다(Race 세션만)."""
    rules = pd.read_csv(DICT / "race_points_rules.csv", dtype={"year": str, "position": str})
    rule = rules.set_index(["year", "position"])["race_base_points"]
    sessions = T["sessions"].set_index("session_key")
    sr = T["session_result"]
    sr = sr[sr["session_key"].map(sessions["session_type"]) == "Race"].copy()
    sr["year"] = sr["session_key"].map(sessions["year"])
    keys = pd.MultiIndex.from_arrays([sr["year"], sr["position"].astype(str)])
    sr["race_base_points"] = pd.Series(rule.reindex(keys).values, index=sr.index).fillna(0)
    team = T["drivers"][["session_key", "driver_number", "team_name"]].rename(columns={"team_name": "team_at_race"})
    return sr, team


def check_points(T, R):
    if "session_result" not in T:
        return
    sr, team = race_points(T)
    src = num(sr["points"])
    diff = (src - sr["race_base_points"]).round(1)
    mask = diff.fillna(0) != 0
    breakdown = diff[mask].value_counts().sort_index()
    note = ", ".join(f"{k:+g}점 {v}건" for k, v in breakdown.items())
    R.add("VC50", "session_result", mask.sum(), len(sr),
          sr.loc[mask, ["year", "session_key", "driver_number", "position", "points", "race_base_points"]], note=note)

    merged = sr.merge(team, on=["session_key", "driver_number"], how="left")
    by_race = sr.groupby("session_key")["race_base_points"].sum()
    by_team = merged.groupby(["session_key", "team_at_race"], dropna=False)["race_base_points"].sum().groupby("session_key").sum()
    bad = (by_race - by_team.reindex(by_race.index).fillna(0)).abs() > 1e-9
    season_driver = sr.groupby("year")["race_base_points"].sum()
    season_team = merged.groupby(["year", "team_at_race"])["race_base_points"].sum().groupby("year").sum()
    season_bad = (season_driver - season_team.reindex(season_driver.index).fillna(0)).abs() > 1e-9
    R.add("VC51", "session_result×drivers", int(bad.sum()) + int(season_bad.sum()), len(by_race) + len(season_driver),
          pd.DataFrame({"driver_sum": by_race[bad], "team_sum": by_team.reindex(by_race.index)[bad]}).reset_index(),
          note=f"Race {len(by_race)}개·시즌 {len(season_driver)}개 대조, 행 수 {len(sr)}→{len(merged)}")
    mask = by_race != 101
    R.add("VC52", "session_result", mask.sum(), len(by_race), by_race[mask].rename("total").reset_index())
    mask = merged["team_at_race"].isna() | (merged["team_at_race"].astype(str).str.strip() == "")
    R.add("VC53", "session_result×drivers", mask.sum(), len(merged), merged.loc[mask, ["session_key", "driver_number", "race_base_points"]])


def check_reconcile(T, R, cleaned, reports):
    manifest_path = reports / "bronze_manifest.csv"
    manifest = pd.read_csv(manifest_path, encoding="utf-8-sig") if manifest_path.exists() else None
    for name in ORIGINAL:
        df = T[name]
        if manifest is not None:
            raw = manifest.loc[manifest["file"] == f"{name}.csv", "rows"]
            raw_rows = int(raw.iloc[0]) if len(raw) else -1
            R.add("VC60", name, abs(raw_rows - len(df)), raw_rows, note=f"원본 {raw_rows} / 정제 {len(df)}")
        if "quarantine_flag" in df:
            flagged = int((df["quarantine_flag"] == "Y").sum())
            qfile = cleaned / "quarantine" / f"{name}.csv"
            qrows = len(pd.read_csv(qfile, dtype=str, keep_default_na=False, encoding="utf-8-sig")) if qfile.exists() else None
            note = f"quarantine/{name}.csv {qrows}행" + ("" if qrows in (None, flagged) else " → 플래그와 불일치")
            R.add("VC61", name, flagged, len(df), df.loc[df["quarantine_flag"] == "Y", KEYS[name] + ["dq_codes"]], note=note)
        if "repair_status" in df:
            methods = df["repair_method"].astype(str)
            fail, sample = 0, []
            for col in business_columns(df):
                orig = "original_" + col
                if orig not in df:
                    continue
                changed = df[col].astype(str) != df[orig].astype(str)
                recorded = (df["repair_status"] == "REPAIRED") & methods.str.contains(f":{col}(?:;|$)", regex=True)
                bad = changed & ~recorded
                fail += int(bad.sum())
                if bad.any():
                    sample.append(df.loc[bad, KEYS[name]].assign(column=col))
            R.add("VC62", name, fail, len(df), pd.concat(sample) if sample else None)


def row_reconciliation(T, cleaned, reports):
    """파일별 행 수 대사.

    처리 결과를 서로 겹치지 않는 4개 구간으로 나눠 합계가 원본 행 수와 같은지 본다.
      원본 유지(UNCHANGED, 격리 아님) + 복구(REPAIRED, 격리 아님) + 격리(quarantine_flag=Y) + 제거(원본 - 정제 후)
    """
    manifest_path = reports / "bronze_manifest.csv"
    manifest = pd.read_csv(manifest_path, encoding="utf-8-sig") if manifest_path.exists() else None
    rows = []
    for name, df in T.items():
        dup = int(df.duplicated(KEYS[name]).sum()) if KEYS[name] else int(df.duplicated(business_columns(df)).sum())
        if name in ORIGINAL:
            raw = manifest.loc[manifest["file"] == f"{name}.csv", "rows"] if manifest is not None else pd.Series(dtype=int)
            raw_rows = int(raw.iloc[0]) if len(raw) else None
            q = df["quarantine_flag"] == "Y"
            unchanged = int(((df["repair_status"] == "UNCHANGED") & ~q).sum())
            repaired = int(((df["repair_status"] == "REPAIRED") & ~q).sum())
            quarantined = int(q.sum())
            qfile = cleaned / "quarantine" / f"{name}.csv"
            qfile_rows = len(pd.read_csv(qfile, dtype=str, keep_default_na=False, encoding="utf-8-sig")) if qfile.exists() else None
            group, note = "오염 정제 6종", "원본 행 수는 04_reports/quality/bronze_manifest.csv"
        else:
            raw_rows, unchanged, repaired, quarantined, qfile_rows = len(df), len(df), 0, 0, None
            group, note = "추가 5종", "정제 단계 없음(원본 그대로 검증)"
        removed = None if raw_rows is None else raw_rows - len(df)
        processed_sum = unchanged + repaired + quarantined + (removed or 0)
        balanced = raw_rows is not None and processed_sum == raw_rows and removed >= 0 \
            and unchanged + repaired + quarantined == len(df) and (qfile_rows is None or qfile_rows == quarantined)
        rows.append({"file": name, "group": group, "raw_rows": raw_rows, "unchanged_rows": unchanged, "repaired_rows": repaired,
                     "quarantined_rows": quarantined, "removed_rows": removed, "processed_sum": processed_sum,
                     "difference": None if raw_rows is None else processed_sum - raw_rows,
                     "cleaned_rows": len(df), "analysis_rows": unchanged + repaired, "quarantine_file_rows": qfile_rows,
                     "duplicate_key_rows": dup, "status": "PASS" if balanced else "FAIL", "note": note})
    out = pd.DataFrame(rows)
    for col in ["raw_rows", "removed_rows", "difference", "quarantine_file_rows"]:
        out[col] = out[col].astype("Int64")
    total = {"file": "합계(오염 정제 6종)", "group": "", "note": ""}
    six = out[out["group"] == "오염 정제 6종"]
    for col in ["raw_rows", "unchanged_rows", "repaired_rows", "quarantined_rows", "removed_rows", "processed_sum", "difference",
                "cleaned_rows", "analysis_rows", "quarantine_file_rows", "duplicate_key_rows"]:
        total[col] = six[col].sum()
    total["status"] = "PASS" if (six["status"] == "PASS").all() else "FAIL"
    return pd.concat([out, pd.DataFrame([total])], ignore_index=True)


RECON_LABELS = {"file": "파일", "group": "구분", "raw_rows": "① 원본 행", "unchanged_rows": "② 원본 유지", "repaired_rows": "③ 복구",
                "quarantined_rows": "④ 격리", "removed_rows": "⑤ 제거(중복 제거 등)", "processed_sum": "처리 합계 ②+③+④+⑤",
                "difference": "차이(합계-①)", "cleaned_rows": "정제 후 행", "analysis_rows": "분석 대상 ②+③",
                "quarantine_file_rows": "quarantine 파일 행", "duplicate_key_rows": "남은 키 중복 행", "status": "status", "note": "비고"}


def check_join_fanout(T, R):
    drivers = T["drivers"][["session_key", "driver_number", "team_name"]]
    for name in ["laps", "stints", "pit", "session_result"]:
        if name not in T:
            continue
        df = T[name]
        joined = df[["session_key", "driver_number"]].merge(drivers, on=["session_key", "driver_number"], how="left")
        R.add("VC70", f"{name}×drivers", len(joined) - len(df), len(df), note=f"{len(df)}→{len(joined)}")


# ---------- 실행 ----------
def run(cleaned, extra, out, samples=20, reports=None):
    cleaned, out = Path(cleaned), Path(out)
    reports = Path(reports) if reports else cleaned / "reports"
    repaired = cleaned / "repaired"
    T = {name: read_csv(repaired / f"{name}.csv", name) for name in ORIGINAL}
    if extra:
        T.update(load_extra(extra))
    catalogue = pd.read_csv(DICT / "validation_checks.csv").set_index("check_id")
    codes = pd.read_csv(DICT / "codes.csv", dtype=str, keep_default_na=False)
    R = Result(catalogue, samples)

    profile = check_missing(T, R)
    check_duplicates(T, R)
    check_references(T, R)
    check_ranges(T, R, codes)
    check_consistency(T, R)
    check_points(T, R)
    check_reconcile(T, R, cleaned, reports)
    check_join_fanout(T, R)

    out.mkdir(parents=True, exist_ok=True)
    result = R.frame()
    result.to_csv(out / "validation_result.csv", index=False, encoding="utf-8-sig")
    R.sample_frame().to_csv(out / "validation_samples.csv", index=False, encoding="utf-8-sig")
    profile.to_csv(out / "null_profile.csv", index=False, encoding="utf-8-sig")
    recon = row_reconciliation(T, cleaned, reports)
    recon.to_csv(out / "row_reconciliation.csv", index=False, encoding="utf-8-sig")
    write_report(result, T, out / "validation_report.md", recon)
    write_html(result, R.sample_frame(), profile, T, cleaned, extra, out / "validation_report.html", recon)
    return result


def write_report(result, T, path, recon):
    counts = result["status"].value_counts()
    fmt = lambda v: "-" if v is None or pd.isna(v) else f"{int(v):,}"
    lines = ["# 정제 후 데이터 검증 결과", "", "## 행 수 대사: 원본 = 원본 유지 + 복구 + 격리 + 제거", "",
             "| 파일 | ① 원본 | ② 원본 유지 | ③ 복구 | ④ 격리 | ⑤ 제거 | 처리 합계 | 차이 | 분석 대상 | 남은 키 중복 | 결과 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    lines += [f"| {r.file} | {fmt(r.raw_rows)} | {fmt(r.unchanged_rows)} | {fmt(r.repaired_rows)} | {fmt(r.quarantined_rows)} | "
              f"{fmt(r.removed_rows)} | {fmt(r.processed_sum)} | {fmt(r.difference)} | {fmt(r.analysis_rows)} | {fmt(r.duplicate_key_rows)} | {r.status} |"
              for r in recon.itertuples()]
    lines += ["", "| 상태 | 건수 |", "|---|---:|"]
    lines += [f"| {s} | {int(counts.get(s, 0))} |" for s in ["PASS", "FAIL", "WARN", "INFO"]]
    lines += ["", "## FAIL·WARN 항목", "", "| 검사 | 대상 | 등급 | 위반 | 전체 | 설명 | 비고 |", "|---|---|---|---:|---:|---|---|"]
    bad = result[result["status"].isin(["FAIL", "WARN"])]
    lines += [f"| {r.check_id} | {r.target} | {r.severity} | {r.fail_count:,} | {r.total_count:,} | {r.description} | {r.note} |"
              for r in bad.itertuples()]
    lines += ["", "## INFO 항목", "", "| 검사 | 대상 | 건수 | 설명 | 비고 |", "|---|---|---:|---|---|"]
    lines += [f"| {r.check_id} | {r.target} | {r.fail_count:,} | {r.description} | {r.note} |"
              for r in result[result["status"] == "INFO"].itertuples()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


STATUS_COLOR = {"PASS": "#1f7a4d", "FAIL": "#b42318", "WARN": "#b54708", "INFO": "#475467"}


def html_table(df):
    if not len(df):
        return "<p>없음</p>"
    out = df.copy()
    if "status" in out:
        out["status"] = [f"<span class='badge' style='background:{STATUS_COLOR.get(s, '#475467')}'>{s}</span>" for s in out["status"]]
    for col in out.columns:
        if col != "status":
            out[col] = out[col].map(lambda v: html.escape(f"{v:,}" if isinstance(v, int) else str(v)))
    return out.to_html(index=False, escape=False, border=0)


def write_html(result, samples, profile, T, cleaned, extra, path, recon):
    counts = result["status"].value_counts()
    cards = "".join(f"<div style='border-top:4px solid {STATUS_COLOR[s]}'>{s}<strong>{int(counts.get(s, 0))}</strong></div>"
                    for s in ["PASS", "FAIL", "WARN", "INFO"])
    recon_view = recon.astype(object).where(recon.notna(), "-").rename(columns=RECON_LABELS)
    totals = recon[recon["group"] == "오염 정제 6종"][["raw_rows", "unchanged_rows", "repaired_rows", "quarantined_rows", "removed_rows", "processed_sum"]].sum()
    cols = ["check_id", "korean_category", "check_name", "target", "severity", "fail_count", "total_count", "status", "description", "note"]
    by_category = result.groupby(["category", "korean_category"]).agg(
        checks=("check_id", "size"), PASS=("status", lambda s: int((s == "PASS").sum())), FAIL=("status", lambda s: int((s == "FAIL").sum())),
        WARN=("status", lambda s: int((s == "WARN").sum())), INFO=("status", lambda s: int((s == "INFO").sum()))).reset_index()
    order = {"FAIL": 0, "WARN": 1, "INFO": 2, "PASS": 3}
    issues = result[result["status"].isin(["FAIL", "WARN"])]
    sample_html = []
    for (check, target), group in samples.groupby(["check_id", "target"], sort=True):
        meta = result[(result["check_id"] == check) & (result["target"] == target)]
        if len(meta) and meta["status"].iat[0] == "PASS":
            continue
        title = f"{check} {target}" + (f" — {meta['description'].iat[0]}" if len(meta) else "")
        sample_html.append(f"<h3>{html.escape(title)}</h3>" + html_table(group[["detail"]]))
    blanks = profile[profile["blank"] > 0].sort_values(["table", "blank_rate"], ascending=[True, False])
    style = ("body{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px;color:#17212b}table{border-collapse:collapse;width:100%;margin:12px 0 28px;font-size:12.5px}"
             "th,td{border:1px solid #d5dee7;padding:6px;text-align:left;vertical-align:top}th{background:#eaf1f6}"
             ".cards{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.cards div{background:#f1f5f8;padding:14px 18px;border-radius:8px;min-width:90px}"
             ".cards strong{display:block;font-size:24px;margin-top:6px}h2{margin-top:36px}.meta{color:#56636f;font-size:13px}"
             ".badge{color:#fff;border-radius:4px;padding:2px 6px;font-size:11.5px;font-weight:bold}")
    body = (f"<h1>F1 정제 후 데이터 검증 리포트</h1>"
            f"<p class='meta'>정제 결과 {html.escape(str(cleaned))} · 추가 데이터 {html.escape(str(extra) if extra else '없음')} · "
            f"검사 정의 data/02_reference/standard_dictionary/validation_checks.csv · 생성 {pd.Timestamp.now():%Y-%m-%d %H:%M}</p>"
            f"<div class='cards'>{cards}</div>"
            "<p class='meta'>FAIL = ERROR 등급 위반, WARN = WARNING 등급 위반(검토), INFO = 참고 건수(통과/실패 판정 없음)</p>"
            "<h2>1. 행 수 대사</h2><p class='meta'>처리 결과를 겹치지 않는 4개 구간으로 나눠 <b>② 원본 유지 + ③ 복구 + ④ 격리 + ⑤ 제거 = ① 원본</b>인지 확인한다. "
            f"오염 정제 6종 합계: {int(totals['unchanged_rows']):,} + {int(totals['repaired_rows']):,} + {int(totals['quarantined_rows']):,} + {int(totals['removed_rows']):,} "
            f"= {int(totals['processed_sum']):,} (원본 {int(totals['raw_rows']):,}). 복구 행은 값이 하나 이상 바뀐 행이고, 격리 행은 복구 여부와 관계없이 ④로만 센다. "
            "파이프라인은 행을 삭제하지 않고 중복 키(DQ026)는 격리하므로 ⑤ 제거는 0이 정상이다. '남은 키 중복 행'은 정제 후 자연키가 겹치는 행 수(VC10)다.</p>" + html_table(recon_view) +
            "<h2>2. 분류별 요약</h2>" + html_table(by_category) +
            "<h2>3. FAIL·WARN 항목</h2>" + html_table(issues[cols]) +
            "<h2>4. 전체 검사 결과</h2>" + html_table(result.sort_values("status", key=lambda s: s.map(order), kind="stable")[cols]) +
            "<h2>5. 위반 샘플</h2><p class='meta'>검사·대상별 최대 샘플 행 (전체는 validation_samples.csv)</p>" + "".join(sample_html) +
            "<h2>6. 결측 프로파일</h2><p class='meta'>공백이 있는 컬럼만 표시 (전체는 null_profile.csv)</p>" + html_table(blanks))
    path.write_text(f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>F1 정제 후 검증 리포트</title>"
                    f"<style>{style}</style></head><body>{body}</body></html>", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cleaned", default=str(ROOT / "data" / "03_cleaned"), help="정제 결과 폴더(repaired/, quarantine/)")
    parser.add_argument("--reports", default=str(ROOT / "data" / "04_reports" / "quality"), help="정제 리포트 폴더(bronze_manifest.csv)")
    parser.add_argument("--extra", default=None, help="추가 데이터 5종 폴더 또는 zip (기본: data/01_raw/f1_extra_data, 없으면 zip)")
    parser.add_argument("--out", default=None, help="검증 결과 폴더 (기본: data/04_reports/validation)")
    parser.add_argument("--samples", type=int, default=20, help="검사·대상별 위반 샘플 행 수")
    args = parser.parse_args()
    extra = args.extra
    if extra is None:
        folder, archive = ROOT / "data" / "01_raw" / "f1_extra_data", ROOT / "data" / "01_raw" / "f1_extra_data.zip"
        extra = folder if (folder / "session_result.csv").exists() else archive if archive.exists() else None
    out = Path(args.out) if args.out else ROOT / "data" / "04_reports" / "validation"
    result = run(args.cleaned, extra, out, args.samples, args.reports)
    shown = result[result["status"] != "PASS"][["check_id", "target", "status", "fail_count", "total_count", "note"]]
    print(shown.to_string(index=False))
    print(result["status"].value_counts().to_string())
    print(f"결과: {out}")
    sys.exit(1 if (result["status"] == "FAIL").any() else 0)


if __name__ == "__main__":
    main()
