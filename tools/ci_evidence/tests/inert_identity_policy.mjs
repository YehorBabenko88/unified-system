import assert from 'node:assert/strict';
let p;try{p=await import('../identity_policy.mjs');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}
assert.equal(typeof p?.snapshotExpected,'function','immutable split collector/workload identity snapshot is required');
const expected={repository:'YehorBabenko88/math',event:'pull_request',runId:'1',attempt:'1',sourceSha:'a'.repeat(40),workflowSha:'b'.repeat(40),workflowRef:'YehorBabenko88/math/.github/workflows/confidential-synthetic-e2e.yml@refs/pull/141/merge',collectorSha:'c'.repeat(40),collectorRepository:'YehorBabenko88/unified-system'};
const frozen=p.snapshotExpected(expected);expected.collectorSha='d'.repeat(40);assert.equal(frozen.collectorSha,'c'.repeat(40));assert(Object.isFrozen(frozen));let controls=1;
for(const change of [x=>x.collectorRepository='YehorBabenko88/math',x=>x.repository='YehorBabenko88/unified-system',x=>x.runId='0',x=>x.attempt='1'.repeat(21),x=>x.collectorSha='a'.repeat(41),x=>x.workflowRef='secret-url',x=>x.sourceSha=true,x=>x.extra='secret']){const value={...frozen};change(value);assert.throws(()=>p.snapshotExpected(value));controls++;}
const getter={...frozen};Object.defineProperty(getter,'collectorSha',{enumerable:true,get(){throw Error('SYNTHETIC_SECRET_GETTER');}});assert.throws(()=>p.snapshotExpected(getter));controls++;
console.log(JSON.stringify({controls,status:'PASS_LOCAL_CONFIGURATION_ONLY',sourceAuth:'NOT_EVALUATED'}));
