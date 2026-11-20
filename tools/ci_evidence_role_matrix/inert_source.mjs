import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';import vm from 'node:vm';import {resolve} from 'node:path';import {pathToFileURL} from 'node:url';
import {parseTerminals} from './contract.mjs';import reporter from './reporter.mjs';
const root=new URL('../../',import.meta.url),workflow=readFileSync(new URL('.github/workflows/ci-evidence-role-matrix.yml',root),'utf8'),plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
assert.equal(process.argv.length,3);const roleRoot=pathToFileURL(resolve(process.argv[2])+'/');
let checks=0;assert.equal(plan.role_source,'006418285667b38810b7ecd1de9807b6db166fa3');checks++;const sha=raw=>createHash('sha256').update(raw).digest('hex');
const manifest=JSON.parse(workflow.match(/const KIT_MANIFEST = (\{[\s\S]*?\n\s*\});/)[1]);assert.equal(Object.keys(manifest).length,8);
for(const[path,hash]of Object.entries(manifest)){assert.equal(sha(readFileSync(new URL(path,root))),hash);checks++;}
assert.doesNotMatch(workflow,/id-token:|secrets\.|actions\/checkout|include-hidden-files|pull_request_target/);checks++;assert.doesNotMatch(workflow,/^  workflow_dispatch:/m);
assert.match(workflow,/node: \['22', '24'\]/);assert.match(workflow,/postgres: \['16', '18'\]/);assert.match(workflow,/contents: read\n  actions: read/);checks++;
assert.match(workflow,/path: \$\{\{ runner.temp \}\}\/ci-evidence-role-matrix\/roles-linux-\$\{\{ matrix.node \}\}-\$\{\{ matrix.postgres \}\}\.json/);checks++;
assert.equal(plan.roles.length,34);assert.equal(plan.roles.filter(x=>x.kind==='HOSTED').length,31);assert.equal(plan.roles.filter(x=>x.kind==='STATIC').length,3);checks++;
for(const name of ['context.mjs','github_identity.mjs']){const source=readFileSync(new URL('tools/ci_evidence/'+name,roleRoot),'utf8');assert(source.includes("root+'/git/commits/'"));assert(!source.includes("root+'/commits/'"));assert(!source.includes('commit.commit?.tree?.sha'));assert(!source.includes('s.commit?.tree?.sha'));checks++;}
const rawLedger=readFileSync(new URL('./provenance/math54c-platform-source-transfers.json.txt',import.meta.url));assert.equal(sha(rawLedger),plan.ledger_source.sha256);const ledger=JSON.parse(rawLedger);
assert.deepEqual(plan.roles.map(x=>x.original),ledger.events.map(x=>x.original));checks++;
for(const[path,hash]of Object.entries(plan.files)){assert.equal(sha(readFileSync(new URL(path,roleRoot))),hash);checks++;}
const code=workflow.slice(workflow.indexOf('          import {mkdtempSync'),workflow.indexOf('\n          ROLE_MATRIX\n')).split('\n').map(line=>line.slice(10)).join('\n');
const sourceCode=code.slice(code.indexOf(' const trees=new Map()'),code.indexOf(' function save('));assert(sourceCode.includes('async function source'));
const pin='a'.repeat(40),tree='b'.repeat(40),raw=Buffer.from('INERT_FIXTURE\n'),blobId=createHash('sha1').update(Buffer.concat([Buffer.from('blob '+raw.length+'\0'),raw])).digest('hex');
const responses={['git/commits/'+pin]:{sha:pin,tree:{sha:tree}},['git/trees/'+tree]:{truncated:false,tree:[{path:'fixture.mjs',type:'blob',mode:'100644',sha:blobId}]},['git/blobs/'+blobId]:{encoding:'base64',size:raw.length,content:raw.toString('base64')}};
async function fixture(overrides={}){const data={...responses,...overrides},calls=[];const source=await vm.runInNewContext('(async()=>{'+sourceCode+';return source;})()',{Map,Buffer,createHash,need:value=>{if(!value)throw Error('INERT_REFUSAL');},api:async path=>{calls.push(path);assert(Object.hasOwn(data,path));return data[path];}});return{source,calls};}
let f=await fixture();assert.deepEqual(await f.source(pin,'fixture.mjs'),raw);assert.equal(f.calls.length,3);checks++;
for(const override of [
 {['git/commits/'+pin]:{sha:'f'.repeat(40),tree:{sha:tree}}},
 {['git/trees/'+tree]:{truncated:true,tree:responses['git/trees/'+tree].tree}},
 {['git/trees/'+tree]:{truncated:false,tree:[...responses['git/trees/'+tree].tree,...responses['git/trees/'+tree].tree]}},
 {['git/blobs/'+blobId]:{...responses['git/blobs/'+blobId],size:131073}},
 {['git/blobs/'+blobId]:{...responses['git/blobs/'+blobId],content:Buffer.from('SECRET_SENTINEL').toString('base64')}}
]){f=await fixture(override);await assert.rejects(f.source(pin,'fixture.mjs'));checks++;}
f=await fixture();await assert.rejects(f.source(pin,'../unowned'));assert.equal(f.calls.length,0);checks++;
const role=plan.roles.find(x=>x.kind==='HOSTED');process.env.ROLE_SOURCE_ROOT='/private/role-source';
async function* events(values){yield* values;}let text='';for await(const chunk of reporter(events([{type:'test:diagnostic',data:{message:'SECRET_SENTINEL'}},{type:'test:pass',data:{name:role.original.name,file:'/private/role-source/'+role.target,nesting:0,details:{}}}]))){text+=chunk;}assert.equal(text,JSON.stringify({id:role.id,status:'PASS'})+'\n');assert(!text.includes('SECRET_SENTINEL'));checks++;
text='';for await(const chunk of reporter(events([{type:'test:fail',data:{name:'SECRET_SENTINEL',details:{error:new Error('SECRET_SENTINEL')}}}]))){text+=chunk;}assert.equal(text,'{"refused":"E_TEST_EVENT"}\n');checks++;
for(const bad of ['SECRET_SENTINEL','x'.repeat(131073),'{}\n'.repeat(32)]){assert.throws(()=>parseTerminals(bad,plan));checks++;}

const custodySource=readFileSync(new URL('./artifact_custody.mjs',import.meta.url),'utf8');const bs=custodySource.indexOf('async function body('),be=custodySource.indexOf('\nasync function archive',bs);assert(bs>=0&&be>bs);
function streamModel(){let timeout=null,cleared=0,clock=0;const read=vm.runInNewContext('('+custodySource.slice(bs,be)+')',{Buffer,Uint8Array,Symbol,Promise,performance:{now:()=>clock},setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{cleared++;},need:x=>{if(!x)throw Error('INERT_BODY_REFUSAL');}});return{read,expire(){assert.equal(typeof timeout,'function');timeout();},late(){clock=10001;},get cleared(){return cleared;}};}
let sm=streamModel();let emptyCalls=0;async function* emptyFragments(){for(let i=0;i<20000;i++){emptyCalls++;yield Buffer.alloc(0);}}await assert.rejects(sm.read({body:emptyFragments()},1));assert.equal(emptyCalls,1);assert.equal(sm.cleared,1);checks++;
sm=streamModel();let tinyCalls=0;async function* tinyFragments(){for(let i=0;i<5000;i++){tinyCalls++;yield Buffer.from('x');}}await assert.rejects(sm.read({body:tinyFragments()},10000));assert.equal(tinyCalls,4097);checks++;
sm=streamModel();async function* validFragments(){yield Buffer.from('a');yield Buffer.from('b');}assert.equal((await sm.read({body:validFragments()},2)).toString(),'ab');assert.equal(sm.cleared,1);checks++;
sm=streamModel();await assert.rejects(sm.read({body:validFragments()},1));checks++;
sm=streamModel();async function* noBytes(){}await assert.rejects(sm.read({body:noBytes()},1));checks++;
sm=streamModel();let returned=0;const stalled={ [Symbol.asyncIterator](){return{next(){return new Promise(()=>{});},return(){returned++;return Promise.resolve({done:true});}};}};const pending=sm.read({body:stalled},1);sm.expire();await assert.rejects(pending);assert.equal(returned,1);assert.equal(sm.cleared,1);checks++;
sm=streamModel();const delayed={ [Symbol.asyncIterator](){return{async next(){sm.late();return{done:false,value:Buffer.from('x')};},return(){return{done:true};}};}};await assert.rejects(sm.read({body:delayed},1));checks++;

console.log(JSON.stringify({checks,status:'PASS_INERT_SOURCE_ONLY',authority:'NONE',production:'NO_GO'}));
