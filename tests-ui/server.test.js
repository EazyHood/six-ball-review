import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const child=spawn(process.execPath,['server.mjs'],{cwd:fileURLToPath(new URL('../',import.meta.url)),env:{...process.env,PORT:'0'},stdio:['ignore','pipe','pipe']});
const base=await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('Server start timed out')),5000);child.once('error',reject);child.stdout.on('data',data=>{const match=data.toString().match(/http:\/\/127\.0\.0\.1:\d+/);if(match){clearTimeout(timeout);resolve(match[0]);}});child.once('exit',code=>{if(code)reject(new Error(`Server exited ${code}`));});});
test.after(()=>child.kill());
test('server serves the real page, module and evidence with explicit content types',async()=>{
 for(const [path,type]of [['/','text/html'],['/app.js','text/javascript'],['/data.json','application/json']]){const r=await fetch(base+path);assert.equal(r.status,200);assert.ok(r.headers.get('content-type').startsWith(type));assert.ok((await r.text()).length>100);}
});
test('server rejects write methods and does not expose parent analysis files',async()=>{
 assert.equal((await fetch(base+'/data.json',{method:'POST',body:'QA'})).status,405);assert.equal((await fetch(base+'/analysis-plan.json')).status,404);assert.ok([400,404].includes((await fetch(base+'/%2e%2e%5canalysis-plan.json')).status));
});
