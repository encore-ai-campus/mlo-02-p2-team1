'use strict';
const D=JSON.parse(document.getElementById('snapshot').textContent);
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const valid=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const num=(v,n=2)=>valid(v)?Number(v).toLocaleString('ko-KR',{minimumFractionDigits:n,maximumFractionDigits:n}):'N/A';
const signed=(v,n=3)=>valid(v)?`${Number(v)>0?'+':''}${num(v,n)}`:'N/A';
const N=v=>num(v,0), lower=v=>valid(v)?Number(v):Infinity;
const P=new Map(D.profiles.map(p=>[p.membership_id,p]));
const raceMap=new Map(D.coverage.map(r=>[r.session_key,r]));
const ST={REPEATED:['동료 비교까지 반복','good'],PACE_ONLY:['페이스 우위 반복','blue'],UNCERTAIN:['조건·표본에 민감','warn'],INSUFFICIENT:['표본 부족 · 판단 보류','warn'],NO_ADVANTAGE:['우위 근거 없음','muted']};
const VN=['기본 정제','날씨 연결 60초','날씨 연결 120초','타이어 나이까지 맞춤','참조 구간 3랩','복구한 랩 제외','재시작 1랩 더 제외','동료 타이어 나이 차 ≤1랩','근접 차량 영향 제한','20랩·10경기 기준','이벤트 불확실 경기 제외'];
const METRICS={relative_pace_pct:['필드 상대 페이스','%',3,'낮을수록 빠름'],teammate_delta_sec:['동료 대비 페이스','초',3,'음수면 동료보다 빠름'],adjusted_iqr_sec:['조건 보정 IQR','초',3,'낮을수록 페이스 편차 작음'],tyre_slope_sec_per_lap:['타이어 잔차 추세','초/랩',4,'낮을수록 상대 페이스 저하 작음'],race_base_points:['본경기 기본 포인트','점',0,'높을수록 많음']};
let year=2025, team='Aston Martin', seat='', selected='', page=0, candidates=[];
let teams=[],players=[],lastRender=0;
const options=(el,items,value)=>{el.innerHTML=items.map(([v,label])=>`<option value="${esc(v)}">${esc(label)}</option>`).join('');if(items.some(i=>i[0]===value))el.value=value;};
const profiles=()=>D.profiles.filter(p=>p.year===year);
const caseFor=(a,b)=>D.cases[`${a}>>${b}`];
const metricValue=(p,k)=>{
 if(k==='race_base_points')return p.unknown_point_rows?null:p[k];
 if(!p.eligible)return null;
 if(k==='teammate_delta_sec'&&p.teammate_races<5)return null;
 if(k==='tyre_slope_sec_per_lap'&&(p.tyre_races<4||p.tyre_stints<8))return null;
 return p[k];
};
const badge=c=>`<span class="badge ${esc(c?.status||'INSUFFICIENT')}">${esc(ST[c?.status||'INSUFFICIENT'][0])}</span>`;
const range=(lo,hi,unit='')=>valid(lo)&&valid(hi)?`${signed(lo)} ~ ${signed(hi)}${unit}`:'N/A';
const stat=(label,value,desc,cl='')=>`<div class="stat"><div class="stat-label">${label}</div><strong class="${cl}">${value}</strong><small>${desc}</small></div>`;
const row=(label,value)=>`<div class="fact-row"><span class="muted">${label}</span><b>${value}</b></div>`;
function init(){
 options($('season'),D.years.map(y=>[String(y),String(y)+(y===2026?' · 누적':'')]),String(year));
 $('season').addEventListener('change',()=>{year=Number($('season').value);loadTeams();});
 $('team').addEventListener('change',()=>{team=$('team').value;loadSeats();});
 $('seat').addEventListener('change',()=>{seat=$('seat').value;selected='';page=0;render();});
 for(const id of ['priority','pool'])$(id).addEventListener('change',()=>{page=0;selected='';render();});
 $('prev').addEventListener('click',()=>{page=Math.max(0,page-1);renderCandidates();});
 $('next').addEventListener('click',()=>{page=Math.min(Math.ceil(candidates.length/CANDIDATE_PAGE_SIZE)-1,page+1);renderCandidates();});
 $('candidate-grid').addEventListener('click',e=>{const b=e.target.closest('[data-candidate]');if(b){selected=b.dataset.candidate;renderCandidates();renderEvidence();renderQuestions();renderSide();}});
 $('theme').addEventListener('click',()=>{const light=document.documentElement.dataset.theme!=='light';document.documentElement.dataset.theme=light?'light':'dark';$('theme').textContent=light?'다크 모드':'라이트 모드';$('theme').setAttribute('aria-label',light?'어두운 화면으로 전환':'밝은 화면으로 전환');});
 initCandidateControls();loadTeams();renderSources();
}
function loadTeams(){
 teams=D.teams.filter(t=>t.year===year).sort((a,b)=>b.race_base_points-a.race_base_points||a.team_name.localeCompare(b.team_name));
 if(!teams.some(t=>t.team_name===team))team=teams[0].team_name;
 options($('team'),teams.map(t=>[t.team_name,t.team_name]),team);loadSeats();
}
function loadSeats(){
 players=profiles().filter(p=>p.team_name===team).sort((a,b)=>a.full_name.localeCompare(b.full_name));
 // A review starting point, not an assertion that replacement is necessary.
 const matched=players.filter(p=>valid(p.teammate_delta_sec));
 const defaultSeat=[...(matched.length?matched:players)].sort((a,b)=>lower(b.teammate_delta_sec??b.relative_pace_pct)-lower(a.teammate_delta_sec??a.relative_pace_pct))[0];
 seat=defaultSeat?.membership_id||players[0]?.membership_id||'';selected='';page=0;
 options($('seat'),players.map(p=>[p.membership_id,`${p.full_name}${p.eligible?'':' · 표본 부족'}`]),seat);render();
}
function render(){
 const s=P.get(seat);if(!s)return;
 let pool=profiles().filter(p=>p.team_name!==team);
 const tf=$('pool').value;
 if(tf!=='all')pool=pool.filter(p=>{const t=teams.find(t=>t.team_name===p.team_name);return tf==='top4'?t.race_base_points_team_rank<=4:t.race_base_points_team_rank>4;});
 const key=$('priority').value;
 candidates=pool.sort((a,b)=>{
  const av=metricValue(a,key),bv=metricValue(b,key);
  if(!valid(av))return valid(bv)?1:a.full_name.localeCompare(b.full_name);
  if(!valid(bv))return -1;
  return (key==='race_base_points'?bv-av:av-bv)||a.full_name.localeCompare(b.full_name);
 });
 if(!candidates.some(p=>p.membership_id===selected))selected=candidates[0]?.membership_id||'';
 page=Math.min(page,Math.max(0,Math.ceil(candidates.length/CANDIDATE_PAGE_SIZE)-1));
 $('overview-title').textContent=`${team}의 현재 관측값은 무엇을 말할까?`;
 const cv=D.coverage.filter(r=>r.year===year);
 $('scope').textContent=`기준 선수: ${s.full_name} · 소속 마지막 관측 구간 ${s.race_entries}경기 · 시즌 전체 원천 ${cv.length} Race`;
 $('period').textContent=year===2026?'2026.10.14 기준 누적 · 시즌 진행 중':`${year} 관측 시즌`;
 renderQuestions();renderPoints();renderCandidates();renderEvidence();renderPit();renderSide();
 document.body.dataset.render=`${++lastRender}`;document.body.dataset.selection=`${year}|${team}|${s.full_name}|${P.get(selected)?.full_name||''}`;
}
function renderQuestions(){renderStoryQuestions();}
function renderPoints(){renderStoryPoints();}
function barChart(data){
 const w=780,left=148,right=70,rh=31,h=data.length*rh+15,max=Math.max(1,...data.map(d=>d.value||0));
 return `<svg class="bar-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${year} 팀별 본경기 기본 포인트 비교">${data.map((d,i)=>{const y=i*rh+7,bw=Math.max(1,(w-left-right)*d.value/max),co=d.active?'var(--mint)':'var(--dim)';return `<text x="0" y="${y+15}" font-size="11" style="fill:${d.active?'var(--mint)':'var(--muted)'}">${esc(d.name)}</text><rect x="${left}" y="${y+2}" width="${w-left-right}" height="17" rx="3" fill="var(--surface2)"/><rect x="${left}" y="${y+2}" width="${bw}" height="17" rx="3" fill="${co}" opacity="${d.active?1:.57}"/><text x="${left+bw+10}" y="${y+15}" font-size="11">${N(d.value)}${d.unknown?'*':''}</text>`;}).join('')}</svg>`;
}
function renderCandidates(){renderCandidateComparison();}
function renderEvidence(){renderTrustEvidence();}
function deltaChart(c,p,s){
 if(!c.common.length)return '<div class="empty">공통 경기와 프로필 표본 기준을 통과하지 못해 경기별 차트를 표시하지 않습니다.</div>';
 const w=780,h=210,l=50,r=20,t=20,b=55,plot=w-l-r,inner=h-t-b,max=Math.max(.15,...c.common.map(v=>Math.abs(v[1])))*1.12,zero=t+inner/2,scale=(inner/2)/max,step=plot/c.common.length;
 let svg=`<svg style="min-width:550px" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(p.full_name)}와 ${esc(s.full_name)}의 경기별 페이스 차이"><line x1="${l}" x2="${w-r}" y1="${zero}" y2="${zero}" stroke="var(--dim)" stroke-dasharray="3 4"/>`;
 for(const v of [-max/2,max/2]){const y=zero-v*scale;svg+=`<line x1="${l}" x2="${w-r}" y1="${y}" y2="${y}" stroke="var(--line)"/><text x="${l-8}" y="${y+4}" text-anchor="end" font-size="10">${signed(v,2)}</text>`;}
 svg+=`<text x="${l-8}" y="${zero+4}" text-anchor="end" font-size="10">0</text>`;
 c.common.forEach((a,i)=>{const x=l+(i+.5)*step,y=zero-a[1]*scale,col=a[1]<0?'var(--mint)':'var(--coral)',race=raceMap.get(a[0]),name=race?.circuit_short_name||a[0];svg+=`<rect x="${x-step*.29}" y="${Math.min(y,zero)}" width="${step*.58}" height="${Math.max(1,Math.abs(y-zero))}" fill="${col}" rx="2"><title>${esc(name)} · ${race?.date_start.slice(0,10)} · 후보−기준 ${signed(a[1])}%p</title></rect><text x="${x}" y="${h-b+20}" transform="rotate(45 ${x} ${h-b+20})" text-anchor="start" font-size="8.5">${esc(name.length>10?name.slice(0,10)+'…':name)}</text>`;});
 return svg+'</svg>';
}
function renderPit(){renderOperations();}
function renderSide(){
 const t=teams.find(t=>t.team_name===team),s=P.get(seat),p=P.get(selected),c=caseFor(seat,selected),cv=D.coverage.filter(r=>r.year===year);
 const state=ST[c?.status||'INSUFFICIENT'];
 $('decision').innerHTML=`<span class="badge">${year} · ${esc(team)}</span><div class="decision-label ${state[1]}">${esc(state[0])}</div><p>${p?`${esc(p.full_name)}를 ${esc(s.full_name)}의 비교 후보로 선택했습니다.`:'선택 가능한 후보가 없습니다.'}</p><h4>다음으로 확인할 것</h4><p>${c?.status==='REPEATED'?'차량 차이를 분리할 추가 근거와 계약·비용·적응 가능성을 검토하세요.':c?.status==='PACE_ONLY'?'후보 자신의 동료 비교가 왜 약한지 먼저 확인하세요. 다른 차량에서의 우위가 선수 개인의 우위인지 판단이 필요합니다.':c?.status==='INSUFFICIENT'?'더 많은 공통 경기와 비교 가능한 랩을 확보한 후 재검토하세요. 표본 부족은 후보 능력 부족을 뜻하지 않습니다.':'조건별 방향·전후반·동료 비교 중 어디서 흔들리는지 아래 검증 결과를 확인하세요.'}</p><h4>경제적 의미</h4><p>성적 경쟁력은 배분금·스폰서십 기회와 관련될 수 있습니다. 이 자료로 영입 후 수익 증가액이나 인과 효과를 계산하지 않습니다.</p>`;
 $('coverage').innerHTML=`${row('시즌 원천 Race',N(cv.length))}${row('팀 유효 비교 경기',`${N(t.valid_races)} / ${N(t.source_races)}`)}${row('선수 유효 비교 경기',`${N(s.valid_races)} / ${N(s.race_entries)}`)}${row('선수 참조 연결 랩',N(s.valid_laps))}${row('피트 원천 없는 Race',N(cv.filter(r=>!r.pit_source_present).length))}${row('팀 포인트 미확정 행',N(t.unknown_point_rows))}${row('비교 가능한 시즌 선수',N(profiles().filter(p=>p.eligible).length))}<p style="margin-top:12px">팀·선수·동료·타이어의 유효 표본은 서로 다릅니다. 피트 원천이 있다는 사실만으로 수집이 완전하다고 검증된 것은 아닙니다.</p>`;
}
function renderSources(){
 const roles={sessions:'시즌·경기·서킷·일정 기준',drivers:'선수 신원과 경기 당시 소속',laps:'랩·섹터·페이스·일관성의 원천',stints:'타이어·나이·스틴트 연결과 추세',weather:'강수·시간 연결로 비교 랩 필터링',pit:'이벤트 횟수·피트레인·정지시간',starting_grid:'예선↔본경기 매핑 · 출발 대비 순위',session_result:'결과·출발/완주·Race 기본 배점',position:'보유·품질 점검. 이 테스트의 후보 계산에는 직접 미사용; 순위 타임라인 화면은 미구현',race_control:'SC/VSC·황기·적기·재시작 제외',intervals:'근접 차량 제한 민감도 · 상황 맥락'};
 $('sources').innerHTML=D.source_counts.map(s=>`<tr><td><code>${esc(s.source)}</code></td><td>${N(s.rows)}</td><td>${N(s.session_count)}</td><td style="text-align:left;white-space:normal;min-width:180px">${roles[s.source]||'원천 품질 확인'}</td></tr>`).join('');
 $('quality-boxes').innerHTML=[['원천 랩',D.summary.source_laps],['기본 정제 통과 랩',D.summary.baseline_clean_laps],['참조 집단 연결 랩',D.summary.baseline_reference_laps],['전체 팀·후보 비교',Object.keys(D.cases).length]].map(([label,n])=>`<div class="quality-box"><b>${N(n)}</b><span>${label} · 전 시즌 합계</span></div>`).join('');
 const remaining=key=>D.quality.find(q=>q.rule===key)?.remaining;
 $('data-issues').innerHTML=[['타이어 구간 미연결·모호',remaining('lap to stint'),'랩 · 성능 비교에서 제외'],['날씨 90초 연결 불가',remaining('weather 90sec'),'랩 · 건조 조건 비교에서 제외'],['격차 10초 연결 불가',remaining('interval 10sec'),'랩 · 근접 차량 제한 조건에서 제외'],['결과 분류 미확정',remaining('RESULT_CLASSIFICATION'),'선수·경기 · 포인트 N/A'],['출발 그리드 미연결',remaining('GRID_MISSING'),'선수·경기 · 순위 변화 N/A'],['피트 원천 미수집',D.coverage.filter(r=>!r.pit_source_present).length,'경기 · 0회로 대체하지 않음']].map(([a,b,c])=>row(esc(a),`${N(b)} <span class="dim">${c}</span>`)).join('');
}
init();
