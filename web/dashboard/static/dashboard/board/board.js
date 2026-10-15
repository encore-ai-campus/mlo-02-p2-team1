const OP_COLUMNS=[
 {key:'lane_sec_relative',label:'피트레인 차이',unit:'초',dec:3,relative:true,warm:true,sample:'lane_sec_races',meaning:'같은 경기의 타 팀 기준 대비 피트레인 시간 차이 · +면 긴 방향'},
 {key:'lane_sec_median',label:'피트레인 시간',unit:'초',dec:2,warm:true,sample:'lane_sec_races',meaning:'피트레인 이용시간 중앙값 · 이동시간 포함 · 서킷 구성 영향 있음'},
 {key:'stop_sec_median',label:'정지시간',unit:'초',dec:2,warm:true,sample:'stop_sec_races',meaning:'유효 정지시간의 중앙값 · 피트레인 이용시간과 다른 지표'},
 {key:'stop_sec_relative',label:'정지시간 차이',unit:'초',dec:3,relative:true,warm:true,sample:'stop_sec_races',meaning:'같은 경기의 타 팀 기준 대비 정지시간 차이 · +면 긴 방향'},
 {key:'slow_pit_pct',label:'1초 초과 피트',unit:'%',dec:1,warm:true,meaning:'같은 경기의 타 팀 기준보다 피트레인 이용시간이 1초 넘게 긴 관측 이벤트 비율'},
 {key:'pit_event_mean',label:'경기당 피트',unit:'회',dec:2,sample:'pit_denominator',meaning:'집계 가능한 선수·경기당 평균 피트 이벤트 횟수 · 0회 포함'},
 {key:'median_observed_stint_laps',label:'스틴트 길이',unit:'랩',dec:1,meaning:'유효 스틴트의 관측 길이 중앙값 · 많고 적음이 전략 우열을 뜻하지 않음'},
 {key:'pit_comparable_events',label:'비교 이벤트',unit:'건',dec:0,meaning:'1초 초과 비율을 계산할 수 있었던 유효 피트 이벤트 수'}
];
function operationCell(t,col){
 const value=t[col.key],available=valid(value),values=teams.map(x=>x[col.key]).filter(valid),lo=Math.min(...values),hi=Math.max(...values);
 const shade=available&&col.warm?(hi>lo?(value-lo)/(hi-lo):.5):0;
 const formatted=available?(col.relative?signed(value,col.dec):num(value,col.dec))+col.unit:'N/A';
 const count=col.sample?`${N(t[col.sample])}${col.sample==='pit_denominator'?' 선수·경기':'경기'}`:col.key==='slow_pit_pct'?`${N(t.slow_events)} / ${N(t.pit_comparable_events)}건`:col.key==='median_observed_stint_laps'?`${N(t.valid_stints)} 스틴트`:'유효 피트 표본';
 return `<td data-op="${col.key}" data-value="${available?value:''}"><div class="ops-cell ${!available?'missing':col.warm?'heat':'neutral'}" style="--heat:${(12+shade*38).toFixed(1)}%" title="${esc(col.meaning)} · ${esc(count)}"><b>${formatted}</b><small>${available?count:'자료·표본 부족'}</small></div></td>`;
}
function renderOperations(){
 const t=teams.find(t=>t.team_name===team),ordered=[...teams].sort((a,b)=>lower(a.lane_sec_relative)-lower(b.lane_sec_relative)||a.team_name.localeCompare(b.team_name));
 $('ops-headers').innerHTML='<th scope="col" class="ops-team">팀</th>'+OP_COLUMNS.map(c=>`<th scope="col" title="${esc(c.meaning)}">${c.label}${c.relative?'<small>타 팀 기준 대비</small>':''}</th>`).join('');
 $('pit-table').innerHTML=ordered.map(x=>`<tr class="${x.team_name===team?'ops-selected':''}" data-team="${esc(x.team_name)}"><th scope="row" class="ops-team">${esc(x.team_name)}${x.team_name===team?'<span>선택한 팀</span>':''}</th>${OP_COLUMNS.map(col=>operationCell(x,col)).join('')}</tr>`).join('');
 $('ops-selection').innerHTML=`<strong>${esc(team)}</strong> · ${year}년 관측 ${N(t.source_races)}경기 중 피트레인 비교 ${N(t.lane_sec_races)}경기 / 정지시간 비교 ${N(t.stop_sec_races)}경기. ${valid(t.lane_sec_relative)?`피트레인 차이는 ${signed(t.lane_sec_relative)}초이며 +면 타 팀 기준보다 긴 방향입니다.`:'피트레인 상대 차이를 계산할 표본이 부족합니다.'}`;
 const bins=[{label:'0회',n:t.pit_zero_count,cls:'zero'},{label:'1회',n:t.pit_1,cls:'one'},{label:'2회',n:t.pit_2,cls:'two'},{label:'3회 이상',n:t.pit_3plus,cls:'many'}];
 const denom=t.pit_denominator||0;
 $('pit-distribution-title').textContent=`${team} · 선수별 경기당 피트 이벤트 횟수 분포`;
 $('pit-distribution').innerHTML=denom?bins.filter(b=>b.n>0).map(b=>{
  const pct=b.n/denom*100;return `<div class="pit-bin ${b.cls}" style="width:${pct}%" data-count="${b.n}" data-percent="${pct}" title="${b.label} · ${N(b.n)}건 / ${N(denom)}건 (${num(pct,1)}%)">${pct>=13?`${b.label} · ${num(pct,1)}%`:''}</div>`;
 }).join(''):'<span class="ops-no-distribution">분포를 계산할 수 있는 표본이 없습니다.</span>';
 $('pit-distribution-legend').innerHTML=bins.map(b=>`<span class="pit-bin-legend"><i class="${b.cls}"></i><b>${b.label}</b> ${num(denom?100*b.n/denom:null,1)}% <small>(${N(b.n)}건)</small></span>`).join('');
 $('pit-distribution-note').textContent=`분모: 피트 원천이 있고 집계 가능한 선수·경기 ${N(denom)}건. 0회도 포함합니다. 피트 원천이 없는 경기를 0회로 채우지 않습니다. 원천이 있다는 사실만으로 수집 완전성이 검증된 것은 아닙니다.`;
}

// Plain-language reading layer over the unchanged case verdicts and evidence.
const TRUST_COPY={
 REPEATED:['여러 비교에서 후보의 우위가 반복됩니다','페이스와 후보 본인의 동료 비교에서 검토할 근거가 관측됩니다.','차량 차이를 더 분리할 근거와 계약·비용·적응 가능성을 다음으로 확인하세요.'],
 PACE_ONLY:['빠른 기록은 반복되지만, 선수 개인의 우위는 더 확인해야 합니다','후보가 기존 차량에서 더 빨랐다는 결과와, 선수 개인이 더 우수하다는 판단은 구분해야 합니다.','후보가 자기 팀 동료와 비교해도 우위인지 먼저 확인하세요. 차량의 이점이 얼마나 섞였는지는 이 자료만으로 분리하기 어렵습니다.'],
 UNCERTAIN:['이 조합은 결론을 서두르기 어렵습니다','조건·경기 표본·시즌 전후반을 바꾸면 근거가 흔들리거나 확실하지 않습니다.','아래 세 질문 중 판단이 보류되거나 방향이 달라진 부분부터 확인하세요. 한 가지 평균이나 순위로 영입을 결정하기 어렵습니다.'],
 INSUFFICIENT:['아직 비교할 자료가 충분하지 않습니다','필요한 경기·랩 표본을 채우지 못해 빠름과 느림을 판정하지 않았습니다.','공통 경기와 조건을 맞춘 랩을 더 확보한 뒤 다시 확인하세요. 자료 부족은 후보 능력 부족을 뜻하지 않습니다.'],
 NO_ADVANTAGE:['현재 비교에서 후보가 더 빠르다는 근거가 없습니다','기본 조건에서 후보의 페이스 우위가 확인되지 않았습니다.','페이스 외의 보완 역량을 검토하거나 다른 후보와 비교해 보세요. 이 판정이 선수의 모든 역량에 대한 평가는 아닙니다.']
};
function trustQuestion(number,title,state,label,explanation,fact){
 const symbol={pass:'✓',different:'×',hold:'?'}[state];
 return `<article class="trust-question ${state}" data-trust-question="${number}" data-state="${state}"><div class="trust-question-title"><span>${number}</span><h3>${title}</h3></div><div class="trust-question-result"><span aria-hidden="true">${symbol}</span><b>${label}</b></div><p>${explanation}</p><small>${fact}</small></article>`;
}
function renderTrustEvidence(){
 const c=caseFor(seat,selected),s=P.get(seat),p=P.get(selected);
 if(!c||!p){$('evidence-body').innerHTML='<h2>이 후보를 더 검토할 근거가 있을까?</h2><div class="empty">03번에서 후보를 선택하면 결론과 근거를 볼 수 있습니다.</div>';return;}
 const [headline,description,next]=TRUST_COPY[c.status],tone=ST[c.status][1],base=valid(c.delta)&&valid(c.low)&&valid(c.high);
 const paceState=!base?'hold':c.high<0?'pass':c.low>=0?'different':'hold';
 const paceLabel=!base?'비교 표본 부족':paceState==='pass'?'같은 경기에서도 빠른 방향':paceState==='different'?'더 빠르다는 근거 없음':'빠름·느림을 단정하기 어려움';
 const paceText=!base?'두 선수의 유효 표본과 공통 경기 기준을 먼저 채워야 합니다.':paceState==='pass'?`${N(c.common_races)}개 공통 경기에서 비교했고, 경기를 다시 뽑아 계산해도 후보가 빠른 쪽에 범위가 놓입니다.`:paceState==='different'?'기본 비교의 범위가 기준 선수와 같거나 느린 쪽에 있습니다.':'중앙값 하나는 빠르게 나와도, 경기를 다시 뽑아 계산한 범위가 0을 포함해 빠른 방향으로 단정하기 어렵습니다.';
 const halves=valid(c.first)&&valid(c.second),repeatState=!base||c.missing||!halves?'hold':c.faster===11&&c.first<0&&c.second<0?'pass':'different';
 const repeatLabel=repeatState==='pass'?'조건·전후반에서 빠른 방향 유지':repeatState==='different'?'조건·기간에 따라 방향이 달라짐':'모든 조건·기간을 확인하기 어려움';
 const repeatText=!base?'기본 비교의 표본이 부족해 반복 여부도 판단을 보류합니다.':c.missing?`11조건 중 ${N(c.missing)}조건은 표본 기준에 미달합니다. 확인하지 못한 조건을 통과한 것으로 세지 않습니다.`:!halves?'11가지 조건은 계산했지만 시즌 전반·후반을 각각 비교할 표본이 부족합니다.':repeatState==='pass'?'정제 조건 11가지를 바꾸고 시즌 전반·후반을 나눠도 후보가 빠른 방향입니다.':'일부 정제 조건 또는 시즌 전후반에서 후보가 더 빠른 방향을 유지하지 못했습니다.';
 const ownCI=valid(p.own_low)&&valid(p.own_high),ownPass=ownCI&&p.own_high<0&&c.own_negative===11&&!c.own_missing;
 const ownState=ownPass?'pass':!ownCI||c.own_missing?'hold':p.own_low>=0||c.own_negative<11?'different':'hold';
 const ownLabel=ownState==='pass'?'본인 동료 비교에서도 우위 반복':ownState==='different'?'동료 대비 우위가 반복되지 않음':'선수 개인의 우위를 더 확인해야 함';
 const ownText=!ownCI?'후보 자신의 팀 동료와 조건을 맞춘 비교 표본이 부족합니다.':c.own_missing?`후보 본인의 동료 비교에서도 ${N(c.own_missing)}조건은 판단할 수 없습니다.`:ownPass?'본인 동료 대비 11조건이 모두 빠른 방향이고, 기본 비교의 범위도 빠른 쪽에 있습니다. 그래도 차량 영향을 완전히 분리한 것은 아닙니다.':p.own_low>=0?'후보 자신의 동료보다 빠르다는 방향이 기본 비교에서 확인되지 않습니다.':c.own_negative<11?'후보가 자기 팀 동료보다 빠른지에 대한 방향이 조건에 따라 달라집니다.':'후보 자신의 동료 대비 범위가 빠른 쪽과 느린 쪽을 함께 포함합니다.';
 $('evidence-body').innerHTML=`<h2 class="trust-heading">이 후보를 더 검토할 근거가 있을까?</h2><div class="selected-title trust-selection"><h3>${esc(p.full_name)} → ${esc(team)}</h3><p>비교 기준: ${esc(s.full_name)} · 같은 시즌의 관측 기록</p></div><div class="trust-conclusion ${tone}" data-verdict="${c.status}"><span class="trust-overline">지금 읽을 결론</span><h3>${headline}</h3><p>${description}</p><div class="chips">${badge(c)}<span class="chip">공통 ${N(c.common_races)}경기</span></div></div><p class="trust-instruction">아래 세 질문을 순서대로 읽으면 됩니다. <b>✓는 관측 근거가 확인됐다는 뜻</b>이며, 영입 후 성과를 보장하지 않습니다.</p><div class="trust-questions">${trustQuestion(1,'같은 경기끼리 비교해도 빠른가?',paceState,paceLabel,paceText,base?`후보 − 기준 선수 ${signed(c.delta)}%p · 음수면 후보가 빠름`:'기본 기준: 두 선수 각각 8경기·200랩, 공통 경기 8개 이상')}${trustQuestion(2,'조건이나 기간을 바꿔도 유지될까?',repeatState,repeatLabel,repeatText,`후보가 빠른 조건 ${c.faster}/11 · 판단 불가 ${c.missing}조건`)}${trustQuestion(3,'자기 팀 동료와 비교해도 빠른가?',ownState,ownLabel,ownText,`후보 자신의 동료 비교 ${N(p.teammate_races)}경기 · 별도 표본`)}</div><div class="trust-next"><b>그래서 지금 할 일</b><p>${next}</p></div>${c.status==='INSUFFICIENT'?`<p class="trust-missing">부족한 항목: ${c.reasons.map(esc).join(' · ')}</p>`:''}<div class="trust-more-heading"><h3>숫자와 그래프가 필요할 때만 펼쳐보세요</h3><p>결론에 쓰인 기존 근거를 아래에서 확인할 수 있습니다.</p></div><details class="trust-details" id="trust-races"><summary>① 경기별 결과와 빠름·느림의 범위 보기</summary><p>막대가 0 아래면 후보가 빠른 경기입니다. 위로 올라가면 기준 선수가 빠른 경기입니다.</p><div id="race-delta" class="chart-scroll">${deltaChart(c,p,s)}</div><div class="legend"><span><i class="dot"></i>후보가 빠름</span><span><i class="dot" style="background:var(--coral)"></i>기준 선수가 빠름</span></div><div class="big-compare">${stat('기본 차이의 95% 재표집 구간',range(c.low,c.high),'%p · 경기 단위 2,000회 다시 추출')}${stat('시즌 일정 전반 / 후반',`${signed(c.first)} / ${signed(c.second)}`,'%p · 각 반기 공통 4경기 이상 필요')}${stat('한 경기씩 빼 본 차이의 범위',range(c.loo_min,c.loo_max),'%p · 특정 한 경기 의존 여부 확인')}</div><p>95% 재표집 구간은 관측 경기를 다시 뽑아 계산한 차이의 범위입니다. 0 양쪽에 걸치면 빠름·느림을 확실히 나누기 어렵습니다. 이적 후 효과에 대한 확률은 아닙니다.</p></details><details class="trust-details" id="trust-conditions"><summary>② 정제 조건 11가지를 바꾼 결과 보기</summary><p>조건마다 두 선수의 표본 기준을 통과해야 숫자를 표시합니다. 차이는 후보 − 기준 선수(%p)이며, N/A는 표본 부족입니다.</p><div class="scenario-grid">${c.scenarios.map((v,i)=>`<div class="scenario ${v[0]===null?'na':v[0]<0?'pass':'fail'}"><div>${VN[i]}<em>${v[0]===null?'판단 보류':v[0]<0?'후보가 빠른 방향':v[0]>0?'기준 선수가 빠른 방향':'같은 값'} · 공통 ${v[1]}경기</em><em>후보 본인 동료 대비 ${signed(v[2])}초</em></div><strong>${signed(v[0])}</strong></div>`).join('')}</div></details><details class="trust-details" id="trust-own"><summary>③ 후보 본인의 동료 비교와 다른 역량 보기</summary>${stat('후보 본인 동료 대비 95% 구간',range(p.own_low,p.own_high),'초 · 음수면 본인 동료보다 빠름 · '+N(p.teammate_races)+'경기')}<p>같은 팀의 차량을 비교하는 추가 근거입니다. 상대 선수·경기·랩 표본이 다르므로 다른 후보의 동료 대비 값과 직접 대결한 기록처럼 읽지 않습니다.</p><div class="grid2">${stat('타이어 추세 차이 · 후보 − 기준',`${signed(c.tyre_delta,4)} 초/랩`,`같은 경기·타이어 ${N(c.tyre_races)}경기 · 95% ${range(c.tyre_low,c.tyre_high)}`)}${stat('일관성 차이 · 후보 − 기준',`${signed(c.iqr_delta)} 초`,`공통 경기의 조건 보정 IQR · 95% ${range(c.iqr_low,c.iqr_high)}`)}</div><p>두 보조 지표는 음수일 때 후보가 낮은 관측값입니다. 타이어는 같은 경기·컴파운드 4경기 이상, 일관성은 공통 8경기 이상이 필요합니다. 이 값들까지 11조건 반복 검증을 한 것은 아닙니다.</p></details><p class="trust-scope-note">이 화면은 기존 기록의 내부 검증입니다. 차량 차이·이적 후 적응·계약·비용을 통제한 영입 효과나 독립된 미래 경기의 성과를 검증한 결과는 아닙니다.</p>`;
}

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

// Introductory stories use the frozen metrics. They do not change fit verdicts.
function middle(values){const a=values.filter(valid).map(Number).sort((a,b)=>a-b),n=a.length;return n?(n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2):null;}
function storyMetric(value,unit,label){return `<div class="story-metric"><strong>${value}<small>${unit}</small></strong><span>${label}</span></div>`;}
function storyCard({index,topic,guess,state,answer,metrics,chart,note,meaning}){
 const signs={match:'O',different:'X',hold:'?'},labels={match:'관측값과 일치',different:'관측값과 다름',hold:'판단 보류'};
 return `<article class="question story-card" data-story="${index}" data-verdict="${state}"><div class="q-index">처음 생각 ${index} · ${topic}</div><h3>“${guess}”</h3><div class="story-answer ${state}"><span class="story-sign" aria-hidden="true">${signs[state]}</span><div><b>${labels[state]}</b><p>${answer}</p></div></div><div class="story-metrics">${metrics.join('')}</div><div class="story-chart">${chart}</div><p class="story-chart-note">${note}</p><p class="interpretation"><b>그래서</b> ${meaning}</p></article>`;
}
function miniBars(data,{unit='',digits=2,signedValues=true,label='관측값 비교',rowHeight=19,fontSize=10}={}){
 if(!data.length)return '<div class="empty">비교 가능한 데이터가 없습니다.</div>';
 const width=410,left=122,right=65,plot=width-left-right,rowH=rowHeight,height=data.length*rowH+8;
 const values=data.filter(d=>valid(d.value)).map(d=>Math.abs(d.value)),max=Math.max(.000001,...values);
 const zero=signedValues?left+plot/2:left;
 return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(label)}">${signedValues?`<line x1="${zero}" x2="${zero}" y1="0" y2="${height-5}" stroke="var(--dim)" stroke-dasharray="2 3"/>`:''}${data.map((d,i)=>{
  const y=i*rowH+3,bw=valid(d.value)?Math.abs(d.value)/max*(signedValues?plot/2:plot):0,x=signedValues&&d.value<0?zero-bw:zero,col=d.active?'var(--mint)':'var(--dim)';
  return `<text x="0" y="${y+11}" font-size="${fontSize}" style="fill:${d.active?'var(--text)':'var(--muted)'}">${esc(d.name)}</text><rect x="${left}" y="${y+1}" width="${plot}" height="10" rx="3" fill="var(--surface2)"/>${valid(d.value)?`<rect x="${x}" y="${y+1}" width="${Math.max(.7,bw)}" height="10" rx="3" fill="${col}" opacity="${d.active?1:.65}"/>`:''}<text x="${width}" y="${y+11}" text-anchor="end" font-size="${fontSize}" style="fill:${d.active?'var(--mint)':'var(--muted)'}">${valid(d.value)?(signedValues?signed(d.value,digits):num(d.value,digits))+unit:'N/A'}</text>`;
 }).join('')}</svg>`;
}
function renderStoryQuestions(){
 const t=teams.find(t=>t.team_name===team),s=P.get(seat),p=P.get(selected),c=caseFor(seat,selected);
 const paceTeams=teams.filter(t=>t.eligible&&valid(t.relative_pace_pct)).sort((a,b)=>a.relative_pace_pct-b.relative_pace_pct);
 const paceRank=t.eligible&&valid(t.relative_pace_pct)?1+paceTeams.filter(x=>x.relative_pace_pct<t.relative_pace_pct).length:null;
 const median=middle(paceTeams.map(t=>t.relative_pace_pct)),paceOK=valid(paceRank)&&paceTeams.length>=5,paceSlower=paceOK&&t.relative_pace_pct>median;
 const nearMedian=paceOK&&Math.abs(t.relative_pace_pct-median)<.0005;
 const paceState=!paceOK||nearMedian?'hold':paceSlower?'match':'different';
 const tyreOK=valid(t.tyre_slope_sec_per_lap)&&t.tyre_valid_races>=4&&t.valid_stints>=8,tyreMS=t.tyre_slope_sec_per_lap*1000;
 const tyreState=!tyreOK||Math.abs(tyreMS)<.05?'hold':tyreMS>0?'match':'different';
 const own=metricValue(s,'teammate_delta_sec'),ownCI=valid(own)&&valid(s.own_low)&&valid(s.own_high);
 const ownState=!ownCI?'hold':s.own_low>0?'match':s.own_high<0?'different':'hold';
 const laneOK=valid(t.lane_sec_relative)&&t.lane_sec_races>0,laneState=!laneOK||Math.abs(t.lane_sec_relative)<.0005?'hold':t.lane_sec_relative>0?'match':'different';
 const pointsRank=valid(t.race_base_points)?1+teams.filter(x=>x.race_base_points>t.race_base_points).length:null;
 const pointsUnknown=teams.some(x=>x.unknown_point_rows>0),pointsState=!paceOK||!valid(pointsRank)||pointsUnknown?'hold':paceRank===pointsRank?'match':'different';
 const idx=teams.findIndex(x=>x.team_name===team),pointNeighbors=teams.slice(Math.max(0,idx-2),Math.min(teams.length,idx+3));
 const conditionState=!c||c.missing>0?'hold':c.faster===11?'match':'different';
 const shortNames=['기본 정제','날씨 60초','날씨 120초','타이어 나이 맞춤','참조 구간 3랩','복구 랩 제외','재시작 추가 제외','동료 나이 차 ≤1','근접 차량 제한','20랩·10경기','불확실 경기 제외'];
 $('overview-title').textContent=`${team} · 처음 생각과 데이터 결과`;
 $('questions').innerHTML=[
 storyCard({index:1,topic:'팀 진단',guess:`${esc(team)}의 주행 페이스는 팀들 중 중간보다 느릴 것이다`,state:paceState,
  answer:!paceOK?'비교 가능한 팀 또는 선택 팀의 표본이 부족합니다.':nearMedian?'팀 중앙값과 차이가 표시 정밀도 안에 있습니다.':`유효 ${paceTeams.length}팀 중 빠른 순서 ${paceRank}위입니다. 비교 팀 중앙값보다 ${paceSlower?'느린':'빠른'} 방향입니다.`,
  metrics:[storyMetric(t.eligible?signed(t.relative_pace_pct):'N/A','%','필드 상대 페이스 · 낮을수록 빠름'),storyMetric(valid(paceRank)?`${paceRank}/${paceTeams.length}`:'N/A','위','같은 시즌 유효 팀 내 페이스 순위')],
  chart:miniBars(paceTeams.map(x=>({name:x.team_name,value:x.relative_pace_pct,active:x.team_name===team})),{unit:'%',digits:2,label:'전체 팀 필드 상대 페이스'}),
  note:`${N(t.valid_races)}개 유효 경기 · ${N(t.valid_laps)}개 참조 연결 랩. 0은 참조 집단 기준이며, 막대 순서는 빠른 팀부터입니다.`,
  meaning:!paceOK?'현재 표본으로는 팀의 상대 위치를 단정하기 어렵습니다.':nearMedian?'표시 정밀도에서 중간과 뚜렷한 차이가 없어 느린 쪽인지 빠른 쪽인지 판단을 보류합니다.':paceSlower?'주행 경쟁력의 격차는 관측됩니다. 이 격차가 차량 때문인지 선수 때문인지는 동료 비교와 함께 봐야 합니다.':'비교 팀의 중간보다 느리다는 가설은 지지되지 않습니다. 느리다고 미리 정해 놓고 영입 필요성을 설명하지 않습니다.'}),
 storyCard({index:2,topic:'타이어',guess:'타이어를 오래 쓸수록 다른 차량보다 페이스가 더 떨어질 것이다',state:tyreState,
  answer:!tyreOK?'타이어 추세를 비교할 4경기·8스틴트 표본 기준에 미달합니다.':Math.abs(tyreMS)<.05?'상대 페이스 변화가 표시 정밀도 안에 있어 방향 판단을 보류합니다.':`타이어 1랩 사용 증가당 필드 대비 ${num(Math.abs(tyreMS),1)}ms ${tyreMS>0?'느려지는':'유지·개선되는'} 방향이 관측됩니다.`,
  metrics:[storyMetric(tyreOK?signed(tyreMS,1):'N/A','ms/랩','필드 대비 페이스 저하 추세'),storyMetric(num(t.median_observed_stint_laps,1),'랩','관측 스틴트 길이 중앙값')],
  chart:miniBars(teams.filter(x=>valid(x.tyre_slope_sec_per_lap)&&x.tyre_valid_races>=4&&x.valid_stints>=8).sort((a,b)=>a.tyre_slope_sec_per_lap-b.tyre_slope_sec_per_lap).map(x=>({name:x.team_name,value:x.tyre_slope_sec_per_lap*1000,active:x.team_name===team})),{unit:'ms',digits:1,label:'전체 팀 타이어 필드 대비 추세 · ms/랩'}),
  note:`${N(t.tyre_valid_races)}경기 · ${N(t.valid_stints)}개 유효 스틴트. +면 필드 대비 페이스 저하 방향이며, 1ms는 0.001초입니다.`,
  meaning:tyreState==='match'?'타이어 사용 구간에서 약점이 있는지 추가 검토할 이유가 있습니다. 연료·차량·표본 구성의 영향이 있어 타이어 관리가 원인이라고 확정하지 않습니다.':tyreState==='different'?'이 지표만으로 타이어 관리를 약점이라고 보기 어렵습니다. 한 바퀴 페이스와 동료 비교에서 보완점을 따로 확인하세요.':'타이어를 잘 관리한다거나 못 관리한다고 결론 내리기 전에 비교 표본을 더 확인해야 합니다.'}),
 storyCard({index:3,topic:'라인업',guess:`${esc(s.full_name)}의 페이스는 팀 동료보다 느릴 것이다`,state:ownState,
  answer:!ownCI?'동료와 조건을 맞춘 유효 경기 또는 재표집 구간이 부족합니다.':ownState==='hold'?`중앙값은 ${signed(own)}초지만 95% 구간(${range(s.own_low,s.own_high)}초)이 0을 포함해 빠름·느림을 단정하기 어렵습니다.`:`동료 대비 95% 구간이 ${ownState==='match'?'0보다 큰':'0보다 작은'} 쪽에 있습니다. 관측상 ${ownState==='match'?'느린':'빠른'} 방향을 뒷받침합니다.`,
  metrics:[storyMetric(signed(own),'초','동료 대비 차이 · +면 기준 선수가 느림'),storyMetric(N(s.teammate_races),'경기','동료와 조건을 맞춘 비교 표본')],
  chart:miniBars(players.map(x=>({name:x.full_name,value:metricValue(x,'relative_pace_pct'),active:x.membership_id===seat})).sort((a,b)=>lower(a.value)-lower(b.value)),{unit:'%',digits:2,label:'같은 팀 관측 선수의 필드 상대 페이스'}),
  note:'막대는 각 선수의 필드 상대 페이스입니다. 위의 동료 대비 차이는 같은 랩·타이어를 맞춘 별도 표본으로 계산하므로 두 막대를 빼서 구하는 값과 다를 수 있습니다.',
  meaning:ownState==='match'?'이 선수를 기준으로 후보를 비교할 관측 근거가 있습니다. 팀 성적 저하의 책임이나 교체 필요성이 확정되는 것은 아닙니다.':ownState==='different'?'동료보다 느리다는 가설과 다른 결과입니다. 선택한 자리가 반드시 교체 우선순위라는 뜻은 아닙니다.':'중앙값이 느리게 나와도 우열이 확실하지 않을 수 있습니다. 이 선수 때문에 성적이 나쁘다고 단정하지 않습니다.'}),
 storyCard({index:4,topic:'피트 운영',guess:'이 팀의 피트레인 이용시간은 같은 경기의 다른 팀보다 길 것이다',state:laneState,
  answer:!laneOK?'같은 경기의 타 팀과 비교할 피트레인 시간 표본이 없습니다.':laneState==='hold'?'타 팀 기준과의 차이가 표시 정밀도 안에 있습니다.':`같은 경기의 타 팀 기준 대비 ${num(Math.abs(t.lane_sec_relative),3)}초 ${t.lane_sec_relative>0?'길게':'짧게'} 관측됐습니다.`,
  metrics:[storyMetric(signed(t.lane_sec_relative),'초','피트레인 상대 차이 · +면 긴 방향'),storyMetric(num(t.slow_pit_pct,1),'%','타 팀 기준보다 1초 초과한 이벤트')],
  chart:miniBars(teams.filter(x=>valid(x.lane_sec_relative)).sort((a,b)=>a.lane_sec_relative-b.lane_sec_relative).map(x=>({name:x.team_name,value:x.lane_sec_relative,active:x.team_name===team})),{unit:'초',digits:2,label:'전체 팀 피트레인 상대 시간'}),
  note:`상대 시간 ${N(t.lane_sec_races)}경기 · 1초 초과 이벤트 ${N(t.slow_events)}/${N(t.pit_comparable_events)}개. 시간에는 피트레인 이동도 포함됩니다.`,
  meaning:laneState==='match'?'피트 운영 환경을 살펴볼 근거는 있습니다. 혼잡·정비·경기 상황이 섞여 있어 크루나 선수 실력으로 바로 귀속할 수 없습니다.':laneState==='different'?'피트레인 이용시간이 전반적으로 길다는 가설과 다릅니다. 드물게 긴 이벤트가 있었는지는 옆의 비율로 따로 확인하세요.':'표본을 더 확인한 뒤 판단하세요. 원천이 없는 경기를 피트 0회로 바꾸지 않습니다.'}),
 storyCard({index:5,topic:'포인트',guess:'주행 페이스 순위와 본경기 기본 포인트 순위는 같을 것이다',state:pointsState,
  answer:pointsUnknown?`페이스 ${valid(paceRank)?paceRank:'N/A'}위, 관측 포인트 ${valid(pointsRank)?pointsRank:'N/A'}위입니다. 시즌에 미확정 결과가 있어 최종 판정을 보류합니다.`:!paceOK?'페이스 순위를 비교할 표본이 부족합니다.':`페이스 ${paceRank}위, 본경기 기본 포인트 ${pointsRank}위로 ${paceRank===pointsRank?'이번 선택에서는 같습니다':'서로 다릅니다'}.`,
  metrics:[storyMetric(N(t.race_base_points),'점',`${year} 본경기 기본 포인트${t.unknown_point_rows?' · 일부 미확정':''}`),storyMetric(valid(pointsRank)?N(pointsRank):'N/A','위','관측 기본 포인트 기준 · 공동 순위 가능')],
  chart:miniBars(pointNeighbors.map(x=>({name:x.team_name,value:x.race_base_points,active:x.team_name===team})),{unit:'점',digits:0,signedValues:false,label:'선택 팀 주변의 본경기 기본 포인트'}),
  note:'선택 팀 주변의 포인트 비교입니다. Sprint·보너스·예외 배점 등을 제외한 재구성 값이며 공식 챔피언십 전체 순위가 아닙니다.',
  meaning:pointsState==='different'?'한 바퀴 페이스가 실제 성적 순위로 그대로 이어지지는 않습니다. 완주·출발 위치·피트 등 경기 맥락을 함께 확인해야 합니다.':pointsState==='match'?'이번에는 순위가 같지만 항상 같은 것은 아닙니다. 이 값은 현재 성적을 설명하며 후보 영입 후 늘어날 점수를 예측하지 않습니다.':'빠르기 순위와 성적 순위를 비교하려면 미확정 결과와 유효 표본을 먼저 확인해야 합니다.'}),
 storyCard({index:6,topic:'결론의 안정성',guess:'정제 기준을 바꿔도 선택한 후보의 공통 경기 페이스가 더 빠를 것이다',state:conditionState,
  answer:!c?'선택할 후보가 없습니다.':c.missing?`${esc(p.full_name)} 비교에서 ${c.missing}조건은 표본 부족으로 판단할 수 없습니다.`:c.faster===11?`${esc(p.full_name)}는 11가지 조건 모두에서 기준 선수보다 빠른 관측값입니다.`:c.faster===0?`${esc(p.full_name)}는 유효 11조건 중 더 빠른 조건이 없습니다.`:`${esc(p.full_name)}의 빠른 방향은 ${c.faster}/11조건입니다. 조건에 따라 방향이 달라집니다.`,
  metrics:[storyMetric(c?`${c.faster}/11`:'N/A','조건','후보가 더 빠른 조건 수 · N/A는 별도'),storyMetric(c?N(c.common_races):'N/A','경기','기본 조건의 공통 경기')],
  chart:miniBars(c?c.scenarios.map((v,i)=>({name:shortNames[i],value:v[0],active:i===0})):[],{unit:'%p',digits:2,label:'정제 조건별 후보 − 기준 선수 페이스 차이'}),
  note:`후보: ${esc(p?.full_name||'없음')} · 음수면 후보가 빠릅니다. 각 조건의 표본 기준 미달은 N/A로 표시합니다.`,
  meaning:!c?'후보를 선택한 뒤 결과를 확인하세요.':conditionState==='hold'?'모든 조건에서 유지되는지 아직 확인할 수 없습니다. 아래 상세 검증에서 부족한 표본과 이유를 보세요.':conditionState==='different'?'한 가지 정제 조건에서 나온 결과만으로 후보 우위를 확정하기 어렵습니다. 아래 구간·전후반도 함께 확인하세요.':`조건별 방향은 유지됩니다. 전체 판정은 ‘${esc(ST[c.status][0])}’이며 동료 비교·재표집·전후반까지 확인해야 합니다. <a href="#evidence">상세 검증 보기 →</a>`})
 ].join('');
}
function renderStoryPoints(){
 const t=teams.find(t=>t.team_name===team),rankOf=x=>1+teams.filter(y=>y.race_base_points>x.race_base_points).length,rank=rankOf(t);
 const above=teams.filter(x=>x.race_base_points>t.race_base_points).sort((a,b)=>a.race_base_points-b.race_base_points)[0];
 const below=teams.filter(x=>x.race_base_points<t.race_base_points).sort((a,b)=>b.race_base_points-a.race_base_points)[0];
 const ties=teams.filter(x=>x.race_base_points===t.race_base_points),band=teams.filter(x=>Math.abs(x.race_base_points-t.race_base_points)<=10);
 const bandMin=Math.min(...band.map(rankOf)),bandMax=Math.max(...band.map(rankOf)),span=Math.max(...band.map(x=>x.race_base_points))-Math.min(...band.map(x=>x.race_base_points));
 let competition;
 if(band.length>1&&span>0){
  competition=`${esc(team)}은 <strong>${bandMin}~${bandMax}위 ${band.length}개 팀이 ${N(span)}점 안에 모인 경쟁 구간</strong>에 있습니다. 완주·순위 등 경기 결과의 차이를 포인트 경쟁과 함께 살펴볼 만한 상황입니다.`;
 }else if(band.length>1){
  competition=`${esc(team)}을 포함한 <strong>${band.length}개 팀이 ${N(t.race_base_points)}점으로 공동 ${rank}위</strong>입니다. 같은 포인트가 차량·선수의 경쟁력까지 같다는 뜻은 아니므로 주행 지표와 별도로 읽어야 합니다.`;
 }else{
  const neighbor=above||below,gap=neighbor?Math.abs(neighbor.race_base_points-t.race_base_points):null;
  competition=`${esc(team)}은 관측 기본 포인트 <strong>${rank}위</strong>입니다. 선택 팀의 ±10점 안에는 다른 팀이 없습니다.${neighbor?` ${above?'가까운 상위 팀':'다음 하위 팀'} ${esc(neighbor.team_name)}와 ${N(gap)}점 차이여서 작은 점수 차의 접전으로 설명하기는 어렵습니다.`:''}`;
 }
 $('points-chart').innerHTML=`<p class="points-chart-title">${year} 팀별 본경기 기본 포인트 <span class="dim">(Sprint·보너스 제외)</span></p>${miniBars(teams.map(x=>({name:x.team_name+(x.unknown_point_rows?' *':''),value:x.race_base_points,active:x.team_name===team})),{unit:'점',digits:0,signedValues:false,rowHeight:26,fontSize:11,label:`${year} 전체 팀 본경기 기본 포인트`})}`;
 $('point-context').innerHTML=`<div class="point-gap-grid">${stat('기본 포인트 순위',`${ties.length>1?'공동 ':''}${rank}위`,`${teams.length}개 관측 팀 기준`)}${stat(above?`${rankOf(above)}위와의 차이`:'상위 팀과의 차이',above?`−${N(above.race_base_points-t.race_base_points)}점`:'—',above?`${esc(above.team_name)}보다 적음`:'상위 팀 없음')}${stat(below?`${rankOf(below)}위와의 차이`:'하위 팀과의 차이',below?`+${N(t.race_base_points-below.race_base_points)}점`:'—',below?`${esc(below.team_name)}보다 많음`:'하위 팀 없음')}</div><div class="point-explain"><b>이 경쟁 위치를 어떻게 읽을까?</b><p>${competition}</p><p>선택한 선수와 후보의 페이스·동료 비교를 이 성적 맥락과 함께 검토할 수 있습니다. 팀 성적은 <strong>팀 배분금·스폰서십 기회</strong>와 연결해 해석할 수 있는 배경입니다.</p></div><p class="point-economic-note">본경기 기본 포인트로 본 경쟁 위치입니다. 실제 배분 조건·계약·비용 자료가 없어 영입 후 포인트 증가나 배분금·스폰서 수익은 추정하지 않습니다. 후보가 다른 팀에서 얻은 포인트를 선택 팀에 더하지 않습니다.</p>`;
 $('points-meaning').innerHTML=`<b>비교 구간을 정한 기준</b> 선택한 팀의 관측 기본 포인트 ±10점 안에 있는 팀을 함께 봅니다. 순위·점수 차이와 묶인 팀 수는 시즌·팀 선택에 따라 다시 계산됩니다.${year===2026?' <strong>2026년은 10월 14일 기준 누적 결과입니다.</strong>':''}${teams.some(x=>x.unknown_point_rows>0)?' <strong>미확정 결과가 남아 있어 관측 합계와 순위는 불완전할 수 있습니다.</strong>':''}`;
}

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
 const roles={sessions:'시즌·경기·서킷·일정 기준',drivers:'선수 신원과 경기 당시 소속',laps:'랩·섹터·페이스·일관성의 원천',stints:'타이어·나이·스틴트 연결과 추세',weather:'강수·시간 연결로 비교 랩 필터링',pit:'이벤트 횟수·피트레인·정지시간',starting_grid:'예선↔본경기 매핑 · 출발 대비 순위',session_result:'결과·출발/완주·Race 기본 배점',position:'보유·품질 점검. 현재 후보 계산에는 직접 미사용; 순위 타임라인 화면은 미구현',race_control:'SC/VSC·황기·적기·재시작 제외',intervals:'근접 차량 제한 민감도 · 상황 맥락'};
 $('sources').innerHTML=D.source_counts.map(s=>`<tr><td><code>${esc(s.source)}</code></td><td>${N(s.rows)}</td><td>${N(s.session_count)}</td><td style="text-align:left;white-space:normal;min-width:180px">${roles[s.source]||'원천 품질 확인'}</td></tr>`).join('');
 $('quality-boxes').innerHTML=[['원천 랩',D.summary.source_laps],['기본 정제 통과 랩',D.summary.baseline_clean_laps],['참조 집단 연결 랩',D.summary.baseline_reference_laps],['전체 팀·후보 비교',Object.keys(D.cases).length]].map(([label,n])=>`<div class="quality-box"><b>${N(n)}</b><span>${label} · 전 시즌 합계</span></div>`).join('');
 const remaining=key=>D.quality.find(q=>q.rule===key)?.remaining;
 $('data-issues').innerHTML=[['타이어 구간 미연결·모호',remaining('lap to stint'),'랩 · 성능 비교에서 제외'],['날씨 90초 연결 불가',remaining('weather 90sec'),'랩 · 건조 조건 비교에서 제외'],['격차 10초 연결 불가',remaining('interval 10sec'),'랩 · 근접 차량 제한 조건에서 제외'],['결과 분류 미확정',remaining('RESULT_CLASSIFICATION'),'선수·경기 · 포인트 N/A'],['출발 그리드 미연결',remaining('GRID_MISSING'),'선수·경기 · 순위 변화 N/A'],['피트 원천 미수집',D.coverage.filter(r=>!r.pit_source_present).length,'경기 · 0회로 대체하지 않음']].map(([a,b,c])=>row(esc(a),`${N(b)} <span class="dim">${c}</span>`)).join('');
}
init();
