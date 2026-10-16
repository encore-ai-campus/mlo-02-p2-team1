"""드라이버 교체 시나리오: 한 팀의 한 자리에 다른 드라이버를 앉히면 우승·포디움·포인트 확률이 어떻게 바뀌는가.

정제 결과(data/03_cleaned)와 추가 데이터(session_result)만으로 계산한다.

1) 경기별 레이스 페이스: 본경기에서 1랩·피트 인/아웃 랩·격리 행을 빼고, 그 경기 정상 랩 중앙값의 107%를 넘는 랩
   (세이프티카·VSC 등)도 뺀 뒤, 드라이버별 랩타임 중앙값이 그 경기 드라이버 중앙값들의 중앙값보다 몇 % 느린지(%)를 쓴다.
2) 차량·선수 효과 분리: 경기별 팀 평균 페이스 = 차량 효과, 팀 평균과의 차이(동료 대비)의 시즌 평균 = 선수 효과.
   선수 효과는 최근 3시즌을 함께 넣어 팀을 옮긴 선수로 팀 사이를 잇고, 표본이 적을수록 0 쪽으로 줄인다(SHRINK).
3) 시즌 재현: 그 시즌 각 경기를 "그 경기 차량 효과 + 선수 효과 + 경기 당일 변동"으로 다시 치른다.
   변동 크기(SIGMA)는 실제 라인업으로 돌렸을 때 실제 결과를 가장 잘 맞히는 값으로 정하고(로그우도 최대),
   완주 실패는 팀별 그 시즌 비완주율로 뽑는다.
4) 교체: 기준 선수와 후보가 자리를 맞바꾼다(후보는 기준 팀 차량, 기준 선수는 후보 팀 차량). 나머지는 그대로.

출력(data/05_gold/driver_swap/): scenarios.csv(후보별 우승·포디움·포인트·팀 순위 확률), race_detail.csv(후보별 경기별 확률),
calibration.csv(실제 라인업 재현 적중도), driver_effects.csv(선수·차량 효과), report.md.

    python -m pipeline.driver_swap                                   # 기본: 2025 Aston Martin Lance STROLL 자리
    python -m pipeline.driver_swap --year 2024 --team Ferrari --driver "Carlos SAINZ" --sims 5000
"""
from __future__ import annotations

import argparse, sys
from pathlib import Path

import numpy as np
import pandas as pd

from .validate_cleaned import DICT, ROOT, load_extra, num, read_csv

SHRINK = 3          # 선수 효과 축소: n경기 평균에 n/(n+SHRINK)를 곱함
MIN_LAPS = 5        # 경기별 페이스를 쓰는 최소 정상 랩 수
CUTOFF = 1.07       # 경기 정상 랩 중앙값 대비 이 배수를 넘는 랩은 SC·VSC 등으로 보고 제외
SIGMAS = np.round(np.arange(0.15, 1.51, 0.05), 2)  # 경기 당일 변동(%) 후보
SEED = 20261016


# ---------- 데이터 ----------
def load(cleaned: Path, extra):
    T = {name: read_csv(cleaned / "repaired" / f"{name}.csv", name) for name in ["sessions", "drivers", "laps", "pit"]}
    T.update({k: v for k, v in load_extra(extra).items() if k == "session_result"})
    return T


def race_pace(T, year):
    """경기 × 드라이버 레이스 페이스(%)와 팀."""
    s = T["sessions"]
    races = s[(s["session_type"] == "Race") & (s["year"] == str(year)) & (s["is_cancelled"] != "True")]
    races = races.assign(_d=pd.to_datetime(races["date_start"], format="ISO8601")).sort_values("_d")
    keys = list(races["session_key"])
    laps = T["laps"][T["laps"]["session_key"].isin(keys)].copy()
    laps["ld"], laps["ln"] = num(laps["lap_duration"]), num(laps["lap_number"])
    pit = T["pit"][T["pit"]["session_key"].isin(keys)]
    in_lap = set(zip(pit["session_key"], pit["driver_number"], pit["lap_number"].astype(str)))
    laps = laps[(laps["quarantine_flag"] != "Y") & (laps["ln"] > 1) & (laps["is_pit_out_lap"] != "True") & laps["ld"].notna()]
    laps = laps[[(k, d, str(int(n))) not in in_lap for k, d, n in zip(laps["session_key"], laps["driver_number"], laps["ln"])]]
    laps = laps[laps["ld"] <= laps.groupby("session_key")["ld"].transform("median") * CUTOFF]
    g = laps.groupby(["session_key", "driver_number"])["ld"]
    med = g.median()[g.size() >= MIN_LAPS].rename("median_lap").reset_index()
    med["pace"] = (med["median_lap"] / med.groupby("session_key")["median_lap"].transform("median") - 1) * 100
    team = T["drivers"][["session_key", "driver_number", "full_name", "team_name"]]
    return med.merge(team, on=["session_key", "driver_number"], how="left"), keys


def entries(T, keys, year):
    """경기별 출전자(결과 기준)·실제 순위·포인트·완주 여부."""
    sr = T["session_result"][T["session_result"]["session_key"].isin(keys)].copy()
    sr = sr[sr["dns"] != "True"]
    sr["finish"] = num(sr["position"])
    sr["classified"] = sr["finish"].notna() & (sr["dnf"] != "True") & (sr["dsq"] != "True")
    team = T["drivers"][["session_key", "driver_number", "full_name", "team_name"]]
    return sr.merge(team, on=["session_key", "driver_number"], how="left")[
        ["session_key", "driver_number", "full_name", "team_name", "finish", "classified"]]


def points_table(year):
    rules = pd.read_csv(DICT / "race_points_rules.csv", dtype={"year": str})
    rule = rules[rules["year"] == str(year)].set_index("position")["race_base_points"]
    out = np.zeros(40)
    for pos, pts in rule.items():
        out[int(pos) - 1] = float(pts)
    return out


# ---------- 효과 추정 ----------
def fit_effects(pace, iters=200):
    """페이스 = 경기·팀 차량 효과 + 선수 효과 (선수 효과는 SHRINK 경기만큼 0 쪽으로 축소).

    한 시즌 안에서는 동료끼리만 비교되지만, 여러 시즌을 함께 넣으면 팀을 옮긴 선수(예: SAINZ, HAMILTON)가
    팀 사이를 이어 주어 다른 팀 선수끼리도 같은 잣대로 비교된다. 교대 최소제곱으로 푼다.
    """
    p = pace.dropna(subset=["team_name", "full_name"]).copy()
    d = pd.Series(0.0, index=sorted(p["full_name"].unique()))
    for _ in range(iters):
        p["resid"] = p["pace"] - p["full_name"].map(d)
        p["car"] = p.groupby(["session_key", "team_name"])["resid"].transform("mean")
        g = (p["pace"] - p["car"]).groupby(p["full_name"])
        new = g.sum() / (g.size() + SHRINK)
        new -= new.mean()
        if (new - d).abs().max() < 1e-7:
            d = new
            break
        d = new
    p["resid"] = p["pace"] - p["full_name"].map(d)
    car = p.groupby(["session_key", "team_name"])["resid"].mean().rename("car").reset_index()
    races = p.groupby("full_name")["session_key"].nunique()
    return car, pd.DataFrame({"driver_effect": d, "paced_races": races.reindex(d.index).fillna(0).astype(int)})


def link_groups(pace):
    """같은 경기·같은 팀으로 한 번이라도 묶인 선수끼리 연결한 그룹. 다른 그룹 선수 사이의 비교는 데이터로 이어지지 않는다."""
    parent = {}

    def root(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for _, g in pace.dropna(subset=["team_name", "full_name"]).groupby(["session_key", "team_name"]):
        names = list(g["full_name"].unique())
        for a, b in zip(names, names[1:]):
            parent[root(a)] = root(b)
    members = {}
    for n in parent:
        members.setdefault(root(n), []).append(n)
    groups = sorted(members.values(), key=lambda m: (-len(m), sorted(m)[0]))
    return {n: f"G{i + 1}" for i, m in enumerate(groups) for n in m}


def effects(pace_all, keys, entry):
    """차량 효과(대상 시즌 경기×팀), 선수 효과(여러 시즌 연결), 팀 비완주율(대상 시즌)."""
    car, driver = fit_effects(pace_all)
    car = car[car["session_key"].isin(keys)]
    driver = driver.reindex(sorted(set(driver.index) | set(entry["full_name"].dropna()))).fillna({"driver_effect": 0.0, "paced_races": 0})
    driver["paced_races"] = driver["paced_races"].astype(int)
    driver["link_group"] = driver.index.map(link_groups(pace_all)).fillna("-")
    rel = entry.groupby("team_name")["classified"].mean()
    return car, driver, (1 - rel).rename("dnf_rate")


# ---------- 시뮬레이션 ----------
def build_grid(keys, entry, car, driver, dnf, seat_team, seat_driver, candidate):
    """경기별 (드라이버, 기대 페이스, 비완주율) 표. candidate가 있으면 기준 선수와 자리를 맞바꾼다."""
    cand_team = None
    if candidate:
        teams = entry.loc[entry["full_name"] == candidate, "team_name"]
        cand_team = teams.mode().iat[0] if len(teams) else None
    rows = []
    car_idx = car.set_index(["session_key", "team_name"])["car"]
    season_car = car.groupby("team_name")["car"].mean()
    for k in keys:
        e = entry[entry["session_key"] == k]
        for r in e.itertuples():
            name, team = r.full_name, r.team_name
            if candidate and name == seat_driver and cand_team:
                team = cand_team
            elif candidate and name == candidate:
                team = seat_team
            c = car_idx.get((k, team), season_car.get(team, np.nan))
            if pd.isna(c):
                continue
            rows.append((k, name, team, c + driver["driver_effect"].get(name, 0.0), dnf.get(team, 0.0)))
    return pd.DataFrame(rows, columns=["session_key", "full_name", "team_name", "expected_pace", "dnf_rate"])


def simulate(grid, keys, sigma, points, sims, seed):
    """경기마다 sims번: 페이스 + N(0, sigma), 비완주는 맨 뒤. 반환: 선수별 경기 결과 배열들."""
    rng = np.random.default_rng(seed)
    names = sorted(grid["full_name"].unique())
    idx = {n: i for i, n in enumerate(names)}
    wins = np.zeros((sims, len(names)))
    podiums = np.zeros((sims, len(names)))
    pts = np.zeros((sims, len(names)))
    per_race = []
    for k in keys:
        g = grid[grid["session_key"] == k]
        if g.empty:
            continue
        cols = g["full_name"].map(idx).to_numpy()
        pace = g["expected_pace"].to_numpy() + rng.normal(0, sigma, (sims, len(g)))
        out = rng.random((sims, len(g))) < g["dnf_rate"].to_numpy()
        pace = np.where(out, np.inf, pace)
        order = np.argsort(pace, axis=1, kind="stable")
        rank = np.empty_like(order)
        np.put_along_axis(rank, order, np.arange(len(g))[None, :].repeat(sims, 0), axis=1)
        race_pts = np.where(out, 0.0, points[np.minimum(rank, len(points) - 1)])
        wins[:, cols] += rank == 0
        podiums[:, cols] += (rank < 3) & ~out
        pts[:, cols] += race_pts
        per_race.append(pd.DataFrame({"session_key": k, "full_name": g["full_name"].to_numpy(), "team_name": g["team_name"].to_numpy(),
                                      "p_win": (rank == 0).mean(0), "p_podium": ((rank < 3) & ~out).mean(0),
                                      "expected_points": race_pts.mean(0), "expected_finish": (rank + 1).mean(0)}))
    return names, wins, podiums, pts, pd.concat(per_race, ignore_index=True)


def team_ranks(names, grid, pts):
    team_of = grid.groupby("full_name")["team_name"].agg(lambda s: s.mode().iat[0]).reindex(names)
    teams = sorted(team_of.unique())
    tp = np.stack([pts[:, (team_of == t).to_numpy()].sum(1) for t in teams], axis=1)
    # 동점은 무작위가 아니라 낮은 열 순서로 갈리지 않게 아주 작은 잡음으로 푼다
    rank = (-tp).argsort(1, kind="stable").argsort(1) + 1
    return teams, tp, rank


# ---------- 보정 ----------
def calibrate(keys, entry, car, driver, dnf, points, sims, seed):
    """실제 라인업으로 SIGMA 후보마다 재현해 실제 순위의 로그우도가 가장 큰 값을 고른다."""
    grid = build_grid(keys, entry, car, driver, dnf, None, None, None)
    actual = entry[entry["classified"]].set_index(["session_key", "full_name"])["finish"]
    rows = []
    for sigma in SIGMAS:
        _, _, _, _, race = simulate(grid, keys, sigma, points, sims, seed)
        winners = actual[actual == 1].reset_index()[["session_key", "full_name"]]
        w = race.merge(winners, on=["session_key", "full_name"])
        loglik = float(np.log(np.clip(w["p_win"], 1e-3, 1)).sum())
        race["won"] = [actual.get((k, n), 0) == 1 for k, n in zip(race["session_key"], race["full_name"])]
        brier = float(((race["p_win"] - race["won"]) ** 2).groupby(race["session_key"]).sum().mean())
        top = race.loc[race.groupby("session_key")["p_win"].idxmax()]
        hit = float(top["won"].mean())
        fin = race.merge(actual.rename("actual").reset_index(), on=["session_key", "full_name"])
        # 스피어만 = 순위끼리의 피어슨 (scipy 불필요)
        spearman = float(np.mean([g["expected_finish"].rank().corr(g["actual"].rank()) for _, g in fin.groupby("session_key")]))
        rows.append({"sigma": sigma, "winner_loglik": loglik, "brier_win": brier, "favourite_hit_rate": hit,
                     "mean_spearman_finish": spearman, "races": len(winners)})
    cal = pd.DataFrame(rows)
    sigma = float(cal.loc[cal["winner_loglik"].idxmax(), "sigma"])
    # 고른 σ로 팀별 기대 포인트와 실제 기본 포인트 비교
    names, _, _, pts, _ = simulate(grid, keys, sigma, points, sims, seed)
    teams, tp, _ = team_ranks(names, grid, pts)
    real = entry[entry["classified"]].assign(p=lambda x: points[x["finish"].astype(int).clip(upper=len(points)) - 1])
    real = real.groupby("team_name")["p"].sum()
    team_cal = pd.DataFrame({"team_name": teams, "expected_points": tp.mean(0), "actual_points": real.reindex(teams).fillna(0).to_numpy()})
    return sigma, cal, team_cal


# ---------- 실행 ----------
def run(year, seat_team, seat_driver, sims=4000, cleaned=None, extra=None, out=None, seed=SEED, window=3):
    cleaned = Path(cleaned or ROOT / "data" / "03_cleaned")
    out = Path(out or ROOT / "data" / "05_gold" / "driver_swap")
    if extra is None:
        folder, archive = ROOT / "data" / "01_raw" / "f1_extra_data", ROOT / "data" / "01_raw" / "f1_extra_data.zip"
        extra = folder if (folder / "session_result.csv").exists() else archive
    T = load(cleaned, extra)
    pace, keys = race_pace(T, year)
    entry = entries(T, keys, year)
    years = [y for y in range(year - window + 1, year + 1)]
    pace_all = pd.concat([pace] + [race_pace(T, y)[0] for y in years if y != year], ignore_index=True)
    if seat_driver not in set(entry.loc[entry["team_name"] == seat_team, "full_name"]):
        raise SystemExit(f"{year} {seat_team}에 {seat_driver} 출전 기록이 없습니다.")
    points = points_table(year)
    car, driver, dnf = effects(pace_all, keys, entry)
    sigma, cal, team_cal = calibrate(keys, entry, car, driver, dnf, points, max(500, sims // 4), seed)

    # 기준(실제 라인업)과 후보별 교체
    seat_races = entry[(entry["full_name"] == seat_driver)]["session_key"].nunique()
    cands = entry.groupby("full_name").agg(team_name=("team_name", lambda s: s.mode().iat[0]), races=("session_key", "nunique"))
    cands = cands[(cands["team_name"] != seat_team) & (cands["races"] >= seat_races / 2)].index
    scenarios, detail = [], []
    for cand in [None, *sorted(cands)]:
        grid = build_grid(keys, entry, car, driver, dnf, seat_team, seat_driver, cand)
        names, wins, podiums, pts, race = simulate(grid, keys, sigma, points, sims, seed)
        who = cand or seat_driver
        i = names.index(who)
        teams, tp, trank = team_ranks(names, grid, pts)
        ti = teams.index(seat_team)
        champ = (pts.argmax(1) == i).mean()
        scenarios.append({"scenario": "실제 라인업" if cand is None else f"{seat_driver} ↔ {cand}",
                          "seat_driver": who, "from_team": seat_team if cand is None else cands_team(entry, cand),
                          "driver_effect_pct": round(driver["driver_effect"].get(who, 0.0), 3),
                          "paced_races": int(driver["paced_races"].get(who, 0)),
                          "link_group": driver["link_group"].get(who, "-"),
                          "linked_to_seat": driver["link_group"].get(who, "-") == driver["link_group"].get(seat_driver, "?"),
                          "p_win_any": (wins[:, i] > 0).mean(), "expected_wins": wins[:, i].mean(),
                          "p_win_per_race": wins[:, i].mean() / len(keys), "p_podium_any": (podiums[:, i] > 0).mean(),
                          "expected_podiums": podiums[:, i].mean(), "expected_points": pts[:, i].mean(),
                          "p_driver_title": champ, "team_expected_points": tp[:, ti].mean(),
                          "team_expected_rank": trank[:, ti].mean(), "p_team_rank_le_6": (trank[:, ti] <= 6).mean(),
                          "p_team_rank_le_5": (trank[:, ti] <= 5).mean()})
        r = race[race["full_name"] == who].assign(scenario=scenarios[-1]["scenario"])
        detail.append(r)
    sc = pd.DataFrame(scenarios)
    base = sc.iloc[0]
    for col in ["expected_points", "team_expected_points", "p_win_any", "p_podium_any", "p_team_rank_le_6"]:
        sc[f"{col}_vs_base"] = sc[col] - base[col]
    sc = pd.concat([sc.iloc[:1], sc.iloc[1:].sort_values("expected_points", ascending=False)], ignore_index=True)

    out.mkdir(parents=True, exist_ok=True)
    sc.round(4).to_csv(out / "scenarios.csv", index=False, encoding="utf-8-sig")
    pd.concat(detail, ignore_index=True).round(4).to_csv(out / "race_detail.csv", index=False, encoding="utf-8-sig")
    cal.round(4).to_csv(out / "calibration.csv", index=False, encoding="utf-8-sig")
    team_cal.round(2).to_csv(out / "calibration_team_points.csv", index=False, encoding="utf-8-sig")
    eff = driver.reset_index(names="full_name").merge(
        entry.groupby("full_name")["team_name"].agg(lambda s: s.mode().iat[0]).rename("team_name").reset_index(), on="full_name")
    eff = eff.merge(car.groupby("team_name")["car"].mean().rename("car_effect_pct").reset_index(), on="team_name")
    eff = eff.merge(dnf.rename("team_dnf_rate").reset_index(), on="team_name")
    eff.sort_values("driver_effect").round(4).to_csv(
        out / "driver_effects.csv", index=False, encoding="utf-8-sig")
    meta = {"year": year, "seat_team": seat_team, "seat_driver": seat_driver, "races": len(keys), "sims": sims,
            "sigma": sigma, "paced_entries": len(pace), "effect_years": f"{years[0]}~{years[-1]}"}
    write_report(out / "report.md", meta, sc, cal, eff, team_cal)
    return meta, sc, cal


def cands_team(entry, name):
    return entry.loc[entry["full_name"] == name, "team_name"].mode().iat[0]


def pct(v):
    return f"{v * 100:.1f}%"


def write_report(path, meta, sc, cal, eff, team_cal):
    best = cal.loc[cal["sigma"] == meta["sigma"]].iloc[0]
    lines = [f"# 드라이버 교체 시나리오: {meta['year']} {meta['seat_team']} · {meta['seat_driver']} 자리", "",
             f"{meta['year']} 본경기 {meta['races']}경기를 경기마다 {meta['sims']:,}번 다시 치른 결과입니다. 선수 효과는 {meta['effect_years']} 시즌으로 추정했습니다. "
             f"기준 선수와 후보가 자리를 맞바꾼다고 가정합니다(후보는 {meta['seat_team']} 차량, 기준 선수는 후보 팀 차량).", "",
             "## 모델 적중도 (실제 라인업 재현)", "",
             f"경기 당일 변동 σ = {meta['sigma']}%(실제 우승자 로그우도 최대). 이 값으로 실제 라인업을 재현하면 "
             f"우승 확률이 가장 높은 선수가 실제 우승한 비율 {pct(best['favourite_hit_rate'])}, "
             f"경기별 예상 순위와 실제 순위의 스피어만 상관 평균 {best['mean_spearman_finish']:.2f}, 우승 Brier {best['brier_win']:.3f}입니다.", "",
             f"팀별 기대 포인트와 실제 기본 포인트의 상관 {team_cal['expected_points'].corr(team_cal['actual_points']):.2f}, "
             f"평균 절대 오차 {(team_cal['expected_points'] - team_cal['actual_points']).abs().mean():.1f}점입니다.", "",
             "| 팀 | 기대 포인트 | 실제 기본 포인트 |", "|---|---:|---:|",
             *[f"| {r.team_name} | {r.expected_points:.1f} | {r.actual_points:.0f} |" for r in team_cal.sort_values("actual_points", ascending=False).itertuples()],
             "", "## 후보별 결과", "",
             "| 시나리오 | 원래 팀 | 연결 그룹 | 선수 효과(%) | 시즌 1승 이상 | 기대 승수 | 포디움 1회 이상 | 기대 포인트 | 드라이버 챔피언 | 팀 기대 포인트 | 팀 기대 순위 | 팀 6위 이내 |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in sc.itertuples():
        lines.append(f"| {r.scenario} | {r.from_team} | {r.link_group}{'' if r.linked_to_seat else ' *'} | {r.driver_effect_pct:+.3f} | {pct(r.p_win_any)} | {r.expected_wins:.2f} | "
                     f"{pct(r.p_podium_any)} | {r.expected_points:.1f} | {pct(r.p_driver_title)} | {r.team_expected_points:.1f} | "
                     f"{r.team_expected_rank:.2f} | {pct(r.p_team_rank_le_6)} |")
    lines += ["", "선수 효과: 차량 효과를 뺀 레이스 페이스(%, 음수일수록 빠름, 전체 평균 0). 여러 시즌 팀 이동으로 팀 간 비교가 이어지며, 경기 수가 적으면 0 쪽으로 줄임. "
              "`*` = 기준 선수와 다른 연결 그룹(직접 비교 근거 없음, 아래 표 참고).", "",
              "## 비교 연결 그룹", "",
              "같은 경기·같은 팀으로 한 번이라도 함께 달린 선수끼리 이은 그룹입니다. **다른 그룹 선수 사이의 차이는 데이터로 직접 연결되지 않고**, "
              "각 그룹의 평균이 전체 평균과 같다는 가정(축소·중심화)으로만 비교됩니다.", "",
              "| 그룹 | 선수 |", "|---|---|",
              *[f"| {g} | {', '.join(sorted(m['full_name']))} |" for g, m in eff.groupby("link_group")],
              "", "## 해석할 때 주의", "",
              "- 선수 효과는 동료 비교와 팀 이동으로만 연결된다. 팀을 옮긴 선수가 적은 구간은 비교가 약하고, 선수 기량은 3시즌 동안 같다고 가정한다.",
              "- 차량 효과는 그 경기에서 관측된 팀 평균이다. 다른 선수가 타면 차량 개발·전략이 달라지는 효과는 넣지 않았다.",
              "- 출발 순위·추월 난이도·전략·세이프티카는 따로 모델링하지 않고 경기 당일 변동 σ 하나에 담았다.",
              "- 비완주는 팀(차량) 비완주율로 뽑는다. 선수 실수로 인한 리타이어 차이는 반영하지 않는다.",
              "- 확률은 '이 가정이 맞다면'의 값이며, 영입 후 실제 성적을 보장하지 않는다."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--team", default="Aston Martin")
    parser.add_argument("--driver", default="Lance STROLL")
    parser.add_argument("--sims", type=int, default=4000)
    parser.add_argument("--cleaned", default=None)
    parser.add_argument("--extra", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--window", type=int, default=3, help="선수 효과를 추정할 시즌 수(대상 시즌 포함, 팀 이동으로 팀 간 연결)")
    args = parser.parse_args()
    meta, sc, cal = run(args.year, args.team, args.driver, args.sims, args.cleaned, args.extra, args.out, window=args.window)
    cols = ["scenario", "p_win_any", "expected_wins", "p_podium_any", "expected_points", "team_expected_points", "team_expected_rank"]
    print(f"σ={meta['sigma']}% · {meta['races']}경기 · {meta['sims']:,}회")
    print(sc[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
