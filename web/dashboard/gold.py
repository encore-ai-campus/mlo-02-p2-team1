"""MySQL 설계 스키마(sql/04·05) → Decision Board용 Gold 지표.

규칙은 tools/f1_report/analysis_enriched.py · analysis_pitloss.py와 같다.
- 클린 랩: 1랩·피트 아웃/인 랩·격리 행 제외, race_control의 SC·VSC·적기 구간 제외, 드라이버 경기 중앙값 107% 이상 제외, 경기당 15랩 이상
- 기본(6종) 비교용: SC 구간 대신 105% 규칙만 적용
- 포인트: session_result.race_base_points (05에서 기본 배점표로 계산된 값)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from django.conf import settings
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

TEAM = "Aston Martin"
TOP4 = ["McLaren", "Ferrari", "Mercedes", "Red Bull Racing"]
SEASON = 2025
# 기획서 2.5절: 분석에 쓰지 않는 컬럼·파일의 진단코드
OUT_OF_SCOPE_CODES = ["DQ001", "DQ003", "DQ005", "DQ024", "DQ023"]
LINEAGE = {"AlphaTauri": "Racing Bulls", "RB": "Racing Bulls", "Alfa Romeo": "Sauber / Audi",
           "Kick Sauber": "Sauber / Audi", "Audi": "Sauber / Audi"}


def engine():
    db = settings.DATABASES["default"]
    return create_engine(URL.create("mysql+pymysql", username=db["USER"], password=db["PASSWORD"],
                                    host=db["HOST"], port=int(db["PORT"]), database=db["NAME"],
                                    query={"charset": "utf8mb4"}))


def _f(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def neutralised_windows(rc: pd.DataFrame) -> pd.DataFrame:
    """race_control 메시지로 SC·VSC·적기 랩 구간(선두 랩 기준)을 만든다."""
    win = []
    rc = rc.dropna(subset=["lap_number"]).sort_values(["session_key", "recorded_at"])
    for sk, g in rc.groupby("session_key"):
        op = {}
        for r in g.itertuples():
            m, lap = str(r.message).upper(), int(r.lap_number)
            if m.startswith("SAFETY CAR DEPLOYED"):
                op["SC"] = lap
            elif m.startswith("SAFETY CAR IN THIS LAP") and "SC" in op:
                win.append((sk, op.pop("SC"), lap + 1, "SC"))
            elif m.startswith(("VIRTUAL SAFETY CAR DEPLOYED", "VSC DEPLOYED")):
                op["VSC"] = lap
            elif m.startswith(("VIRTUAL SAFETY CAR ENDING", "VSC ENDING")) and "VSC" in op:
                win.append((sk, op.pop("VSC"), lap + 1, "VSC"))
            elif str(r.flag).upper() == "RED":
                win.append((sk, lap, lap + 2, "RED"))
        for k, v in op.items():
            win.append((sk, v, v + 3, k))
    return pd.DataFrame(win, columns=["session_key", "a", "b", "kind"])


def build(log=print) -> dict:
    eng = engine()
    q = lambda sql: pd.read_sql(sql, eng)
    log("원천 읽는 중 (MySQL f1_db)")
    s = q("SELECT session_key, meeting_key, year FROM session WHERE session_type = 'Race'")
    d = q("""SELECT sd.session_key, sd.driver_number, sd.team_name, dr.full_name, dr.name_acronym
             FROM session_driver sd JOIN driver dr ON dr.driver_id = sd.driver_id""")
    L = _f(q("""SELECT session_key, driver_number, lap_number, lap_duration, is_pit_out_lap, date_start
                FROM lap WHERE quarantine_flag = 'N'"""), ["lap_duration"])
    st = q("SELECT session_key, driver_number, stint_number, compound, lap_start, lap_end FROM stint")
    p = _f(q("""SELECT session_key, driver_number, lap_number, lane_duration, stop_duration
                FROM pit_event WHERE quarantine_flag = 'N'"""), ["lane_duration", "stop_duration"])
    rc = q("SELECT session_key, recorded_at, lap_number, flag, message FROM race_control_event")
    res = _f(q("""SELECT r.session_key, r.driver_number, r.finish_position, r.dnf, r.dns, r.dsq,
                         r.source_points, r.race_base_points, g.grid_position
                  FROM session_result r
                  LEFT JOIN starting_grid g ON g.race_session_key = r.session_key AND g.driver_number = r.driver_number"""),
             ["source_points", "race_base_points", "finish_position", "grid_position"])
    races = set(s.session_key)
    L_full = L.copy()  # 피트 인 랩 시각이 필요한 피트 손실 계산용 (클린 랩 필터 전)
    out: dict = {}

    # ---------- 클린 랩 ----------
    W = neutralised_windows(rc)
    W = W[W.session_key.isin(races)]
    L = L[(L.lap_number > 1) & (L.is_pit_out_lap.fillna(0) == 0) & L.lap_duration.notna()]
    pin = p[["session_key", "driver_number", "lap_number"]].drop_duplicates().assign(pit=1)
    L = L.merge(pin, how="left", on=["session_key", "driver_number", "lap_number"])
    L = L[L.pit.isna()].drop(columns="pit")
    mm = L[["session_key", "driver_number", "lap_number"]].merge(W, on="session_key")
    mm = mm[(mm.lap_number >= mm.a) & (mm.lap_number <= mm.b)][["session_key", "driver_number", "lap_number"]].drop_duplicates()
    L = L.merge(mm.assign(neut=True), how="left", on=["session_key", "driver_number", "lap_number"])
    L["neut"] = L.neut.eq(True)
    med = L.groupby(["session_key", "driver_number"]).lap_duration.transform("median")
    basic = L[L.lap_duration < med * 1.05]
    enr = L[~L.neut].copy()
    enr = enr[enr.lap_duration < enr.groupby(["session_key", "driver_number"]).lap_duration.transform("median") * 1.07]
    out["cleanLaps"] = {"basic_105": int(len(basic)), "enriched_sc": int(len(enr)), "neutralised_laps": int(L.neut.sum())}
    out["neutralised"] = {"races_with_window": int(W.session_key.nunique()), "windows": W.kind.value_counts().to_dict()}

    def race_level(LL):
        g = LL.groupby(["session_key", "driver_number"]).lap_duration.agg(
            m="median", q1=lambda x: x.quantile(.25), q3=lambda x: x.quantile(.75), n="size").reset_index()
        g = g[g.n >= 15].copy()
        g["pct"] = (g.m / g.groupby("session_key").m.transform("median") - 1) * 100
        g["iqr"] = g.q3 - g.q1
        return g.merge(d, on=["session_key", "driver_number"]).merge(s, on="session_key")

    log("페이스 지표 계산")
    B, E = race_level(basic), race_level(enr)
    team_season = lambda g: g.groupby(["year", "session_key", "team_name"]).pct.median().reset_index().groupby(["year", "team_name"]).pct.median()
    tb, te = team_season(B), team_season(E)
    years = sorted(int(y) for y in s.year.unique())
    out["paceBasicVsEnriched"] = {str(y): [round(float(tb.get((y, TEAM), np.nan)), 3), round(float(te.get((y, TEAM), np.nan)), 3)] for y in years}
    lines: dict = {}
    for (y, t), v in te.items():
        lines.setdefault(LINEAGE.get(t, t), {})[str(y)] = round(float(v), 3)
    lines.pop("Cadillac", None)
    out["lines"] = lines
    out["fieldSpread"] = {str(y): round(float(te.loc[y].max() - te.loc[y].min()), 3) for y in years}
    rk = E[E.year == SEASON].groupby(["session_key", "team_name"]).pct.median().reset_index()
    rk["r"] = rk.groupby("session_key").pct.rank()
    amr = rk[rk.team_name == TEAM]
    out["amRank"] = {"faster_than_field": int((amr.pct < 0).sum()), "races": int(len(amr)), "median_rank": float(amr.r.median())}

    # ---------- 드라이버 ----------
    E25 = E[E.year == SEASON]
    tm = E25.merge(E25[["session_key", "team_name", "driver_number", "m"]], on=["session_key", "team_name"], suffixes=("", "_tm"))
    tm = tm[tm.driver_number != tm.driver_number_tm]
    tmg = tm.assign(gap=tm.m - tm.m_tm).groupby("full_name").agg(tm_gap=("gap", "median"))
    dr = E25.groupby("full_name").agg(acr=("name_acronym", "first"), team=("team_name", lambda x: x.mode()[0]),
                                     races=("session_key", "nunique"), laps=("n", "sum"), pace=("pct", "median"), iqr=("iqr", "median")).join(tmg)
    h = E25[E25.team_name == TEAM].pivot_table(index="session_key", columns="name_acronym", values="m").dropna()
    out["h2h"] = {"races": int(len(h)), "alo_faster": int((h.ALO < h.STR).sum()), "median_gap_s": round(float((h.STR - h.ALO).median()), 3)}

    log("타이어 기울기 계산")
    Ls = enr.merge(st, on=["session_key", "driver_number"])
    Ls = Ls[(Ls.lap_number >= Ls.lap_start) & (Ls.lap_number <= Ls.lap_end)]
    def slope(g):
        return np.polyfit(g.lap_number - g.lap_start, g.lap_duration, 1)[0] if len(g) >= 10 else np.nan
    sl = Ls.groupby(["session_key", "driver_number", "stint_number", "compound"]).apply(slope, include_groups=False).dropna().rename("slope").reset_index()
    sl = sl[sl.slope.between(-0.5, 0.5)].copy()
    sl["rel"] = sl.slope - sl.groupby(["session_key", "compound"]).slope.transform("median")
    sl = sl.merge(d, on=["session_key", "driver_number"]).merge(s[["session_key", "year"]], on="session_key")
    dr = dr.join(sl[sl.year == SEASON].groupby("full_name").rel.median().rename("tyre"))
    team_tyre = sl[sl.year == SEASON].groupby("team_name").rel.median()

    # ---------- 결과·포인트 ----------
    res = res[res.session_key.isin(races)].merge(s[["session_key", "year"]], on="session_key").merge(d, on=["session_key", "driver_number"], how="left")
    for c in ["dnf", "dns", "dsq"]:
        res[c] = res[c].fillna(0).astype(int).astype(bool)
    res["gain"] = res.grid_position - res.finish_position
    mism = res.groupby("session_key").apply(lambda g: (g.source_points.fillna(0) - g.race_base_points.fillna(0)).abs().sum(), include_groups=False)
    bad = s[s.session_key.isin(mism[mism > 1].index)]
    out["pointsCheck"] = {"races": int(len(races)), "recalculated": int(res.session_key.nunique()),
                          "sourceMismatch": [{"session_key": int(r.session_key), "race": f"{int(r.year)} #{int(r.session_key)}"} for r in bad.itertuples()]}
    y25 = res[res.year == SEASON]
    pts = y25.groupby("team_name").race_base_points.sum().sort_values(ascending=False)
    out["teamPoints25"] = {k: int(v) for k, v in pts.items()}
    dres = y25.groupby("full_name").apply(lambda g: pd.Series({"pts": int(g.race_base_points.sum()), "starts": int((~g.dns).sum()),
                                                               "gain": g.gain.mean(), "dnf": int(g.dnf.sum())}), include_groups=False)
    dr = dr.join(dres)
    dr = dr[dr.races >= 8].copy()
    def top(col, asc):
        return (dr[col].rank(ascending=asc, method="min") / dr[col].notna().sum() * 100).round(0)
    dr["paceTop"], dr["tmTop"], dr["iqrTop"] = top("pace", True), top("tm_gap", True), top("iqr", True)
    dr["tyreTop"], dr["ptsTop"] = top("tyre", True), top("pts", False)
    am = y25[y25.team_name == TEAM]
    out["amResults25"] = {"pts": int(am.race_base_points.sum()), "avg_gain": round(float(am.gain.mean()), 2),
                          "dnf": int(am.dnf.sum()), "starts": int((~am.dns).sum())}
    g_all = q("SELECT COUNT(*) n, SUM(race_session_key IS NOT NULL) mapped FROM starting_grid").iloc[0]
    out["gridMapping"] = {"rows": int(g_all.n), "mapped": int(g_all.mapped)}

    def nz(v, nd=4):
        return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), nd)
    drivers = []
    for name, r in dr.sort_values("pace").iterrows():
        first, last = name.split(" ", 1)
        drivers.append(dict(n=f"{first} {last.capitalize()}", s=last.capitalize(), a=r.acr, t=r.team, r=int(r.races), l=int(r.laps),
                            pace=nz(r.pace, 3), paceTop=nz(r.paceTop, 0), tm=nz(r.tm_gap, 3), tmTop=nz(r.tmTop, 0),
                            iqr=nz(r.iqr, 3), iqrTop=nz(r.iqrTop, 0), tyre=nz(r.tyre * 1000 if pd.notna(r.tyre) else None, 1), tyreTop=nz(r.tyreTop, 0),
                            pts=int(r.pts), ptsTop=nz(r.ptsTop, 0), gain=nz(r.gain, 2), dnf=int(r.dnf), starts=int(r.starts)))
    out["drivers25"] = drivers

    # ---------- 팀 피트·전략 ----------
    log("피트 지표 계산 (position · intervals)")
    starters = y25[~y25.dns][["session_key", "driver_number", "team_name"]]
    pc = p.groupby(["session_key", "driver_number"]).size().rename("stops").reset_index()
    pc = starters.merge(pc, on=["session_key", "driver_number"], how="left").fillna({"stops": 0})
    pc["b"] = pc.stops.clip(upper=3).astype(int)
    dist = pc.groupby("team_name").b.value_counts(normalize=True).unstack(fill_value=0).mul(100).round(1)
    stl = st.merge(s, on="session_key").merge(d, on=["session_key", "driver_number"])
    stl = stl[stl.year == SEASON].assign(len=lambda x: x.lap_end - x.lap_start + 1)
    t25 = te.loc[SEASON]
    teams = {}
    for t in sorted(pc.team_name.dropna().unique()):
        teams[t] = dict(stops=round(float(pc[pc.team_name == t].stops.mean()), 2), dist=[float(dist.loc[t].get(i, 0)) for i in range(4)],
                        n=int((pc.team_name == t).sum()), stint=float(stl[stl.team_name == t]["len"].median()),
                        tyre=round(float(team_tyre.get(t, np.nan)) * 1000, 1), pace=round(float(t25.get(t, np.nan)), 3), pts=int(pts.get(t, 0)))
    out["teams25"] = teams
    out["pitLoss"] = pit_loss(eng, s, d, L_full, p, W)

    # 정지시간 (stop_duration 제공분만, 0으로 채우지 않음)
    p25 = p.merge(s, on="session_key").merge(d, on=["session_key", "driver_number"])
    p25 = p25[(p25.year == SEASON) & p25.stop_duration.notna()]
    stop = p25.groupby("team_name").stop_duration.agg(sm="median", o4=lambda x: (x > 4).mean() * 100)

    # ---------- 품질 범위 (기획서 2.5절) ----------
    qi = q("SELECT diagnostic_code, status FROM quality_issue")
    ins = qi[~qi.diagnostic_code.isin(OUT_OF_SCOPE_CODES)]
    stc = ins.status.str.upper().value_counts()
    quar = int(q("SELECT COUNT(*) n FROM pit_event WHERE quarantine_flag = 'Y'").n.iloc[0])
    out["scope"] = {"inScope": {"detected": int(len(ins)), "repaired": int(stc.get("REPAIRED", 0)), "accepted": int(stc.get("ACCEPTED", 0)),
                                "open": int(stc.get("OPEN", 0)), "quarantined": quar},
                    "excluded": {"detected": int(len(qi) - len(ins))}}
    man = q("SELECT checksum FROM stg_bronze_manifest")
    out["checksum"] = f"{int((man.checksum == 'MATCH').sum())} / {len(man)}"
    out["extraAudit"] = {"lines": audit_lines(q)}

    payload = {"team": TEAM, "top4": TOP4, "season": SEASON,
               "teams25": [{"t": t, "sm": round(float(r.sm), 2)} for t, r in stop.iterrows()],
               "stopOver4": {t: round(float(r.o4), 1) for t, r in stop.iterrows()},
               "pitSlow": [[t, v["slow_pct"]] for t, v in out["pitLoss"]["pitGreen"].items()],
               "enriched": out}
    return payload


def pit_loss(eng, s, d, L, p, W) -> dict:
    """position · intervals로 2025 피트 스톱 전후 순위·시간 손실을 잰다."""
    k25 = tuple(int(x) for x in s[s.year == SEASON].session_key)
    keys = ",".join(map(str, k25))
    po = pd.read_sql(f"SELECT session_key, driver_number, recorded_at t, position FROM position_event WHERE session_key IN ({keys}) AND position BETWEEN 1 AND 22", eng)
    iv = pd.read_sql(f"SELECT session_key, driver_number, recorded_at t, gap_to_leader g FROM interval_event WHERE session_key IN ({keys}) AND gap_to_leader IS NOT NULL", eng)
    iv["g"] = pd.to_numeric(iv.g)
    po, iv = po.sort_values("t"), iv.sort_values("t")
    pog = {k: g for k, g in po.groupby(["session_key", "driver_number"])}
    ivg = {k: g for k, g in iv.groupby(["session_key", "driver_number"])}
    def at(groups, k, t, col):
        g = groups.get(k)
        if g is None:
            return np.nan
        g = g[g.t <= t]
        return g[col].iloc[-1] if len(g) else np.nan
    lt_all = L[L.session_key.isin(k25)].set_index(["session_key", "driver_number", "lap_number"]).date_start
    p25 = p[p.session_key.isin(k25)]
    pits = set(zip(p25.session_key, p25.driver_number, p25.lap_number))
    rows = []
    for r in p25.itertuples():
        t0, t1 = lt_all.get((r.session_key, r.driver_number, r.lap_number)), lt_all.get((r.session_key, r.driver_number, r.lap_number + 2))
        if t0 is None or t1 is None or pd.isna(t0) or pd.isna(t1):
            continue
        w = W[(W.session_key == r.session_key) & (W.a <= r.lap_number) & (W.b >= r.lap_number)]
        k = (r.session_key, r.driver_number)
        rows.append((r.session_key, r.driver_number, r.lap_number, r.lane_duration, at(pog, k, t0, "position"), at(pog, k, t1, "position"), len(w) > 0, t0, t1))
    E = pd.DataFrame(rows, columns=["session_key", "driver_number", "lap", "lane", "before", "after", "neut", "t0", "t1"]).dropna(subset=["before", "after"])
    E["lost"] = E.after - E.before
    E = E.merge(d, on=["session_key", "driver_number"])
    E = E[E.lane.between(10, 60)].copy()
    E["lane_rel"] = E.lane - E.groupby("session_key").lane.transform("median")
    green = E[~E.neut]
    team = green.groupby("team_name").lost.mean().round(2)
    am = green[green.team_name == TEAM]
    # 시간 손실: 본인 선두 격차 변화 − 같은 구간에 피트하지 않은 차들의 격차 변화 중앙값
    tl = []
    for r in green.itertuples():
        dg = at(ivg, (r.session_key, r.driver_number), r.t1, "g") - at(ivg, (r.session_key, r.driver_number), r.t0, "g")
        others = []
        for dn in po[po.session_key == r.session_key].driver_number.unique():
            if dn == r.driver_number or any((r.session_key, dn, l) in pits for l in range(r.lap - 1, r.lap + 3)):
                continue
            o = at(ivg, (r.session_key, dn), r.t1, "g") - at(ivg, (r.session_key, dn), r.t0, "g")
            if not np.isnan(o):
                others.append(o)
        if not np.isnan(dg) and len(others) >= 3:
            tl.append((r.team_name, dg - np.median(others), r.lane_rel))
    TL = pd.DataFrame(tl, columns=["team_name", "loss", "lane_rel"])
    TL = TL[TL.loss.between(0, 60)]
    return {
        "teams": {t: {"lost": float(v)} for t, v in team.items()},
        "am": {"n": int(len(am)), "lost_slow": round(float(am[am.lane_rel > 1].lost.mean()), 2), "lost_norm": round(float(am[am.lane_rel <= 1].lost.mean()), 2)},
        "neut_lost_mean": round(float(E[E.neut].lost.mean()), 2),
        "timeLoss": {"n": int(len(TL)), "teams": TL.groupby("team_name").loss.median().round(1).to_dict(),
                     "slow_vs_normal_s": [round(float(TL[TL.lane_rel > 1].loss.median()), 1), round(float(TL[TL.lane_rel <= 1].loss.median()), 1)]},
        "pitGreen": {t: {"slow_pct": round(float((g.lane_rel > 1).mean() * 100), 1), "lane_rel_med": round(float(g.lane_rel.median()), 2),
                         "lane_rel_q1": round(float(g.lane_rel.quantile(.25)), 2), "lane_rel_q3": round(float(g.lane_rel.quantile(.75)), 2), "n": int(len(g))}
                     for t, g in green.groupby("team_name")},
    }


def audit_lines(q) -> list[str]:
    a = q("""SELECT SUM(finish_position IS NULL AND dnf = 0 AND dns = 0 AND dsq = 0) unflagged,
                    SUM(dnf = 1 AND finish_position IS NOT NULL) dnf_classified FROM session_result""").iloc[0]
    g = int(q("""SELECT COUNT(*) n FROM session_result r LEFT JOIN starting_grid g
                 ON g.race_session_key = r.session_key AND g.driver_number = r.driver_number
                 WHERE g.driver_number IS NULL AND r.dns = 0""").n.iloc[0])
    po = int(q("SELECT COUNT(*) n FROM position_event WHERE position > 22 OR position < 1").n.iloc[0])
    iv = int(q("SELECT COUNT(*) n FROM interval_event WHERE gap_to_leader_laps IS NOT NULL").n.iloc[0])
    return [f"session_result: 순위가 비었는데 DNF·DNS·DSQ 표시가 없는 {int(a.unflagged)}건 → 미분류로 처리",
            f"session_result: DNF인데 순위가 있는 {int(a.dnf_classified)}건 → 규정상 완주 인정, 순위대로 포인트",
            f"starting_grid: 출발 순위 없는 결승 출전 {g}건 → 순위 변화 N/A",
            f"position: 출전 대수를 넘는 순위 값 {po}건 → 제외",
            f"intervals: 선두와 랩 차이로 표시된 {iv:,}건(“+1 LAP” 등) → 초 단위 계산에서 제외"]
