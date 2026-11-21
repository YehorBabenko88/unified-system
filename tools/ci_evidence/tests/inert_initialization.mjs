import assert from 'node:assert/strict';
let init;try{init=await import('../context_init.mjs');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}
assert.equal(typeof init?.initializeContext,'function','closed inert initialization boundary is required');
const {initializeContext}=init;const {publicInitFailure,INIT_PHASES}=await import('../diagnostics.mjs');
const sentinel='SYNTHETIC_PRIVATE_BEARER_PATH_CLAIM_SENTINEL';let controls=0;
for(const target of INIT_PHASES){
 const calls=[];let closed=0;const fault=phase=>{calls.push(phase);if(phase===target)throw new Error(sentinel);};
 const deps={discover:async(expected,stage)=>{for(const p of ['CONTEXT_INPUT','CONTEXT_API_RUN','CONTEXT_API_JOBS','CONTEXT_API_COMMIT','CONTEXT_SHAPE','CONTEXT_SOURCE_BINDING']){stage(p);fault(p);}return Object.freeze({scope:'INERT_NOT_AUTHENTICATED'});},openJournal:()=>{fault('RECEIVER_INIT');return {close(){closed++;}};},createSession:(journal,discovered,stage)=>{for(const p of ['CHALLENGE_ISSUE','KEY_SETUP']){stage(p);fault(p);}return {describe(){fault('DESCRIPTOR');throw new Error('INERT_NEVER_GRANTS_READY');}};}};
 let result;try{await initializeContext(Object.freeze({scope:'INERT_INPUT_NOT_AUTHENTICATED'}),deps);}catch(e){result=publicInitFailure(e);}
 assert.equal(result.phase,target);assert.match(result.code,/^E_/);assert.equal(JSON.stringify(result).includes(sentinel),false);assert.equal(calls.at(-1),target);assert.equal(closed,target==='CHALLENGE_ISSUE'||target==='KEY_SETUP'||target==='DESCRIPTOR'?1:0);controls++;
}
const hostile=new Proxy({}, {get(){throw Error(sentinel);}});assert.deepEqual(publicInitFailure(hostile),{phase:'CONTEXT_INPUT',code:'E_INTERNAL'});controls++;
console.log(JSON.stringify({controls,status:'PASS_INERT_FAILURES_ONLY',authority:'NONE',liveAuth:'NOT_RUN'}));
