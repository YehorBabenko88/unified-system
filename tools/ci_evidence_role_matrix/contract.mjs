import {resolve} from 'node:path';
const reject=()=>{throw Error('ROLE_MATRIX_REFUSED');};
const need=value=>{if(!value)reject();};
const oid=value=>typeof value==='string'&&/^[a-f0-9]{40}$/.test(value);
const hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const id=value=>typeof value==='string'&&/^[1-9][0-9]{0,19}$/.test(value);
function closed(value,fields){need(value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype);const d=Object.getOwnPropertyDescriptors(value);need(Object.keys(d).length===fields.length&&fields.every(key=>Object.hasOwn(d,key)&&Object.hasOwn(d[key],'value')));}
export function validateCell(cell){need(typeof cell==='string'&&/^linux-(22|24)-(16|18)$/.test(cell));const[,node,postgres]=cell.split('-');return Object.freeze({cell,node,postgres});}
function planned(plan){need(plan.schema==='unified.ci-evidence-role-plan.v1'&&plan.role_source==='006418285667b38810b7ecd1de9807b6db166fa3'&&Array.isArray(plan.roles)&&plan.roles.length===34&&new Set(plan.roles.map(x=>x.id)).size===34);need(plan.roles.filter(x=>x.kind==='HOSTED').length===31&&plan.roles.filter(x=>x.kind==='STATIC').length===3);for(const role of plan.roles)need(hash(role.id)&&role.original.parent===null&&role.original.occurrence===1);return plan;}
export function projectTerminal(event,plan,root){
 planned(plan);need(event!==null&&typeof event==='object'&&typeof event.type==='string');
 if(event.type!=='test:pass'&&event.type!=='test:fail')return null;
 need(event.type==='test:pass');const data=event.data;
 need(data!==null&&typeof data==='object'&&data.nesting===0&&typeof data.name==='string'&&data.name.length<=512&&typeof data.file==='string'&&data.file.length<=4096&&!data.skip&&!data.todo&&!data.cancelled&&!data.details?.error);
 const roles=plan.roles.filter(role=>role.kind==='HOSTED'&&role.original.name===data.name&&resolve(root,role.target)===resolve(data.file));need(roles.length===1);
 return Object.freeze({id:roles[0].id,status:'PASS'});
}
export function requireTerminals(terminals,plan){planned(plan);need(Array.isArray(terminals)&&terminals.length===31);const expected=plan.roles.filter(role=>role.kind==='HOSTED').map(role=>role.id).sort();for(const value of terminals){closed(value,['id','status']);need(hash(value.id)&&value.status==='PASS');}need(JSON.stringify(terminals.map(x=>x.id).sort())===JSON.stringify(expected));return terminals;}
export function bindWorkload(run,jobs,pr,expected){
 const cell=validateCell(expected.cell);need(oid(expected.runnerSource));need(Array.isArray(run?.referenced_workflows)&&run.referenced_workflows.length<=32&&run.referenced_workflows.filter(value=>value.path==='YehorBabenko88/unified-system/.github/workflows/ci-evidence-role-matrix.yml@'+expected.runnerSource&&value.sha===expected.runnerSource).length===1);
 need(['push','pull_request','workflow_dispatch'].includes(expected.event)&&id(expected.runId)&&id(expected.attempt)&&oid(expected.workloadHead));
 need(Number.isSafeInteger(run?.id)&&run.id>0&&Number.isSafeInteger(run.run_attempt)&&run.run_attempt>0);
 need(run?.repository?.full_name==='YehorBabenko88/math'&&String(run.id)===expected.runId&&String(run.run_attempt)===expected.attempt&&run.event===expected.event&&run.status==='in_progress'&&oid(run.head_sha));
 if(expected.event==='pull_request'){
  need(Number.isSafeInteger(pr?.number)&&pr.number>0&&id(expected.prNumber)&&expected.ref==='refs/pull/'+expected.prNumber+'/merge');
  need(Array.isArray(run.pull_requests)&&run.pull_requests.length===1&&String(run.pull_requests[0].number)===expected.prNumber&&run.pull_requests[0].head?.sha===expected.workloadHead);
  need(String(pr?.number)===expected.prNumber&&pr.head?.sha===expected.workloadHead&&typeof pr.head?.repo?.full_name==='string'&&new RegExp('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$').test(pr.head.repo.full_name)&&pr.base?.repo?.full_name==='YehorBabenko88/math');
 }else{
  need(pr===null&&typeof expected.ref==='string'&&expected.ref.length<=256&&(expected.ref.startsWith('refs/heads/')||expected.ref.startsWith('refs/tags/'))&&new RegExp('^[A-Za-z0-9._/-]+$').test(expected.ref)&&!expected.ref.includes('..'));
  const branch=expected.ref.slice(expected.ref.startsWith('refs/heads/')?11:10);need(branch.length>0&&run.head_branch===branch&&run.head_repository?.full_name==='YehorBabenko88/math'&&run.head_sha===expected.workloadHead);
 }
 need(Number.isSafeInteger(jobs?.total_count)&&jobs.total_count>0&&jobs.total_count<=100&&Array.isArray(jobs.jobs)&&jobs.jobs.length===jobs.total_count);
 const label='Root transferred unit roles '+cell.cell;
 const found=jobs.jobs.filter(job=>typeof job.name==='string'&&job.name.length<=512&&(job.name===label||job.name.endsWith(' / '+label)));need(found.length===1);const job=found[0];
 need(Number.isSafeInteger(job.id)&&job.id>0&&Number.isSafeInteger(job.run_id)&&Number.isSafeInteger(job.run_attempt)&&String(job.run_id)===expected.runId&&String(job.run_attempt)===expected.attempt&&job.status==='in_progress'&&job.head_sha===run.head_sha);
 const prefix='https://api.github.com/repos/YehorBabenko88/math/check-runs/';need(typeof job.check_run_url==='string'&&job.check_run_url.startsWith(prefix));const checkId=job.check_run_url.slice(prefix.length);need(id(checkId));
 return Object.freeze({workload_event:expected.event,workload_head:expected.workloadHead,run_head:run.head_sha,run_id:expected.runId,attempt:expected.attempt,job_id:String(job.id),check_run_id:checkId,cell:cell.cell});
}
const contextFields=['workload_event','cell','workload_head','run_head','run_id','attempt','job_id','check_run_id','runner_workflow_source','runner_workflow_sha256'];
function context(ctx){closed(ctx,contextFields);validateCell(ctx.cell);need(['push','pull_request','workflow_dispatch'].includes(ctx.workload_event));need(oid(ctx.workload_head)&&oid(ctx.run_head)&&oid(ctx.runner_workflow_source)&&hash(ctx.runner_workflow_sha256));for(const key of ['run_id','attempt','job_id','check_run_id'])need(id(ctx[key]));}
export function makeReceipt(plan,ctx,observed){
 planned(plan);context(ctx);const cell=validateCell(observed.cell);need(ctx.cell===cell.cell);need(observed.actualNode===cell.node&&typeof observed.pgVersion==='string'&&new RegExp('^'+cell.postgres+'[0-9]{4}$').test(observed.pgVersion));requireTerminals(observed.terminals,plan);need(observed.staticPassed===true);
 const files=Object.keys(plan.files).sort().map(path=>plan.files[path]);need(files.length===31&&files.every(hash));
 return {schema:'unified.ci-evidence-role-cell.v1',role_source:plan.role_source,runner_workflow_source:ctx.runner_workflow_source,runner_workflow_sha256:ctx.runner_workflow_sha256,workload_repository:'YehorBabenko88/math',workload_event:ctx.workload_event,workload_head:ctx.workload_head,run_head:ctx.run_head,run_id:ctx.run_id,attempt:ctx.attempt,job_id:ctx.job_id,check_run_id:ctx.check_run_id,cell:cell.cell,node_major:cell.node,postgres_major:cell.postgres,postgres_version_num:observed.pgVersion,roles:plan.roles.map(role=>({id:role.id,status:'PASS'})),file_hashes:files,scope:'UNIT_ONLY',authority:'NONE',source_authentication:'NOT_EVALUATED',native_acceptance:'NOT_QUALIFIED',production:'NO_GO'};
}
export function validateReceipt(receipt,plan,ctx){
 closed(receipt,['schema','role_source','runner_workflow_source','runner_workflow_sha256','workload_repository','workload_event','workload_head','run_head','run_id','attempt','job_id','check_run_id','cell','node_major','postgres_major','postgres_version_num','roles','file_hashes','scope','authority','source_authentication','native_acceptance','production']);
 need(Array.isArray(receipt.roles)&&receipt.roles.length===34&&Array.isArray(receipt.file_hashes)&&receipt.file_hashes.length===31);for(const role of receipt.roles){closed(role,['id','status']);need(hash(role.id)&&role.status==='PASS');}need(receipt.file_hashes.every(hash));
 context(ctx);const expected=makeReceipt(plan,ctx,{cell:receipt.cell,actualNode:receipt.node_major,pgVersion:receipt.postgres_version_num,terminals:plan.roles.filter(x=>x.kind==='HOSTED').map(x=>({id:x.id,status:'PASS'})),staticPassed:true});closed(receipt,Object.keys(expected));need(JSON.stringify(receipt)===JSON.stringify(expected));return true;
}
export function parseTerminals(text,plan){
 need(typeof text==='string'&&text.length<=131072);const lines=text.trimEnd().split('\n');need(lines.length===31&&lines.every(line=>line.length<=256));
 const values=lines.map(line=>{try{return JSON.parse(line);}catch{reject();}});return requireTerminals(values,plan);
}
