import assert from 'node:assert/strict';
globalThis.fetch=()=>{throw Error('REAL_NETWORK_FORBIDDEN');};
let bodyLibrary;try{bodyLibrary=await import('../http_body.mjs');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}assert.equal(typeof bodyLibrary?.readHttpBody,'function','one shared bounded body reader required');
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


const {readFileSync}=await import('node:fs');const vm=await import('node:vm');const sharedSource=readFileSync(new URL('../http_body.mjs',import.meta.url),'utf8');
function apiBodyModel(timeoutMs=5000,maxBytes=1048576){let clock=0,timer,closed=0,delay;const read=vm.runInNewContext('(function(){'+sharedSource.replace(/^export /gm,'')+';return response=>readHttpBody(response,{maxBytes:'+maxBytes+',timeoutMs:'+timeoutMs+'});})()',{Buffer,Uint8Array,Symbol,Promise,performance:{now:()=>clock},setTimeout:(fn,ms)=>{timer=fn;delay=ms;return 1;},clearTimeout:()=>{closed++;}});return{read,late(value=5001){clock=value;},expire(){assert.equal(typeof timer,'function');timer();},get closed(){return closed;},get delay(){return delay;}};}

let am=apiBodyModel();async function* complete(){yield Buffer.from('{');yield Buffer.from('}');}assert.equal((await am.read({body:complete()})).toString(),'{}');assert.equal(am.closed,1);controls++;
am=apiBodyModel();let ended=0;const silent={ [Symbol.asyncIterator](){return{next(){return new Promise(()=>{});},return(){ended++;return Promise.resolve({done:true});}};}};const waiting=am.read({body:silent});am.expire();await assert.rejects(waiting);assert.equal(ended,1);assert.equal(am.closed,1);controls++;
am=apiBodyModel();const late={ [Symbol.asyncIterator](){return{async next(){am.late();return{done:false,value:Buffer.from('{}')};},return(){return{done:true};}};}};await assert.rejects(am.read({body:late}));controls++;
am=apiBodyModel();const failedClose={ [Symbol.asyncIterator](){return{async next(){return{done:false,value:Buffer.alloc(0)};},return(){return Promise.reject(Error(secret));}};}};await assert.rejects(am.read({body:failedClose}));assert.equal(am.closed,1);controls++;


// The same implementation also supplies the artifact10s policy, not another reader.
am=apiBodyModel(10000,2);async function* withinArtifactDeadline(){am.late(5001);yield Buffer.from('{}');}assert.equal((await am.read({body:withinArtifactDeadline()})).toString(),'{}');assert.equal(am.delay,10000);controls++;
am=apiBodyModel(10000,2);async function* pastArtifactDeadline(){am.late(10001);yield Buffer.from('{}');}await assert.rejects(am.read({body:pastArtifactDeadline()}));controls++;
am=apiBodyModel(10000,1);let artifactEmpty=0;async function* artifactEmptyFragments(){for(let i=0;i<20000;i++){artifactEmpty++;yield Buffer.alloc(0);}}await assert.rejects(am.read({body:artifactEmptyFragments()}));assert.equal(artifactEmpty,1);controls++;
am=apiBodyModel(10000,10000);let artifactTiny=0;async function* artifactTinyFragments(){for(let i=0;i<5000;i++){artifactTiny++;yield Buffer.from('x');}}await assert.rejects(am.read({body:artifactTinyFragments()}));assert.equal(artifactTiny,4097);controls++;
am=apiBodyModel(10000,1);const waitingArtifact=am.read({body:silent});am.expire();await assert.rejects(waitingArtifact);assert.equal(am.delay,10000);controls++;
const {readHttpBody,httpBodyFailure}=bodyLibrary;let optionCallbacks=0,bodyTouches=0;const wrongOptions=[undefined,null,true,{}, {maxBytes:0,timeoutMs:5000},{maxBytes:true,timeoutMs:5000},{maxBytes:1048577,timeoutMs:5000},{maxBytes:1,timeoutMs:0},{maxBytes:1,timeoutMs:5001},{maxBytes:1,timeoutMs:10001},{maxBytes:1,timeoutMs:5000,errorPolicy:()=>true}];const accessor={maxBytes:1};Object.defineProperty(accessor,'timeoutMs',{enumerable:true,get(){optionCallbacks++;throw Error(secret);}});wrongOptions.push(accessor);
for(const options of wrongOptions){const response={get body(){bodyTouches++;throw Error(secret);}};await assert.rejects(readHttpBody(response,options),e=>httpBodyFailure(e)==='RESPONSE');controls++;}assert.equal(bodyTouches,0);assert.equal(optionCallbacks,0);
const forged={get code(){optionCallbacks++;throw Error(secret);},kind:'BOUND'};assert.equal(httpBodyFailure(forged),undefined);assert.equal(optionCallbacks,0);controls++;
let foreignReads=0;const foreignError=new Proxy({}, {get(){foreignReads++;throw Error(secret);}});async function* failForeign(){throw foreignError;}await assert.rejects(readHttpBody({body:failForeign()},{maxBytes:1,timeoutMs:5000}),e=>httpBodyFailure(e)==='RESPONSE'&&e.message==='HTTP_BODY_REFUSED');assert.equal(foreignReads,0);controls++;

console.log(JSON.stringify({controls,status:'PASS_INERT_API_FAILURES_ONLY',network:'NOT_RUN',PKI:'NOT_RUN',SQLite:'NOT_RUN'}));
