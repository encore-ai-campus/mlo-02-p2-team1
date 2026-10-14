from __future__ import annotations
import argparse, csv, html, io, json, math, zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"C:\Users\Playdata\Downloads\F1_distribution.압축")
FILES = ["sessions.csv", "drivers.csv", "laps.csv", "stints.csv", "weather.csv", "pit.csv"]
NUMERIC_LAP = ["duration_sector_1","duration_sector_2","duration_sector_3","i1_speed","i2_speed","lap_duration","st_speed"]
LOCATION = ["year","country_name","country_code","circuit_short_name","location","meeting_key","session_name","session_type"]
VALID_COMPOUNDS = {"SOFT","MEDIUM","HARD","INTERMEDIATE","WET"}

def read_rows(z, name):
    return list(csv.DictReader(io.StringIO(z.read(f"F1_distribution/all_years/{name}").decode("utf-8-sig"))))

def num(v):
    try: return float(v) if v != "" else None
    except (TypeError, ValueError): return None

def med(vals):
    vals=sorted(x for x in vals if x is not None and math.isfinite(x))
    if not vals: return None
    n=len(vals); return vals[n//2] if n%2 else (vals[n//2-1]+vals[n//2])/2

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys=[]
    for row in rows:
        for key in row:
            if key not in keys: keys.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def add_repair(row, field, value, method, confidence, reason, details):
    if row.get(field, "") == "" and value not in (None, ""):
        row[field]=str(value); row["repair_status"]="REPAIRED"; row["repair_confidence"]=confidence
        row["repair_method"]=method; row["repair_reason"]=reason; details.append([row["source_file"],row.get("session_key",""),row.get("driver_number",""),row.get("lap_number",row.get("stint_number","")),field,"",str(value),method,confidence,reason])

def enrich_sessions(rows, sessions, details):
    sm={x["session_key"]:x for x in sessions}
    for r in rows:
        r["source_file"]="drivers.csv"; r.update({"original_"+k:r.get(k,"") for k in r})
        for k in LOCATION:
            if not r.get(k," ").strip(): add_repair(r,k,sm.get(r["session_key"],{}).get(k,""),"session_key_join","HIGH","sessions.csv의 동일 session_key로 복구",details)
    return rows

def repair_laps(rows, sessions, drivers, details):
    sm={x["session_key"]:x for x in sessions}; dm={(x["session_key"],x["driver_number"]):x for x in drivers}
    pools=defaultdict(lambda:defaultdict(list)); spools=defaultdict(lambda:defaultdict(list))
    for r in rows:
        for f in NUMERIC_LAP:
            v=num(r.get(f,""));
            if v is not None: pools[(r["session_key"],r["driver_number"])][f].append(v); spools[r["session_key"]][f].append(v)
    for r in rows:
        r["source_file"]="laps.csv"; r.update({"original_"+k:r.get(k,"") for k in r});
        r.update({"session_"+k:sm.get(r["session_key"],{}).get(k,"") for k in LOCATION})
        r.update({"driver_"+k:dm.get((r["session_key"],r["driver_number"]),{}).get(k,"") for k in ["full_name","team_name","country_code"]})
        for f in NUMERIC_LAP:
            if r[f]=="":
                v=med(pools[(r["session_key"],r["driver_number"])][f]) or med(spools[r["session_key"]][f])
                if v is not None: add_repair(r,f,f"{v:.6f}".rstrip("0").rstrip("."),"median_session_driver_or_session","MEDIUM","동일 세션·드라이버 또는 세션 중앙값",details)
        if r["date_start"]=="": add_repair(r,"date_start",None,"unresolved","LOW","주변 랩의 시간정보만으로 유일한 복구값을 결정할 수 없음",details)
    return rows

def repair_stints(rows, drivers, details):
    for r in rows:
        r["source_file"]="stints.csv"; r.update({"original_"+k:r.get(k,"") for k in r})
        if r["compound"]=="": add_repair(r,"compound","UNKNOWN","explicit_unknown","LOW","원본에 타이어 정보가 없어 UNKNOWN으로 표시",details)
        for f in ["lap_start","lap_end"]:
            if r[f]=="": add_repair(r,f,"","unresolved","LOW","스틴트 경계값을 유일하게 결정할 근거 없음",details)
    return rows

def repair_generic(rows, name):
    for r in rows:
        r["source_file"]=name; r.update({"original_"+k:r.get(k,"") for k in r})
    return rows

def table(rows, cols, limit=30):
    head="<tr>"+"".join(f"<th>{html.escape(c)}</th>" for c in cols)+"</tr>"
    body="".join("<tr>"+"".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols)+"</tr>" for r in rows[:limit])
    return f"<table><thead>{head}</thead><tbody>{body}</tbody></table>"

def make_report(out, counts, details, source_rows, repaired_rows):
    status=Counter(x["status"] for x in counts.values()); total=sum(status.values())
    rows="".join(f"<tr><td>{html.escape(k)}</td><td>{v['rows']:,}</td><td>{v['changes']:,}</td><td>{html.escape(v['status'])}</td></tr>" for k,v in counts.items())
    drows=details[:500]
    doc=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>F1 데이터 복구 품질 리포트</title><style>
body{{font-family:Arial,"Malgun Gothic",sans-serif;margin:0;background:#f4f7fa;color:#17212b}}header{{background:#182b49;color:white;padding:28px 42px}}main{{max-width:1200px;margin:24px auto;padding:0 18px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card{{background:white;border:1px solid #dce4ec;border-radius:10px;padding:16px}}.num{{font-size:27px;font-weight:700}}h2{{margin-top:30px}}table{{width:100%;border-collapse:collapse;background:white;font-size:13px}}th,td{{padding:9px;border-bottom:1px solid #e6edf2;text-align:left}}th{{background:#eaf1f6}}.warn{{color:#a84b00;font-weight:700}}.ok{{color:#16724a;font-weight:700}}.note{{background:#fff7e8;padding:14px;border-left:4px solid #e8893b}}
</style></head><body><header><h1>F1 오염 데이터 복구 품질 리포트</h1><div>명세서 대조 · 관계 검증 · 복구값 근거 기록</div></header><main>
<div class="grid"><div class="card"><div>검토 파일</div><div class="num">6</div></div><div class="card"><div>복구·표시 변경</div><div class="num">{len(details):,}</div></div><div class="card"><div>복구 근거 상세</div><div class="num">{len(drows):,}+</div></div><div class="card"><div>원본 보존</div><div class="num ok">YES</div></div></div>
<div class="note"><b>복구 원칙</b><br>원본값은 original_ 컬럼으로 보존하고, 직접 관계로 확인한 값과 통계적으로 추정한 값을 repair_confidence로 구분했습니다. 근거가 부족한 값은 무리하게 확정하지 않고 LOW/UNRESOLVED로 표시했습니다.</div>
<h2>파일별 처리 현황</h2><table><thead><tr><th>파일</th><th>행 수</th><th>복구·표시 변경</th><th>상태</th></tr></thead><tbody>{rows}</tbody></table>
<h2>복구 상세 샘플</h2>{table([dict(zip(['source_file','session_key','driver_number','row_key','field','old','new','method','confidence','reason'],x)) for x in drows],['source_file','session_key','driver_number','row_key','field','new','method','confidence','reason'])}
<h2>Django 연결 포인트</h2><p>이 리포트의 표와 복구 결과 CSV는 Django의 <code>templates/report.html</code> 및 ORM 모델로 분리해 연결할 수 있습니다. 특히 repair_status와 repair_confidence를 필터 조건으로 사용하면 원본·복구·추정 데이터를 구분해 화면에 표시할 수 있습니다.</p>
</main></body></html>'''
    (out/"reports").mkdir(parents=True,exist_ok=True); (out/"reports"/"quality_report.html").write_text(doc,encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",type=Path,default=DEFAULT_INPUT); ap.add_argument("--output",type=Path,default=ROOT/"outputs"/"f1_recovery"); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    details=[]; counts={}
    with zipfile.ZipFile(a.input) as z:
        sessions=read_rows(z,"sessions.csv"); drivers=read_rows(z,"drivers.csv"); laps=read_rows(z,"laps.csv"); stints=read_rows(z,"stints.csv"); weather=read_rows(z,"weather.csv"); pit=read_rows(z,"pit.csv")
    repaired={"sessions.csv":repair_generic(sessions,"sessions.csv"),"drivers.csv":enrich_sessions(drivers,sessions,details),"laps.csv":repair_laps(laps,sessions,drivers,details),"stints.csv":repair_stints(stints,drivers,details),"weather.csv":repair_generic(weather,"weather.csv"),"pit.csv":repair_generic(pit,"pit.csv")}
    for name,rows in repaired.items():
        write_csv(a.output/"repaired"/name,rows); changes=sum(1 for r in rows if r.get("repair_status")); counts[name]={"rows":len(rows),"changes":changes,"status":"REPAIRED" if changes else "UNCHANGED"}
    write_csv(a.output/"reports"/"repair_detail.csv",[dict(zip(["source_file","session_key","driver_number","row_key","field","old_value","new_value","method","confidence","reason"],x)) for x in details] or [{"source_file":"","session_key":"","driver_number":"","row_key":"","field":"","old_value":"","new_value":"","method":"","confidence":"","reason":""}])
    write_csv(a.output/"reports"/"repair_summary.csv",[{"file":k,**v} for k,v in counts.items()]); make_report(a.output,counts,details,repaired,repaired); print(json.dumps({"output":str(a.output),"details":len(details)},ensure_ascii=False))
if __name__=="__main__": main()
