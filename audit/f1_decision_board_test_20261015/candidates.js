// Compare real measurements, without introducing an aggregate score.
const CANDIDATE_PAGE_SIZE=5;
const CANDIDATE_METRICS=[
 ['relative_pace_pct','전체 페이스','%',3,'낮을수록 빠름'],
 ['teammate_delta_sec','팀 동료 대비','초/랩',3,'각자 본인의 팀 동료 대비 · 음수면 빠름'],
 ['adjusted_iqr_sec','일관성','초',3,'조건 보정 IQR · 낮을수록 편차 작음'],
 ['tyre_slope_sec_per_lap','타이어 유지','ms/랩',1,'필드 대비 페이스 변화 추세 · 낮을수록 상대 저하 작음'],
 ['race_base_points','포인트','점',0,'마지막 관측 소속 구간의 본경기 기본 포인트 · 높을수록 많음']
];
function initCandidateControls(){
 $('candidate-sort').addEventListener('click',e=>{
  const b=e.target.closest('[data-sort]');if(!b)return;
  $('priority').value=b.dataset.sort;page=0;selected='';render();
 });
}
function candidatePercentile(p,key){
 // A shared, visible population: this season's last observed profiles only.
 if(!p.eligible||!valid(metricValue(p,key)))return {pct:null,n:0};
 const group=profiles().filter(x=>x.eligible&&valid(metricValue(x,key)));
 const v=metricValue(p,key),better=group.filter(x=>key==='race_base_points'?metricValue(x,key)>v:metricValue(x,key)<v).length;
 return {pct:group.length?(better+1)/group.length*100:null,n:group.length};
}
function firstReview(p){
 const s=P.get(seat),c=caseFor(seat,p.membership_id),own=metricValue(p,'teammate_delta_sec');
 return Boolean(s?.eligible&&p.eligible&&c&&valid(c.delta)&&valid(own)&&Number(p.relative_pace_pct.toFixed(3))<Number(s.relative_pace_pct.toFixed(3))&&Number(own.toFixed(3))<0);
}
function candidateMetricRows(p,reference){
 const s=P.get(seat),active=$('priority').value;
 return CANDIDATE_METRICS.map(([key,label,unit,dec,meaning])=>{
  const v=metricValue(p,key),base=metricValue(s,key),shown=key==='tyre_slope_sec_per_lap'&&valid(v)?v*1000:v,baseShown=key==='tyre_slope_sec_per_lap'&&valid(base)?base*1000:base;
  const better=!reference&&valid(shown)&&valid(baseShown)&&(key==='race_base_points'?Number(shown.toFixed(dec))>Number(baseShown.toFixed(dec)):Number(shown.toFixed(dec))<Number(baseShown.toFixed(dec)));
  const {pct,n}=candidatePercentile(p,key);
  const value=valid(shown)?(key==='race_base_points'||key==='adjusted_iqr_sec'?num(shown,dec):signed(shown,dec))+unit:'N/A';
  return `<div class="candidate-metric-row ${active===key?'sort-active':''}" data-metric="${key}" data-value="${valid(v)?v:''}" data-better="${better}" title="${esc(meaning)}"><span class="candidate-metric-label">${label}</span><span class="candidate-metric-value">${value}${better?'<span class="metric-check" aria-label="기준 선수보다 좋은 관측값">✓</span>':''}</span><span class="candidate-percentile" title="같은 시즌 기본 표본 충족·해당 항목 유효 선수 ${n}명 중 공동 순위 기준">${valid(pct)?`상위 ${num(pct,Math.abs(pct-Math.round(pct))<1e-8?0:1)}%`:'상위 N/A'}</span></div>`;
 }).join('');
}
function candidateComparisonCard(p,reference=false){
 const c=reference?null:caseFor(seat,p.membership_id),first=!reference&&firstReview(p),isSelected=!reference&&selected===p.membership_id;
 const tag=reference?'article':'button',attrs=reference?`data-reference="${esc(p.membership_id)}"`:`type="button" data-candidate="${esc(p.membership_id)}" aria-pressed="${isSelected}"`;
 const label=reference?'기준 선수 · 비교할 자리':!p.eligible?'표본 부족':first?'1차 검토':'조건 확인';
 const hint=reference?'이 선수보다 좋은 관측값에 ✓ 표시':first?'기본 페이스·본인 동료 비교 조건 충족':!p.eligible?'8경기·200랩 기준 미달':'1차 검토 조건의 일부 미충족';
 return `<${tag} ${attrs} class="candidate candidate-detail ${reference?'reference-card':''} ${first?'first-review':''} ${isSelected?'selected':''}"><div class="candidate-card-head"><span class="name">${esc(p.full_name)}</span>${isSelected?'<span class="candidate-selected-tag">선택됨</span>':''}</div><div class="team">${esc(p.team_name)} · 유효 ${N(p.valid_races)}경기 · 참조 ${N(p.valid_laps)}랩</div><div class="candidate-metric-list">${candidateMetricRows(p,reference)}</div><div class="candidate-extra"><span>완주 / 출발</span><b>${N(p.finished_races)} / ${N(p.started_races)}</b><span>공통 경기</span><b>${reference?'기준':`${N(c?.common_races)}경기`}</b></div><div class="candidate-card-footer"><span class="review-tag ${reference?'reference':first?'pass':!p.eligible?'hold':''}" title="${esc(hint)}">${label}</span>${reference?'':badge(c)}</div><div class="candidate-card-hint">${hint}</div></${tag}>`;
}
function renderCandidateComparison(){
 const s=P.get(seat),key=$('priority').value,start=page*CANDIDATE_PAGE_SIZE,total=candidates.length;
 const eligible=profiles().filter(p=>p.eligible).length,poolLabel=$('pool').selectedOptions[0].text;
 $('candidate-caption').textContent=`점수를 합치지 않고 실제 기록과 ${year}년 선수 ${eligible}명 중 위치(상위 %)를 함께 봅니다. 먼저 볼 항목을 누르면 후보가 정렬됩니다.`;
 $('candidate-count').textContent=`후보 ${total}명 · ${poolLabel}`;
 $('candidate-sort').innerHTML='<span>먼저 볼 항목</span>'+CANDIDATE_METRICS.map(([k,label])=>`<button type="button" data-sort="${k}" aria-pressed="${k===key}">${label}</button>`).join('');
 $('candidate-rule').innerHTML=`<b>1차 검토 기준</b> ① 카드의 <strong>전체 페이스</strong>가 ${esc(s.full_name)}보다 빠르고 ② <strong>자기 팀 동료보다도 빠른</strong> 후보입니다. 공통 경기 등 표본 기준도 통과해야 표시합니다. <span class="muted">현재 범위: ${esc(poolLabel)}. 1차 검토와 아래의 11조건 안정성 판정은 별개이며 계약 가능성은 판단하지 않습니다.</span>`;
 $('candidate-grid').innerHTML=candidateComparisonCard(s,true)+candidates.slice(start,start+CANDIDATE_PAGE_SIZE).map(p=>candidateComparisonCard(p)).join('')+(!total?'<div class="empty">선택 범위에 후보가 없습니다. 후보 소속 범위를 바꿔 보세요.</div>':'');
 $('candidate-selection').innerHTML=selected?`<span>선택한 후보: <strong>${esc(P.get(selected).full_name)}</strong> · 카드를 누르면 04번 상세 검증도 바뀝니다.</span><a href="#evidence">선택한 후보 검증 보기 →</a>`:'후보 소속 범위를 바꾸면 다른 후보를 볼 수 있습니다.';
 $('page-info').textContent=total?`후보 ${start+1}–${Math.min(start+CANDIDATE_PAGE_SIZE,total)} / ${total}명 · 기준 선수는 매 페이지 첫 칸에 고정`:'후보 없음';
 $('prev').disabled=page===0;$('next').disabled=start+CANDIDATE_PAGE_SIZE>=total;
 $('candidate-guide').innerHTML=`<span><b class="good">✓</b> ${esc(s.full_name)}보다 좋은 관측값</span><span><b>상위 %</b> 작을수록 해당 지표의 순위가 높음</span><span><b>N/A</b> 표본·결과 부족으로 비교 보류</span>`;
 $('candidate-population').textContent=`상위 %는 이 시즌의 마지막 관측 소속 프로필 중 기본 표본을 충족한 ${eligible}명을 바탕으로, 항목별 유효 선수만 비교합니다. 동점은 같은 순위이며 종합점수가 아닙니다. 기준 선수와 후보의 관측 기간은 다를 수 있습니다.`;
}
