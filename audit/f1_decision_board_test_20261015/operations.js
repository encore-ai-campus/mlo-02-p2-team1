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
