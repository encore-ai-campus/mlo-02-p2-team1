from __future__ import annotations

import argparse, io, json, math, zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

FILES = ["sessions.csv", "drivers.csv", "laps.csv", "stints.csv", "weather.csv", "pit.csv"]
SCHEMA = {
    "drivers.csv": "broadcast_name country_code driver_number first_name full_name headshot_url last_name meeting_key name_acronym session_key team_colour team_name".split(),
    "laps.csv": "date_start driver_number duration_sector_1 duration_sector_2 duration_sector_3 i1_speed i2_speed is_pit_out_lap lap_duration lap_number meeting_key segments_sector_1 segments_sector_2 segments_sector_3 session_key st_speed".split(),
    "pit.csv": "date driver_number lane_duration lap_number meeting_key pit_duration session_key stop_duration".split(),
    "sessions.csv": "circuit_key circuit_short_name country_code country_key country_name date_end date_start gmt_offset is_cancelled location meeting_key session_key session_name session_type year".split(),
    "stints.csv": "compound driver_number lap_end lap_start meeting_key session_key stint_number tyre_age_at_start".split(),
    "weather.csv": "air_temperature date humidity meeting_key pressure rainfall session_key track_temperature wind_direction wind_speed".split(),
}
NUMERIC = ["duration_sector_1", "duration_sector_2", "duration_sector_3", "i1_speed", "i2_speed", "lap_duration", "st_speed", "lane_duration", "pit_duration", "stop_duration"]
COMPOUNDS = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", "UNKNOWN"}


def is_blank(series):
    return series.isna() | series.astype("string").str.strip().isin(["", "NULL", "None", "nan"])


def load_archive(path):
    with zipfile.ZipFile(path) as archive:
        marker = next((name for name in archive.namelist() if name.endswith("all_years/sessions.csv")), None)
        if marker is None:
            raise ValueError("압축파일에서 all_years/sessions.csv를 찾지 못했습니다.")
        root = marker[: -len("sessions.csv")]
        data = {name: pd.read_csv(io.BytesIO(archive.read(root + name)), dtype="string", keep_default_na=False) for name in FILES}
        spec_present = any(name.endswith("00. 데이터_명세서.md") for name in archive.namelist())
    return data, spec_present


def prepare(data):
    for name, df in data.items():
        for col in list(df.columns):
            df[f"original_{col}"] = df[col]
        df["source_file"] = name
        df["repair_status"] = "UNCHANGED"
        df["repair_method"] = "NONE"
        df["repair_confidence"] = "HIGH"
        df["repair_reason"] = "원본값 유지"


def record(data, mask, field, values, method, confidence, reason, details):
    df = data
    target = mask & is_blank(df[field]) & values.notna()
    if not target.any():
        return
    old = df.loc[target, field].astype("string").fillna("")
    new = values.loc[target].astype("string")
    for idx in df.index[target]:
        details.append({"source_file": df.at[idx, "source_file"], "session_key": df.at[idx, "session_key"] if "session_key" in df else "", "driver_number": df.at[idx, "driver_number"] if "driver_number" in df else "", "row_key": df.at[idx, "lap_number"] if "lap_number" in df else (df.at[idx, "stint_number"] if "stint_number" in df else ""), "field": field, "old_value": old.loc[idx], "new_value": new.loc[idx], "method": method, "confidence": confidence, "reason": reason})
    df.loc[target, field] = values.loc[target]
    df.loc[target, "repair_status"] = "REPAIRED"
    df.loc[target, "repair_method"] = method
    df.loc[target, "repair_confidence"] = confidence
    df.loc[target, "repair_reason"] = reason


def repair(data, details):
    sessions = data["sessions.csv"].set_index("session_key", drop=False)
    for name in ["drivers.csv", "laps.csv"]:
        df = data[name]
        for field in ["year", "country_name", "country_code", "circuit_short_name", "location", "meeting_key", "session_name", "session_type"]:
            if field in df.columns:
                values = df["session_key"].map(sessions[field] if field in sessions else pd.Series(dtype="string"))
                record(df, pd.Series(True, index=df.index), field, values, "session_key_join", "HIGH", "동일 session_key의 sessions.csv 값", details)
    laps = data["laps.csv"]
    for field in ["duration_sector_1", "duration_sector_2", "duration_sector_3", "i1_speed", "i2_speed", "st_speed"]:
        laps[field] = pd.to_numeric(laps[field], errors="coerce")
        grouped = laps.groupby(["session_key", "driver_number"], dropna=False)[field].transform("median")
        fallback = laps.groupby("session_key", dropna=False)[field].transform("median")
        record(laps, pd.Series(True, index=laps.index), field, grouped.fillna(fallback), "median_session_driver_or_session", "MEDIUM", "동일 세션·드라이버 중앙값, 없으면 세션 중앙값", details)
    stints = data["stints.csv"]
    record(stints, is_blank(stints["compound"]), "compound", pd.Series("UNKNOWN", index=stints.index, dtype="string"), "explicit_unknown", "LOW", "원본 타이어 정보가 없어 UNKNOWN으로 명시", details)


def validate(data):
    issues = []
    for name, df in data.items():
        missing = sorted(set(SCHEMA[name]) - set(df.columns))
        if missing:
            issues.append({"file": name, "kind": "SCHEMA", "row_key": "", "session_key": "", "field": "", "message": "missing columns: " + ", ".join(missing)})
        for field in NUMERIC:
            if field in df.columns:
                parsed = pd.to_numeric(df[field], errors="coerce")
                bad = (~is_blank(df[field])) & parsed.isna()
                for idx in df.index[bad]:
                    issues.append({"file": name, "kind": "TYPE", "row_key": idx, "session_key": df.at[idx, "session_key"] if "session_key" in df else "", "field": field, "message": "숫자로 해석할 수 없음"})
        if name == "stints.csv":
            start, end = pd.to_numeric(df["lap_start"], errors="coerce"), pd.to_numeric(df["lap_end"], errors="coerce")
            for idx in df.index[(start.notna() & end.notna() & (end < start))]:
                issues.append({"file": name, "kind": "RANGE", "row_key": df.at[idx, "stint_number"], "session_key": df.at[idx, "session_key"], "field": "lap_end", "message": "lap_end < lap_start"})
            invalid = ~is_blank(df["compound"]) & ~df["compound"].isin(COMPOUNDS)
            for idx in df.index[invalid]:
                issues.append({"file": name, "kind": "DOMAIN", "row_key": df.at[idx, "stint_number"], "session_key": df.at[idx, "session_key"], "field": "compound", "message": "허용 목록 외 compound"})
        if name == "laps.csv":
            bad = pd.to_numeric(df["lap_duration"], errors="coerce") > 300
            for idx in df.index[bad]:
                issues.append({"file": name, "kind": "OUTLIER", "row_key": df.at[idx, "lap_number"], "session_key": df.at[idx, "session_key"], "field": "lap_duration", "message": "300초 초과 비정상 랩"})
        if name == "pit.csv":
            bad = pd.to_numeric(df["pit_duration"], errors="coerce") > 180
            for idx in df.index[bad]:
                issues.append({"file": name, "kind": "OUTLIER", "row_key": df.at[idx, "lap_number"], "session_key": df.at[idx, "session_key"], "field": "pit_duration", "message": "180초 초과 비정상 피트 시간"})
    stints = data["stints.csv"].copy()
    stints["_start"] = pd.to_numeric(stints["lap_start"], errors="coerce")
    stints["_end"] = pd.to_numeric(stints["lap_end"], errors="coerce")
    stints = stints.sort_values(["session_key", "driver_number", "_start"])
    previous = stints.groupby(["session_key", "driver_number"], dropna=False)["_end"].shift()
    overlap = stints["_start"].notna() & previous.notna() & (stints["_start"] < previous)
    for idx in stints.index[overlap]:
        issues.append({"file": "stints.csv", "kind": "OVERLAP", "row_key": stints.at[idx, "stint_number"], "session_key": stints.at[idx, "session_key"], "field": "lap_start", "message": "동일 세션·드라이버 스틴트 구간이 실제로 겹침"})
    return issues


def build_report(out, data, details, issues, spec_present):
    report_dir = out / "reports"; report_dir.mkdir(parents=True, exist_ok=True)
    detail_df = pd.DataFrame(details); issue_df = pd.DataFrame(issues)
    if detail_df.empty: detail_df = pd.DataFrame([{"source_file": "", "field": "", "old_value": "", "new_value": "", "method": "", "confidence": "", "reason": ""}])
    if issue_df.empty: issue_df = pd.DataFrame([{"file": "", "kind": "", "field": "", "message": "검증 이슈 없음"}])
    detail_df.to_csv(report_dir / "repair_detail.csv", index=False, encoding="utf-8-sig")
    issue_df.to_csv(report_dir / "validation_issues.csv", index=False, encoding="utf-8-sig")
    summary = []
    for name, df in data.items():
        file_issues = sum(1 for issue in issues if issue["file"] == name)
        summary.append({"file": name, "rows": len(df), "changes": int((df["repair_status"] == "REPAIRED").sum()), "status": "PASS" if file_issues == 0 else "REVIEW", "issues": file_issues})
    summary_df = pd.DataFrame(summary); summary_df.to_csv(report_dir / "repair_summary.csv", index=False, encoding="utf-8-sig")
    cards = f"<div class='cards'><div>복구 기록<strong>{len(details):,}</strong></div><div>검증 이슈<strong>{len(issues):,}</strong></div><div>명세서<strong>{'확인' if spec_present else '미확인'}</strong></div></div>"
    html = "<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>F1 품질 리포트</title><style>body{font-family:Arial,'Malgun Gothic';margin:32px;color:#17212b}table{border-collapse:collapse;width:100%;margin:12px 0 28px;font-size:13px}th,td{border:1px solid #d5dee7;padding:7px;text-align:left}th{background:#eaf1f6}.cards{display:flex;gap:12px;margin:20px 0}.cards div{background:#f1f5f8;padding:16px;border-radius:8px}.cards strong{display:block;font-size:25px;margin-top:6px}h2{margin-top:32px}</style></head><body>"
    html += "<h1>F1 오염 데이터 복구 및 품질 검증 리포트</h1>" + cards + "<h2>파일별 처리 결과</h2>" + summary_df.to_html(index=False, escape=True)
    html += "<h2>복구 기록 샘플</h2>" + detail_df.head(2000).to_html(index=False, escape=True)
    html += "<h2>검증 이슈</h2>" + issue_df.head(2000).to_html(index=False, escape=True) + "</body></html>"
    (report_dir / "quality_report.html").write_text(html, encoding="utf-8")
    (report_dir / "run_result.json").write_text(json.dumps({"output": str(out), "repair_records": len(details), "validation_issues": len(issues), "spec_present": spec_present}, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", type=Path, default=Path("config.json")); args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8")); out = Path(config["output_directory"]); data, spec = load_archive(Path(config["input_archive"])); prepare(data); details = []; repair(data, details); issues = validate(data)
    for name, df in data.items():
        (out / "repaired").mkdir(parents=True, exist_ok=True); df.to_csv(out / "repaired" / name, index=False, encoding="utf-8-sig")
    build_report(out, data, details, issues, spec); print(json.dumps({"output": str(out), "repair_records": len(details), "validation_issues": len(issues)}, ensure_ascii=False))


if __name__ == "__main__": main()
