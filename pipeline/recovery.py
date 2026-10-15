"""F1 오염 데이터 검증·복구 파이프라인.

입력(폴더 또는 zip)의 CSV 6종을 문자열 그대로 읽고, 진단코드(DQ001~)별로
결함을 탐지·복구·격리한 뒤 복구 CSV와 품질 리포트를 만든다.
원본 파일은 수정하지 않는다.

실행(저장소 루트): python -m pipeline.recovery [--config pipeline/config.json]
"""
from __future__ import annotations

import argparse, hashlib, html, io, json, os, re, zipfile
from pathlib import Path

import pandas as pd

PIPELINE_VERSION = "0.2.0"
FILES = ["sessions.csv", "drivers.csv", "laps.csv", "stints.csv", "weather.csv", "pit.csv"]
SCHEMA = {
    "drivers.csv": "broadcast_name country_code driver_number first_name full_name headshot_url last_name meeting_key name_acronym session_key team_colour team_name".split(),
    "laps.csv": "date_start driver_number duration_sector_1 duration_sector_2 duration_sector_3 i1_speed i2_speed is_pit_out_lap lap_duration lap_number meeting_key segments_sector_1 segments_sector_2 segments_sector_3 session_key st_speed".split(),
    "pit.csv": "date driver_number lane_duration lap_number meeting_key pit_duration session_key stop_duration".split(),
    "sessions.csv": "circuit_key circuit_short_name country_code country_key country_name date_end date_start gmt_offset is_cancelled location meeting_key session_key session_name session_type year".split(),
    "stints.csv": "compound driver_number lap_end lap_start meeting_key session_key stint_number tyre_age_at_start".split(),
    "weather.csv": "air_temperature date humidity meeting_key pressure rainfall session_key track_temperature wind_direction wind_speed".split(),
}
KEYS = {
    "sessions.csv": ["session_key"],
    "drivers.csv": ["session_key", "driver_number"],
    "laps.csv": ["session_key", "driver_number", "lap_number"],
    "stints.csv": ["session_key", "driver_number", "stint_number"],
    "weather.csv": ["session_key", "date"],
    "pit.csv": ["session_key", "driver_number", "lap_number"],
}
NUMERIC = {
    "sessions.csv": ["circuit_key", "country_key", "meeting_key", "session_key", "year"],
    "drivers.csv": ["driver_number", "meeting_key", "session_key"],
    "laps.csv": ["driver_number", "duration_sector_1", "duration_sector_2", "duration_sector_3", "i1_speed", "i2_speed", "st_speed", "lap_duration", "lap_number", "meeting_key", "session_key"],
    "pit.csv": ["driver_number", "lane_duration", "lap_number", "meeting_key", "pit_duration", "session_key", "stop_duration"],
    "stints.csv": ["driver_number", "lap_end", "lap_start", "meeting_key", "session_key", "stint_number", "tyre_age_at_start"],
    "weather.csv": ["air_temperature", "humidity", "meeting_key", "pressure", "session_key", "track_temperature", "wind_direction", "wind_speed"],
}
DATES = {"sessions.csv": ["date_start", "date_end"], "laps.csv": ["date_start"], "pit.csv": ["date"], "weather.csv": ["date"]}
DOMAINS = {
    ("sessions.csv", "is_cancelled"): {"True", "False"},
    ("laps.csv", "is_pit_out_lap"): {"True", "False"},
    ("weather.csv", "rainfall"): {"0", "1"},
    ("stints.csv", "compound"): {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", "UNKNOWN"},
}
IDENTITY = ["full_name", "first_name", "last_name", "broadcast_name", "name_acronym"]
CHILD_FILES = ["drivers.csv", "laps.csv", "stints.csv", "weather.csv", "pit.csv"]
CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
ROOT = Path(__file__).resolve().parents[1]
DICT_PATH = ROOT / "data" / "02_reference" / "standard_dictionary" / "diagnostic_codes.csv"


def blank(series):
    return series.astype("string").fillna("").str.strip().isin(["", "NULL", "None", "nan"])


def num(series):
    return pd.to_numeric(series.where(~blank(series)), errors="coerce")


def ts(series):
    return pd.to_datetime(series.where(~blank(series)), errors="coerce", utc=True, format="mixed")


def fmt_num(value, digits=3):
    if digits == 0:
        return str(int(round(value)))
    text = f"{value:.{digits}f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def is_blank(value):
    return str(value).strip() in ("", "NULL", "None", "nan")


def fmt_ts(value):
    return value.isoformat(sep=" ", timespec="microseconds")


# ---------------------------------------------------------------- 입력·Bronze

def load_source(path: Path):
    """폴더(all_years 포함 가능) 또는 zip에서 CSV 6종을 bytes로 읽는다."""
    raw, checksums, spec = {}, {}, ""
    if path.is_dir():
        root = path / "all_years" if (path / "all_years").is_dir() else path
        for name in FILES:
            raw[name] = (root / name).read_bytes()
        sums = next((p for p in [path / "SHA256SUMS.txt", root / "SHA256SUMS.txt"] if p.exists()), None)
        if sums:
            checksums = parse_sums(sums.read_text(encoding="utf-8"))
        spec_file = next(iter(sorted(path.glob("*데이터_명세서.md"))), None)
        if spec_file:
            spec = spec_file.read_text(encoding="utf-8")
    else:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            marker = next((n for n in names if n.endswith("all_years/sessions.csv")), None)
            if marker is None:
                raise ValueError("압축파일에서 all_years/sessions.csv를 찾지 못했습니다.")
            root = marker[: -len("sessions.csv")]
            for name in FILES:
                raw[name] = archive.read(root + name)
            sums = next((n for n in names if n.endswith("SHA256SUMS.txt")), None)
            if sums:
                checksums = parse_sums(archive.read(sums).decode("utf-8"))
            spec_name = next((n for n in names if n.endswith("데이터_명세서.md")), None)
            if spec_name:
                spec = archive.read(spec_name).decode("utf-8")
    return raw, checksums, spec


def parse_spec(text):
    """명세서 1장 표에서 파일별 배포 행 수·컬럼 수, 3장 컬럼 사전에서 컬럼 순서를 읽는다."""
    counts = {m[0]: (int(m[1].replace(",", "")), int(m[2])) for m in re.findall(r"\| (\w+\.csv) \| ([\d,]+) \| (\d+) \|", text)}
    columns, current = {}, None
    for line in text.splitlines():
        head = re.match(r"### (\w+\.csv)", line)
        if head:
            current = head.group(1)
            columns[current] = []
        elif current and line.startswith("| ") and not line.startswith("| 컬럼"):
            columns[current].append(line.strip("|").split("|")[0].strip())
    return counts, columns


def parse_sums(text):
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[Path(parts[1]).name] = parts[0]
    return out


MANIFEST_COLUMNS = [
    ("file", "파일명"),
    ("rows", "실제 데이터 행 수 (헤더 제외)"),
    ("columns", "실제 컬럼 수"),
    ("spec_rows", "데이터 명세서(00. 데이터_명세서.md)에 적힌 행 수"),
    ("spec_columns", "데이터 명세서에 적힌 컬럼 수"),
    ("spec_row_count", "행·컬럼 수가 명세서와 같으면 MATCH, 다르면 MISMATCH, 명세서가 없으면 NO_SPEC"),
    ("schema", "명세서 컬럼 이름이 빠짐없이 있고 추가 컬럼이 없으면 OK"),
    ("column_order", "컬럼 순서까지 명세서와 같으면 OK, 순서만 다르면 DIFFERENT"),
    ("checksum", "파일이 배포본 그대로인지: sha256 = sha256_expected 이면 MATCH, 기준값이 없으면 NO_REFERENCE, 다르면 MISMATCH(파일 변경·손상)"),
    ("encoding", "판별한 문자 인코딩 (utf-8, BOM이 있으면 utf-8-sig)"),
    ("bytes", "파일 크기(바이트)"),
    ("sha256", "이번에 읽은 파일 바이트의 SHA-256 해시 (원본 보존 증빙, 참고용)"),
    ("sha256_expected", "배포본 SHA256SUMS.txt에 적힌 기준 해시 (참고용)"),
]


def bronze(raw, checksums, spec, ledger):
    data, manifest = {}, []
    spec_counts, spec_columns = parse_spec(spec) if spec else ({}, {})
    for name in FILES:
        content = raw[name]
        encoding = "utf-8-sig" if content.startswith(b"\xef\xbb\xbf") else "utf-8"
        df = pd.read_csv(io.BytesIO(content), dtype="string", keep_default_na=False, encoding=encoding)
        digest = hashlib.sha256(content).hexdigest()
        expected = checksums.get(name, "")
        expected_columns = spec_columns.get(name) or SCHEMA[name]
        missing = sorted(set(expected_columns) - set(df.columns))
        extra = sorted(set(df.columns) - set(expected_columns))
        spec_rows, spec_cols = spec_counts.get(name, (None, None))
        # 판정 컬럼을 앞에, 참고용 해시는 맨 뒤에 둔다 (컬럼 설명은 MANIFEST_COLUMNS)
        manifest.append({"file": name, "rows": len(df), "columns": len(df.columns),
                         "spec_rows": "" if spec_rows is None else spec_rows, "spec_columns": "" if spec_cols is None else spec_cols,
                         "spec_row_count": "NO_SPEC" if spec_rows is None else ("MATCH" if spec_rows == len(df) and spec_cols == len(df.columns) else "MISMATCH"),
                         "schema": "OK" if not missing and not extra else "MISMATCH",
                         "column_order": "OK" if list(df.columns) == list(expected_columns) else "DIFFERENT",
                         "checksum": "MATCH" if expected == digest else ("NO_REFERENCE" if not expected else "MISMATCH"),
                         "encoding": encoding, "bytes": len(content), "sha256": digest, "sha256_expected": expected})
        if spec_rows is not None and (spec_rows != len(df) or spec_cols != len(df.columns)):
            ledger.issue(name, "DQ013", None, "", "", observed=f"행 {len(df)}·열 {len(df.columns)} / 명세서 행 {spec_rows}·열 {spec_cols}", action="REVIEW")
        if missing or extra:
            ledger.issue(name, "DQ013", None, "", "", observed="누락: " + ",".join(missing) + " / 추가: " + ",".join(extra), action="REVIEW")
        df.insert(0, "source_row", [str(i + 2) for i in range(len(df))])
        data[name] = df
    return data, pd.DataFrame(manifest)


# ---------------------------------------------------------------- 이력 관리

class Ledger:
    """진단 이슈와 복구 이력을 함께 기록한다. fix=False면 탐지만 한다."""

    def __init__(self, catalogue, fix=True):
        self.catalogue = catalogue
        self.fix = fix
        self.issues = []
        self.repairs = []
        self.data = None

    def row_key(self, name, idx):
        if idx is None:
            return ""
        df = self.data[name]
        return "|".join(str(df.at[idx, k]) for k in KEYS[name])

    def issue(self, name, code, idx, field, expected="", observed=None, evidence="", action="REVIEW", status="OPEN", confidence=""):
        meta = self.catalogue[code]
        df = self.data[name] if self.data and idx is not None else None
        if observed is None:
            observed = "" if df is None or not field else str(df.at[idx, field])
        record = {
            "issue_id": f"{code}:{name}:{self.row_key(name, idx)}:{field}",
            "diagnostic_code": code, "diagnostic_name": meta["diagnostic_name"], "korean_name": meta["korean_name"],
            "error_type": meta["error_type"], "error_type_korean": meta["error_type_korean"], "severity": meta["severity"],
            "file": name, "source_row": "" if df is None else df.at[idx, "source_row"],
            "row_key": self.row_key(name, idx),
            "session_key": "" if df is None or "session_key" not in df else df.at[idx, "session_key"],
            "driver_number": "" if df is None or "driver_number" not in df else df.at[idx, "driver_number"],
            "field": field, "observed_value": observed, "expected_value": expected, "evidence": evidence,
            "action": action, "status": status, "confidence": confidence, "_idx": idx,
        }
        self.issues.append(record)
        return record

    def repair(self, name, code, idx, field, new_value, method, confidence, evidence):
        """결함을 기록하고 fix 모드면 값을 바꾼다."""
        df = self.data[name]
        old = str(df.at[idx, field])
        if not self.fix:
            return self.issue(name, code, idx, field, expected=new_value, evidence=evidence, action="AUTO_FIX")
        record = self.issue(name, code, idx, field, expected=new_value, evidence=evidence, action="AUTO_FIX", status="REPAIRED", confidence=confidence)
        df.at[idx, field] = new_value
        self.repairs.append({"issue_id": record["issue_id"], "diagnostic_code": code, "error_type": record["error_type"],
                             "file": name, "source_row": record["source_row"], "row_key": record["row_key"],
                             "session_key": record["session_key"], "driver_number": record["driver_number"],
                             "field": field, "old_value": old, "new_value": new_value, "method": method,
                             "confidence": confidence, "reason": evidence})
        return record


def load_catalogue(path=DICT_PATH):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return {row.diagnostic_code: row._asdict() for row in df.itertuples(index=False)}


# ---------------------------------------------------------------- 검사 규칙

def check_format(data, lg):
    for name, df in data.items():
        for field in NUMERIC[name]:
            bad = ~blank(df[field]) & num(df[field]).isna()
            for idx in df.index[bad]:
                lg.issue(name, "DQ014", idx, field, evidence="숫자로 해석할 수 없음", action="QUARANTINE")
        for field in DATES.get(name, []):
            bad = ~blank(df[field]) & ts(df[field]).isna()
            for idx in df.index[bad]:
                lg.issue(name, "DQ014", idx, field, evidence="일시로 해석할 수 없음", action="QUARANTINE")
    for (name, field), allowed in DOMAINS.items():
        df = data[name]
        for idx in df.index[~blank(df[field]) & ~df[field].isin(allowed)]:
            lg.issue(name, "DQ014", idx, field, evidence="허용값: " + "|".join(sorted(allowed)), action="QUARANTINE")


def check_keys(data, lg):
    sessions = set(data["sessions.csv"]["session_key"])
    entrants = set(zip(data["drivers.csv"]["session_key"], data["drivers.csv"]["driver_number"]))
    for name, df in data.items():
        for idx in df.index[df.duplicated(KEYS[name], keep=False)]:
            lg.issue(name, "DQ026", idx, KEYS[name][-1], evidence="자연키 " + "+".join(KEYS[name]) + " 중복", action="QUARANTINE")
        if name != "sessions.csv":
            for idx in df.index[~df["session_key"].isin(sessions)]:
                lg.issue(name, "DQ027", idx, "session_key", evidence="sessions.csv에 없는 session_key", action="QUARANTINE")
        if name in ("laps.csv", "stints.csv", "pit.csv"):
            pairs = pd.Series(list(zip(df["session_key"], df["driver_number"])), index=df.index)
            for idx in df.index[~pairs.isin(entrants)]:
                lg.issue(name, "DQ027", idx, "driver_number", evidence="drivers.csv에 없는 session_key+driver_number", action="QUARANTINE")


def check_meeting_key(data, lg):
    """같은 session_key의 meeting_key를 하위 5개 파일 합의값과 비교한다."""
    votes = pd.concat([data[n][["session_key", "meeting_key"]].assign(file=n) for n in CHILD_FILES])
    per_file = votes.groupby(["session_key", "file"])["meeting_key"].agg(lambda s: s.mode().iat[0])
    consensus = {}
    for sk, group in per_file.groupby(level=0):
        values = set(group)
        if len(values) == 1:
            consensus[sk] = values.pop()
    sessions = data["sessions.csv"]
    for idx in sessions.index:
        sk, mk = sessions.at[idx, "session_key"], sessions.at[idx, "meeting_key"]
        if sk in consensus and consensus[sk] != mk:
            lg.repair("sessions.csv", "DQ015", idx, "meeting_key", consensus[sk], "child_file_consensus", "HIGH",
                      f"하위 5개 파일이 모두 meeting_key={consensus[sk]}로 일치")
    truth = sessions.set_index("session_key")["meeting_key"]
    for name in CHILD_FILES:
        df = data[name]
        expected = df["session_key"].map(truth)
        for idx in df.index[expected.notna() & (df["meeting_key"] != expected)]:
            lg.repair(name, "DQ015", idx, "meeting_key", expected[idx], "session_key_join", "HIGH", "sessions.csv의 같은 session_key 값")


def season_frame(data):
    drivers = data["drivers.csv"]
    sessions = data["sessions.csv"].set_index("session_key")
    return drivers.assign(_year=drivers["session_key"].map(sessions["year"]),
                          _start=ts(drivers["session_key"].map(sessions["date_start"])))


def check_identity(data, lg):
    """시즌 내 차량번호별 신원 합의값과 다른 행이 같은 세션에서 서로 바뀌어 있으면 교환 복구."""
    df = season_frame(data)
    ident = df[IDENTITY].astype(str).agg("|".join, axis=1)
    consensus = {}
    for key, group in ident.groupby([df["_year"], df["driver_number"]]):
        top = group.value_counts()
        if len(group) >= 3 and top.iat[0] / len(group) >= 0.8:
            consensus[key] = top.index[0]
    for sk, group in df.groupby("session_key"):
        wrong = [i for i in group.index if consensus.get((df.at[i, "_year"], df.at[i, "driver_number"]), ident[i]) != ident[i]]
        for i in wrong:
            want = consensus[(df.at[i, "_year"], df.at[i, "driver_number"])]
            partner = [j for j in wrong if j != i and ident[j] == want]
            if not partner:
                lg.issue("drivers.csv", "DQ016", i, "full_name", expected=want.split("|")[0], evidence="시즌 차량번호 합의 신원과 다름(교환 상대 없음)", action="QUARANTINE")
                continue
            for field, value in zip(IDENTITY, want.split("|")):
                if data["drivers.csv"].at[i, field] != value:
                    lg.repair("drivers.csv", "DQ016", i, field, value, "season_number_consensus_swap", "HIGH",
                              f"{df.at[i, '_year']} 시즌 #{df.at[i, 'driver_number']}의 신원 합의값, 같은 세션 #{df.at[partner[0], 'driver_number']} 행과 교환됨")


def check_team(data, lg):
    """앞뒤 세션 소속팀이 같고 팀 색상도 그 팀과 일치하는데 이 세션만 다른 경우 복구."""
    df = season_frame(data)
    drivers = data["drivers.csv"]
    colour = drivers["team_colour"].str.upper()
    for _, group in df.sort_values("_start").groupby(["_year", "full_name"]):
        idx = list(group.index)
        for pos in range(1, len(idx) - 1):
            i, before, after = idx[pos], drivers.at[idx[pos - 1], "team_name"], drivers.at[idx[pos + 1], "team_name"]
            current = drivers.at[i, "team_name"]
            if before == after and current != before:
                own_colour = colour[i]
                if own_colour == colour[idx[pos - 1]]:
                    lg.repair("drivers.csv", "DQ017", i, "team_name", before, "adjacent_session_team", "HIGH",
                              f"앞뒤 세션 소속 {before}, 팀 색상 {own_colour}도 {before}와 일치")
                else:
                    lg.issue("drivers.csv", "DQ017", i, "team_name", expected=before, evidence="앞뒤 세션과 소속팀이 다름(색상 근거 없음)", action="REVIEW")


def check_country(data, lg):
    drivers = data["drivers.csv"]
    filled = drivers[~blank(drivers["country_code"])]
    for idx in drivers.index[blank(drivers["country_code"])]:
        counts = filled.loc[filled["full_name"] == drivers.at[idx, "full_name"], "country_code"].value_counts()
        if len(counts) == 1:
            lg.repair("drivers.csv", "DQ001", idx, "country_code", counts.index[0], "driver_consensus", "HIGH",
                      f"같은 드라이버의 다른 {counts.iat[0]}개 세션 값이 모두 {counts.index[0]}")
        elif len(counts) > 1 and counts.iat[0] / counts.sum() >= 0.9:
            lg.repair("drivers.csv", "DQ001", idx, "country_code", counts.index[0], "driver_consensus", "MEDIUM",
                      f"같은 드라이버 세션 {counts.sum()}개 중 {counts.iat[0]}개가 {counts.index[0]}")
        else:
            lg.issue("drivers.csv", "DQ001", idx, "country_code", evidence="같은 드라이버의 다른 세션 값 없음", action="REVIEW")


def check_headshot(data, lg):
    df = season_frame(data)
    filled = df[~blank(df["headshot_url"])]
    for idx in df.index[blank(df["headshot_url"])]:
        urls = filled.loc[(filled["full_name"] == df.at[idx, "full_name"]) & (filled["_year"] == df.at[idx, "_year"]), "headshot_url"].unique()
        if len(urls) == 1:
            lg.repair("drivers.csv", "DQ024", idx, "headshot_url", urls[0], "driver_season_unique", "MEDIUM", "같은 드라이버·시즌의 유일한 주소")
        else:
            lg.issue("drivers.csv", "DQ024", idx, "headshot_url", evidence="같은 시즌 주소가 없거나 여러 개", action="ACCEPT", status="ACCEPTED")


def lap_frame(laps):
    frame = pd.DataFrame({"t": ts(laps["date_start"]), "ld": num(laps["lap_duration"]), "ln": num(laps["lap_number"]),
                          "sk": laps["session_key"], "dn": laps["driver_number"]}, index=laps.index)
    return frame.sort_values(["sk", "dn", "ln"])


def check_lap_dates(data, lg):
    """앞 랩 시작+소요시간과 맞지 않는 시작 시각을 찾아 인접 교환 또는 앞뒤 근거로 복구."""
    laps = data["laps.csv"]
    frame = lap_frame(laps)
    one = pd.Timedelta(seconds=1)
    for _, group in frame.groupby(["sk", "dn"], sort=False):
        idx = list(group.index)
        t = {i: frame.at[i, "t"] for i in idx}
        for pos in range(1, len(idx)):
            i, prev = idx[pos], idx[pos - 1]
            if frame.at[i, "ln"] != frame.at[prev, "ln"] + 1 or pd.isna(t[i]) or pd.isna(t[prev]) or pd.isna(frame.at[prev, "ld"]):
                continue
            expected = t[prev] + pd.Timedelta(seconds=float(frame.at[prev, "ld"]))
            if abs(t[i] - expected) <= one:
                continue
            nxt = idx[pos + 1] if pos + 1 < len(idx) else None
            if nxt is not None and pd.notna(t[nxt]) and abs(t[nxt] - expected) <= pd.Timedelta(seconds=0.5) and pd.notna(frame.at[i, "ld"]) \
                    and abs(t[i] - (t[nxt] + pd.Timedelta(seconds=float(frame.at[i, "ld"])))) <= pd.Timedelta(seconds=0.5):
                old_i, old_n = laps.at[i, "date_start"], laps.at[nxt, "date_start"]
                lg.repair("laps.csv", "DQ019", i, "date_start", old_n, "adjacent_swap", "HIGH", "다음 랩과 시작 시각이 서로 바뀜(교환 시 앞뒤 랩타임과 일치)")
                lg.repair("laps.csv", "DQ019", nxt, "date_start", old_i, "adjacent_swap", "HIGH", "이전 랩과 시작 시각이 서로 바뀜(교환 시 앞뒤 랩타임과 일치)")
                if lg.fix:
                    t[i], t[nxt] = t[nxt], t[i]
                continue
            if nxt is not None and pd.notna(t[nxt]) and pd.notna(frame.at[i, "ld"]):
                from_next = t[nxt] - pd.Timedelta(seconds=float(frame.at[i, "ld"]))
                if abs(from_next - expected) <= pd.Timedelta(seconds=0.5):
                    lg.repair("laps.csv", "DQ019", i, "date_start", fmt_ts(expected), "prev_lap_plus_duration", "MEDIUM",
                              "앞 랩 시작+소요시간과 다음 랩 시작-소요시간이 0.5초 이내로 일치")
                    if lg.fix:
                        t[i] = expected
                    continue
            lg.issue("laps.csv", "DQ019", i, "date_start", expected=fmt_ts(expected),
                     evidence=f"앞 랩 기준 예상과 {(t[i] - expected).total_seconds():+.3f}초 차이(적기·세이프티카·체커 이후 등 원천 특성 가능, 근거 부족으로 미수정)", action="REVIEW")


def check_lap_missing(data, lg):
    laps = data["laps.csv"]
    frame = lap_frame(laps)
    nxt_t = frame.groupby(["sk", "dn"])["t"].shift(-1)
    nxt_ln = frame.groupby(["sk", "dn"])["ln"].shift(-1)
    for idx in frame.index[blank(laps.loc[frame.index, "date_start"])]:
        if frame.at[idx, "ln"] == 1:
            lg.issue("laps.csv", "DQ002", idx, "date_start", evidence="1랩 시작 시각은 원천에서 비어 있는 경우가 있음", action="ACCEPT", status="ACCEPTED")
        elif pd.notna(nxt_t[idx]) and nxt_ln[idx] == frame.at[idx, "ln"] + 1 and pd.notna(frame.at[idx, "ld"]):
            value = nxt_t[idx] - pd.Timedelta(seconds=float(frame.at[idx, "ld"]))
            lg.repair("laps.csv", "DQ002", idx, "date_start", fmt_ts(value), "next_lap_minus_duration", "MEDIUM", "다음 랩 시작 시각 - 현재 랩 소요시간")
        else:
            lg.issue("laps.csv", "DQ002", idx, "date_start", evidence="다음 랩 시각 또는 랩 소요시간 없음", action="REVIEW")
    for idx in frame.index[blank(laps.loc[frame.index, "lap_duration"])]:
        if frame.at[idx, "ln"] == 1:
            lg.issue("laps.csv", "DQ018", idx, "lap_duration", evidence="1랩은 원천에서 랩타임을 제공하지 않는 경우가 있음", action="ACCEPT", status="ACCEPTED")
        elif pd.notna(nxt_t[idx]) and pd.notna(frame.at[idx, "t"]) and nxt_ln[idx] == frame.at[idx, "ln"] + 1:
            value = (nxt_t[idx] - frame.at[idx, "t"]).total_seconds()
            lg.repair("laps.csv", "DQ018", idx, "lap_duration", fmt_num(value), "next_lap_start_gap", "MEDIUM", "다음 랩 시작 - 현재 랩 시작 (원본 랩의 99.7%가 0.5초 이내 일치)")
        else:
            reason = "드라이버의 마지막 랩(완주·리타이어)이라 다음 랩 없음" if pd.isna(nxt_ln[idx]) else "다음 랩 시작 시각 없음"
            lg.issue("laps.csv", "DQ018", idx, "lap_duration", evidence=reason, action="REVIEW")


def check_sectors(data, lg):
    laps = data["laps.csv"]
    cols = ["duration_sector_1", "duration_sector_2", "duration_sector_3"]
    values = pd.DataFrame({c: num(laps[c]) for c in cols})
    lap = num(laps["lap_duration"].where(~laps.index.isin([r["_idx"] for r in lg.issues if r["diagnostic_code"] == "DQ018" and r["status"] == "REPAIRED"])))
    missing = values.isna()
    for c in cols:
        others = [o for o in cols if o != c]
        for idx in laps.index[missing[c] & blank(laps[c])]:
            if missing.loc[idx].sum() == 1 and pd.notna(lap[idx]):
                value = lap[idx] - values.loc[idx, others].sum()
                if value > 0:
                    lg.repair("laps.csv", "DQ004", idx, c, fmt_num(value), "lap_minus_other_sectors", "HIGH", "랩타임 - 나머지 두 섹터 (원본 랩의 99%에서 섹터 합 = 랩타임)")
                    continue
            lg.issue("laps.csv", "DQ004", idx, c, evidence="결측 섹터가 2개 이상이거나 원본 랩타임 없음", action="REVIEW")
    values = pd.DataFrame({c: num(laps[c]) for c in cols})
    diff = values.sum(axis=1, min_count=3) - num(laps["lap_duration"])
    for idx in laps.index[diff.abs() > 0.5]:
        lg.issue("laps.csv", "DQ020", idx, "lap_duration", expected=fmt_num(values.loc[idx].sum()), evidence=f"섹터 합 - 랩타임 = {diff[idx]:+.3f}초", action="REVIEW")


def check_lap_values(data, lg):
    laps = data["laps.csv"]
    for field in ["i1_speed", "i2_speed", "st_speed"]:
        for idx in laps.index[blank(laps[field])]:
            lg.issue("laps.csv", "DQ003", idx, field, evidence="원천 결측 가능, 중앙값 대체하지 않음", action="ACCEPT", status="ACCEPTED")
    for field in ["segments_sector_1", "segments_sector_2", "segments_sector_3"]:
        for idx in laps.index[blank(laps[field])]:
            lg.issue("laps.csv", "DQ005", idx, field, evidence="원문 결측 유지", action="ACCEPT", status="ACCEPTED")
    for idx in laps.index[num(laps["lap_duration"]) > 300]:
        lg.issue("laps.csv", "DQ006", idx, "lap_duration", evidence="300초 초과(적기·세이프티카 가능)", action="REVIEW")


def check_pit(data, lg):
    pit, laps = data["pit.csv"], data["laps.csv"]
    for idx in pit.index[num(pit["pit_duration"]) > 180]:
        lg.issue("pit.csv", "DQ007", idx, "pit_duration", evidence="180초 초과", action="REVIEW")
    for idx in pit.index[(pit["lane_duration"] != pit["pit_duration"]) & ~blank(pit["lane_duration"]) & ~blank(pit["pit_duration"])]:
        lg.issue("pit.csv", "DQ021", idx, "pit_duration", expected=pit.at[idx, "lane_duration"],
                 evidence=f"원천에서 두 컬럼이 동일({(pit['lane_duration'] == pit['pit_duration']).mean():.2%})한데 이 행만 다름", action="QUARANTINE")
    for idx in pit.index[num(pit["stop_duration"]) > 10]:
        lg.issue("pit.csv", "DQ022", idx, "stop_duration", evidence="10초 초과 정지(수리·페널티 가능)", action="REVIEW")
    last = num(laps["lap_number"]).groupby([laps["session_key"], laps["driver_number"]]).max()
    limit = pd.Series([last.get((s, d)) for s, d in zip(pit["session_key"], pit["driver_number"])], index=pit.index)
    for idx in pit.index[num(pit["lap_number"]) > limit]:
        lg.issue("pit.csv", "DQ025", idx, "lap_number", expected=fmt_num(limit[idx], 0), evidence="해당 드라이버 최대 랩보다 큼", action="REVIEW")


def check_stints(data, lg):
    stints, laps = data["stints.csv"], data["laps.csv"]
    for idx in stints.index[blank(stints["compound"])]:
        lg.repair("stints.csv", "DQ008", idx, "compound", "UNKNOWN", "explicit_unknown", "LOW", "원본 타이어 정보가 없어 UNKNOWN으로 명시")
    order = stints.assign(_n=num(stints["stint_number"])).sort_values(["session_key", "driver_number", "_n"])
    last = num(laps["lap_number"]).groupby([laps["session_key"], laps["driver_number"]]).max()
    for _, group in order.groupby(["session_key", "driver_number"], sort=False):
        idx = list(group.index)
        for pos, i in enumerate(idx):
            if is_blank(stints.at[i, "lap_start"]):
                prev_end = pd.to_numeric(stints.at[idx[pos - 1], "lap_end"], errors="coerce") if pos else None
                if pos == 0:
                    lg.repair("stints.csv", "DQ009", i, "lap_start", "1", "first_stint_start", "MEDIUM", "첫 스틴트는 1랩에서 시작")
                elif pd.notna(prev_end):
                    lg.repair("stints.csv", "DQ009", i, "lap_start", fmt_num(prev_end + 1, 0), "previous_stint_end_plus_one", "MEDIUM", "이전 스틴트 종료 랩 + 1")
                else:
                    lg.issue("stints.csv", "DQ009", i, "lap_start", evidence="이전 스틴트 경계 없음", action="REVIEW")
            if is_blank(stints.at[i, "lap_end"]):
                next_start = pd.to_numeric(stints.at[idx[pos + 1], "lap_start"], errors="coerce") if pos + 1 < len(idx) else None
                driver_last = last.get((stints.at[i, "session_key"], stints.at[i, "driver_number"]))
                if next_start is not None and pd.notna(next_start):
                    lg.repair("stints.csv", "DQ009", i, "lap_end", fmt_num(next_start - 1, 0), "next_stint_start_minus_one", "MEDIUM", "다음 스틴트 시작 랩 - 1")
                elif next_start is None and driver_last is not None and pd.notna(driver_last):
                    lg.repair("stints.csv", "DQ009", i, "lap_end", fmt_num(driver_last, 0), "driver_last_lap", "LOW", "마지막 스틴트: laps.csv의 해당 드라이버 최대 랩")
                else:
                    lg.issue("stints.csv", "DQ009", i, "lap_end", evidence="다음 스틴트·랩 기록 없음", action="REVIEW")
    start, end = num(stints["lap_start"]), num(stints["lap_end"])
    for idx in stints.index[end < start]:
        if end[idx] == start[idx] - 1:
            lg.issue("stints.csv", "DQ010", idx, "lap_end", evidence="lap_end = lap_start - 1인 빈 스틴트(피트레인 출발 등 원천 특성)", action="ACCEPT", status="ACCEPTED")
        else:
            lg.issue("stints.csv", "DQ010", idx, "lap_end", evidence="lap_end < lap_start", action="QUARANTINE")
    order = stints.assign(_s=start, _e=end, _n=num(stints["stint_number"])).sort_values(["session_key", "driver_number", "_n"])
    valid = order[order["_e"] >= order["_s"]]
    previous = valid.groupby(["session_key", "driver_number"])["_e"].shift()
    for idx in valid.index[previous.notna() & (valid["_s"] < previous)]:
        lg.issue("stints.csv", "DQ011", idx, "lap_start", evidence=f"이전 스틴트 종료 {fmt_num(previous[idx], 0)} 이후에 시작해야 함", action="REVIEW")


def check_weather(data, lg):
    weather = data["weather.csv"]
    order = weather.assign(_t=ts(weather["date"])).sort_values(["session_key", "_t"])
    for field, low, high in [("humidity", 0, 100), ("wind_direction", 0, 360)]:
        value = num(weather[field])
        for idx in weather.index[(value < low) | (value > high)]:
            lg.issue("weather.csv", "DQ023", idx, field, evidence=f"허용 범위 {low}~{high}", action="QUARANTINE")
    temp = num(order["track_temperature"])
    prev = temp.groupby(order["session_key"]).shift()
    nxt = temp.groupby(order["session_key"]).shift(-1)
    spike = prev.notna() & nxt.notna() & ((prev - nxt).abs() <= 3) & ((temp - (prev + nxt) / 2).abs() >= 10)
    for idx in order.index[spike]:
        lg.repair("weather.csv", "DQ023", idx, "track_temperature", fmt_num(round((prev[idx] + nxt[idx]) / 2, 1), 1), "neighbour_mean", "MEDIUM",
                  f"앞뒤 측정 {prev[idx]}, {nxt[idx]}과 10도 이상 차이 나는 단일값")


CHECKS = [check_format, check_keys, check_meeting_key, check_identity, check_team, check_country, check_headshot,
          check_lap_dates, check_lap_missing, check_sectors, check_lap_values, check_pit, check_stints, check_weather]


def run_checks(data, catalogue, fix):
    ledger = Ledger(catalogue, fix=fix)
    ledger.data = data
    for check in CHECKS:
        check(data, ledger)
    return ledger


# ---------------------------------------------------------------- 결과 정리

def annotate(data, original, ledger):
    """행 단위 관리 컬럼(original_*, repair_*, dq_codes, quarantine_flag)을 붙인다."""
    by_row = {}
    for record in ledger.issues:
        if record["_idx"] is not None:
            by_row.setdefault((record["file"], record["_idx"]), []).append(record)
    out = {}
    for name, df in data.items():
        frame = df.copy()
        for col in SCHEMA[name]:
            if col in frame:
                frame[f"original_{col}"] = original[name][col]
        status, method, confidence, reason, codes, quarantine = [], [], [], [], [], []
        for idx in frame.index:
            records = by_row.get((name, idx), [])
            fixed = [r for r in records if r["status"] == "REPAIRED"]
            status.append("REPAIRED" if fixed else "UNCHANGED")
            method.append(";".join(sorted({r["diagnostic_code"] + ":" + r["field"] for r in fixed})) or "NONE")
            confidence.append(min((r["confidence"] for r in fixed), key=lambda c: CONFIDENCE_RANK[c]) if fixed else "HIGH")
            reason.append(" / ".join(dict.fromkeys(r["evidence"] for r in fixed)) or "원본값 유지")
            codes.append(";".join(sorted({r["diagnostic_code"] for r in records})))
            quarantine.append("Y" if any(r["status"] == "OPEN" and r["action"] == "QUARANTINE" for r in records) else "N")
        frame["source_file"] = name
        frame["repair_status"], frame["repair_method"], frame["repair_confidence"] = status, method, confidence
        frame["repair_reason"], frame["dq_codes"], frame["quarantine_flag"] = reason, codes, quarantine
        out[name] = frame
    return out


def summarize(data, ledger, residual, catalogue):
    issues = pd.DataFrame(ledger.issues)
    residual_counts = pd.DataFrame(residual.issues).groupby(["file", "diagnostic_code"]).size() if residual.issues else pd.Series(dtype=int)
    rows = []
    if not issues.empty:
        for (name, code), group in issues.groupby(["file", "diagnostic_code"]):
            meta = catalogue[code]
            rows.append({"file": name, "diagnostic_code": code, "diagnostic_name": meta["diagnostic_name"], "korean_name": meta["korean_name"],
                         "error_type": meta["error_type"], "error_type_korean": meta["error_type_korean"], "severity": meta["severity"],
                         "detected": len(group), "repaired": int((group["status"] == "REPAIRED").sum()),
                         "accepted": int((group["status"] == "ACCEPTED").sum()), "open": int((group["status"] == "OPEN").sum()),
                         "quarantined_rows": int(group.loc[(group["status"] == "OPEN") & (group["action"] == "QUARANTINE"), "_idx"].nunique()),
                         "residual_after_repair": int(residual_counts.get((name, code), 0))})
    return pd.DataFrame(rows, columns=["file", "diagnostic_code", "diagnostic_name", "korean_name", "error_type", "error_type_korean", "severity",
                                       "detected", "repaired", "accepted", "open", "quarantined_rows", "residual_after_repair"])


def file_summary(annotated, ledger):
    issues = pd.DataFrame(ledger.issues)
    rows = []
    for name, df in annotated.items():
        part = issues[issues["file"] == name] if not issues.empty else issues
        rows.append({"file": name, "rows": len(df), "issue_count": len(part),
                     "repaired_cells": int((part["status"] == "REPAIRED").sum()) if len(part) else 0,
                     "repaired_rows": int((df["repair_status"] == "REPAIRED").sum()),
                     "open_issues": int((part["status"] == "OPEN").sum()) if len(part) else 0,
                     "quarantined_rows": int((df["quarantine_flag"] == "Y").sum()),
                     "status": "PASS" if not len(part) or not (part["status"] == "OPEN").any() else "REVIEW"})
    return pd.DataFrame(rows)


def table(df, limit=None):
    shown = df if limit is None else df.head(limit)
    return shown.to_html(index=False, escape=True, border=0) if len(shown) else "<p>없음</p>"


def md_table(df, limit=None):
    """GitHub에서 표로 보이는 마크다운 표 (칸 안의 |·줄바꿈은 이스케이프)."""
    shown = df if limit is None else df.head(limit)
    if not len(shown):
        return "없음\n"
    cell = lambda v: "" if pd.isna(v) else (f"{v:,}" if isinstance(v, int) else str(v)).replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    lines = ["| " + " | ".join(map(str, shown.columns)) + " |", "|" + "---|" * len(shown.columns)]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in shown.astype(object).itertuples(index=False)]
    more = f"\n_{len(df):,}건 중 {len(shown):,}건 표시_\n" if len(shown) < len(df) else ""
    return "\n".join(lines) + "\n" + more


def build_report(report_dir, annotated, ledger, manifest, dq_summary, files_df, run_info):
    report_dir.mkdir(parents=True, exist_ok=True)
    issue_cols = ["issue_id", "diagnostic_code", "diagnostic_name", "korean_name", "error_type", "error_type_korean", "severity", "file",
                  "source_row", "row_key", "session_key", "driver_number", "field", "observed_value", "expected_value", "evidence",
                  "action", "status", "confidence"]
    issues = pd.DataFrame(ledger.issues, columns=issue_cols + ["_idx"])[issue_cols]
    repairs = pd.DataFrame(ledger.repairs, columns=["issue_id", "diagnostic_code", "error_type", "file", "source_row", "row_key", "session_key",
                                                    "driver_number", "field", "old_value", "new_value", "method", "confidence", "reason"])
    issues.to_csv(report_dir / "validation_issues.csv", index=False, encoding="utf-8-sig")
    repairs.to_csv(report_dir / "repair_detail.csv", index=False, encoding="utf-8-sig")
    files_df.to_csv(report_dir / "repair_summary.csv", index=False, encoding="utf-8-sig")
    dq_summary.to_csv(report_dir / "dq_summary.csv", index=False, encoding="utf-8-sig")
    manifest.to_csv(report_dir / "bronze_manifest.csv", index=False, encoding="utf-8-sig")

    by_type = dq_summary.groupby(["error_type", "error_type_korean"], as_index=False)[["detected", "repaired", "accepted", "open", "quarantined_rows"]].sum() \
        if len(dq_summary) else dq_summary
    cards = "".join(f"<div>{html.escape(label)}<strong>{value:,}</strong></div>" for label, value in [
        ("탐지", len(issues)), ("자동 복구", int((issues["status"] == "REPAIRED").sum())),
        ("허용(원천 특성)", int((issues["status"] == "ACCEPTED").sum())), ("검토 필요", int((issues["status"] == "OPEN").sum())),
        ("격리 행", int(files_df["quarantined_rows"].sum()))])
    samples = []
    for code, group in issues[issues["status"] != "ACCEPTED"].groupby("diagnostic_code"):
        samples.append(f"<h3>{html.escape(code)} {html.escape(group['korean_name'].iat[0])} ({len(group):,}건)</h3>" +
                       table(group.drop(columns=["issue_id", "diagnostic_name", "korean_name", "error_type_korean"]), 20))
    style = ("body{font-family:Arial,'Malgun Gothic',sans-serif;margin:32px;color:#17212b}table{border-collapse:collapse;width:100%;margin:12px 0 28px;font-size:12.5px}"
             "th,td{border:1px solid #d5dee7;padding:6px;text-align:left;vertical-align:top}th{background:#eaf1f6}"
             ".cards{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.cards div{background:#f1f5f8;padding:14px 18px;border-radius:8px}"
             ".cards strong{display:block;font-size:24px;margin-top:6px}h2{margin-top:36px}.meta{color:#56636f;font-size:13px}")
    body = (f"<h1>F1 오염 데이터 검증·복구 리포트</h1><p class='meta'>파이프라인 {PIPELINE_VERSION} · 입력 {html.escape(run_info['input'])} · run_id {run_info['run_id']}</p>"
            f"<div class='cards'>{cards}</div>"
            "<h2>1. Bronze 매니페스트</h2><p class='meta'>원본 파일이 배포본 그대로인지(체크섬)와 명세서의 행·컬럼 구성과 같은지 확인한다. "
            "판정 컬럼(spec_row_count·schema·column_order·checksum)이 모두 MATCH/OK이면 정상이다. 해시 값은 증빙용이라 맨 뒤에 앞 12자리만 표시한다(전체 값은 bronze_manifest.csv).</p>" + table(manifest.assign(
                sha256=manifest["sha256"].str[:12] + "…", sha256_expected=manifest["sha256_expected"].astype(str).str[:12] + "…")) +
            "<details open><summary>컬럼 설명</summary>" + table(pd.DataFrame(MANIFEST_COLUMNS, columns=["컬럼", "의미"])) + "</details>" +
            "<h2>2. 파일별 처리 결과</h2>" + table(files_df) +
            "<h2>3. 오류 유형별 집계</h2>" + table(by_type) +
            "<h2>4. 진단코드별 집계</h2><p class='meta'>residual_after_repair: 복구 후 같은 규칙으로 다시 검사했을 때 남은 건수 (= accepted + open 이어야 함)</p>" + table(dq_summary) +
            "<h2>5. 진단코드별 상세 샘플 (허용 제외, 코드당 20건)</h2>" + "".join(samples) +
            "<h2>6. 복구 이력 샘플</h2>" + table(repairs, 200))
    (report_dir / "quality_report.html").write_text(f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>F1 품질 리포트</title><style>{style}</style></head><body>{body}</body></html>", encoding="utf-8")

    # 같은 내용의 마크다운판: GitHub에서는 HTML이 코드로만 보이므로 표로 바로 읽히게 만든다 (샘플은 줄여서)
    counts = [("탐지", len(issues)), ("자동 복구", int((issues["status"] == "REPAIRED").sum())),
              ("허용(원천 특성)", int((issues["status"] == "ACCEPTED").sum())), ("검토 필요", int((issues["status"] == "OPEN").sum())),
              ("격리 행", int(files_df["quarantined_rows"].sum()))]
    md_samples = "".join(
        f"\n#### {code} {group['korean_name'].iat[0]} ({len(group):,}건)\n\n" +
        md_table(group[["severity", "file", "row_key", "field", "observed_value", "expected_value", "evidence", "action", "status"]], 5)
        for code, group in issues[issues["status"] != "ACCEPTED"].groupby("diagnostic_code"))
    md = (f"# F1 오염 데이터 검증·복구 리포트\n\n"
          f"파이프라인 {PIPELINE_VERSION} · 입력 `{run_info['input']}` · run_id `{run_info['run_id']}`  \n"
          f"전체 샘플과 원자료: [quality_report.html](./quality_report.html) (내려받아 브라우저로 열기) · `validation_issues.csv` · `repair_detail.csv`\n\n"
          "| " + " | ".join(label for label, _ in counts) + " |\n|" + "---:|" * len(counts) + "\n| " +
          " | ".join(f"{value:,}" for _, value in counts) + " |\n\n"
          "## 1. Bronze 매니페스트\n\n원본 파일이 배포본 그대로인지(체크섬)와 명세서의 행·컬럼 구성과 같은지 확인한다. "
          "판정 컬럼(spec_row_count·schema·column_order·checksum)이 모두 MATCH/OK이면 정상이다.\n\n" +
          md_table(manifest.drop(columns=["sha256", "sha256_expected"], errors="ignore")) +
          "\n## 2. 파일별 처리 결과\n\n" + md_table(files_df) +
          "\n## 3. 오류 유형별 집계\n\n" + md_table(by_type) +
          "\n## 4. 진단코드별 집계\n\nresidual_after_repair: 복구 후 같은 규칙으로 다시 검사했을 때 남은 건수 (= accepted + open 이어야 함)\n\n" + md_table(dq_summary) +
          "\n## 5. 진단코드별 상세 샘플 (허용 제외, 코드당 5건)\n" + md_samples +
          "\n## 6. 복구 이력 샘플\n\n" + md_table(repairs[["diagnostic_code", "file", "row_key", "field", "old_value", "new_value", "method", "confidence", "reason"]], 30))
    (report_dir / "quality_report.md").write_text(md, encoding="utf-8")
    (report_dir / "run_result.json").write_text(json.dumps(run_info, ensure_ascii=False, indent=2), encoding="utf-8")
    return issues, repairs


def run(input_path: Path, out: Path, catalogue_path: Path = DICT_PATH, report_dir: Path | None = None):
    """out에 정제 결과(repaired/·quarantine/), report_dir(기본 out/reports)에 리포트를 쓴다."""
    report_dir = report_dir or out / "reports"
    catalogue = load_catalogue(catalogue_path)
    raw, checksums, spec = load_source(input_path)
    pre = Ledger(catalogue)
    data, manifest = bronze(raw, checksums, spec, pre)
    pre.data = data
    original = {name: df.copy() for name, df in data.items()}
    ledger = run_checks(data, catalogue, fix=True)
    ledger.issues = pre.issues + ledger.issues
    residual = run_checks({name: df.copy() for name, df in data.items()}, catalogue, fix=False)
    annotated = annotate(data, original, ledger)
    for sub in ["repaired", "quarantine"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    for name, df in annotated.items():
        df.drop(columns=["source_row"]).to_csv(out / "repaired" / name, index=False, encoding="utf-8-sig")
        df[df["quarantine_flag"] == "Y"].to_csv(out / "quarantine" / name, index=False, encoding="utf-8-sig")
    dq_summary = summarize(data, ledger, residual, catalogue)
    files_df = file_summary(annotated, ledger)
    run_id = hashlib.sha256(("".join(manifest["sha256"]) + PIPELINE_VERSION).encode()).hexdigest()[:12]
    run_info = {"run_id": run_id, "pipeline_version": PIPELINE_VERSION, "input": str(input_path), "output": str(out), "report_output": str(report_dir),
                "issues": len(ledger.issues), "repaired_cells": len(ledger.repairs),
                "open_issues": sum(r["status"] == "OPEN" for r in ledger.issues),
                "accepted_issues": sum(r["status"] == "ACCEPTED" for r in ledger.issues),
                "quarantined_rows": int(files_df["quarantined_rows"].sum()),
                "checksum_ok": bool((manifest["checksum"] != "MISMATCH").all()),
                "spec_ok": bool((manifest["spec_row_count"] != "MISMATCH").all() and (manifest["schema"] == "OK").all())}
    build_report(report_dir, annotated, ledger, manifest, dq_summary, files_df, run_info)
    return run_info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parent / "config.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source = config.get("input_path") or config["input_archive"]
    # config의 상대 경로는 저장소 루트 기준 (리포트에 PC별 절대 경로가 남지 않도록 루트로 이동해 상대 경로로 실행)
    os.chdir(ROOT)
    reports = config.get("report_directory")
    info = run(Path(source), Path(config["output_directory"]), report_dir=Path(reports) if reports else None)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
