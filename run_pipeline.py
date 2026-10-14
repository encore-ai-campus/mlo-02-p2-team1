from __future__ import annotations
import argparse,csv,io,json,math,statistics,zipfile
from collections import defaultdict
from html import escape
from pathlib import Path

FILES=['sessions.csv','drivers.csv','laps.csv','stints.csv','weather.csv','pit.csv']
SCHEMA={
'drivers.csv':'broadcast_name country_code driver_number first_name full_name headshot_url last_name meeting_key name_acronym session_key team_colour team_name'.split(),
'laps.csv':'date_start driver_number duration_sector_1 duration_sector_2 duration_sector_3 i1_speed i2_speed is_pit_out_lap lap_duration lap_number meeting_key segments_sector_1 segments_sector_2 segments_sector_3 session_key st_speed'.split(),
'pit.csv':'date driver_number lane_duration lap_number meeting_key pit_duration session_key stop_duration'.split(),
'sessions.csv':'circuit_key circuit_short_name country_code country_key country_name date_end date_start gmt_offset is_cancelled location meeting_key session_key session_name session_type year'.split(),
'stints.csv':'compound driver_number lap_end lap_start meeting_key session_key stint_number tyre_age_at_start'.split(),
'weather.csv':'air_temperature date humidity meeting_key pressure rainfall session_key track_temperature wind_direction wind_speed'.split()}
NUM={'duration_sector_1','duration_sector_2','duration_sector_3','i1_speed','i2_speed','lap_duration','st_speed','lane_duration','pit_duration','stop_duration'}
COMPOUNDS={'SOFT','MEDIUM','HARD','INTERMEDIATE','WET','UNKNOWN'}
def num(v):
 try:return float(v) if str(v).strip() else None
 except:return None
def med(v):
 v=sorted(x for x in v if x is not None and math.isfinite(x));return statistics.median(v) if v else None
def write(path,rows,fields=None):
 path.parent.mkdir(parents=True,exist_ok=True);fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',encoding='utf-8-sig',newline='') as f: csv.DictWriter(f,fieldnames=fields,extrasaction='ignore').writeheader();csv.DictWriter(f,fieldnames=fields,extrasaction='ignore').writerows(rows)
def load(path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist(); marker=next((n for n in names if n.endswith('all_years/sessions.csv')),None)
  if not marker:raise ValueError('all_years/sessions.csv not found')
  root=marker[:-len('sessions.csv')]; data={n:list(csv.DictReader(io.StringIO(z.read(root+n).decode('utf-8-sig')))) for n in FILES}
  spec=next((n for n in names if n.endswith('00. 데이터_명세서.md')),None)
  return data,bool(spec)
def prep(name,rows):
 out=[]
 for x in rows:
  r=dict(x);r['source_file']=name
  for k,v in x.items():r['original_'+k]=v
  r.update(repair_status='UNCHANGED',repair_method='NONE',repair_confidence='HIGH',repair_reason='원본값 유지');out.append(r)
 return out
def setv(r,f,v,method,conf,reason,details,key):
 if r.get(f,'') or v in (None,''):return
 r[f]=str(v);r.update(repair_status='REPAIRED',repair_method=method,repair_confidence=conf,repair_reason=reason)
 details.append({'source_file':r['source_file'],**key,'field':f,'old_value':'','new_value':str(v),'method':method,'confidence':conf,'reason':reason})
def repair(data,details):
 sessions={r['session_key']:r for r in data['sessions.csv']}; pools=defaultdict(lambda:defaultdict(list));sp=defaultdict(lambda:defaultdict(list))
 for r in data['laps.csv']:
  for f in NUM:
   v=num(r.get(f));
   if v is not None and f!='lap_duration':pools[(r['session_key'],r['driver_number'])][f].append(v);sp[r['session_key']][f].append(v)
 for name,rows in data.items():
  for r in rows:
   key={'session_key':r.get('session_key',''),'driver_number':r.get('driver_number',''),'row_key':r.get('lap_number',r.get('stint_number',r.get('date','')))}
   if name in ('drivers.csv','laps.csv'):
    s=sessions.get(r.get('session_key'),{})
    for f in ('year','country_name','country_code','circuit_short_name','location','meeting_key','session_name','session_type'):
     if f in r:setv(r,f,s.get(f,''),'session_key_join','HIGH','동일 session_key의 sessions.csv 값',details,key)
   if name=='laps.csv':
    for f in ('duration_sector_1','duration_sector_2','duration_sector_3','i1_speed','i2_speed','st_speed'):
     v=med(pools[(r['session_key'],r['driver_number'])][f]) or med(sp[r['session_key']][f]);setv(r,f,v and f'{v:.6f}'.rstrip('0').rstrip('.'),'median_session_driver_or_session','MEDIUM','동일 세션·드라이버 우선 중앙값',details,key)
   if name=='stints.csv' and r.get('compound','') in ('','NULL','None'):setv(r,'compound','UNKNOWN','explicit_unknown','LOW','원본 타이어 정보가 없어 UNKNOWN으로 명시',details,key)
def validate(data):
 issues=[];summary={}
 def add(file,kind,r,field,msg):issues.append({'file':file,'kind':kind,'row_key':r.get('lap_number',r.get('stint_number',r.get('date',''))),'session_key':r.get('session_key',''),'field':field,'message':msg})
 for name,rows in data.items():
  cols=set(rows[0]) if rows else set();missing=set(SCHEMA[name])-cols
  if missing:add(name,'SCHEMA',{},'', 'missing columns: '+','.join(sorted(missing)))
  summary[name]={'rows':len(rows),'expected_columns':len(SCHEMA[name]),'actual_columns':len(cols),'issues':0}
  for r in rows:
   for f in NUM:
    if f in r and r[f] and num(r[f]) is None:add(name,'TYPE',r,f,'숫자로 해석할 수 없음')
   if name=='stints.csv' and num(r.get('lap_start')) is not None and num(r.get('lap_end')) is not None and num(r['lap_end'])<num(r['lap_start']):add(name,'RANGE',r,'lap_end','lap_end < lap_start')
   if name=='stints.csv' and r.get('compound','') not in COMPOUNDS:add(name,'DOMAIN',r,'compound','허용 목록 외 compound')
   if name=='laps.csv' and (num(r.get('lap_duration')) or 0)>300:add(name,'OUTLIER',r,'lap_duration','300초 초과 비정상 랩')
   if name=='pit.csv' and (num(r.get('pit_duration')) or 0)>180:add(name,'OUTLIER',r,'pit_duration','180초 초과 비정상 피트 시간')
 groups=defaultdict(list)
 for r in data['stints.csv']:groups[(r.get('session_key',''),r.get('driver_number',''))].append(r)
 for rs in groups.values():
  rs.sort(key=lambda r:num(r.get('lap_start')) if num(r.get('lap_start')) is not None else float('inf'))
  for prev,cur in zip(rs,rs[1:]):
   end,start=num(prev.get('lap_end')),num(cur.get('lap_start'))
   if end is not None and start is not None and start<=end:add('stints.csv','OVERLAP',cur,'lap_start','동일 세션·드라이버 스틴트 구간 겹침 후보')
 for i in issues:summary[i['file']]['issues']+=1
 return summary,issues
def report(out,summary,issues,details,spec):
 write(out/'reports'/'validation_issues.csv',issues or [{'file':'','kind':'','row_key':'','session_key':'','field':'','message':'검증 이슈 없음'}])
 h="<meta charset='utf-8'><style>body{font-family:Arial,'Malgun Gothic';margin:32px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd;padding:6px;text-align:left}th{background:#eaf1f6}</style><h1>F1 오염 데이터 복구 품질 리포트</h1>"
 h+=f"<p>명세서 포함: <b>{'YES' if spec else 'NO'}</b> · 복구 기록: <b>{len(details)}</b> · 검증 이슈: <b>{len(issues)}</b></p><h2>파일별 검증</h2><table><tr><th>파일</th><th>행</th><th>명세 컬럼</th><th>결과 컬럼</th><th>이슈</th></tr>"+''.join(f"<tr><td>{escape(k)}</td><td>{v['rows']}</td><td>{v['expected_columns']}</td><td>{v['actual_columns']}</td><td>{v['issues']}</td></tr>" for k,v in summary.items())+'</table>'
 h+="<h2>복구 전후 및 근거</h2><p>original_* 컬럼으로 원본을 보존합니다. 조인은 HIGH, 중앙값은 MEDIUM, UNKNOWN 표시는 LOW입니다.</p><table><tr><th>파일</th><th>세션</th><th>행</th><th>필드</th><th>전</th><th>후</th><th>방법</th><th>신뢰도</th><th>근거</th></tr>"+''.join(f"<tr><td>{escape(str(d['source_file']))}</td><td>{escape(str(d['session_key']))}</td><td>{escape(str(d['row_key']))}</td><td>{escape(d['field'])}</td><td>{escape(d['old_value'])}</td><td>{escape(d['new_value'])}</td><td>{escape(d['method'])}</td><td>{d['confidence']}</td><td>{escape(d['reason'])}</td></tr>" for d in details[:2000])+'</table>'
 h+="<h2>검증 이슈 샘플</h2><table><tr><th>파일</th><th>종류</th><th>세션</th><th>필드</th><th>내용</th></tr>"+''.join(f"<tr><td>{i['file']}</td><td>{i['kind']}</td><td>{i['session_key']}</td><td>{i['field']}</td><td>{escape(i['message'])}</td></tr>" for i in issues[:2000])+'</table>'
 (out/'reports'/'quality_report.html').write_text('<!doctype html>'+h,encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,default=Path('config.json'));a=ap.parse_args();cfg=json.loads(a.config.read_text(encoding='utf-8'));out=Path(cfg['output_directory']);raw,spec=load(Path(cfg['input_archive']));data={k:prep(k,v) for k,v in raw.items()};details=[];repair(data,details);summary,issues=validate(data)
 for n,r in data.items():write(out/'repaired'/n,r)
 write(out/'reports'/'repair_detail.csv',details or [{'source_file':'','session_key':'','driver_number':'','row_key':'','field':'','old_value':'','new_value':'','method':'','confidence':'','reason':''}]);write(out/'reports'/'repair_summary.csv',[{'file':k,'rows':v['rows'],'changes':sum(r['repair_status']=='REPAIRED' for r in data[k]),'status':'PASS' if not v['issues'] else 'REVIEW','issues':v['issues']} for k,v in summary.items()]);report(out,summary,issues,details,spec);(out/'reports'/'run_result.json').write_text(json.dumps({'output':str(out),'repair_records':len(details),'validation_issues':len(issues),'spec_present':spec},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'output':str(out),'repair_records':len(details),'validation_issues':len(issues)},ensure_ascii=False))
if __name__=='__main__':main()
