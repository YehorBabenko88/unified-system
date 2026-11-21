import {types as _bindTypes} from 'node:util';
import {resolve} from 'node:path';
const reject=()=>{throw Error('ROLE_MATRIX_REFUSED');};
const need=value=>{if(!value)reject();};
const oid=value=>typeof value==='string'&&/^[a-f0-9]{40}$/.test(value);
const hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const id=value=>typeof value==='string'&&/^[1-9][0-9]{0,19}$/.test(value);
function closed(value,fields){need(value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.getPrototypeOf(value)===Object.prototype);const d=Object.getOwnPropertyDescriptors(value);need(Object.keys(d).length===fields.length&&fields.every(key=>Object.hasOwn(d,key)&&Object.hasOwn(d[key],'value')));}
export function validateCell(cell){need(typeof cell==='string'&&/^linux-(22|24)-(16|18)$/.test(cell));const[,node,postgres]=cell.split('-');return Object.freeze({cell,node,postgres});}
function planned(plan){need(plan.schema==='unified.ci-evidence-role-plan.v1'&&plan.role_source==='4ba390b8e12070499d54b12e5609c683c00607ee'&&plan.files&&Object.hasOwn(plan.files,'tools/ci_evidence/http_body.mjs')&&Array.isArray(plan.roles)&&plan.roles.length===34&&new Set(plan.roles.map(x=>x.id)).size===34);need(plan.roles.filter(x=>x.kind==='HOSTED').length===31&&plan.roles.filter(x=>x.kind==='STATIC').length===3);for(const role of plan.roles)need(hash(role.id)&&role.original.parent===null&&role.original.occurrence===1);return plan;}
export function projectTerminal(event,plan,root){
 planned(plan);need(event!==null&&typeof event==='object'&&typeof event.type==='string');
 if(event.type!=='test:pass'&&event.type!=='test:fail')return null;
 need(event.type==='test:pass');const data=event.data;
 need(data!==null&&typeof data==='object'&&data.nesting===0&&typeof data.name==='string'&&data.name.length<=512&&typeof data.file==='string'&&data.file.length<=4096&&!data.skip&&!data.todo&&!data.cancelled&&!data.details?.error);
 const roles=plan.roles.filter(role=>role.kind==='HOSTED'&&role.original.name===data.name&&resolve(root,role.target)===resolve(data.file));need(roles.length===1);
 return Object.freeze({id:roles[0].id,status:'PASS'});
}
export function requireTerminals(terminals,plan){planned(plan);need(Array.isArray(terminals)&&terminals.length===31);const expected=plan.roles.filter(role=>role.kind==='HOSTED').map(role=>role.id).sort();for(const value of terminals){closed(value,['id','status']);need(hash(value.id)&&value.status==='PASS');}need(JSON.stringify(terminals.map(x=>x.id).sort())===JSON.stringify(expected));return terminals;}
export function bindWorkload(run,jobs,pr,expected,jobPhase='in_progress'){
 need(jobPhase==='in_progress'||jobPhase==='completed');
 const cell=validateCell(expected.cell);need(oid(expected.runnerSource));need(Array.isArray(run?.referenced_workflows)&&run.referenced_workflows.length<=32&&run.referenced_workflows.filter(value=>value.path==='YehorBabenko88/unified-system/.github/workflows/ci-evidence-role-matrix.yml@'+expected.runnerSource&&value.sha===expected.runnerSource).length===1);
 need(['push','pull_request','workflow_dispatch'].includes(expected.event)&&id(expected.runId)&&id(expected.attempt)&&oid(expected.workloadHead));
 need(Number.isSafeInteger(run?.id)&&run.id>0&&Number.isSafeInteger(run.run_attempt)&&run.run_attempt>0);
 need(run?.repository?.full_name==='YehorBabenko88/math'&&String(run.id)===expected.runId&&String(run.run_attempt)===expected.attempt&&run.event===expected.event&&run.status==='in_progress'&&oid(run.head_sha));
 if(expected.event==='pull_request'){
  need(Number.isSafeInteger(pr?.number)&&pr.number>0&&id(expected.prNumber)&&expected.ref==='refs/pull/'+expected.prNumber+'/merge'&&run.head_sha===expected.workloadHead);
  need(Array.isArray(run.pull_requests)&&run.pull_requests.length===1&&String(run.pull_requests[0].number)===expected.prNumber&&run.pull_requests[0].head?.sha===expected.workloadHead);
  need(String(pr?.number)===expected.prNumber&&pr.head?.sha===expected.workloadHead&&typeof pr.head?.repo?.full_name==='string'&&new RegExp('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$').test(pr.head.repo.full_name)&&pr.base?.repo?.full_name==='YehorBabenko88/math');
 }else{
  need(pr===null&&typeof expected.ref==='string'&&expected.ref.length<=256&&(expected.ref.startsWith('refs/heads/')||expected.ref.startsWith('refs/tags/'))&&new RegExp('^[A-Za-z0-9._/-]+$').test(expected.ref)&&!expected.ref.includes('..'));
  const branch=expected.ref.slice(expected.ref.startsWith('refs/heads/')?11:10);need(branch.length>0&&run.head_branch===branch&&run.head_repository?.full_name==='YehorBabenko88/math'&&run.head_sha===expected.workloadHead);
 }
 need(Number.isSafeInteger(jobs?.total_count)&&jobs.total_count>0&&jobs.total_count<=100&&Array.isArray(jobs.jobs)&&jobs.jobs.length===jobs.total_count);
 const label='Root transferred unit roles '+cell.cell;
 const found=jobs.jobs.filter(job=>typeof job.name==='string'&&job.name.length<=512&&(job.name===label||job.name.endsWith(' / '+label)));need(found.length===1);const job=found[0];
 need(Number.isSafeInteger(job.id)&&job.id>0&&Number.isSafeInteger(job.run_id)&&Number.isSafeInteger(job.run_attempt)&&String(job.run_id)===expected.runId&&String(job.run_attempt)===expected.attempt&&job.status===jobPhase&&(jobPhase!=='completed'||job.conclusion==='success')&&job.head_sha===run.head_sha);
 const prefix='https://api.github.com/repos/YehorBabenko88/math/check-runs/';need(typeof job.check_run_url==='string'&&job.check_run_url.startsWith(prefix));const checkId=job.check_run_url.slice(prefix.length);need(id(checkId));
 return Object.freeze({workload_event:expected.event,workload_head:expected.workloadHead,run_head:run.head_sha,run_id:expected.runId,attempt:expected.attempt,job_id:String(job.id),check_run_id:checkId,cell:cell.cell});
}
const contextFields=['workload_event','cell','workload_head','run_head','run_id','attempt','job_id','check_run_id','runner_workflow_source','runner_workflow_sha256'];
function context(ctx){closed(ctx,contextFields);validateCell(ctx.cell);need(['push','pull_request','workflow_dispatch'].includes(ctx.workload_event));need(oid(ctx.workload_head)&&oid(ctx.run_head)&&oid(ctx.runner_workflow_source)&&hash(ctx.runner_workflow_sha256));if(ctx.workload_event==='pull_request')need(ctx.run_head===ctx.workload_head);for(const key of ['run_id','attempt','job_id','check_run_id'])need(id(ctx[key]));}
export function makeReceipt(plan,ctx,observed){
 planned(plan);context(ctx);const cell=validateCell(observed.cell);need(ctx.cell===cell.cell);need(observed.actualNode===cell.node&&typeof observed.pgVersion==='string'&&new RegExp('^'+cell.postgres+'[0-9]{4}$').test(observed.pgVersion));requireTerminals(observed.terminals,plan);need(observed.staticPassed===true);
 const files=Object.keys(plan.files).sort().map(path=>plan.files[path]);need(files.length===32&&files.every(hash));
 return {schema:'unified.ci-evidence-role-cell.v1',role_source:plan.role_source,runner_workflow_source:ctx.runner_workflow_source,runner_workflow_sha256:ctx.runner_workflow_sha256,workload_repository:'YehorBabenko88/math',workload_event:ctx.workload_event,workload_head:ctx.workload_head,run_head:ctx.run_head,run_id:ctx.run_id,attempt:ctx.attempt,job_id:ctx.job_id,check_run_id:ctx.check_run_id,cell:cell.cell,node_major:cell.node,postgres_major:cell.postgres,postgres_version_num:observed.pgVersion,roles:plan.roles.map(role=>({id:role.id,status:'PASS'})),file_hashes:files,scope:'UNIT_ONLY',authority:'NONE',source_authentication:'NOT_EVALUATED',native_acceptance:'NOT_QUALIFIED',production:'NO_GO'};
}
export function validateReceipt(receipt,plan,ctx){
 closed(receipt,['schema','role_source','runner_workflow_source','runner_workflow_sha256','workload_repository','workload_event','workload_head','run_head','run_id','attempt','job_id','check_run_id','cell','node_major','postgres_major','postgres_version_num','roles','file_hashes','scope','authority','source_authentication','native_acceptance','production']);
 need(Array.isArray(receipt.roles)&&receipt.roles.length===34&&Array.isArray(receipt.file_hashes)&&receipt.file_hashes.length===32);for(const role of receipt.roles){closed(role,['id','status']);need(hash(role.id)&&role.status==='PASS');}need(receipt.file_hashes.every(hash));
 context(ctx);const expected=makeReceipt(plan,ctx,{cell:receipt.cell,actualNode:receipt.node_major,pgVersion:receipt.postgres_version_num,terminals:plan.roles.filter(x=>x.kind==='HOSTED').map(x=>({id:x.id,status:'PASS'})),staticPassed:true});closed(receipt,Object.keys(expected));need(JSON.stringify(receipt)===JSON.stringify(expected));return true;
}
export function parseTerminals(text,plan){
 need(typeof text==='string'&&text.length<=131072);const lines=text.trimEnd().split('\n');need(lines.length===31&&lines.every(line=>line.length<=256));
 const values=lines.map(line=>{try{return JSON.parse(line);}catch{reject();}});return requireTerminals(values,plan);
}

// Descriptor-only diagnostic projection. It never calls bindWorkload or grants acceptance.
const _bindUnavailable=Symbol('unavailable');
function _bindRecord(value){return value!==null&&typeof value==='object'&&!_bindTypes.isProxy(value)&&!Array.isArray(value);}
function _bindData(value,key){
 if(value===null||typeof value!=='object'||_bindTypes.isProxy(value))return _bindUnavailable;
 const descriptor=Object.getOwnPropertyDescriptor(value,key);
 return descriptor&&Object.hasOwn(descriptor,'value')?descriptor.value:_bindUnavailable;
}
function _bindStatus(value,prefix){
 if(value===_bindUnavailable)return prefix+'UNAVAILABLE';
 const states=['in_progress','queued','waiting','requested','pending','completed'];
 return typeof value==='string'&&value.length<=32&&states.includes(value)?prefix+value.toUpperCase():prefix+'OTHER';
}
function _bindJobSnapshot(jobs,expected){
 if(!_bindRecord(jobs)||!_bindRecord(expected))return{status:'J_BAD_DATA',job:null};
 const cell=_bindData(expected,'cell');if(typeof cell!=='string'||!/^linux-(22|24)-(16|18)$/.test(cell))return{status:'J_BAD_EXPECTED',job:null};
 const list=_bindData(jobs,'jobs'),count=_bindData(jobs,'total_count');
 if(list===null||typeof list!=='object'||_bindTypes.isProxy(list)||!Array.isArray(list))return{status:'J_BAD_DATA',job:null};
 const length=_bindData(list,'length');if(!Number.isSafeInteger(length)||length<0||length>100||count!==length)return{status:'J_BAD_DATA',job:null};
 const label='Root transferred unit roles '+cell;let found=null,matches=0;
 for(let index=0;index<length;index++){
  const item=_bindData(list,String(index));if(!_bindRecord(item))return{status:'J_BAD_DATA',job:null};
  const name=_bindData(item,'name');if(typeof name!=='string'||name.length>512)return{status:'J_BAD_DATA',job:null};
  if(name===label||name.endsWith(' / '+label)){found=item;matches++;}
 }
 if(matches===0)return{status:'J_MISSING',job:null};if(matches!==1)return{status:'J_AMBIGUOUS',job:null};return{status:_bindStatus(_bindData(found,'status'),'J_'),job:found};
}
function _bindRefShape(expected){
 if(!_bindRecord(expected))return'REF_UNAVAILABLE';
 const event=_bindData(expected,'event'),ref=_bindData(expected,'ref');
 if(typeof event!=='string'||typeof ref!=='string'||ref.length>512)return'REF_UNAVAILABLE';
 if(event==='pull_request'){
  const number=_bindData(expected,'prNumber');if(typeof number!=='string'||!/^[1-9][0-9]{0,19}$/.test(number))return'REF_UNAVAILABLE';
  return ref==='refs/pull/'+number+'/merge'?'REF_PR_MERGE_SHAPE':'REF_PR_OTHER';
 }
 if(event!=='push'&&event!=='workflow_dispatch')return'REF_EVENT';
 if(ref.length>256||!/^[A-Za-z0-9._/-]+$/.test(ref)||ref.includes('..'))return'REF_INVALID';
 if(ref.startsWith('refs/heads/')&&ref.length>11)return'REF_HEADS_SHAPE';
 if(ref.startsWith('refs/tags/')&&ref.length>10)return'REF_TAGS_SHAPE';return'REF_INVALID';
}
function _bindFieldMatch(record,key,expected,kind){
 const value=_bindRecord(record)?_bindData(record,key):_bindUnavailable;if(value===_bindUnavailable)return'MISSING';
 if(typeof expected!=='string'||(kind==='attempt'?!/^[1-9][0-9]{0,19}$/.test(expected):!/^[a-f0-9]{40}$/.test(expected)))return'UNAVAILABLE';
 if(kind==='attempt')return Number.isSafeInteger(value)&&value>0?(String(value)===expected?'MATCH':'MISMATCH'):'INVALID';
 return typeof value==='string'&&/^[a-f0-9]{40}$/.test(value)?(value===expected?'MATCH':'MISMATCH'):'INVALID';
}
function _bindWorkflowFlag(run,expected){
 const list=_bindRecord(run)?_bindData(run,'referenced_workflows'):_bindUnavailable;
 if(list===_bindUnavailable)return'MISSING';if(list===null||typeof list!=='object'||_bindTypes.isProxy(list)||!Array.isArray(list))return'INVALID';
 const source=_bindRecord(expected)?_bindData(expected,'runnerSource'):_bindUnavailable;if(typeof source!=='string'||!/^[a-f0-9]{40}$/.test(source))return'UNAVAILABLE';
 const length=_bindData(list,'length');if(!Number.isSafeInteger(length)||length<0||length>32)return'INVALID';if(length===0)return'MISSING';let matches=0;
 for(let index=0;index<length;index++){
  const row=_bindData(list,String(index));if(!_bindRecord(row))return'INVALID';const path=_bindData(row,'path'),sha=_bindData(row,'sha');
  if(path===_bindUnavailable||sha===_bindUnavailable)return'MISSING';if(typeof path!=='string'||path.length>512||typeof sha!=='string'||!/^[a-f0-9]{40}$/.test(sha))return'INVALID';
  if(path==='YehorBabenko88/unified-system/.github/workflows/ci-evidence-role-matrix.yml@'+source&&sha===source)matches++;
 }return matches===1?'MATCH':'MISMATCH';
}
function _bindCheckShape(job){
 const value=_bindRecord(job)?_bindData(job,'check_run_url'):_bindUnavailable;if(value===_bindUnavailable)return'MISSING';
 const prefix='https://api.github.com/repos/YehorBabenko88/math/check-runs/';return typeof value==='string'&&value.length<=256&&value.startsWith(prefix)&&/^[1-9][0-9]{0,19}$/.test(value.slice(prefix.length))?'SHAPE':'INVALID';
}
export function workloadBindingDiagnostic(run,jobs,expected){
 try{
  const selected=_bindJobSnapshot(jobs,expected),attempt=_bindRecord(expected)?_bindData(expected,'attempt'):_bindUnavailable,head=_bindRecord(expected)?_bindData(expected,'workloadHead'):_bindUnavailable,runHead=_bindRecord(run)?_bindData(run,'head_sha'):_bindUnavailable;
  return _bindStatus(_bindRecord(run)?_bindData(run,'status'):_bindUnavailable,'R_')+'__'+selected.status+'__'+_bindRefShape(expected)+'__RA_'+_bindFieldMatch(run,'run_attempt',attempt,'attempt')+'__JA_'+_bindFieldMatch(selected.job,'run_attempt',attempt,'attempt')+'__RH_'+_bindFieldMatch(run,'head_sha',head,'head')+'__JH_'+_bindFieldMatch(selected.job,'head_sha',runHead,'head')+'__WF_'+_bindWorkflowFlag(run,expected)+'__CHECK_'+_bindCheckShape(selected.job);
 }catch{return'R_UNAVAILABLE__J_UNAVAILABLE__REF_UNAVAILABLE__RA_UNAVAILABLE__JA_UNAVAILABLE__RH_UNAVAILABLE__JH_UNAVAILABLE__WF_UNAVAILABLE__CHECK_INVALID';}
}
