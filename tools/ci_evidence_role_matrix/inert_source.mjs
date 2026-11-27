import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';import vm from 'node:vm';import {resolve} from 'node:path';import {pathToFileURL} from 'node:url';
import {parseTerminals} from './contract.mjs';import reporter from './reporter.mjs';
const root=new URL('../../',import.meta.url),workflow=readFileSync(new URL('.github/workflows/ci-evidence-role-matrix.yml',root),'utf8'),plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
assert.equal(process.argv.length,3);const roleRoot=pathToFileURL(resolve(process.argv[2])+'/');
let checks=0;assert.equal(Object.keys(plan.files).length,32,'PUBLISHED_RBRAVO_32_SOURCE_INPUTS_REQUIRED');checks++;assert.equal(plan.role_source,'4ba390b8e12070499d54b12e5609c683c00607ee');checks++;const sha=raw=>createHash('sha256').update(raw).digest('hex');
const manifest=JSON.parse(workflow.match(/const KIT_MANIFEST = (\{[\s\S]*?\n\s*\});/)[1]);assert.equal(Object.keys(manifest).length,8);
for(const[path,hash]of Object.entries(manifest)){assert.equal(sha(readFileSync(new URL(path,root))),hash);checks++;}
assert.doesNotMatch(workflow,/id-token:|secrets\.|include-hidden-files|pull_request_target/);checks++;assert.doesNotMatch(workflow,/^  workflow_dispatch:/m);
assert.match(workflow,/node: \['22', '24'\]/);assert.match(workflow,/postgres: \['16', '18'\]/);assert.match(workflow,/contents: read\n  actions: read/);checks++;
assert.match(workflow,/path: \$\{\{ runner.temp \}\}\/ci-evidence-role-matrix\/roles-linux-\$\{\{ matrix.node \}\}-\$\{\{ matrix.postgres \}\}\.json/);checks++;
assert.equal(plan.roles.length,34);assert.equal(plan.roles.filter(x=>x.kind==='HOSTED').length,31);assert.equal(plan.roles.filter(x=>x.kind==='STATIC').length,3);checks++;
for(const name of ['context.mjs','github_identity.mjs']){const source=readFileSync(new URL('tools/ci_evidence/'+name,roleRoot),'utf8');assert(source.includes("root+'/git/commits/'"));assert(!source.includes("root+'/commits/'"));assert(!source.includes('commit.commit?.tree?.sha'));assert(!source.includes('s.commit?.tree?.sha'));checks++;}

const expectedCheckout="      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        env:\n          GIT_CONFIG_COUNT: '1'\n          GIT_CONFIG_KEY_0: core.autocrlf\n          GIT_CONFIG_VALUE_0: 'false'\n        with:\n          repository: YehorBabenko88/unified-system\n          ref: ${{ steps.matrix_bootstrap_source.outputs.source_sha }}\n          path: ${{ steps.matrix_bootstrap_source.outputs.checkout_path }}\n          persist-credentials: false\n          fetch-depth: 1\n          set-safe-directory: false\n          submodules: false\n          lfs: false\n";
function matrixCheckoutContract(text){assert.equal((text.match(/uses: actions\/checkout@/g)||[]).length,1);assert(text.includes(expectedCheckout));const jobs=text.split('jobs:\n')[1];assert.deepEqual(jobs.match(/^  [A-Za-z0-9_-]+:$/gm),['  roles:']);assert.deepEqual([...text.matchAll(/^\s+(?:- )?uses: ([^\n]+)$/gm)].map(x=>x[1]),['actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020','actions/checkout@11d5960a326750d5838078e36cf38b85af677262','actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02']);assert(text.indexOf('id: matrix_bootstrap_source')<text.indexOf(expectedCheckout));return true;}
assert.equal(matrixCheckoutContract(workflow),true);checks++;
for(const change of [x=>x.replace('repository: YehorBabenko88/unified-system','repository: YehorBabenko88/math'),x=>x.replace('steps.matrix_bootstrap_source.outputs.source_sha','github.sha'),x=>x.replace('persist-credentials: false','persist-credentials: true'),x=>x.replace('steps.matrix_bootstrap_source.outputs.checkout_path','inputs.path'),x=>x+expectedCheckout,x=>x.replace('checkout@11d5960a326750d5838078e36cf38b85af677262','checkout@'+'0'.repeat(40)),x=>x.replace("GIT_CONFIG_VALUE_0: 'false'","GIT_CONFIG_VALUE_0: 'true'"),x=>x+'  extra:\n    runs-on: ubuntu-latest\n']){assert.throws(()=>matrixCheckoutContract(change(workflow)));checks++;}
const preflight=workflow.split("node --input-type=module <<'ROOT_MATRIX_SOURCE'\n")[1]?.split('\n          ROOT_MATRIX_SOURCE')[0];assert(preflight);const rootPin=vm.runInNewContext('('+preflight.match(/function rootInput\(value\)\{[^\n]+\}/)[0]+')');assert.equal(rootPin('a'.repeat(40)),'a'.repeat(40));checks++;for(const value of [null,true,'main','A'.repeat(40),'a'.repeat(39),'a'.repeat(41)]){assert.throws(()=>rootPin(value));checks++;}

// Execute the actual bootstrap path statement with its declared imports; compiling alone misses unbound names.
function bootstrapPathBindings(text){
 const block=text.split("node --input-type=module <<'ROLE_MATRIX'\n")[1]?.split('\n          ROLE_MATRIX')[0];assert(block);
 const names=block.match(/import \{([^}]+)\} from 'node:path'/)[1].split(',');
 const statement=block.match(/const workspace=realpathSync\(process.env.GITHUB_WORKSPACE\),sourceDir=[^\n]+/)[0];
 const pathRoot='/inert/workspace',source=pathRoot+'/.root-role-source-Ab12Cd/root';
 const bindings={join:(...parts)=>parts.join('/'),dirname:value=>value.slice(0,value.lastIndexOf('/')),resolve:value=>value};
 const context={realpathSync:value=>value,process:{env:{GITHUB_WORKSPACE:pathRoot,ROLE_MATRIX_ROOT_CHECKOUT:source}},check:assert};
 for(const name of names){assert(Object.hasOwn(bindings,name));context[name]=bindings[name];}
 return vm.runInNewContext(statement+';sourceDir',context);
}
assert.equal(bootstrapPathBindings(workflow),'/inert/workspace/.root-role-source-Ab12Cd/root');checks++;
assert.throws(()=>bootstrapPathBindings(workflow.replace('import {join,dirname,resolve}', 'import {join,dirname}')),/resolve is not defined/);checks++;

const seed=vm.runInNewContext('('+workflow.match(/const ROOT_HTTP_BODY = Object.freeze\((\{[^\n]+\})\);/)[1]+')');assert.equal(seed.path,'tools/ci_evidence/http_body.mjs');assert.equal(seed.sha256,plan.files[seed.path]);assert(workflow.includes('helper.readHttpBody(response,{maxBytes:1048576,timeoutMs:5000})'));assert(!workflow.includes('const chunks=[]'));checks++;
assert(workflow.includes('/^[.]root-role-source-[A-Za-z0-9]{6}$/'));assert(preflight.includes("mkdtempSync(join(workspace,'.root-role-source-'))"));assert(workflow.indexOf("digest('hex')===ROOT_HTTP_BODY.sha256")<workflow.indexOf("await import('data:text/javascript;base64,'"));checks++;
const runner=readFileSync(new URL('./runner.mjs',import.meta.url),'utf8');assert(runner.includes('readHttpBody(response,{maxBytes:1048576,timeoutMs:5000})'));assert(runner.includes('staticResult.controls===92'));assert(!runner.includes('const chunks=[]'));checks++;


const collectorWorkflow=readFileSync(new URL('.github/workflows/ci-evidence-collector.yml',roleRoot),'utf8').replaceAll('\r\n','\n');function custodyFunctions(text){const a=text.indexOf('          function readOwned('),b=text.indexOf('\n',text.indexOf('          function rootHead(',a));assert(a>=0&&b>a);return text.slice(a,b);}assert.equal(custodyFunctions(workflow),custodyFunctions(collectorWorkflow));checks++;

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

const custodySource=readFileSync(new URL('./artifact_custody.mjs',import.meta.url),'utf8');assert(!custodySource.includes('async function body('));assert(custodySource.includes('readHttpBody(response,{maxBytes:download.size_in_bytes,timeoutMs:10000})'));
const bodySource=readFileSync(new URL('tools/ci_evidence/http_body.mjs',roleRoot),'utf8');assert.equal(sha(readFileSync(new URL('tools/ci_evidence/http_body.mjs',root))),plan.files['tools/ci_evidence/http_body.mjs']);
function streamModel(){let timeout=null,cleared=0,clock=0;const read=vm.runInNewContext('(function(){'+bodySource.replace(/^export /gm,'')+';return(response,limit)=>readHttpBody(response,{maxBytes:limit,timeoutMs:10000});})()',{Buffer,Uint8Array,Symbol,Promise,performance:{now:()=>clock},setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{cleared++;}});return{read,expire(){assert.equal(typeof timeout,'function');timeout();},late(){clock=10001;},get cleared(){return cleared;}};}

let sm=streamModel();let emptyCalls=0;async function* emptyFragments(){for(let i=0;i<20000;i++){emptyCalls++;yield Buffer.alloc(0);}}await assert.rejects(sm.read({body:emptyFragments()},1));assert.equal(emptyCalls,1);assert.equal(sm.cleared,1);checks++;
sm=streamModel();let tinyCalls=0;async function* tinyFragments(){for(let i=0;i<5000;i++){tinyCalls++;yield Buffer.from('x');}}await assert.rejects(sm.read({body:tinyFragments()},10000));assert.equal(tinyCalls,4097);checks++;
sm=streamModel();async function* validFragments(){yield Buffer.from('a');yield Buffer.from('b');}assert.equal((await sm.read({body:validFragments()},2)).toString(),'ab');assert.equal(sm.cleared,1);checks++;
sm=streamModel();await assert.rejects(sm.read({body:validFragments()},1));checks++;
sm=streamModel();async function* noBytes(){}await assert.rejects(sm.read({body:noBytes()},1));checks++;
sm=streamModel();let returned=0;const stalled={ [Symbol.asyncIterator](){return{next(){return new Promise(()=>{});},return(){returned++;return Promise.resolve({done:true});}};}};const pending=sm.read({body:stalled},1);sm.expire();await assert.rejects(pending);assert.equal(returned,1);assert.equal(sm.cleared,1);checks++;
sm=streamModel();const delayed={ [Symbol.asyncIterator](){return{async next(){sm.late();return{done:false,value:Buffer.from('x')};},return(){return{done:true};}};}};await assert.rejects(sm.read({body:delayed},1));checks++;


// Child diagnostics disclose only fixed stage codes, never child-controlled bytes.
const diagnosticSource=workflow.match(/function runnerDiagnostic\(value\)\{[^\n]+\}/)?.[0];assert(diagnosticSource,'CLOSED_RUNNER_DIAGNOSTIC_REQUIRED');
const diagnose=vm.runInNewContext('('+diagnosticSource+')');
const failedChild={status:1,signal:null,stdout:'',stderr:'ROLE_MATRIX_BLOCKED:E_WORKLOAD_BIND\n'};
assert.equal(diagnose(failedChild),'E_WORKLOAD_BIND');checks++;
for(const value of [null,true,'SECRET_SENTINEL',{}, {status:1,signal:null,stdout:'SECRET_SENTINEL',stderr:failedChild.stderr},{...failedChild,stderr:'SECRET_SENTINEL'},{...failedChild,stderr:failedChild.stderr+'SECRET_SENTINEL'},{...failedChild,stderr:'ROLE_MATRIX_BLOCKED:E_NOT_APPROVED\n'}]){const code=diagnose(value);assert(/^E_CHILD_(SHAPE|RESULT)$/.test(code));assert(!code.includes('SECRET'));checks++;}
assert.equal(diagnose({...failedChild,error:new Error('SECRET_SENTINEL')}),'E_CHILD_EXECUTION');checks++;
assert.equal(diagnose({...failedChild,signal:'SIGTERM'}),'E_CHILD_SIGNAL');checks++;
for(const key of ['status','signal','stdout','stderr','error']){let reads=0;const hostile={...failedChild};Object.defineProperty(hostile,key,{get(){reads++;throw Error('SECRET_SENTINEL');}});assert.equal(diagnose(hostile),'E_CHILD_SHAPE');assert.equal(reads,0);checks++;}

const runnerStages=[...new Set([...runner.matchAll(/phase='(E_[A-Z_]+)'/g)].map(x=>x[1]))];for(const code of runnerStages){assert.equal(diagnose({...failedChild,stderr:'ROLE_MATRIX_BLOCKED:'+code+'\n'}),code);checks++;}
assert(workflow.includes("console.error('ROLE_MATRIX_RUNNER_DIAGNOSTIC:'+runnerDiagnostic(child))"));assert(!workflow.includes('console.error(child.stderr)'));checks++;


const bindingPacket='ROLE_MATRIX_BIND_DIAGNOSTIC:R_IN_PROGRESS__J_QUEUED__REF_PR_MERGE_SHAPE__RA_MATCH__JA_MISSING__RH_MATCH__JH_MATCH__WF_MATCH__CHECK_SHAPE\nROLE_MATRIX_BLOCKED:E_WORKLOAD_BIND\n';
assert.equal(diagnose({...failedChild,stderr:bindingPacket}),'E_WORKLOAD_BIND__R_IN_PROGRESS__J_QUEUED__REF_PR_MERGE_SHAPE__RA_MATCH__JA_MISSING__RH_MATCH__JH_MATCH__WF_MATCH__CHECK_SHAPE');checks++;
for(const raw of [bindingPacket+'SECRET_SENTINEL',bindingPacket.replace('J_QUEUED','J_SECRET_SENTINEL'),bindingPacket.replace('REF_PR_MERGE_SHAPE','REF_UNKNOWN'),bindingPacket.replace('BLOCKED:E_WORKLOAD_BIND','BLOCKED:E_PG_QUERY'),bindingPacket.replace('R_IN_PROGRESS','R_in_progress')]){assert.equal(diagnose({...failedChild,stderr:raw}),'E_CHILD_RESULT');checks++;}
assert.equal(diagnose({...failedChild,stderr:bindingPacket,stdout:'SECRET_SENTINEL'}),'E_CHILD_RESULT');checks++;

console.log(JSON.stringify({checks,status:'PASS_INERT_SOURCE_ONLY',authority:'NONE',production:'NO_GO'}));
