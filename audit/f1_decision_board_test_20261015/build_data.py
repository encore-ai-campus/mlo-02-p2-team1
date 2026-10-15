"""Expand the frozen final-spec analysis to every observed season/team/seat.

No repair or metric definition changes; reads prior final-analysis outputs only.
All new artifacts stay under this test folder.
"""
from pathlib import Path
import json,hashlib,importlib.util,sys
import numpy as np
import pandas as pd
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent
SRC=O.parent/'f1_final_analysis_20261015'
VARIANTS=['baseline','weather60','weather120','age_matched_reference','reference3laps','exclude_repaired','restart_plus1lap','teammate_age1lap','traffic_free','min20laps_10races','exclude_uncertain_event_races']
spec=importlib.util.spec_from_file_location('frozen_final_analysis',SRC/'analyze_final.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
def frame(p):return pd.read_csv(SRC/p,dtype={'session_key':str})
def records(df):return json.loads(df.to_json(orient='records',force_ascii=False,date_format='iso'))
def finite(v):return v is not None and pd.notna(v) and np.isfinite(v)
def f(v):return float(v) if finite(v) else None
def median(v):return float(np.median(v)) if len(v) else None
def clean(o):
    if isinstance(o,dict):return {str(k):clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)):return [clean(v) for v in o]
    if isinstance(o,(np.bool_,)):return bool(o)
    if isinstance(o,(np.integer,)):return int(o)
    if isinstance(o,(float,np.floating)):return float(o) if np.isfinite(o) else None
    return o
def main():
    print('Reading frozen metrics for all four seasons',flush=True)
    profiles=frame('gold/gold_driver_profile.csv')
    profiles=profiles[profiles.current_segment.eq(True)].copy()
    team=frame('gold/gold_team_profile.csv');teamrace=frame('checks/team_race_metrics.csv')
    outcome=frame('silver/silver_driver_race.csv');coverage=frame('checks/coverage.csv')
    pairs=frame('silver/silver_teammate_comparison.csv');tyre=frame('gold/gold_tyre_performance.csv')
    pit=frame('silver/silver_pit_event.csv');membership=frame('silver/silver_team_membership.csv')
    race_groups={};prof_groups={};own_group={}
    for variant in VARIANTS:
        r=frame(f'checks/scenarios/{variant}_race_metrics.csv')
        p=frame(f'checks/scenarios/{variant}_profiles.csv')
        race_groups[variant]={mid:{str(row.session_key):row for row in g.itertuples()} for mid,g in r.groupby('membership_id')}
        prof_groups[variant]={row.membership_id:row for row in p.itertuples()}
    for mid,g in pairs.groupby('membership_id'):own_group[mid]=g.teammate_delta_sec.to_numpy(float)
    own_cis={}
    for r in profiles.itertuples():
        own=own_group.get(r.membership_id,np.array([]))
        ci=analysis.bootstrap(own,('own',r.year,r.membership_id)) if len(own)>=5 else (None,None,None)
        own_cis[r.membership_id]={'own_low':f(ci[0]),'own_high':f(ci[1]),'own_races':len(own)}
    profiles['own_low']=profiles.membership_id.map(lambda k:own_cis[k]['own_low'])
    profiles['own_high']=profiles.membership_id.map(lambda k:own_cis[k]['own_high'])
    profiles['own_races']=profiles.membership_id.map(lambda k:own_cis[k]['own_races'])
    # Supplement team facts without interpreting event counts as strategy quality.
    team_extra=[]
    for (year,tname),tg in team.groupby(['year','team_name']):
        yr=outcome[outcome.year.eq(year)&outcome.team_name.eq(tname)]
        valid_counts=yr[yr.pit_count_eligible.eq(True)].pit_event_count
        grid=yr.grid_change.dropna()
        ty=tyre[tyre.year.eq(year)&tyre.team_name.eq(tname)]
        meta=dict(year=int(year),team_name=tname,pit_denominator=len(valid_counts),pit_zero_count=int(valid_counts.eq(0).sum()),pit_1=int(valid_counts.eq(1).sum()),pit_2=int(valid_counts.eq(2).sum()),pit_3plus=int(valid_counts.ge(3).sum()),grid_change_mean=f(grid.mean()),grid_change_rows=len(grid),tyre_valid_races=ty.session_key.nunique(),source_races=yr.session_key.nunique(),source_driver_rows=len(yr),source_started=int(yr.started.sum()),classification_unknown=int(yr.classification_status.eq('UNKNOWN').sum()))
        team_extra.append(meta)
    team=team.merge(pd.DataFrame(team_extra),on=['year','team_name'],how='left',validate='one_to_one')
    # Same-race pit comparison. A source-present race is still not proof of complete collection.
    pit_enrich=[]
    for (year,sk),g in pit.groupby(['year','session_key']):
        valid=g[g.lane_benchmark_eligible.eq(True)]
        med=valid.groupby('team_name').lane_sec.median()
        if len(med)<5:continue
        for tn,gg in valid.groupby('team_name'):
            peers=med.drop(index=tn)
            if len(peers)<4:continue
            delta=gg.lane_sec-peers.median()
            pit_enrich.append(dict(year=int(year),session_key=sk,team_name=tn,observed_events=len(gg),slow_events=int(delta.gt(1).sum())))
    pe=pd.DataFrame(pit_enrich)
    slow=pe.groupby(['year','team_name']).agg(slow_events=('slow_events','sum'),pit_comparable_events=('observed_events','sum')).reset_index()
    slow['slow_pit_pct']=100*slow.slow_events/slow.pit_comparable_events
    team=team.merge(slow,on=['year','team_name'],how='left',validate='one_to_one')
    start_by_sk=coverage.set_index('session_key').date_start.to_dict()
    midpoint={int(y):g.sort_values('date_start').date_start.iloc[len(g)//2] for y,g in coverage.groupby('year')}
    tyre_groups={mid:g.groupby(['session_key','compound']).field_adjusted_slope_sec_per_lap.median().to_dict() for mid,g in tyre.groupby('membership_id')}
    cases={};count=0
    for year,players in profiles.groupby('year'):
        print(f'Expanding {int(year)}: {len(players)} observed players',flush=True)
        for seat in players.itertuples():
            for cand in players[players.team_name.ne(seat.team_name)].itertuples():
                mid_a=cand.membership_id;mid_b=seat.membership_id
                key=mid_b+'>>'+mid_a
                scenarios=[];base_common=[];base_delta=[];base_quality=False;first=None;second=None
                own_negative=0;own_missing=0
                for name in VARIANTS:
                    a=race_groups[name].get(mid_a,{});b=race_groups[name].get(mid_b,{})
                    common=sorted(a.keys()&b.keys(),key=lambda sk:start_by_sk.get(sk,''))
                    cp=prof_groups[name].get(mid_a);sp=prof_groups[name].get(mid_b)
                    minraces=10 if name=='min20laps_10races' else 8
                    quality=bool(cp is not None and sp is not None and cp.eligible and sp.eligible and len(common)>=minraces)
                    diff=[float(a[k].relative_pace_pct-b[k].relative_pace_pct) for k in common]
                    delta=median(diff) if quality else None
                    own=f(cp.teammate_delta_sec) if cp is not None else None
                    if own is None:own_missing+=1
                    elif own<0:own_negative+=1
                    scenarios.append([delta,len(common),own,quality])
                    if name=='baseline':
                        base_common=[[k,d,float(a[k].relative_pace_pct),float(b[k].relative_pace_pct)] for k,d in zip(common,diff)]
                        base_delta=diff;base_quality=quality
                        h1=[d for k,d in zip(common,diff) if start_by_sk.get(k,'')<midpoint[int(year)]]
                        h2=[d for k,d in zip(common,diff) if start_by_sk.get(k,'')>=midpoint[int(year)]]
                        first=median(h1) if quality and len(h1)>=4 else None
                        second=median(h2) if quality and len(h2)>=4 else None
                ci=analysis.bootstrap(base_delta,('pair',int(year),*sorted([mid_a,mid_b]))) if base_quality else (None,None,None)
                low,high=f(ci[0]),f(ci[1])
                values=[r[0] for r in scenarios if r[0] is not None]
                faster=sum(v<0 for v in values);missing=len(VARIANTS)-len(values)
                own_ci=own_cis[mid_a]
                stable=bool(base_quality and not missing and faster==len(VARIANTS) and high is not None and high<0 and first is not None and first<0 and second is not None and second<0)
                own_ok=bool(own_ci['own_high'] is not None and own_ci['own_high']<0 and own_negative==len(VARIANTS) and not own_missing)
                state='REPEATED' if stable and own_ok else 'PACE_ONLY' if stable else 'INSUFFICIENT' if not base_quality else 'NO_ADVANTAGE' if low is not None and low>=0 else 'UNCERTAIN'
                loo=[median(base_delta[:i]+base_delta[i+1:]) for i in range(len(base_delta))] if base_quality else []
                a=tyre_groups.get(mid_a,{});b=tyre_groups.get(mid_b,{})
                td={}
                for k in sorted(a.keys()&b.keys()):td.setdefault(k[0],[]).append(float(a[k]-b[k]))
                td=[float(np.median(td[k])) for k in sorted(td)]
                tc=analysis.bootstrap(td,('tyre',int(year),*sorted([mid_a,mid_b]))) if base_quality and len(td)>=4 else (None,None,None)
                # Fixed-condition common-race consistency is diagnostic, not 11-scenario proof.
                ar=race_groups['baseline'].get(mid_a,{});br=race_groups['baseline'].get(mid_b,{})
                cd=[float(ar[k].adjusted_iqr_sec-br[k].adjusted_iqr_sec) for k in sorted(ar.keys()&br.keys())]
                cc=analysis.bootstrap(cd,('iqr',int(year),*sorted([mid_a,mid_b]))) if base_quality and len(cd)>=8 else (None,None,None)
                reasons=[]
                if not cand.eligible:reasons.append('후보의 8경기·200랩 기준 미달')
                if not seat.eligible:reasons.append('비교 자리의 8경기·200랩 기준 미달')
                if len(base_common)<8:reasons.append('공통 경기 8개 미만')
                cases[key]=dict(year=int(year),seat=mid_b,candidate=mid_a,status=state,delta=median(base_delta) if base_quality else None,low=low,high=high,common_races=len(base_common),common=base_common if base_quality else [],faster=faster,missing=missing,own_negative=own_negative,own_missing=own_missing,first=first,second=second,loo_min=min(loo) if loo else None,loo_max=max(loo) if loo else None,scenarios=scenarios,tyre_races=len(td),tyre_delta=median(td) if base_quality and len(td)>=4 else None,tyre_low=f(tc[0]),tyre_high=f(tc[1]),iqr_delta=median(cd) if base_quality and len(cd)>=8 else None,iqr_low=f(cc[0]),iqr_high=f(cc[1]),reasons=reasons)
                count+=1
    # Time trends preserve actual team names; no automatic team-lineage reassignment.
    summary=json.loads((SRC/'analysis_summary.json').read_text(encoding='utf-8'))
    quality=records(frame('gold/gold_data_quality.csv'))
    payload=dict(created='2026-10-15',cutoff='2026-10-14',years=sorted(int(y) for y in profiles.year.unique()),variants=VARIANTS,profiles=records(profiles),teams=records(team),team_races=records(teamrace),coverage=records(coverage),outcomes=records(outcome[['session_key','driver_number','full_name','team_name','year','finish_position','grid_position','race_base_points','classification_status','points_rule_status','grid_change']]),cases=cases,source_counts=records(frame('bronze/source_manifest.csv')),quality=quality,summary=summary,thresholds=dict(races=8,laps=200,teammate_races=5,tyre_races=4,tyre_stints=8),methodology=json.loads((SRC/'methodology.json').read_text(encoding='utf-8')))
    (O/'data.json').write_text(json.dumps(clean(payload),ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    pd.DataFrame([{k:v for k,v in c.items() if k not in ['common','scenarios','reasons']} for c in cases.values()]).to_csv(O/'all_candidate_cases.csv',index=False,encoding='utf-8-sig')
    stats=dict(seasons=len(payload['years']),teams_by_season={int(y):g.team_name.nunique() for y,g in team.groupby('year')},observed_players_by_season={int(y):len(g) for y,g in profiles.groupby('year')},candidate_comparisons=count,scenario_comparisons=count*len(VARIANTS),bootstrap_draws=2000)
    (O/'build_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
