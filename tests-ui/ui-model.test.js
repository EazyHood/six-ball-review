import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {validateDataset,filterProfiles,addSelection,editSelection,makeReview,readableReview,pct,pp} from '../dist/ui-model.js';
const text=await readFile(new URL('../dist/data.json',import.meta.url),'utf8');
const data=JSON.parse(text);
const hash=createHash('sha256').update(text).digest('hex');
const stamp='2026-10-18T15:00:00.000Z';
test('the real producer snapshot is accepted without modifying any profile',()=>{
 const before=structuredClone(data);assert.equal(validateDataset(data),data);assert.deepEqual(data,before);
});
test('phase search orders alphabetically and never adds profiles outside the selected phase',()=>{
 for(const phase of ['1-6','7-15','16-20']){const rows=filterProfiles(data,{phase});assert.ok(rows.length);assert.ok(rows.every(p=>p.phase===phase));assert.deepEqual(rows,[...rows].sort((a,b)=>a.player_name.localeCompare(b.player_name,'en')||a.player_id.localeCompare(b.player_id,'en')));const p=rows[0];assert.ok(filterProfiles(data,{phase,search:p.player_id.toUpperCase()}).some(row=>row.profile_id===p.profile_id));}
 assert.equal(filterProfiles(data,{phase:'1-6',search:'no such exact synthetic QA name 48392'}).length,0);
 const limited=filterProfiles(data,{phase:'1-6',evidence:'limited'});assert.ok(limited.length);assert.ok(limited.every(p=>p.evidence.status==='limited'));
});
test('manual selection permits three distinct cases and never evicts an existing note',()=>{
 let selected=[];for(const p of data.profiles.slice(0,3))selected=addSelection(selected,p);
 selected=editSelection(selected,selected[0].profile_id,'note','QA note retained across phase changes.');const before=structuredClone(selected);
 assert.equal(addSelection(selected,data.profiles[0]),selected);assert.throws(()=>addSelection(selected,data.profiles[3]),/three cases/);assert.deepEqual(selected,before);
 const exported=makeReview(data,selected,'16-20',hash,stamp);assert.equal(exported.cases[0].note,before[0].note);assert.equal(exported.cases[0].profile.phase,data.profiles[0].phase);assert.equal(exported.active_view_phase,'16-20');
});
test('both export formats preserve abstentions, exact profile values, provenance and analyst text',()=>{
 const profiles=['abstain','uncertain','reviewable'].map(status=>data.profiles.find(p=>p.review.status===status));assert.ok(profiles.every(Boolean));let selected=[];for(const p of profiles)selected=addSelection(selected,p);
 const hostile='QA only: <img src=x onerror=alert(1)> & "quotes" 🧵';selected=editSelection(selected,profiles[0].profile_id,'note',hostile);
 const sheet=makeReview(data,selected,'7-15',hash,stamp);const roundtrip=JSON.parse(JSON.stringify(sheet));assert.equal(roundtrip.cases[0].note,hostile);
 profiles.forEach((p,i)=>assert.deepEqual(roundtrip.cases[i].profile,p));assert.deepEqual(roundtrip.provenance,data.provenance);assert.deepEqual(roundtrip.evaluation,data.evaluation);assert.equal(sheet.source_snapshot.sha256,hash);
 const html=readableReview(sheet);assert.ok(!html.includes('<img src=x'));assert.ok(html.includes('&lt;img src=x onerror=alert(1)&gt;'));assert.ok(html.includes('ODC Attribution License'));assert.ok(html.includes(hash));assert.ok(html.includes(profiles[0].review.reasons[0]));
 sheet.cases[0].profile.player_name='Mutated export';assert.notEqual(profiles[0].player_name,'Mutated export');
});
test('missing questions, duplicate IDs and unknown references cannot be exported',()=>{
 const s=addSelection([],data.profiles[0]);assert.throws(()=>makeReview(data,[],'1-6',hash,stamp));assert.throws(()=>makeReview(data,[s[0],s[0]],'1-6',hash,stamp));assert.throws(()=>makeReview(data,[{...s[0],question:' '}],'1-6',hash,stamp));assert.throws(()=>makeReview(data,[{...s[0],profile_id:'missing'}],'1-6',hash,stamp));assert.throws(()=>editSelection(s,s[0].profile_id,'question','x'.repeat(401)));assert.throws(()=>editSelection(s,s[0].profile_id,'note','x'.repeat(1201)));
});
test('missing evidence, malformed bounds and a 2026 provenance leak fail closed',()=>{
 const mutations=[d=>{d.profiles[0].regularized.dot=NaN;},d=>{d.profiles[0].checks.bands.dot.lower=1.2;},d=>{d.profiles[0].review.status='reviewable';d.profiles[0].checks.status='not_computed';},d=>{d.profiles[0].evidence.status='excellent';},d=>{d.profiles.find(p=>p.match_rows.length).match_rows[0].season=2026;},d=>{d.profiles[0].raw={dot:0,boundary:0,other:1};}];
 for(const change of mutations){const copy=structuredClone(data);change(copy);assert.throws(()=>validateDataset(copy));}
});
test('missing rates do not become zero and probability contrasts keep their units',()=>{
 assert.equal(pct(null),'—');assert.equal(pct(0),'0.0%');assert.equal(pp(.005),'+0.50 pp');assert.equal(pp(-.005),'-0.50 pp');assert.equal(pp(-5.55e-17),'0.00 pp');assert.equal(pp(5.55e-17),'0.00 pp');
});
