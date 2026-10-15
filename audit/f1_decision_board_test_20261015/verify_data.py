"""Check complete selection coverage and compare against independently stored marts."""
from pathlib import Path
import json,hashlib,math,re
import pandas as pd
import numpy as np
O=Path(__file__).resolve().parent
S=O.parent/'f1_final_analysis_20261015'
d=json.loads((O/'data.json').read_text(encoding='utf-8'))
p={x['membership_id']:x for x in d['profiles']}
failures=[];checks=0
def check(ok,message):
    global checks
    checks+=1
    if not ok:failures.append(message)
def near(a,b):
    return a is None and b is None or a is not None and b is not None and abs(a-b)<1e-8
for y in d['years']:
    ps=[x for x in p.values() if x['year']==y]
    expected=sum(a['team_name']!=b['team_name'] for a in ps for b in ps)
    check(expected==sum(c['year']==y for c in d['cases'].values()),f'coverage {y}')
for key,c in d['cases'].items():
    a,b=p[c['seat']],p[c['candidate']]
    check(a['year']==b['year']==c['year'] and a['team_name']!=b['team_name'],f'membership {key}')
    check(len(c['scenarios'])==11,f'conditions {key}')
    check(c['faster']==sum(v[0] is not None and v[0]<0 for v in c['scenarios']),f'faster {key}')
    check(c['missing']==sum(v[0] is None for v in c['scenarios']),f'missing {key}')
    if not a['eligible'] or not b['eligible'] or c['common_races']<8:
        check(c['status']=='INSUFFICIENT' and c['delta'] is None and not c['common'],f'insufficient {key}')
    else:
        check(near(c['delta'],float(np.median([v[1] for v in c['common']]))),f'common median {key}')
    reverse=d['cases'][c['candidate']+'>>'+c['seat']]
    check(near(c['delta'],None if reverse['delta'] is None else -reverse['delta']),f'reverse median {key}')
    check(near(c['low'],None if reverse['high'] is None else -reverse['high']),f'reverse interval {key}')
    if c['status'] in ('REPEATED','PACE_ONLY'):
        check(c['missing']==0 and c['faster']==11 and c['high']<0 and c['first']<0 and c['second']<0,f'stability {key}')
    if c['status']=='REPEATED':
        check(b['own_high']<0 and c['own_negative']==11 and c['own_missing']==0,f'own proof {key}')
    for i,v in enumerate(c['scenarios']):
        check(v[3]==(v[0] is not None),f'quality {key}/{i}')
        if v[3]:check(v[1]>=(10 if i==9 else 8),f'min races {key}/{i}')
# Original two case studies: same baseline values and condition direction counts.
old=pd.read_csv(S/'gold/gold_driver_team_fit.csv')
old_compared=0
for row in old.itertuples():
    seats=[x for x in p.values() if x['year']==2025 and x['team_name']==row.target_team and x['full_name']==row.replaced_driver]
    c=d['cases'][seats[0]['membership_id']+'>>'+row.candidate_membership_id]
    check(near(c['delta'],row.candidate_minus_seat_pct),f'prior case delta {row.target_team}/{row.candidate}')
    check(c['faster']==row.scenario_faster_count and c['missing']==row.scenario_missing_count,f'prior scenario {row.candidate}')
    old_compared+=1
# Point aggregation is reproduced from source-derived driver-race rows, including missingness.
for t in d['teams']:
    out=[r for r in d['outcomes'] if r['year']==t['year'] and r['team_name']==t['team_name']]
    check(near(t['race_base_points'],sum(r['race_base_points'] or 0 for r in out)),f'points {t["year"]}/{t["team_name"]}')
    check(t['unknown_point_rows']==sum(r['race_base_points'] is None for r in out),f'unknown points {t["team_name"]}')
hashes=json.loads((O/'existing_hashes.json').read_text(encoding='utf-8'))
changed=[]
for name,before in hashes.items():
    f=O.parents[1]/name
    if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=before:changed.append(name)
check(not changed,'Existing files changed: '+', '.join(changed))
html=(O/'F1_decision_board_test.html').read_text(encoding='utf-8')
check(html==(O/'dist/index.html').read_text(encoding='utf-8'),'HTML copies differ')
check(not re.search(r'<(?:script|img|iframe)\b[^>]*\bsrc\s*=|<link\b[^>]*\bhref\s*=',html,re.I),'External resource dependency')
embedded=re.search(r'<script id="snapshot" type="application/json">(.*?)</script>',html,re.S).group(1)
check(json.loads(embedded)==d,'Embedded snapshot mismatch')
report=dict(checks=checks,failures=failures,all_candidate_cases=len(d['cases']),prior_case_values_checked=old_compared,existing_files_hashed=len(hashes),existing_files_changed=changed)
(O/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if failures:raise SystemExit(1)
