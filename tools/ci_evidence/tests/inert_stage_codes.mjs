import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {stageCode,stageBlocked,evidenceStages} from '../strict.mjs';
let controls=0;const secret='SYNTHETIC_PRIVATE_CODE_SENTINEL';
assert.equal(stageCode({code:secret},'E_API'),'E_API');controls++;
let touched=0,thrown=false,result;const accessor=Object.defineProperty({},'code',{get(){touched++;throw Error(secret);}});try{result=stageCode(accessor,'E_API');}catch{thrown=true;}assert.equal(thrown,false,'diagnostic sanitization must not invoke an error.code getter');assert.equal(touched,0);assert.equal(result,'E_API');controls++;
const proxy=new Proxy({}, {getOwnPropertyDescriptor(){throw Error(secret);},get(){throw Error(secret);}});assert.equal(stageCode(proxy,'E_API'),'E_API');controls++;
assert.equal(stageCode(Object.create({code:'E_OIDC_SIGNATURE'}),'E_API'),'E_API');controls++;
for(const code of evidenceStages){assert.equal(stageCode({code}),code);let e;try{stageBlocked(code);}catch(error){e=error;}assert.equal(e.code,code);assert(!e.message.includes(secret));controls++;}
const source=readFileSync(new URL('../github_identity.mjs',import.meta.url),'utf8');assert.doesNotMatch(source,/if\(error\.code\)throw error/);assert.match(source,/stageBlocked\(stageCode\(error,stage\)\)/);controls++;
console.log(JSON.stringify({controls,status:'PASS_CLOSED_ERROR_CODES_ONLY',PKI:'NOT_RUN'}));
