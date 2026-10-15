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
