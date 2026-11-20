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
console.log(JSON.stringify({controls,status:'PASS_INERT_API_FAILURES_ONLY',network:'NOT_RUN',PKI:'NOT_RUN',SQLite:'NOT_RUN'}));
