import {fetchGitHubJson} from '../ci_evidence/github_identity.mjs';
import {strictJson} from '../ci_evidence/strict.mjs';
import {planRootRoleDownloads,validateRootRoleCoverage} from './aggregate.mjs';
import {readCellArtifact} from './artifact_zip.mjs';
const need=x=>{if(!x)throw Error('ROOT_ARTIFACT_CUSTODY_REFUSED');};
const root='/repos/YehorBabenko88/math';
function expectedInput(raw){
 need(typeof raw==='string'&&raw.length<=4096);const e=strictJson(raw,4096),keys=['event','ref','runnerSource','runId','attempt','prNumber','workloadHead'];need(e&&typeof e==='object'&&!Array.isArray(e)&&Object.keys(e).length===keys.length&&keys.every(k=>Object.hasOwn(e,k)));
 need(['push','pull_request','workflow_dispatch'].includes(e.event)&&typeof e.ref==='string'&&e.ref.length>0&&e.ref.length<=512&&typeof e.runnerSource==='string'&&/^[a-f0-9]{40}$/.test(e.runnerSource)&&typeof e.workloadHead==='string'&&/^[a-f0-9]{40}$/.test(e.workloadHead));
 for(const k of ['runId','attempt'])need(typeof e[k]==='string'&&/^[1-9][0-9]{0,19}$/.test(e[k]));need(e.event==='pull_request'?typeof e.prNumber==='string'&&/^[1-9][0-9]{0,19}$/.test(e.prNumber):e.prNumber===null);return e;
}
async function body(response,limit){
 need(Number.isSafeInteger(limit)&&limit>0&&limit<=1048576&&response.body&&typeof response.body[Symbol.asyncIterator]==='function');
 const storage=Buffer.alloc(limit),deadline=performance.now()+10000;let size=0,count=0,finished=false,iterator,pendingReject=null,timedOut=false;
 const timer=setTimeout(()=>{timedOut=true;if(pendingReject)pendingReject(Error('ROOT_ARTIFACT_BODY_DEADLINE'));},10000);
 function next(){return new Promise((resolve,reject)=>{pendingReject=reject;try{Promise.resolve(iterator.next()).then(step=>{if(pendingReject===reject)pendingReject=null;resolve(step);},error=>{if(pendingReject===reject)pendingReject=null;reject(error);});}catch(error){pendingReject=null;reject(error);}});}
 try{
  iterator=response.body[Symbol.asyncIterator]();
  for(;;){
   need(!timedOut&&performance.now()<=deadline);const step=await next();need(!timedOut&&performance.now()<=deadline&&step!==null&&typeof step==='object'&&typeof step.done==='boolean');
   if(step.done){finished=true;need(size>0);return storage.subarray(0,size);}
   const chunk=step.value;need(++count<=4096&&(Buffer.isBuffer(chunk)||chunk instanceof Uint8Array)&&[Buffer.prototype,Uint8Array.prototype].includes(Object.getPrototypeOf(chunk))&&Object.getOwnPropertyDescriptor(chunk,'byteLength')===undefined&&Object.getOwnPropertyDescriptor(chunk,'length')===undefined);
   const bytes=chunk.byteLength;need(bytes>0&&size+bytes<=limit);storage.set(chunk,size);size+=bytes;
  }
 }finally{clearTimeout(timer);pendingReject=null;if(!finished&&iterator&&typeof iterator.return==='function'){try{Promise.resolve(iterator.return()).catch(()=>{});}catch{}}}
}
async function archive(download,token,fetcher){
 const apiUrl='https://api.github.com'+root+'/actions/artifacts/'+download.artifact_id+'/zip';
 const redirect=await fetcher(apiUrl,{headers:{Accept:'application/vnd.github+json',Authorization:'Bearer '+token},redirect:'manual',credentials:'omit',signal:AbortSignal.timeout(10000)});
 need(redirect.status===302&&new URL(redirect.url||apiUrl).href===apiUrl);const location=redirect.headers.get('location');need(typeof location==='string'&&location.length>0&&location.length<=32768);
 const target=new URL(location);need(target.protocol==='https:'&&/^productionresultssa[0-9]{1,3}\.blob\.core\.windows\.net$/.test(target.hostname)&&!target.username&&!target.password&&!target.port&&!target.hash);
 const response=await fetcher(target.href,{headers:{Accept:'application/zip'},redirect:'error',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(10000)});
 need(response.status===200&&response.ok&&new URL(response.url||target.href).href===target.href);return body(response,download.size_in_bytes);
}
/** Fixed current Math run read-only custody; never source authentication/admission. */
export async function collectRootRoleCoverage(expectedRaw,options={}){
 let phase='E_ROOT_ARTIFACT_INPUT';try{
  need(options!==null&&typeof options==='object'&&!Array.isArray(options)&&Object.getPrototypeOf(options)===Object.prototype);const descriptors=Object.getOwnPropertyDescriptors(options),keys=Object.keys(descriptors);need(keys.length>=1&&keys.length<=2&&keys.every(k=>k==='token'||k==='fetcher')&&Object.hasOwn(descriptors,'token')&&keys.every(k=>Object.hasOwn(descriptors[k],'value')));const token=descriptors.token.value,fetcher=Object.hasOwn(descriptors,'fetcher')?descriptors.fetcher.value:fetch;
  need(typeof token==='string'&&/^[A-Za-z0-9_.-]{1,4096}$/.test(token)&&typeof fetcher==='function');const expected=expectedInput(expectedRaw);
  const get=path=>fetchGitHubJson(root+path,{authorization:'Bearer '+token,fetcher:(url,init)=>fetcher(url,{...init,credentials:'omit'})});
  async function metadata(){const[run,jobs,pr,artifacts]=await Promise.all([get('/actions/runs/'+expected.runId),get('/actions/runs/'+expected.runId+'/attempts/'+expected.attempt+'/jobs?per_page=100'),expected.event==='pull_request'?get('/pulls/'+expected.prNumber):Promise.resolve(null),get('/actions/runs/'+expected.runId+'/artifacts?per_page=100')]);return{schema:'unified.ci-evidence-role-download-plan.v1',expected,run,jobs,pr,artifacts};}
  phase='E_ROOT_ARTIFACT_METADATA';const before=await metadata(),planned=planRootRoleDownloads(JSON.stringify(before));need(planned.status==='CONSISTENT_METADATA_ONLY');
  phase='E_ROOT_ARTIFACT_DOWNLOAD';const archives=await Promise.all(planned.downloads.map(async download=>({download,zip:await archive(download,token,fetcher)})));
  phase='E_ROOT_ARTIFACT_ZIP';const receipts=archives.map(({download,zip})=>{const bytes=readCellArtifact(zip,download.cell,download.size_in_bytes,download.digest);return{artifact_id:download.artifact_id,content:new TextDecoder('utf-8',{fatal:true}).decode(bytes)};});
  phase='E_ROOT_ARTIFACT_POST_METADATA';const after=await metadata(),post=planRootRoleDownloads(JSON.stringify(after));need(post.status==='CONSISTENT_METADATA_ONLY'&&JSON.stringify(post.downloads)===JSON.stringify(planned.downloads));
  phase='E_ROOT_ARTIFACT_CELLS';const result=validateRootRoleCoverage(JSON.stringify({...after,schema:'unified.ci-evidence-role-aggregate-input.v1',receipts}));need(result.status==='CONSISTENT_SOURCE_ONLY');
  return Object.freeze({...result,status:'VALIDATED_UNIT_ARTIFACT_CUSTODY',coverage:'ROOT_FOUR_UNIT_CELLS_ONLY',scope:'ROOT_FOUR_DOWNLOADED_UNIT_ARTIFACTS',download_custody:'CURRENT_RUN_ZIP_DIGEST_AND_METADATA_BOUND',archives:Object.freeze(planned.downloads.map(d=>Object.freeze({cell:d.cell,artifact_id:d.artifact_id,zip_sha256:d.digest.slice(7),zip_bytes:d.size_in_bytes})))});
 }catch{return Object.freeze({status:'HELD',coverage:'HELD',code:phase,scope:'ROOT_FOUR_DOWNLOADED_UNIT_ARTIFACTS',download_custody:'NOT_QUALIFIED',authority:'NONE',source_authentication:'NOT_EVALUATED',native_acceptance:'NOT_QUALIFIED',production:'NO_GO'});}
}
