import assert from 'node:assert/strict';
globalThis.fetch=()=>{throw Error('REAL_NETWORK_FORBIDDEN');};
const {fetchGitHubJson}=await import('../github_identity.mjs');const {atInitPhase,publicInitFailure}=await import('../diagnostics.mjs');
const route='/repos/YehorBabenko88/math/actions/runs/1';let controls=0;const secret='SYNTHETIC_PRIVATE_BEARER_ERROR_SENTINEL';
async function refused(fetcher,code,path=route){let error;try{await atInitPhase('CONTEXT_API_RUN',()=>fetchGitHubJson(path,{fetcher,authorization:'Bearer '+secret}));}catch(e){error=e;}const safe=publicInitFailure(error);assert.deepEqual(safe,{phase:'CONTEXT_API_RUN',code});assert(!JSON.stringify(safe).includes(secret));controls++;}
for(const status of [401,403]){let body=false;await refused(async()=>({ok:false,status,get body(){body=true;throw Error(secret);}}),'E_API_AUTH');assert.equal(body,false);}
let continued=false;await refused(async()=>({ok:true,url:'https://api.github.com'+route,body:(async function*(){yield Buffer.alloc(1048577);continued=true;yield Buffer.from(secret);})()}),'E_API_BOUND');assert.equal(continued,false);
await refused(async()=>({ok:true,url:'https://unapproved.invalid/',body:[]}),'E_API_RESPONSE');
await refused(async()=>({ok:true,url:'https://api.github.com'+route,body:[Buffer.from('{')]}),'E_API_RESPONSE');
await refused(async()=>{throw new Proxy({}, {get(){throw Error(secret);}});},'E_API_RESPONSE');
let called=false;await refused(async()=>{called=true;throw Error(secret);},'E_API_RESPONSE','/repos/YehorBabenko88/math/../forbidden');assert.equal(called,false);

// Minimal native Git commit metadata: no REST diff expansion or DTO fallback.
const {discoverContext}=await import('../context.mjs');const {readPlatform,verifySourceBinding}=await import('../github_identity.mjs');
const expected={collectorRepository:'YehorBabenko88/unified-system',repository:'YehorBabenko88/math',event:'pull_request',runId:'3',attempt:'1',sourceSha:'a'.repeat(40),workflowSha:'a'.repeat(40),workflowRef:'YehorBabenko88/math/.github/workflows/confidential-synthetic-e2e.yml@refs/pull/1/merge',collectorSha:'1'.repeat(40)};
const gitCommit={sha:expected.sourceSha,tree:{sha:'b'.repeat(40)},parents:[{sha:'f'.repeat(40)},{sha:'e'.repeat(40)}]};
const run={id:3,run_attempt:1,repository:{full_name:expected.repository,id:1,owner:{id:2}},event:'pull_request',status:'in_progress',head_sha:'e'.repeat(40),pull_requests:[{base:{sha:'f'.repeat(40)},head:{sha:'e'.repeat(40)}}]};
const job={id:4,run_id:3,status:'in_progress',head_sha:run.head_sha,name:'qualification / collector',check_run_url:'https://api.github.com/repos/YehorBabenko88/math/check-runs/5'};
const jobs={total_count:1,jobs:[job]};const paths=[];
const fake=async(url)=>{const p=new URL(url).pathname;paths.push(p);let value;if(p.includes('/git/commits/'))value=gitCommit;else if(p.includes('/commits/'))value={files:['DIFF'.repeat(350000)]};else if(p.includes('/attempts/'))value=jobs;else if(p.includes('/actions/jobs/'))value=job;else value=run;return new Response(JSON.stringify(value));};
const discovered=await discoverContext(expected,{fetcher:fake});assert.equal(discovered.context.sourceTree,gitCommit.tree.sha);assert(paths.includes('/repos/YehorBabenko88/math/git/commits/'+expected.sourceSha));assert(!paths.some(p=>/^.*math\/commits\//.test(p)));controls++;
paths.length=0;const platform=await readPlatform(discovered.context,{fetcher:fake});assert.equal(JSON.stringify(platform.commit),JSON.stringify(gitCommit));assert(paths.includes('/repos/YehorBabenko88/math/git/commits/'+expected.sourceSha));assert(!paths.some(p=>/^.*math\/commits\//.test(p)));controls++;
assert.equal(verifySourceBinding({policy:discovered.policy,challenge:discovered.context,platform}).sourceTree,gitCommit.tree.sha);controls++;
for(const commit of [{...gitCommit,sha:'0'.repeat(40)},{...gitCommit,tree:{sha:'0'.repeat(40)}},{sha:gitCommit.sha,commit:{tree:gitCommit.tree},parents:gitCommit.parents},{...gitCommit,parents:[...gitCommit.parents].reverse()},{...gitCommit,parents:gitCommit.parents.slice(1)},{...gitCommit,parents:[...gitCommit.parents,{sha:'c'.repeat(40)}]}]){assert.throws(()=>verifySourceBinding({policy:discovered.policy,challenge:discovered.context,platform:{...platform,commit}}));controls++;}
assert.equal(Object.hasOwn(gitCommit,'commit'),false);controls++;


let emptyCount=0;await refused(async()=>({ok:true,url:'https://api.github.com'+route,body:(async function*(){for(let i=0;i<20000;i++){emptyCount++;yield Buffer.alloc(0);}})()}),'E_API_BOUND');assert.equal(emptyCount,1);
let tinyCount=0;await refused(async()=>({ok:true,url:'https://api.github.com'+route,body:(async function*(){for(let i=0;i<5000;i++){tinyCount++;yield Buffer.from(' ');}yield Buffer.from('{}');})()}),'E_API_BOUND');assert.equal(tinyCount,4097);
const partial=await fetchGitHubJson(route,{fetcher:async()=>({ok:true,url:'https://api.github.com'+route,body:(async function*(){yield Buffer.from('{');yield Buffer.from('}');})()})});assert.equal(JSON.stringify(partial),'{}');controls++;
await refused(async()=>({ok:true,url:'https://api.github.com'+route,body:(async function*(){})()}),'E_API_RESPONSE');
let byteCallbacks=0;await refused(async()=>({ok:true,url:'https://api.github.com'+route,body:(async function*(){yield{valueOf(){byteCallbacks++;throw Error(secret);}};})()}),'E_API_RESPONSE');assert.equal(byteCallbacks,0);


const {readFileSync}=await import('node:fs');const vm=await import('node:vm');const apiSource=readFileSync(new URL('../github_identity.mjs',import.meta.url),'utf8'),ab=apiSource.indexOf('async function readApiBody('),ae=apiSource.indexOf('\n// Fixed HTTPS origin',ab);assert(ab>=0&&ae>ab);
function apiBodyModel(){let clock=0,timer,closed=0;const read=vm.runInNewContext('('+apiSource.slice(ab,ae)+')',{Buffer,Uint8Array,Symbol,Promise,performance:{now:()=>clock},setTimeout:fn=>{timer=fn;return 1;},clearTimeout:()=>{closed++;},apiBoundFailure:()=>Error('INERT_API_BOUND'),need:x=>{if(!x)throw Error('INERT_API_RESPONSE');}});return{read,late(){clock=5001;},expire(){assert.equal(typeof timer,'function');timer();},get closed(){return closed;}};}
let am=apiBodyModel();async function* complete(){yield Buffer.from('{');yield Buffer.from('}');}assert.equal((await am.read({body:complete()})).toString(),'{}');assert.equal(am.closed,1);controls++;
am=apiBodyModel();let ended=0;const silent={ [Symbol.asyncIterator](){return{next(){return new Promise(()=>{});},return(){ended++;return Promise.resolve({done:true});}};}};const waiting=am.read({body:silent});am.expire();await assert.rejects(waiting);assert.equal(ended,1);assert.equal(am.closed,1);controls++;
am=apiBodyModel();const late={ [Symbol.asyncIterator](){return{async next(){am.late();return{done:false,value:Buffer.from('{}')};},return(){return{done:true};}};}};await assert.rejects(am.read({body:late}));controls++;
am=apiBodyModel();const failedClose={ [Symbol.asyncIterator](){return{async next(){return{done:false,value:Buffer.alloc(0)};},return(){return Promise.reject(Error(secret));}};}};await assert.rejects(am.read({body:failedClose}));assert.equal(am.closed,1);controls++;

console.log(JSON.stringify({controls,status:'PASS_INERT_API_FAILURES_ONLY',network:'NOT_RUN',PKI:'NOT_RUN',SQLite:'NOT_RUN'}));
