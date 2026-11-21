import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateCell,projectTerminal,requireTerminals,makeReceipt,validateReceipt,bindWorkload,workloadBindingDiagnostic} from './contract.mjs';
const plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
let checks=0;assert(Object.hasOwn(plan.files,'tools/ci_evidence/http_body.mjs'),'PUBLISHED_RBRAVO_HELPER_SOURCE_REQUIRED');checks++;assert.equal(plan.role_source,'4ba390b8e12070499d54b12e5609c683c00607ee');checks++;
for(const cell of plan.cells){assert.equal(validateCell(cell).cell,cell);checks++;}
for(const bad of ['linux-20-16','windows-22-16','linux-22-17','linux-22-16/secret',null]){assert.throws(()=>validateCell(bad));checks++;}
const role=plan.roles.find(x=>x.kind==='HOSTED'),root='/private/role-source';
const event={type:'test:pass',data:{name:role.original.name,file:root+'/'+role.target,nesting:0,details:{}}};
assert.equal(projectTerminal(event,plan,root).id,role.id);checks++;
for(const changed of [{type:'test:fail'}, {data:{...event.data,skip:true}},{data:{...event.data,todo:true}},{data:{...event.data,nesting:1}},{data:{...event.data,name:'SECRET_SENTINEL'}},{data:{...event.data,file:'/unowned/secret'}}]){assert.throws(()=>projectTerminal({...event,...changed},plan,root));checks++;}
const terminals=plan.roles.filter(x=>x.kind==='HOSTED').map(x=>({id:x.id,status:'PASS'}));assert.equal(requireTerminals(terminals,plan).length,31);checks++;
for(const wrong of [terminals.slice(1),[...terminals,terminals[0]],[...terminals.slice(1),{id:'f'.repeat(64),status:'PASS'}],terminals.map((x,i)=>i?x:{...x,status:'SKIP'})]){assert.throws(()=>requireTerminals(wrong,plan));checks++;}
const context={workload_event:'pull_request',cell:'linux-22-16',workload_head:'a'.repeat(40),run_head:'a'.repeat(40),run_id:'10',attempt:'2',job_id:'20',check_run_id:'30',runner_workflow_source:'c'.repeat(40),runner_workflow_sha256:'d'.repeat(64)};
const receipt=makeReceipt(plan,context,{cell:'linux-22-16',actualNode:'22',pgVersion:'160009',terminals,staticPassed:true});assert.equal(validateReceipt(receipt,plan,context),true);checks++;
for(const changed of [{token:'SECRET_SENTINEL'},{authority:'GRANTED'},{roles:receipt.roles.slice(1)},{postgres_version_num:'180001'},{cell:'linux-22-18',postgres_major:'18',postgres_version_num:'180001'},{file_hashes:[]},{runner_workflow_source:'e'.repeat(40)}]){assert.throws(()=>validateReceipt({...receipt,...changed},plan,context));checks++;}
assert.throws(()=>makeReceipt(plan,{...context,run_head:'b'.repeat(40)},{cell:'linux-22-16',actualNode:'22',pgVersion:'160009',terminals,staticPassed:true}));checks++;
assert.throws(()=>validateReceipt({...receipt,run_head:'b'.repeat(40)},plan,{...context,run_head:'b'.repeat(40)}));checks++;
const run={referenced_workflows:[{path:'YehorBabenko88/unified-system/.github/workflows/ci-evidence-role-matrix.yml@'+'c'.repeat(40),sha:'c'.repeat(40)}],id:10,run_attempt:2,repository:{full_name:'YehorBabenko88/math'},event:'pull_request',status:'in_progress',head_sha:'a'.repeat(40),pull_requests:[{number:1,head:{sha:'a'.repeat(40)}}]};
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
assert.throws(()=>bindWorkload({...run,head_sha:'b'.repeat(40)},{total_count:1,jobs:[{...job,head_sha:'b'.repeat(40)}]},pr,expected));checks++;
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
 p=>{p.run.head_sha='b'.repeat(40);for(const j of p.jobs.jobs)j.head_sha=p.run.head_sha;for(const a of p.artifacts.artifacts)a.workflow_run.head_sha=p.run.head_sha;for(let i=0;i<4;i++)alter(p,i,r=>r.run_head=p.run.head_sha);},p=>p.expected.runId='11',p=>p.expected.attempt='3',p=>p.expected.workloadHead='f'.repeat(40),p=>p.run.referenced_workflows=[],p=>delete p.run.head_branch,p=>delete p.artifacts.artifacts[0].workflow_run.head_branch,p=>p.jobs.jobs[1].check_run_url=p.jobs.jobs[0].check_run_url,
 p=>p.jobs.jobs[0].status='in_progress',p=>p.jobs.jobs[0].conclusion='cancelled',p=>p.jobs.jobs[0].conclusion='skipped',p=>p.jobs.jobs[0].head_sha='f'.repeat(40),p=>p.jobs.jobs[0].run_attempt=3,p=>p.jobs.jobs.push(p.jobs.jobs[0]),p=>{p.jobs.jobs.push(p.jobs.jobs[0]);p.jobs.total_count++;},
 p=>p.artifacts.artifacts[0].expired=true,p=>p.artifacts.artifacts[0].size_in_bytes=1048577,p=>p.artifacts.artifacts[0].name+='-stale',p=>p.artifacts.artifacts[0].workflow_run.id=11,p=>p.artifacts.artifacts[0].workflow_run.repository_id=2,p=>p.artifacts.artifacts[0].workflow_run.head_sha='f'.repeat(40),p=>p.artifacts.artifacts[0].workflow_run.head_branch='other',p=>{p.artifacts.artifacts.push({...p.artifacts.artifacts[0],id:99});p.artifacts.total_count++;},
 p=>p.extra='SECRET_SENTINEL'
];
for(const change of changes){const p=structuredClone(packet);change(p);const result=qualify(p);assert.equal(result.status,'HELD');assert.equal(result.code,'E_ROOT_ROLE_EVIDENCE');assert(!JSON.stringify(result).includes('SECRET_SENTINEL'));checks++;}
for(const raw of [undefined,null,true,'','{',' '.repeat(2097153),JSON.stringify(packet).replace('{','{\"schema\":\"duplicate\",')]){assert.equal(validateRootRoleCoverage(raw).status,'HELD');checks++;}
let parsedHuge=false;const realParse=JSON.parse;try{JSON.parse=()=>{parsedHuge=true;throw Error('UNEXPECTED_PARSE');};assert.equal(validateRootRoleCoverage('x'.repeat(2097153)).status,'HELD');assert.equal(parsedHuge,false);checks++;}finally{JSON.parse=realParse;}
let coercions=0;const hostile={toString(){coercions++;throw Error('SECRET_SENTINEL');}};assert.equal(validateRootRoleCoverage(hostile).status,'HELD');assert.equal(coercions,0);checks++;
const mixed=structuredClone(packet);mixed.jobs.jobs.push({...job,id:100,name:'Math platform linux-22-16'});mixed.jobs.total_count++;mixed.artifacts.artifacts.push({id:100,name:'platform-linux-22-16'});mixed.artifacts.total_count++;assert.equal(qualify(mixed).status,'CONSISTENT_SOURCE_ONLY');checks++;


let zipApi;try{zipApi=await import('./artifact_zip.mjs');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}assert.equal(typeof zipApi?.readArtifactMember,'function','bounded official deflate ZIP reader required');
const {readArtifactMember,readCellArtifact}=zipApi;
const zipHash=b=>createHash('sha256').update(b).digest('hex');
const officialZip=Buffer.from('UEsDBBQACAAIAEC1dF0AAAAAAAAAAAAAAAASAAAAcXVhbGlmaWNhdGlvbi5qc29ufY5NT4QwFEX3/ArCWqOzm8wOmMoQmXaUksiKvCk1NHw8bIuGGP+7gToxZhKX7917bs6n5/uBEY3sIdj5mxt34iiDnR/kJeUHwtO4OrCck33FaFYGa0dg10lhUT/LEY2yqOeFKGWDOoKzHFrcbu+mQb0qWd+a2VjZO/IDddsh1P+CPdjG1Y0FO5mlEmUsfiR79x4bMKtjzCgnL7wKT2kVs+Mx5RfBes3JmkSsoD/kAFa9y1AIOVoYhLyaxlFqsAoH6P62CvpUhFn6kP5KzEYJ6JLNtZ/GehLLyhJRViXMBWfENgHr3DOWX4C3+3WEnQgNvC/vG1BLBwjQySV29AAAAJgBAABQSwECLQMUAAgACABAtXRd0MkldvQAAACYAQAAEgAAAAAAAAAAACAAgIEAAAAAcXVhbGlmaWNhdGlvbi5qc29uUEsFBgAAAAABAAEAQAAAADQBAAAAAA==','base64');
assert.equal(zipHash(officialZip),'3814d4007742b6ce99d291886cb5360697b8bcab3cc4f498ab1e7a9db8b46610');
const officialMember=readArtifactMember(officialZip,'qualification.json',zipHash(officialZip));assert.equal(officialMember.length,408);assert.equal(JSON.parse(officialMember.toString('utf8')).status,'BLOCKED');checks++;
assert.throws(()=>readCellArtifact(officialZip,'linux-22-16',officialZip.length,'sha256:'+zipHash(officialZip)));checks++;
const {deflateRawSync}=await import('node:zlib');
function crcFixture(bytes){let x=0xffffffff;for(const b of bytes){x^=b;for(let k=0;k<8;k++)x=(x>>>1)^((x&1)?0xedb88320:0);}return (x^0xffffffff)>>>0;}
function zipFixture(name,data,method=8,descriptor=true){const n=Buffer.from(name),packed=method===8?deflateRawSync(data):Buffer.from(data),crc=crcFixture(data);const local=Buffer.alloc(30),central=Buffer.alloc(46),end=Buffer.alloc(22),dd=descriptor?Buffer.alloc(16):Buffer.alloc(0);local.writeUInt32LE(0x04034b50);local.writeUInt16LE(20,4);local.writeUInt16LE(descriptor?8:0,6);local.writeUInt16LE(method,8);local.writeUInt16LE(n.length,26);if(!descriptor){local.writeUInt32LE(crc,14);local.writeUInt32LE(packed.length,18);local.writeUInt32LE(data.length,22);}if(descriptor){dd.writeUInt32LE(0x08074b50);dd.writeUInt32LE(crc,4);dd.writeUInt32LE(packed.length,8);dd.writeUInt32LE(data.length,12);}central.writeUInt32LE(0x02014b50);central.writeUInt16LE(813,4);central.writeUInt16LE(20,6);central.writeUInt16LE(descriptor?8:0,8);central.writeUInt16LE(method,10);central.writeUInt32LE(crc,16);central.writeUInt32LE(packed.length,20);central.writeUInt32LE(data.length,24);central.writeUInt16LE(n.length,28);central.writeUInt32LE(0x81a40020,38);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(1,8);end.writeUInt16LE(1,10);end.writeUInt32LE(46+n.length,12);end.writeUInt32LE(30+n.length+packed.length+dd.length,16);return Buffer.concat([local,n,packed,dd,central,n,end]);}
const cellName='roles-linux-22-16.json',cellBytes=Buffer.from('CELL_INERT_DATA\n'),cellZip=zipFixture(cellName,cellBytes);assert.deepEqual(readCellArtifact(cellZip,'linux-22-16',cellZip.length,'sha256:'+zipHash(cellZip)),cellBytes);checks++;
for(const method of [0,8])for(const descriptor of [false,true]){const b=zipFixture(cellName,cellBytes,method,descriptor);assert.deepEqual(readArtifactMember(b,cellName,zipHash(b)),cellBytes);checks++;}
const centralOffset=b=>b.readUInt32LE(b.length-6);
const malformed=[b=>b.writeUInt16LE(1,6),b=>b.writeUInt16LE(1,centralOffset(b)+8),b=>b.writeUInt16LE(99,centralOffset(b)+10),b=>b.writeUInt16LE(45,centralOffset(b)+6),b=>b.writeUInt16LE(1,b.length-18),b=>b.writeUInt16LE(2,b.length-12),b=>b.writeUInt32LE(0xffffffff,b.length-6),b=>b.writeUInt16LE(1,centralOffset(b)+30),b=>b.writeUInt16LE(1,28),b=>b.writeUInt32LE(1,centralOffset(b)+42),b=>b.writeUInt32LE(0xa1ff0000,centralOffset(b)+38),b=>b.writeUInt32LE(0,centralOffset(b)+16),b=>b.writeUInt32LE(65537,centralOffset(b)+24),b=>b.writeUInt32LE(0,centralOffset(b)-16),b=>b.writeUInt32LE(1,centralOffset(b)-8),b=>b[30]^=1,b=>b[centralOffset(b)+46]^=1];
for(const change of malformed){const b=Buffer.from(cellZip);change(b);assert.throws(()=>readArtifactMember(b,cellName,zipHash(b)));checks++;}
for(const name of ['../roles-linux-22-16.json','.hidden','dir/'+cellName,cellName+'/x']){const b=zipFixture(name,cellBytes);assert.throws(()=>readArtifactMember(b,name,zipHash(b)));checks++;}
assert.throws(()=>readArtifactMember(Buffer.concat([cellZip,Buffer.from('TRAIL')]),cellName,zipHash(Buffer.concat([cellZip,Buffer.from('TRAIL')]))));checks++;
assert.throws(()=>readArtifactMember(cellZip,cellName,'0'.repeat(64)));checks++;
assert.throws(()=>readCellArtifact(cellZip,'linux-22-16',cellZip.length+1,'sha256:'+zipHash(cellZip)));checks++;
assert.throws(()=>readArtifactMember(Buffer.alloc(1048577),cellName,'0'.repeat(64)));checks++;
const bomb=zipFixture(cellName,Buffer.alloc(65537,32));bomb.writeUInt32LE(1,centralOffset(bomb)+24);bomb.writeUInt32LE(1,centralOffset(bomb)-4);assert.throws(()=>readArtifactMember(bomb,cellName,zipHash(bomb)));checks++;


assert.equal(typeof aggregate.planRootRoleDownloads,'function','metadata must validate before any archive download');
const {planRootRoleDownloads}=aggregate;
const downloadsPacket=structuredClone(packet),archiveBytes=new Map();
for(const entry of downloadsPacket.receipts){const receipt=JSON.parse(entry.content),zip=zipFixture('roles-'+receipt.cell+'.json',Buffer.from(entry.content));archiveBytes.set(entry.artifact_id,zip);const a=downloadsPacket.artifacts.artifacts.find(x=>String(x.id)===entry.artifact_id);a.size_in_bytes=zip.length;a.digest='sha256:'+zipHash(zip);}
const metadataPacket=p=>{const {receipts,...rest}=p;return {...rest,schema:'unified.ci-evidence-role-download-plan.v1'};};
const plannedDownloads=planRootRoleDownloads(JSON.stringify(metadataPacket(downloadsPacket)));assert.equal(plannedDownloads.status,'CONSISTENT_METADATA_ONLY');assert.equal(plannedDownloads.downloads.length,4);assert.equal(plannedDownloads.coverage,'HELD');checks++;
const badMeta=structuredClone(downloadsPacket);badMeta.artifacts.artifacts[0].workflow_run.id=11;assert.equal(planRootRoleDownloads(JSON.stringify(metadataPacket(badMeta))).status,'HELD');checks++;
let custody;try{custody=await import('./artifact_custody.mjs');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}assert.equal(typeof custody?.collectRootRoleCoverage,'function','fixed API archive custody collector required');


globalThis.fetch=()=>{throw Error('REAL_NETWORK_FORBIDDEN');};
function fakeDownloads(change={}){const p=structuredClone(downloadsPacket),state={calls:[],apiZip:0,blob:0,runReads:0,continued:false};if(change.packet)change.packet(p);const fetcher=async(url,init)=>{const u=new URL(url);state.calls.push({host:u.hostname,path:u.pathname});const headers=new Headers(init.headers);if(u.hostname==='api.github.com'){assert.equal(headers.get('authorization'),'Bearer INERT_PRIVATE_TOKEN');if(change.throwApi)throw Error('INERT_PRIVATE_TOKEN');if(u.pathname.includes('/actions/artifacts/')){state.apiZip++;assert.equal(init.redirect,'manual');const aid=u.pathname.split('/').at(-2);return new Response(null,{status:change.redirectStatus??302,headers:{location:change.location??('https://productionresultssa4.blob.core.windows.net/inert/artifact'+aid+'?sig=INERT_PRIVATE_SIGNED_QUERY')}});}let value;if(u.pathname.endsWith('/actions/runs/10')){state.runReads++;value=change.post&&state.runReads>1?{...p.run,run_attempt:3}:p.run;}else if(u.pathname.includes('/attempts/'))value=p.jobs;else if(u.pathname.endsWith('/artifacts')){value=structuredClone(p.artifacts);if(change.postDigest&&state.runReads>1)value.artifacts[0].digest='sha256:'+'f'.repeat(64);}else if(u.pathname.endsWith('/pulls/1'))value=p.pr;else throw Error('UNEXPECTED_API_PATH');return new Response(JSON.stringify(value));}
 assert.equal(u.hostname,'productionresultssa4.blob.core.windows.net');assert.equal(headers.has('authorization'),false);assert.equal(init.redirect,'error');state.blob++;const aid=u.pathname.replace('/inert/artifact','');const bytes=(change.archives??archiveBytes).get(aid);assert(bytes);if(change.oversize)return{status:200,ok:true,url,body:(async function*(){yield Buffer.alloc(1048577);state.continued=true;yield Buffer.from('INERT_PRIVATE_TOKEN');})()};if(change.origin)return{status:200,ok:true,url:'https://unapproved.invalid/',body:[]};return new Response(change.body??bytes,{status:change.blobStatus??200});};return{fetcher,state};}
const invoke=async change=>{const f=fakeDownloads(change);const result=await custody.collectRootRoleCoverage(JSON.stringify(downloadsPacket.expected),{token:'INERT_PRIVATE_TOKEN',fetcher:f.fetcher});assert(!JSON.stringify(result).includes('INERT_PRIVATE'));return{result,state:f.state};};
const fetched=await invoke({});assert.equal(fetched.result.status,'VALIDATED_UNIT_ARTIFACT_CUSTODY');assert.equal(fetched.result.coverage,'ROOT_FOUR_UNIT_CELLS_ONLY');assert.equal(fetched.result.authority,'NONE');assert.equal(fetched.result.production,'NO_GO');assert.equal(fetched.state.apiZip,4);assert.equal(fetched.state.blob,4);assert.equal(fetched.state.runReads,2);checks++;
for(const change of [
 {location:'http://productionresultssa4.blob.core.windows.net/inert'},
 {location:'https://unapproved.invalid/inert'},
 {location:'https://productionresultssa4.blob.core.windows.net@unapproved.invalid/inert'},
 {location:'https://productionresultssa4.blob.core.windows.net:444/inert'},
 {location:'https://productionresultssa4.blob.core.windows.net/inert#secret'},
 {redirectStatus:307},{location:'/relative'},{location:'x'.repeat(32769)},{throwApi:true},{postDigest:true},{blobStatus:302},{origin:true},{oversize:true},{body:Buffer.from('DAMAGED_ARCHIVE')},{post:true},
 {packet:p=>p.artifacts.artifacts[0].expired=true},
 {packet:p=>p.artifacts.artifacts[0].workflow_run.id=11},
 {packet:p=>p.artifacts.artifacts[0].digest='sha256:'+'0'.repeat(64)},
 {packet:p=>p.artifacts.artifacts[0].digest=null}
]){const {result,state}=await invoke(change);assert.equal(result.status,'HELD');assert.equal(result.coverage,'HELD');assert.equal(state.continued,false);if(change.packet&&(change.packet.toString().includes('expired')||change.packet.toString().includes('workflow_run')||change.packet.toString().includes('digest=null')))assert.equal(state.apiZip,0);checks++;}
let touched=false;const noNetwork=()=>{touched=true;throw Error('INERT_PRIVATE_TOKEN');};for(const [raw,token]of [['{}','INERT_PRIVATE_TOKEN'],[JSON.stringify(downloadsPacket.expected),''],[JSON.stringify(downloadsPacket.expected),true]]){const result=await custody.collectRootRoleCoverage(raw,{token,fetcher:noNetwork});assert.equal(result.status,'HELD');assert.equal(touched,false);checks++;}


const badCrc=Buffer.from(cellZip),bc=centralOffset(badCrc);badCrc.writeUInt32LE(0,bc+16);badCrc.writeUInt32LE(0,bc-12);assert.throws(()=>readArtifactMember(badCrc,cellName,zipHash(badCrc)));checks++;
const extraPacked=Buffer.concat([cellZip.subarray(0,centralOffset(cellZip)-16),Buffer.from('TAIL'),cellZip.subarray(centralOffset(cellZip)-16)]);const ec=centralOffset(cellZip)+4;extraPacked.writeUInt32LE(ec,extraPacked.length-6);extraPacked.writeUInt32LE(extraPacked.readUInt32LE(ec+20)+4,ec+20);extraPacked.writeUInt32LE(extraPacked.readUInt32LE(ec-8)+4,ec-8);assert.throws(()=>readArtifactMember(extraPacked,cellName,zipHash(extraPacked)));checks++;
const utf=Buffer.from(cellZip);utf.writeUInt16LE(0x808,6);utf.writeUInt16LE(0x808,centralOffset(utf)+8);assert.deepEqual(readArtifactMember(utf,cellName,zipHash(utf)),cellBytes);checks++;
const wrongReceipt=JSON.parse(downloadsPacket.receipts[0].content);wrongReceipt.authority='GRANTED';const wrongZip=zipFixture(cellName,Buffer.from(JSON.stringify(wrongReceipt)+'\n'));const wrongArchives=new Map(archiveBytes);wrongArchives.set('40',wrongZip);const badCells=await invoke({archives:wrongArchives,packet:p=>{p.artifacts.artifacts[0].size_in_bytes=wrongZip.length;p.artifacts.artifacts[0].digest='sha256:'+zipHash(wrongZip);}});assert.equal(badCells.result.status,'HELD');assert.equal(badCells.result.code,'E_ROOT_ARTIFACT_CELLS');checks++;
const jsonNotZip=await invoke({packet:p=>p.artifacts.artifacts[0].digest='sha256:'+zipHash(Buffer.from(p.receipts[0].content))});assert.equal(jsonNotZip.result.status,'HELD');checks++;


let optionCallbacks=0;const accessor={fetcher:noNetwork};Object.defineProperty(accessor,'token',{enumerable:true,get(){optionCallbacks++;throw Error('INERT_PRIVATE_TOKEN');}});for(const options of [null,true,'token',[],accessor]){const r=await custody.collectRootRoleCoverage(JSON.stringify(downloadsPacket.expected),options);assert.equal(r.status,'HELD');checks++;}assert.equal(optionCallbacks,0);assert.equal(touched,false);


for(const field of ['length',Symbol.iterator]){let callbacks=0;const hostile=Buffer.from(cellZip);Object.defineProperty(hostile,field,{get(){callbacks++;throw Error('INERT_PRIVATE_TOKEN');}});assert.throws(()=>readArtifactMember(hostile,cellName,zipHash(cellZip)));assert.equal(callbacks,0);checks++;}


// Binding diagnostics are closed metadata observations, NEVER binding/coverage success.
const diagnosticExpected={...expected};const diagnosticJobs={total_count:1,jobs:[job]};
assert.equal(workloadBindingDiagnostic(run,diagnosticJobs,diagnosticExpected),'R_IN_PROGRESS__J_IN_PROGRESS__REF_PR_MERGE_SHAPE__RA_MATCH__JA_MATCH__RH_MATCH__JH_MATCH__WF_MATCH__CHECK_SHAPE');checks++;
for(const status of ['queued','waiting','requested','pending','completed','in_progress']){assert(workloadBindingDiagnostic({...run,status},diagnosticJobs,diagnosticExpected).startsWith('R_'+status.toUpperCase()+'__'));checks++;}
for(const status of ['queued','waiting','pending','completed','in_progress']){assert(workloadBindingDiagnostic(run,{total_count:1,jobs:[{...job,status}]},diagnosticExpected).includes('__J_'+status.toUpperCase()+'__'));checks++;}
assert(workloadBindingDiagnostic({...run,status:'SECRET_SENTINEL'},diagnosticJobs,diagnosticExpected).startsWith('R_OTHER__'));checks++;
for(const ref of ['refs/heads/main','refs/pull/2/merge','SECRET_SENTINEL']){const code=workloadBindingDiagnostic(run,diagnosticJobs,{...diagnosticExpected,ref});assert(!code.includes('SECRET'));assert(!code.includes('__REF_PR_MERGE_SHAPE__'));checks++;}
for(const [event,ref,suffix]of [['push','refs/heads/main','REF_HEADS_SHAPE'],['workflow_dispatch','refs/tags/v1','REF_TAGS_SHAPE'],['push','refs/heads/../bad','REF_INVALID']]){assert(workloadBindingDiagnostic(run,diagnosticJobs,{...diagnosticExpected,event,ref}).includes('__'+suffix+'__'));checks++;}
for(const value of [{total_count:0,jobs:[]},{total_count:2,jobs:[job,job]},{total_count:101,jobs:[job]}]){const code=workloadBindingDiagnostic(run,value,diagnosticExpected);assert(/__J_(MISSING|AMBIGUOUS|BAD_DATA)__/.test(code));checks++;}
for(const [target,key]of [['run','status'],['jobs','jobs'],['jobs','total_count'],['job','name'],['job','status'],['expected','event'],['expected','ref'],['expected','cell'],['expected','prNumber']]){let reads=0;let r={...run},j={total_count:1,jobs:[{...job}]},e={...diagnosticExpected};const object=target==='run'?r:target==='jobs'?j:target==='job'?j.jobs[0]:e;Object.defineProperty(object,key,{get(){reads++;throw Error('SECRET_SENTINEL');}});const code=workloadBindingDiagnostic(r,j,e);assert(!code.includes('SECRET'));assert.equal(reads,0);checks++;}
for(const target of ['run','jobs','list','job','expected']){let traps=0;const proxy=new Proxy({}, {get(){traps++;throw Error('SECRET_SENTINEL');},ownKeys(){traps++;throw Error('SECRET_SENTINEL');},getOwnPropertyDescriptor(){traps++;throw Error('SECRET_SENTINEL');},getPrototypeOf(){traps++;throw Error('SECRET_SENTINEL');}});let r=run,j=diagnosticJobs,e=diagnosticExpected;if(target==='run')r=proxy;else if(target==='jobs')j=proxy;else if(target==='list')j={total_count:1,jobs:proxy};else if(target==='job')j={total_count:1,jobs:[proxy]};else e=proxy;const code=workloadBindingDiagnostic(r,j,e);assert(!code.includes('SECRET'));assert.equal(traps,0);checks++;}
const revoked=Proxy.revocable({},{});revoked.revoke();assert(workloadBindingDiagnostic(revoked.proxy,diagnosticJobs,diagnosticExpected).startsWith('R_UNAVAILABLE__'));checks++;


for(const [target,key,changed,flag]of [['run','run_attempt',undefined,'RA_MISSING'],['run','run_attempt','2','RA_INVALID'],['run','run_attempt',3,'RA_MISMATCH'],['job','run_attempt',undefined,'JA_MISSING'],['job','run_attempt',3,'JA_MISMATCH'],['run','head_sha',undefined,'RH_MISSING'],['run','head_sha','f'.repeat(40),'RH_MISMATCH'],['job','head_sha',undefined,'JH_MISSING'],['job','head_sha','f'.repeat(40),'JH_MISMATCH'],['run','referenced_workflows',undefined,'WF_MISSING'],['run','referenced_workflows',[],'WF_MISSING'],['run','referenced_workflows',[{}],'WF_MISSING'],['job','check_run_url',undefined,'CHECK_MISSING'],['job','check_run_url','SECRET_SENTINEL','CHECK_INVALID']]){const r={...run},j={total_count:1,jobs:[{...job}]};const targetObject=target==='run'?r:j.jobs[0];if(changed===undefined)delete targetObject[key];else targetObject[key]=changed;const code=workloadBindingDiagnostic(r,j,diagnosticExpected);assert(code.includes('__'+flag));assert(!code.includes('SECRET'));checks++;}
for(const [target,key]of [['run','run_attempt'],['run','head_sha'],['run','referenced_workflows'],['job','run_attempt'],['job','head_sha'],['job','check_run_url'],['expected','attempt'],['expected','workloadHead'],['expected','runnerSource']]){let reads=0;const r={...run},j={total_count:1,jobs:[{...job}]},e={...diagnosticExpected};const value=target==='run'?r:target==='job'?j.jobs[0]:e;Object.defineProperty(value,key,{get(){reads++;throw Error('SECRET_SENTINEL');}});const code=workloadBindingDiagnostic(r,j,e);assert(!code.includes('SECRET'));assert.equal(reads,0);checks++;}
for(const nested of ['workflow-list','workflow-row']){let traps=0;const proxy=new Proxy([], {get(){traps++;throw Error('SECRET_SENTINEL');},getOwnPropertyDescriptor(){traps++;throw Error('SECRET_SENTINEL');},ownKeys(){traps++;throw Error('SECRET_SENTINEL');}});const code=workloadBindingDiagnostic({...run,referenced_workflows:nested==='workflow-list'?proxy:[proxy]},diagnosticJobs,diagnosticExpected);assert(code.includes('__WF_INVALID__'));assert.equal(traps,0);checks++;}

console.log(JSON.stringify({checks,status:'PASS_INERT_ONLY',authority:'NONE',production:'NO_GO'}));
