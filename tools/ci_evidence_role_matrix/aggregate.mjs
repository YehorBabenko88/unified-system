import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {bindWorkload,validateReceipt} from './contract.mjs';
const plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
const workflowSha256=createHash('sha256').update(readFileSync(new URL('../../.github/workflows/ci-evidence-role-matrix.yml',import.meta.url))).digest('hex');
const cells=Object.freeze(['linux-22-16','linux-22-18','linux-24-16','linux-24-18']);
const MAX_PACKET=2097152,MAX_RECEIPT=65536;
const need=x=>{if(!x)throw Error('ROOT_ROLE_EVIDENCE_REFUSED');};
const record=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype;
const id=x=>Number.isSafeInteger(x)&&x>0;
function closed(x,keys){need(record(x));const own=Object.keys(x);need(own.length===keys.length&&keys.every(k=>Object.hasOwn(x,k)));}
function parse(raw,downloadPlan){
 need(typeof raw==='string'&&raw.length>0&&raw.length<=MAX_PACKET&&Buffer.byteLength(raw,'utf8')<=MAX_PACKET);const packet=JSON.parse(raw);need(JSON.stringify(packet)===raw);
 closed(packet,downloadPlan?['schema','expected','run','jobs','pr','artifacts']:['schema','expected','run','jobs','pr','artifacts','receipts']);
 need(packet.schema===(downloadPlan?'unified.ci-evidence-role-download-plan.v1':'unified.ci-evidence-role-aggregate-input.v1'));return packet;
}
function metadata(packet){
 const {expected,run,jobs,pr,artifacts}=packet;closed(expected,['event','ref','runnerSource','runId','attempt','prNumber','workloadHead']);
 for(const key of ['event','ref','runnerSource','runId','attempt','workloadHead'])need(typeof expected[key]==='string'&&expected[key].length<=512);need(expected.prNumber===null||typeof expected.prNumber==='string'&&expected.prNumber.length<=20);
 need(record(run)&&typeof run.head_branch==='string'&&run.head_branch.length>0&&run.head_branch.length<=256&&record(run.repository)&&id(run.repository.id)&&record(jobs)&&Number.isSafeInteger(jobs.total_count)&&jobs.total_count>0&&jobs.total_count<=100&&Array.isArray(jobs.jobs)&&jobs.jobs.length===jobs.total_count);
 need(jobs.jobs.every(j=>record(j)&&id(j.id))&&new Set(jobs.jobs.map(j=>j.id)).size===jobs.jobs.length);
 need(record(artifacts)&&Number.isSafeInteger(artifacts.total_count)&&artifacts.total_count>=4&&artifacts.total_count<=100&&Array.isArray(artifacts.artifacts)&&artifacts.artifacts.length===artifacts.total_count);
 need(artifacts.artifacts.every(a=>record(a)&&id(a.id)&&typeof a.name==='string'&&a.name.length<=256)&&new Set(artifacts.artifacts.map(a=>a.id)).size===artifacts.artifacts.length);
 const selected=new Map(),usedJobs=new Set(),usedChecks=new Set();
 for(const cell of cells){
  const name='root-ci-evidence-unit-'+cell+'-'+expected.runId+'-'+expected.attempt,matches=artifacts.artifacts.filter(a=>a.name===name);need(matches.length===1);const artifact=matches[0];
  need(artifact.expired===false&&Number.isSafeInteger(artifact.size_in_bytes)&&artifact.size_in_bytes>0&&artifact.size_in_bytes<=1048576&&record(artifact.workflow_run)&&id(artifact.workflow_run.id)&&String(artifact.workflow_run.id)===expected.runId&&artifact.workflow_run.repository_id===run.repository.id&&artifact.workflow_run.head_sha===run.head_sha&&artifact.workflow_run.head_branch===run.head_branch);
  const bound=bindWorkload(run,jobs,pr,{...expected,cell},'completed');need(!usedJobs.has(bound.job_id)&&!usedChecks.has(bound.check_run_id));usedJobs.add(bound.job_id);usedChecks.add(bound.check_run_id);selected.set(cell,{artifact,bound});
 }return selected;
}
function held(){return Object.freeze({status:'HELD',coverage:'HELD',code:'E_ROOT_ROLE_EVIDENCE',scope:'FOUR_ROOT_UNIT_RECEIPT_CONSISTENCY_ONLY',download_custody:'NOT_EVALUATED',authority:'NONE',source_authentication:'NOT_EVALUATED',native_acceptance:'NOT_QUALIFIED',production:'NO_GO'});}
/** Bind current-run metadata before any archive download; never a coverage PASS. */
export function planRootRoleDownloads(raw){try{const packet=parse(raw,true),selected=metadata(packet);const downloads=[];for(const[cell,{artifact:a,bound:b}]of selected){need(typeof a.digest==='string'&&/^sha256:[a-f0-9]{64}$/.test(a.digest));downloads.push(Object.freeze({cell,artifact_id:String(a.id),size_in_bytes:a.size_in_bytes,digest:a.digest,job_id:b.job_id,check_run_id:b.check_run_id}));}return Object.freeze({status:'CONSISTENT_METADATA_ONLY',coverage:'HELD',downloads:Object.freeze(downloads),download_custody:'NOT_EVALUATED',authority:'NONE',source_authentication:'NOT_EVALUATED',native_acceptance:'NOT_QUALIFIED',production:'NO_GO'});}catch{return held();}}
/** Bounded caller-evidence consistency only. Real hosted download custody is mandatory. */
export function validateRootRoleCoverage(raw){try{
 const packet=parse(raw,false),selected=metadata(packet),{expected,receipts}=packet;need(Array.isArray(receipts)&&receipts.length===4);const usedIds=new Set(),seenCells=new Set(),bindings=[];
 for(const entry of receipts){
  closed(entry,['artifact_id','content']);need(typeof entry.artifact_id==='string'&&/^[1-9][0-9]{0,19}$/.test(entry.artifact_id)&&!usedIds.has(entry.artifact_id));usedIds.add(entry.artifact_id);
  need(typeof entry.content==='string'&&entry.content.length>0&&entry.content.length<=MAX_RECEIPT&&Buffer.byteLength(entry.content,'utf8')<=MAX_RECEIPT);const receipt=JSON.parse(entry.content);need(record(receipt)&&JSON.stringify(receipt)+'\n'===entry.content&&cells.includes(receipt.cell)&&!seenCells.has(receipt.cell));seenCells.add(receipt.cell);
  const {artifact,bound}=selected.get(receipt.cell);need(String(artifact.id)===entry.artifact_id);const context={...bound,runner_workflow_source:expected.runnerSource,runner_workflow_sha256:workflowSha256};validateReceipt(receipt,plan,context);
  bindings.push(Object.freeze({cell:receipt.cell,artifact_id:entry.artifact_id,job_id:bound.job_id,check_run_id:bound.check_run_id,receipt_sha256:createHash('sha256').update(entry.content).digest('hex')}));
 }need(seenCells.size===4);return Object.freeze({status:'CONSISTENT_SOURCE_ONLY',coverage:'HELD',scope:'FOUR_ROOT_UNIT_RECEIPT_CONSISTENCY_ONLY',cells:4,roles_per_cell:34,role_source:plan.role_source,runner_workflow_source:expected.runnerSource,workload_head:expected.workloadHead,run_id:expected.runId,attempt:expected.attempt,bindings:Object.freeze(bindings.sort((a,b)=>a.cell.localeCompare(b.cell))),download_custody:'NOT_EVALUATED',authority:'NONE',source_authentication:'NOT_EVALUATED',native_acceptance:'NOT_QUALIFIED',production:'NO_GO'});
 }catch{return held();}}
