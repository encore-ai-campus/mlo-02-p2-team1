"""후보 선정 근거 보강: 정제 결과(Silver)에서 같은 차 동료 비교와 타이어 유지를 직접 다시 계산한다.

Gold 후보 지표(data/05_gold/decision_board.json)는 저장소 밖 분석 코드로 만든 결과 파일이다. 이 모듈은 그중
선정 근거의 핵심인 "같은 차 동료 비교"와 "타이어 유지"를 기획서 방법론과 같은 규칙으로 저장소 안에서 재계산해,
(1) Gold 값이 재현되는지 확인하고 (2) 두 후보를 같은 동료(HAMILTON) 기준으로 잰다.

정상 랩: 본경기, 2랩부터, 피트 인·아웃 랩과 격리 행 제외, 0 < 랩타임 <= 300초, 마른 노면 컴파운드(SOFT·MEDIUM·HARD),
         비 측정 경기 제외, SC·VSC·적기 구간(race_control 공지 + 종료 뒤 MARGIN초) 제외,
         드라이버의 그 경기 정상 랩 중앙값 107% 초과 제외. 스틴트가 둘 이상 걸리는 랩은 제외.
동료 비교: 같은 경기·팀·랩 번호·컴파운드, 타이어 나이 차 <= 3랩, 랩 시작 시각 차 <= 90초인 랩 쌍.
           경기당 8쌍 이상인 경기만 쓰고, 경기별 중앙값 차이의 평균을 동료 대비(초/랩)로 쓴다.
           95% 구간은 경기 단위 부트스트랩(2000회, 고정 시드).
타이어 유지: 스틴트별 (랩타임 ~ 타이어 나이) 기울기(ms/랩)에서 같은 경기·컴파운드의 다른 스틴트 중앙값을 뺀 값.
             유효 랩 8개 이상, 타이어 나이 범위 7랩 이상인 스틴트만. 작을수록 타이어를 오래 쓴다.

    python -m pipeline.driver_check                    # 기본 비교 세트 → data/05_gold/driver_check/
"""
from __future__ import annotations

import argparse, io, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEANED = ROOT / "data" / "03_cleaned" / "repaired"
EXTRA_ZIP = ROOT / "data" / "01_raw" / "f1_extra_data.zip"
OUT = ROOT / "data" / "05_gold" / "driver_check"

DRY = {"SOFT", "MEDIUM", "HARD"}
MARGIN = 120          # SC·VSC 종료 공지 뒤에도 정상 속도로 돌아오기까지 제외하는 시간(초)
CUTOFF = 1.07
AGE_DIFF, TIME_DIFF, MIN_PAIRS = 3, 90, 8
MIN_STINT_LAPS, MIN_AGE_RANGE = 8, 7
BOOT, SEED = 2000, 20261016

# (비교 이름, 시즌들, 선수 A, 선수 B) — A − B, 음수면 A가 빠름
PAIRS = [
    ("RUSSELL vs HAMILTON (Mercedes)", [2023, 2024], "George RUSSELL", "Lewis HAMILTON"),
    ("LECLERC vs HAMILTON (Ferrari)", [2025], "Charles LECLERC", "Lewis HAMILTON"),
    ("RUSSELL vs ANTONELLI (Mercedes)", [2025], "George RUSSELL", "Kimi ANTONELLI"),
    ("LECLERC vs SAINZ (Ferrari)", [2023, 2024], "Charles LECLERC", "Carlos SAINZ"),
    ("STROLL vs ALONSO (Aston Martin)", [2025], "Lance STROLL", "Fernando ALONSO"),
    ("STROLL vs ALONSO (Aston Martin)", [2023, 2024], "Lance STROLL", "Fernando ALONSO"),
]
# 시즌별 동료 비교(2025 한 시즌 결과가 다른 시즌에도 유지되는지): 2025 같은 경기 비교 통과 7명 + 기준 선수
SEASON_DRIVERS = ["Charles LECLERC", "George RUSSELL", "Lando NORRIS", "Oscar PIASTRI", "Max VERSTAPPEN",
                  "Lewis HAMILTON", "Kimi ANTONELLI", "Lance STROLL"]
SEASONS, MIN_SEASON_RACES = [2023, 2024, 2025, 2026], 3
TYRE_DRIVERS = ["George RUSSELL", "Charles LECLERC", "Lance STROLL", "Lewis HAMILTON", "Fernando ALONSO", "Kimi ANTONELLI"]


def _csv(path):
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def _ts(s):
    return pd.to_datetime(s, format="ISO8601", utc=True, errors="coerce")


def load():
    s = _csv(CLEANED / "sessions.csv")
    s = s[(s["session_type"] == "Race") & (s["is_cancelled"].astype(str) != "True")][["session_key", "year", "date_end"]]
    laps = _csv(CLEANED / "laps.csv")[["session_key", "driver_number", "lap_number", "lap_duration", "date_start",
                                       "is_pit_out_lap", "quarantine_flag"]]
    stints = _csv(CLEANED / "stints.csv")[["session_key", "driver_number", "stint_number", "compound", "lap_start",
                                           "lap_end", "tyre_age_at_start", "quarantine_flag"]]
    pit = _csv(CLEANED / "pit.csv")[["session_key", "driver_number", "lap_number"]]
    drivers = _csv(CLEANED / "drivers.csv")[["session_key", "driver_number", "full_name", "team_name"]]
    weather = _csv(CLEANED / "weather.csv")[["session_key", "rainfall"]]
    with zipfile.ZipFile(EXTRA_ZIP) as zf:
        name = next(n for n in zf.namelist() if n.endswith("race_control.csv"))
        rc = pd.read_csv(io.BytesIO(zf.read(name)))
    return s, laps, stints, pit, drivers, weather, rc


def neutralised(rc, sessions):
    """SC·VSC·적기 구간 (session_key, 시작, 끝). 끝 공지가 없으면 세션 끝까지."""
    rc = rc.assign(t=_ts(rc["date"])).sort_values(["session_key", "t"])
    end_of = sessions.set_index("session_key")["date_end"].pipe(_ts)
    out = []
    for key, g in rc.groupby("session_key"):
        start = None
        for _, r in g.iterrows():
            msg, flag = str(r["message"]).upper(), str(r["flag"]).upper()
            if ("SAFETY CAR DEPLOYED" in msg or "VSC DEPLOYED" in msg or flag == "RED") and start is None:
                start = r["t"]
            elif start is not None and ("IN THIS LAP" in msg or "ENDING" in msg or (flag == "GREEN" and "PIT EXIT" not in msg)):
                out.append((key, start, r["t"] + pd.Timedelta(seconds=MARGIN)))
                start = None
        if start is not None:
            out.append((key, start, end_of.get(key, start + pd.Timedelta(hours=3))))
    return pd.DataFrame(out, columns=["session_key", "w0", "w1"])


def normal_laps(s, laps, stints, pit, drivers, weather, rc):
    keys = set(s["session_key"])
    wet = set(weather[(weather["session_key"].isin(keys)) & (pd.to_numeric(weather["rainfall"], errors="coerce") > 0)]["session_key"])
    keys -= wet
    L = laps[laps["session_key"].isin(keys)].copy()
    L["ld"] = pd.to_numeric(L["lap_duration"], errors="coerce")
    L["t"] = _ts(L["date_start"])
    L = L[(L["quarantine_flag"].astype(str) != "Y") & (L["lap_number"] > 1) & (L["is_pit_out_lap"].astype(str) != "True")
          & (L["ld"] > 0) & (L["ld"] <= 300) & L["t"].notna()]
    inlap = pit.assign(x=1).drop_duplicates(["session_key", "driver_number", "lap_number"])
    L = L.merge(inlap, on=["session_key", "driver_number", "lap_number"], how="left")
    L = L[L["x"].isna()].drop(columns="x")
    # 중립화 구간
    W = neutralised(rc[rc["session_key"].isin(keys)], s)
    L["neutral"] = False
    for key, w in W.groupby("session_key"):
        m = L["session_key"] == key
        t = L.loc[m, "t"]
        end = t + pd.to_timedelta(L.loc[m, "ld"], unit="s")
        hit = np.zeros(m.sum(), bool)
        for w0, w1 in zip(w["w0"], w["w1"]):
            hit |= ((t < w1) & (end > w0)).to_numpy()
        L.loc[m, "neutral"] = hit
    L = L[~L["neutral"]]
    # 스틴트: 컴파운드·타이어 나이 (여러 스틴트에 걸리면 제외)
    st = stints[(stints["quarantine_flag"].astype(str) != "Y") & stints["session_key"].isin(keys)].copy()
    st["compound"] = st["compound"].astype(str).str.upper()
    j = L.merge(st[["session_key", "driver_number", "stint_number", "compound", "lap_start", "lap_end", "tyre_age_at_start"]],
                on=["session_key", "driver_number"], how="inner")
    j = j[(j["lap_number"] >= j["lap_start"]) & (j["lap_number"] <= j["lap_end"])]
    j = j[~j.duplicated(["session_key", "driver_number", "lap_number"], keep=False)]
    j = j[j["compound"].isin(DRY)].copy()
    j["age"] = j["tyre_age_at_start"] + j["lap_number"] - j["lap_start"]
    j = j[j["ld"] <= j.groupby(["session_key", "driver_number"])["ld"].transform("median") * CUTOFF]
    j = j.merge(drivers.drop_duplicates(["session_key", "driver_number"]), on=["session_key", "driver_number"], how="left")
    return j.merge(s[["session_key", "year"]], on="session_key")


def boot_ci(values, rng):
    v = np.asarray(values, float)
    if len(v) < 2:
        return np.nan, np.nan
    m = rng.choice(v, size=(BOOT, len(v)), replace=True).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def teammate(j, years, a, b, rng):
    x = j[j["year"].isin(years)]
    A, B = x[x["full_name"] == a], x[x["full_name"] == b]
    p = A.merge(B, on=["session_key", "team_name", "lap_number", "compound"], suffixes=("_a", "_b"))
    p = p[((p["age_a"] - p["age_b"]).abs() <= AGE_DIFF) & ((p["t_a"] - p["t_b"]).dt.total_seconds().abs() <= TIME_DIFF)]
    p["d"] = p["ld_a"] - p["ld_b"]
    per = p.groupby("session_key").agg(pairs=("d", "size"), delta=("d", "median"))
    per = per[per["pairs"] >= MIN_PAIRS]
    lo, hi = boot_ci(per["delta"], rng)
    return {"delta": float(per["delta"].mean()) if len(per) else np.nan, "low": lo, "high": hi, "races": len(per),
            "pairs": int(per["pairs"].sum()), "faster_races": int((per["delta"] < 0).sum()),
            "team": ", ".join(sorted(p["team_name"].dropna().unique()))}, per.reset_index().assign(a=a, b=b)


def tyre(j):
    rows = []
    for (key, drv, stn), g in j.groupby(["session_key", "driver_number", "stint_number"]):
        if len(g) < MIN_STINT_LAPS or g["age"].max() - g["age"].min() < MIN_AGE_RANGE:
            continue
        slope = np.polyfit(g["age"], g["ld"], 1)[0] * 1000
        rows.append((key, g["year"].iat[0], g["full_name"].iat[0], g["team_name"].iat[0], g["compound"].iat[0], len(g), slope))
    t = pd.DataFrame(rows, columns=["session_key", "year", "full_name", "team_name", "compound", "laps", "slope_ms"])
    grp = t.groupby(["session_key", "compound"])["slope_ms"]
    # 같은 경기·컴파운드의 다른 스틴트 중앙값 대비 (자기 스틴트 제외가 원칙이나 스틴트 수가 많아 중앙값 차이는 작다)
    t["rel_ms"] = t["slope_ms"] - grp.transform("median")
    t = t[grp.transform("size") >= 4]
    return t


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    j = normal_laps(*load())
    rows, races = [], []
    for name, years, a, b in PAIRS:
        r, per = teammate(j, years, a, b, rng)
        rows.append({"comparison": name, "seasons": "-".join(map(str, (min(years), max(years)))) if len(years) > 1 else str(years[0]), **r})
        races.append(per.assign(comparison=name))
    tm = pd.DataFrame(rows)
    tm.to_csv(out / "teammate.csv", index=False, encoding="utf-8-sig")
    pd.concat(races).to_csv(out / "teammate_races.csv", index=False, encoding="utf-8-sig")

    by_season = []
    for y in SEASONS:
        x = j[j["year"] == y]
        for d in SEASON_DRIVERS:
            for team in x.loc[x["full_name"] == d, "team_name"].dropna().unique():
                for mate in sorted(set(x.loc[x["team_name"] == team, "full_name"]) - {d}):
                    r, _ = teammate(j, [y], d, mate, rng)
                    if r["races"] >= MIN_SEASON_RACES:
                        by_season.append({"driver": d, "year": y, "teammate": mate, **r,
                                          "clear": "faster" if r["high"] < 0 else ("slower" if r["low"] > 0 else "unclear")})
    pd.DataFrame(by_season).to_csv(out / "teammate_by_season.csv", index=False, encoding="utf-8-sig")

    t = tyre(j)
    t.to_csv(out / "tyre_stints.csv", index=False, encoding="utf-8-sig")
    season = t.groupby(["year", "full_name"]).agg(stints=("rel_ms", "size"), rel_ms=("rel_ms", "median")).reset_index()
    season = season[season["stints"] >= 8]
    season["top_pct"] = season.groupby("year")["rel_ms"].rank(pct=True).mul(100).round()
    pooled = t[t["year"].between(2023, 2025)].groupby("full_name").agg(stints=("rel_ms", "size"), rel_ms=("rel_ms", "median"))
    pooled = pooled[pooled["stints"] >= 20]
    pooled["top_pct"] = pooled["rel_ms"].rank(pct=True).mul(100).round()
    season.to_csv(out / "tyre_season.csv", index=False, encoding="utf-8-sig")
    pooled.reset_index().to_csv(out / "tyre_2023_2025.csv", index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 200)
    print(tm.round(3).to_string(index=False))
    print(season[season["full_name"].isin(TYRE_DRIVERS)].sort_values(["full_name", "year"]).round(1).to_string(index=False))
    print(pooled.loc[pooled.index.isin(TYRE_DRIVERS)].round(1).to_string())
    print(f"정상 랩 {len(j):,}개 · 결과: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
