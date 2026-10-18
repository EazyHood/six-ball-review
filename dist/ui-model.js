export const PHASES=['1-6','7-15','16-20'];
export const CATEGORIES=['dot','boundary','other'];
export const EVIDENCE_LABELS={no_history:'No history in phase',limited:'Limited evidence',adequate_for_review:'Enough for review'};
export const REVIEW_LABELS={abstain:'Abstain from a performance conclusion',pending_checks:'Checks pending',uncertain:'Uncertain relative to reference',reviewable:'Reviewable against this reference'};
export const pct=value=>Number.isFinite(value)?`${(value*100).toFixed(1)}%`:'—';
export const pp=value=>{if(!Number.isFinite(value))return '—';const rounded=Number((value*100).toFixed(2));return `${rounded>0?'+':''}${(rounded===0?0:rounded).toFixed(2)} pp`;};
export const rateRange=band=>band?`${pct(band.lower)}–${pct(band.upper)}`:'Unavailable';
const REASONS={boundary_contrast_not_separated_from_reference:'The boundary-rate band spans the reference',dot_contrast_not_separated_from_reference:'The dot-rate band spans the reference',contrast_sign_changes_without_dominant_venue:'Removing the dominant venue changes a contrast’s direction',contrast_sign_changes_without_one_match:'Removing one match changes a contrast’s direction',fewer_than_5_matches:'Fewer than five matches',fewer_than_60_legal_deliveries:'Fewer than 60 legal deliveries',no_known_venue_with_legal_history:'No known venue has legal-delivery history for this profile',no_legal_delivery_history:'No legal-delivery history in this phase'};
export const humanReason=value=>REASONS[value]||String(value).replaceAll('_',' ');
export const reasonText=reasons=>reasons.map(humanReason).join('; ');
export const reviewExplanation=p=>reasonText(p.review.reasons)||({reviewable:'The stated checks are complete. This does not establish player superiority.',uncertain:'The stated reference comparison remains uncertain.',pending_checks:'Required checks are not complete.',abstain:'This profile does not support a performance conclusion.'})[p.review.status];
export const phaseText=phase=>phase.replace('-','–');
export const quantity=(value,singular,plural=`${singular}s`)=>`${new Intl.NumberFormat('en').format(value)} ${value===1?singular:plural}`;
export const referenceLabel=kind=>kind==='excluding_player'?'excluding this player':'pooled phase fallback';
export const escapeHTML=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fail=message=>{throw new Error(message);};
const rate=value=>Number.isFinite(value)&&value>=0&&value<=1;
const vector=value=>value&&CATEGORIES.every(key=>rate(value[key]))&&Math.abs(CATEGORIES.reduce((sum,key)=>sum+value[key],0)-1)<1e-8;
export function validateDataset(data){
  if(data?.schema_version!=='0.1'||!Array.isArray(data.profiles)||!data.profiles.length||!data.provenance?.dataset_sha256||!data.method||!data.scope||!data.evaluation?.models)fail('The published evidence has an unsupported or incomplete format.');
  const seen=new Set();
  for(const p of data.profiles){
    if(!p.profile_id||seen.has(p.profile_id)||typeof p.player_name!=='string'||!PHASES.includes(p.phase)||!Number.isInteger(p.legal_deliveries)||p.legal_deliveries<0||!Number.isInteger(p.matches)||p.matches<0||!Array.isArray(p.match_rows))fail('A profile has invalid identity or volume information.');
    seen.add(p.profile_id);
    if(!vector(p.regularized)||!vector(p.reference?.rates)||(p.legal_deliveries===0?p.raw!==null:!vector(p.raw)))fail('A profile contains an invalid probability vector.');
    if(!CATEGORIES.every(k=>Number.isInteger(p.counts?.[k])&&p.counts[k]>=0)||CATEGORIES.reduce((sum,k)=>sum+p.counts[k],0)!==p.legal_deliveries)fail('A profile has inconsistent counts.');
    if(!EVIDENCE_LABELS[p.evidence?.status]||!REVIEW_LABELS[p.review?.status]||!Array.isArray(p.review.reasons)||!Array.isArray(p.evidence.reasons)||!p.checks)fail('A profile is missing its evidence state.');
    if(p.checks.bands&&!CATEGORIES.every(k=>rate(p.checks.bands[k]?.lower)&&rate(p.checks.bands[k]?.upper)&&p.checks.bands[k].lower<=p.checks.bands[k].upper))fail('A profile contains invalid uncertainty bounds.');
    if(p.review.status==='reviewable'&&(p.checks.status!=='complete'||!p.checks.bands||!p.checks.contrasts_vs_reference||!p.checks.leave_one_match))fail('An incomplete profile cannot be labeled reviewable.');
    if(p.match_rows.some(m=>![2023,2024,2025].includes(m.season))||new Set(p.match_rows.map(m=>m.match_id)).size!==p.matches)fail('Profile provenance does not match the declared evidence window.');
  }
  return data;
}
export function filterProfiles(data,{phase,search='',evidence='all'}){
  const needle=search.trim().toLocaleLowerCase('en');
  return data.profiles.filter(p=>p.phase===phase&&(evidence==='all'||p.evidence.status===evidence)&&(!needle||`${p.player_name} ${p.player_id}`.toLocaleLowerCase('en').includes(needle)))
    .sort((a,b)=>a.player_name.localeCompare(b.player_name,'en')||a.player_id.localeCompare(b.player_id,'en'));
}
export function addSelection(selected,profile){
  if(selected.some(s=>s.profile_id===profile.profile_id))return selected;
  if(selected.length>=3)fail('Your sheet already has three cases. Remove one before adding another.');
  return [...selected,{profile_id:profile.profile_id,question:`What match context might explain this ${phaseText(profile.phase)}-over profile, and what should I check in footage?`,note:''}];
}
export function editSelection(selected,id,field,value){
  if(!['question','note'].includes(field)||typeof value!=='string'||value.length>(field==='question'?400:1200))fail('The review note is too long or has an invalid field.');
  return selected.map(item=>item.profile_id===id?{...item,[field]:value}:item);
}
export function makeReview(data,selected,activePhase,dataHash,createdAt){
  if(!selected.length||selected.length>3||new Set(selected.map(s=>s.profile_id)).size!==selected.length||!PHASES.includes(activePhase))fail('Choose one to three unique profiles before exporting.');
  const entries=selected.map(selection=>{
    const profile=data.profiles.find(p=>p.profile_id===selection.profile_id);
    if(!profile||!selection.question.trim()||selection.question.length>400||selection.note.length>1200)fail('Each selected case needs a review question (up to 400 characters).');
    return {question:selection.question,note:selection.note,profile:structuredClone(profile)};
  });
  return {format:'six-ball-review-sheet',version:1,created_at_utc:createdAt,selection_mode:'manual',active_view_phase:activePhase,active_view_phase_note:'The active view is not a filter on saved cases. Each case retains its own phase; no cross-phase ranking or pairwise inference is calculated.',source_snapshot:{file:'data.json',sha256:dataHash,generated_at_utc:data.generated_at_utc,schema_version:data.schema_version},scope:structuredClone(data.scope),provenance:structuredClone(data.provenance),method:structuredClone(data.method),evaluation:structuredClone(data.evaluation),cases:entries,notes_context:'Questions and notes are analyst-authored prompts. Selecting a case does not assert that footage was viewed, a player is superior, or a lineup should change.'};
}
export function readableReview(sheet){
  const e=escapeHTML;
  const cases=sheet.cases.map(({profile:p,question,note},index)=>`<section><p class="eyebrow">Case ${index+1} · overs ${e(phaseText(p.phase))}</p><h2>${e(p.player_name)}</h2><p>${e(p.player_id)}</p><div class="warning"><strong>${e(REVIEW_LABELS[p.review.status])}</strong><p>${e(reviewExplanation(p))}</p><p>Evidence: ${e(EVIDENCE_LABELS[p.evidence.status])}. ${e(reasonText(p.evidence.reasons))} Checks: ${e(p.checks.status)}.</p></div><p>${p.legal_deliveries} legal deliveries · ${e(quantity(p.matches,'match','matches'))} · ${p.illegal_deliveries} illegal deliveries (${e(pct(p.illegal_rate))} of all recorded deliveries).</p><table><thead><tr><th>Outcome</th><th>Observed</th><th>Regularized${p.legal_deliveries?'':' fallback'}</th><th>95% resampling band</th><th>Reference</th></tr></thead><tbody>${CATEGORIES.map(k=>`<tr><th>${e(k)}</th><td>${e(pct(p.raw?.[k]))}</td><td>${e(pct(p.regularized[k]))}</td><td>${e(rateRange(p.checks.bands?.[k]))}</td><td>${e(pct(p.reference.rates[k]))}</td></tr>`).join('')}</tbody></table><p class="small">Reference: ${e(referenceLabel(p.reference.kind))}. Bands condition on the model and cohort; they do not measure intrinsic skill.</p><h3>Review question</h3><p class="note">${e(question)}</p><h3>Your note</h3><p class="note">${e(note||'No note added.')}</p><details><summary>Exact evidence, checks and source matches</summary><pre>${e(JSON.stringify(p,null,2))}</pre></details><p class="small">Contributing match IDs: ${e(p.match_rows.map(m=>m.match_id).join(', ')||'None in this phase.')}</p></section>`).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; form-action 'none'; base-uri 'none'"><title>Six-Ball Review sheet</title><style>body{font:15px/1.6 Arial,sans-serif;max-width:920px;margin:45px auto;padding:0 22px;color:#202a29}header{border-bottom:4px solid #153f3b;padding-bottom:20px}h1{font-size:30px;margin:0}h2{font-size:24px;margin:0}h3{font-size:15px}section{padding:28px 0;border-bottom:1px solid #bcc8bf;break-inside:avoid}.eyebrow,.small{font-size:12px;color:#4c5c52}.warning{background:#f4eee3;padding:15px;border-left:3px solid #8f4d2e;margin:18px 0}.warning p{margin:6px 0}table{width:100%;border-collapse:collapse;font-size:12px}td,th{text-align:left;padding:9px;border-bottom:1px solid #ccd4cf}.note{white-space:pre-wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px}summary{cursor:pointer;padding:10px 0}footer{margin:30px 0;font-size:12px}.hash{overflow-wrap:anywhere;font-family:monospace}@media print{body{margin:0;max-width:none;font-size:11px}details{display:none}table{font-size:10px}a{color:inherit}}</style></head><body><header><h1>Six-Ball Review</h1><p>Manual bowling review sheet · ${e(sheet.scope.competition)} · ${e(sheet.scope.evidence_seasons.join('–'))} evidence</p><p class="small">Created ${e(sheet.created_at_utc)}. Cases preserve their own phase. No automatic ranking, pairwise claim or lineup recommendation.</p></header>${cases}<section><h2>Limits & provenance</h2><ul>${sheet.method.limitations.map(text=>`<li>${e(text)}</li>`).join('')}</ul><p>${e(sheet.notes_context)}</p><p class="hash">Snapshot SHA-256: ${e(sheet.source_snapshot.sha256)}<br>Dataset SHA-256: ${e(sheet.provenance.dataset_sha256)}<br>Producer SHA-256: ${e(sheet.provenance.producer_sha256)}<br>Plan SHA-256: ${e(sheet.provenance.plan_sha256)}</p><details><summary>Full method and frozen evaluation</summary><pre>${e(JSON.stringify({scope:sheet.scope,method:sheet.method,evaluation:sheet.evaluation,provenance:sheet.provenance},null,2))}</pre></details></section><footer><p>Contains information from <a href="https://cricsheet.org/">Cricsheet</a>, available under the <a href="https://opendatacommons.org/licenses/by/1-0/">ODC Attribution License</a>. ${e(sheet.provenance.attribution)}</p><p>Built with substantial OpenAI Codex assistance. Use your browser’s Print command for a paper copy. The companion JSON retains every source field and check.</p></footer></body></html>`;
}
