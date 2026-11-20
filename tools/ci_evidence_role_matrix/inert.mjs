import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateCell,projectTerminal,requireTerminals,makeReceipt,validateReceipt,bindWorkload} from './contract.mjs';
const plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
let checks=0;
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
console.log(JSON.stringify({checks,status:'PASS_INERT_ONLY',authority:'NONE',production:'NO_GO'}));
