import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateCell,projectTerminal,requireTerminals,makeReceipt,validateReceipt,bindWorkload} from './contract.mjs';
const plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
let checks=0;assert.equal(plan.role_source,'006418285667b38810b7ecd1de9807b6db166fa3');checks++;
for(const cell of plan.cells){assert.equal(validateCell(cell).cell,cell);checks++;}
for(const bad of ['linux-20-16','windows-22-16','linux-22-17','linux-22-16/secret',null]){assert.throws(()=>validateCell(bad));checks++;}
const role=plan.roles.find(x=>x.kind==='HOSTED'),root='/private/role-source';
const event={type:'test:pass',data:{name:role.original.name,file:root+'/'+role.target,nesting:0,details:{}}};
assert.equal(projectTerminal(event,plan,root).id,role.id);checks++;
for(const changed of [{type:'test:fail'}, {data:{...event.data,skip:true}},{data:{...event.data,todo:true}},{data:{...event.data,nesting:1}},{data:{...event.data,name:'SECRET_SENTINEL'}},{data:{...event.data,file:'/unowned/secret'}}]){assert.throws(()=>projectTerminal({...event,...changed},plan,root));checks++;}
const terminals=plan.roles.filter(x=>x.kind==='HOSTED').map(x=>({id:x.id,status:'PASS'}));assert.equal(requireTerminals(terminals,plan).length,31);checks++;
for(const wrong of [terminals.slice(1),[...terminals,terminals[0]],[...terminals.slice(1),{id:'f'.repeat(64),status:'PASS'}],terminals.map((x,i)=>i?x:{...x,status:'SKIP'})]){assert.throws(()=>requireTerminals(wrong,plan));checks++;}
const context={workload_event:'pull_request',cell:'linux-22-16',workload_head:'a'.repeat(40),run_head:'b'.repeat(40),run_id:'10',attempt:'2',job_id:'20',check_run_id:'30',runner_workflow_source:'c'.repeat(40),runner_workflow_sha256:'d'.repeat(64)};
const receipt=makeReceipt(plan,context,{cell:'linux-22-16',actualNode:'22',pgVersion:'160009',terminals,staticPassed:true});assert.equal(validateReceipt(receipt,plan,context),true);checks++;
for(const changed of [{token:'SECRET_SENTINEL'},{authority:'GRANTED'},{roles:receipt.roles.slice(1)},{postgres_version_num:'180001'},{cell:'linux-22-18',postgres_major:'18',postgres_version_num:'180001'},{file_hashes:[]},{runner_workflow_source:'e'.repeat(40)}]){assert.throws(()=>validateReceipt({...receipt,...changed},plan,context));checks++;}
const run={referenced_workflows:[{path:'YehorBabenko88/unified-system/.github/workflows/ci-evidence-role-matrix.yml@'+'c'.repeat(40),sha:'c'.repeat(40)}],id:10,run_attempt:2,repository:{full_name:'YehorBabenko88/math'},event:'pull_request',status:'in_progress',head_sha:'b'.repeat(40),pull_requests:[{number:1,head:{sha:'a'.repeat(40)}}]};
const job={id:20,run_id:10,run_attempt:2,status:'in_progress',head_sha:run.head_sha,name:'caller / Root transferred unit roles linux-22-16',check_run_url:'https://api.github.com/repos/YehorBabenko88/math/check-runs/30'};
const pr={number:1,head:{sha:'a'.repeat(40),repo:{full_name:'YehorBabenko88/math'}},base:{repo:{full_name:'YehorBabenko88/math'}}};
const expected={event:'pull_request',ref:'refs/pull/1/merge',runnerSource:'c'.repeat(40),runId:'10',attempt:'2',prNumber:'1',workloadHead:'a'.repeat(40),cell:'linux-22-16'};
assert.equal(bindWorkload(run,{total_count:1,jobs:[job]},pr,expected).job_id,'20');checks++;
for(const jobs of [{total_count:2,jobs:[job,job]},{total_count:101,jobs:[job]},{total_count:1,jobs:[{...job,status:'completed'}]},{total_count:1,jobs:[{...job,head_sha:'f'.repeat(40)}]}]){assert.throws(()=>bindWorkload(run,jobs,pr,expected));checks++;}
assert.throws(()=>bindWorkload(run,{total_count:1,jobs:[job]},{...pr,head:{...pr.head,sha:'f'.repeat(40)}},expected));checks++;
for(const event of ['push','workflow_dispatch']){
 const pushRun={...run,event,head_sha:'a'.repeat(40),head_branch:'main',head_repository:{full_name:'YehorBabenko88/math'},pull_requests:[]};
 const pushJob={...job,head_sha:pushRun.head_sha};const request={...expected,event,ref:'refs/heads/main'};
 assert.equal(bindWorkload(pushRun,{total_count:1,jobs:[pushJob]},null,request).workload_event,event);checks++;
 for(const change of [{event:'schedule'},{ref:'refs/pull/1/merge'},{ref:'refs/heads/../secret'},{workloadHead:'f'.repeat(40)}]){assert.throws(()=>bindWorkload(pushRun,{total_count:1,jobs:[pushJob]},null,{...request,...change}));checks++;}
}
assert.equal(bindWorkload(run,{total_count:1,jobs:[job]},{...pr,head:{...pr.head,repo:{full_name:'forkOwner/math'}}},expected).workload_head,expected.workloadHead);checks++;
assert.throws(()=>makeReceipt(plan,context,{cell:'linux-22-16',actualNode:'24',pgVersion:'160009',terminals,staticPassed:true}));checks++;
assert.throws(()=>makeReceipt(plan,context,{cell:'linux-22-16',actualNode:'22',pgVersion:'160009',terminals,staticPassed:1}));checks++;
for(const value of ['10',true,Number.MAX_SAFE_INTEGER+1]){assert.throws(()=>bindWorkload({...run,id:value},{total_count:1,jobs:[job]},pr,expected));checks++;}
assert.throws(()=>bindWorkload({...run,referenced_workflows:[]},{total_count:1,jobs:[job]},pr,expected));checks++;
assert.throws(()=>makeReceipt({...plan,role_source:'82bf1578c5e36bafd76615661fbb3fe4e22dca55'},context,{cell:'linux-22-16',actualNode:'22',pgVersion:'160009',terminals,staticPassed:true}));checks++;

// Four-Root packet consistency is not hosted download/authentication evidence.
let aggregate;try{aggregate=await import('./aggregate.mjs');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}
assert.equal(typeof aggregate?.validateRootRoleCoverage,'function','bounded four-cell aggregate validator required');
const {validateRootRoleCoverage}=aggregate;
const {createHash}=await import('node:crypto');const wfHash=createHash('sha256').update(readFileSync(new URL('../../.github/workflows/ci-evidence-role-matrix.yml',import.meta.url))).digest('hex');
const allRun={...run,repository:{...run.repository,id:1},head_branch:'feature'};
const allJobs=plan.cells.map((cell,i)=>({...job,id:20+i,name:'caller / Root transferred unit roles '+cell,status:'completed',conclusion:'success',check_run_url:'https://api.github.com/repos/YehorBabenko88/math/check-runs/'+(30+i)}));
const packet={schema:'unified.ci-evidence-role-aggregate-input.v1',expected:{event:'pull_request',ref:'refs/pull/1/merge',runnerSource:'c'.repeat(40),runId:'10',attempt:'2',prNumber:'1',workloadHead:'a'.repeat(40)},run:allRun,jobs:{total_count:4,jobs:allJobs},pr,artifacts:{total_count:4,artifacts:[]},receipts:[]};
for(const[cellIndex,cell]of plan.cells.entries()){
 const cellInfo=validateCell(cell),ctx={...context,cell,job_id:String(20+cellIndex),check_run_id:String(30+cellIndex),runner_workflow_sha256:wfHash};
 const item=makeReceipt(plan,ctx,{cell,actualNode:cellInfo.node,pgVersion:cellInfo.postgres+'0001',terminals,staticPassed:true});
 const aid=40+cellIndex;packet.receipts.push({artifact_id:String(aid),content:JSON.stringify(item)+'\n'});packet.artifacts.artifacts.push({id:aid,name:'root-ci-evidence-unit-'+cell+'-10-2',expired:false,size_in_bytes:1024,workflow_run:{id:10,repository_id:1,head_sha:allRun.head_sha,head_branch:allRun.head_branch}});
}
const qualify=p=>validateRootRoleCoverage(JSON.stringify(p));const positive=qualify(packet);assert.equal(positive.status,'CONSISTENT_SOURCE_ONLY');assert.equal(positive.coverage,'HELD');assert.equal(positive.download_custody,'NOT_EVALUATED');assert.equal(positive.authority,'NONE');assert.equal(positive.cells,4);checks++;
const alter=(p,i,change)=>{const r=JSON.parse(p.receipts[i].content);change(r);p.receipts[i].content=JSON.stringify(r)+'\n';};
const changes=[
 p=>p.receipts.pop(),p=>p.receipts.push(p.receipts[0]),p=>p.receipts[1]=p.receipts[0],p=>p.receipts[0].artifact_id='999',
 p=>p.receipts[0].content='{}\n',p=>p.receipts[0].content+=' ',p=>p.receipts[0].content=p.receipts[0].content.replace('{','{\"schema\":\"forged\",'),
 p=>alter(p,0,r=>r.authority='GRANTED'),p=>alter(p,0,r=>r.roles[0].status='XFAIL'),p=>alter(p,0,r=>r.roles.pop()),p=>alter(p,0,r=>r.file_hashes[0]='f'.repeat(64)),p=>alter(p,0,r=>r.postgres_version_num='180001'),p=>alter(p,0,r=>r.node_major='24'),p=>alter(p,0,r=>r.runner_workflow_sha256='0'.repeat(64)),
 p=>p.expected.runId='11',p=>p.expected.attempt='3',p=>p.expected.workloadHead='f'.repeat(40),p=>p.run.referenced_workflows=[],p=>delete p.run.head_branch,p=>delete p.artifacts.artifacts[0].workflow_run.head_branch,p=>p.jobs.jobs[1].check_run_url=p.jobs.jobs[0].check_run_url,
 p=>p.jobs.jobs[0].status='in_progress',p=>p.jobs.jobs[0].conclusion='cancelled',p=>p.jobs.jobs[0].conclusion='skipped',p=>p.jobs.jobs[0].head_sha='f'.repeat(40),p=>p.jobs.jobs[0].run_attempt=3,p=>p.jobs.jobs.push(p.jobs.jobs[0]),p=>{p.jobs.jobs.push(p.jobs.jobs[0]);p.jobs.total_count++;},
 p=>p.artifacts.artifacts[0].expired=true,p=>p.artifacts.artifacts[0].size_in_bytes=1048577,p=>p.artifacts.artifacts[0].name+='-stale',p=>p.artifacts.artifacts[0].workflow_run.id=11,p=>p.artifacts.artifacts[0].workflow_run.repository_id=2,p=>p.artifacts.artifacts[0].workflow_run.head_sha='f'.repeat(40),p=>p.artifacts.artifacts[0].workflow_run.head_branch='other',p=>{p.artifacts.artifacts.push({...p.artifacts.artifacts[0],id:99});p.artifacts.total_count++;},
 p=>p.extra='SECRET_SENTINEL'
];
for(const change of changes){const p=structuredClone(packet);change(p);const result=qualify(p);assert.equal(result.status,'HELD');assert.equal(result.code,'E_ROOT_ROLE_EVIDENCE');assert(!JSON.stringify(result).includes('SECRET_SENTINEL'));checks++;}
for(const raw of [undefined,null,true,'','{',' '.repeat(2097153),JSON.stringify(packet).replace('{','{\"schema\":\"duplicate\",')]){assert.equal(validateRootRoleCoverage(raw).status,'HELD');checks++;}
let parsedHuge=false;const realParse=JSON.parse;try{JSON.parse=()=>{parsedHuge=true;throw Error('UNEXPECTED_PARSE');};assert.equal(validateRootRoleCoverage('x'.repeat(2097153)).status,'HELD');assert.equal(parsedHuge,false);checks++;}finally{JSON.parse=realParse;}
let coercions=0;const hostile={toString(){coercions++;throw Error('SECRET_SENTINEL');}};assert.equal(validateRootRoleCoverage(hostile).status,'HELD');assert.equal(coercions,0);checks++;
const mixed=structuredClone(packet);mixed.jobs.jobs.push({...job,id:100,name:'Math platform linux-22-16'});mixed.jobs.total_count++;mixed.artifacts.artifacts.push({id:100,name:'platform-linux-22-16'});mixed.artifacts.total_count++;assert.equal(qualify(mixed).status,'CONSISTENT_SOURCE_ONLY');checks++;

console.log(JSON.stringify({checks,status:'PASS_INERT_ONLY',authority:'NONE',production:'NO_GO'}));
