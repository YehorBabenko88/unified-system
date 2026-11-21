import {readHttpBody} from '../ci_evidence/http_body.mjs';
import {readFileSync,writeFileSync,mkdirSync,lstatSync,realpathSync} from 'node:fs';
import {resolve,join,dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {validateCell,parseTerminals,bindWorkload,makeReceipt,validateReceipt} from './contract.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const need=value=>{if(!value)throw Error('ROLE_MATRIX_REFUSED');};
let phase='E_PROFILE';
try{
 need(process.platform==='linux'&&process.env.GITHUB_ACTIONS==='true'&&process.env.RUNNER_ENVIRONMENT==='github-hosted'&&process.env.GITHUB_REPOSITORY==='YehorBabenko88/math'&&['push','pull_request','workflow_dispatch'].includes(process.env.GITHUB_EVENT_NAME));
 need(!process.env.NODE_OPTIONS&&!process.env.NODE_PATH&&!process.env.NODE_DEBUG&&!process.env.NODE_DEBUG_NATIVE&&!process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN&&!process.env.ACTIONS_ID_TOKEN_REQUEST_URL);
 const cell=validateCell(process.env.ROLE_MATRIX_CELL);need(process.versions.node.split('.')[0]===cell.node&&process.argv.length===3);
 const root=realpathSync(process.argv[2]),temp=realpathSync(process.env.RUNNER_TEMP);need(root.startsWith(temp+'/'));
 for(let path=root;;path=dirname(path)){const st=lstatSync(path);need(st.isDirectory()&&!st.isSymbolicLink());if(dirname(path)===path)break;}
 need((lstatSync(root).mode&0o077)===0);
 const plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
 const proof=JSON.parse(readFileSync(join(root,'bootstrap-proof.json')));need(proof.runner_workflow_source===process.env.ROLE_MATRIX_SHA&&/^[a-f0-9]{40}$/.test(proof.runner_workflow_source)&&/^[a-f0-9]{64}$/.test(proof.runner_workflow_sha256));
 const kit=Object.entries(proof.kit_hashes);need(kit.length===9);
 function sourceBytes(){
  const all=[...Object.entries(plan.files),...kit];need(new Set(all.map(x=>x[0])).size===all.length);
  for(const [path,hash]of all){need(/^[A-Za-z0-9_./-]+$/.test(path)&&!path.includes('..')&&/^[a-f0-9]{64}$/.test(hash));const file=join(root,path),st=lstatSync(file);need(st.isFile()&&!st.isSymbolicLink()&&st.nlink===1&&st.size<=131072&&sha(readFileSync(file))===hash);}
 }
 phase='E_SOURCE';sourceBytes();
 const api=async path=>{const response=await fetch('https://api.github.com/repos/YehorBabenko88/math/'+path,{headers:{Authorization:'Bearer '+process.env.ROLE_MATRIX_API_TOKEN,Accept:'application/vnd.github+json'},redirect:'error',signal:AbortSignal.timeout(5000)});need(response.ok);return JSON.parse((await readHttpBody(response,{maxBytes:1048576,timeoutMs:5000})).toString('utf8'));};
 phase='E_WORKLOAD';const runId=process.env.GITHUB_RUN_ID,attempt=process.env.GITHUB_RUN_ATTEMPT,prNumber=process.env.ROLE_MATRIX_PR_NUMBER;need(/^[1-9][0-9]{0,19}$/.test(runId)&&/^[1-9][0-9]{0,19}$/.test(attempt)&&(process.env.GITHUB_EVENT_NAME!=='pull_request'||/^[1-9][0-9]{0,19}$/.test(prNumber)));
 const [run,jobs,pr]=await Promise.all([api('actions/runs/'+runId),api('actions/runs/'+runId+'/attempts/'+attempt+'/jobs?per_page=100'),process.env.GITHUB_EVENT_NAME==='pull_request'?api('pulls/'+prNumber):Promise.resolve(null)]);
 const bound=bindWorkload(run,jobs,pr,{event:process.env.GITHUB_EVENT_NAME,ref:process.env.GITHUB_REF,runnerSource:proof.runner_workflow_source,runId,attempt,prNumber,workloadHead:process.env.ROLE_MATRIX_WORKLOAD_HEAD,cell:cell.cell});
 const context={...bound,runner_workflow_source:proof.runner_workflow_source,runner_workflow_sha256:proof.runner_workflow_sha256};
 phase='E_PG_PROFILE';need(process.env.PGHOST==='127.0.0.1'&&process.env.PGPORT==='5432'&&process.env.PGDATABASE==='math_universe_test'&&process.env.PGUSER==='math_test'&&process.env.PGPASSWORD==='math_test_ci_only');
 const pg=spawnSync('/usr/bin/psql',['-X','-A','-t','-v','ON_ERROR_STOP=1','-c','SHOW server_version_num'],{encoding:'utf8',timeout:10000,maxBuffer:4096,env:{PATH:'/usr/bin:/bin',PGHOST:'127.0.0.1',PGPORT:'5432',PGDATABASE:'math_universe_test',PGUSER:'math_test',PGPASSWORD:'math_test_ci_only',LC_ALL:'C'}});
 need(!pg.error&&pg.status===0&&pg.signal===null&&pg.stderr==='');const version=pg.stdout.trim();need(new RegExp('^'+cell.postgres+'[0-9]{4}$').test(version));
 phase='E_STATIC_ROLES';const env={NODE_NO_WARNINGS:'1',NODE_DEBUG:'',NODE_DEBUG_NATIVE:'',TMPDIR:root,TEMP:root,TMP:root,ROLE_SOURCE_ROOT:root};
 const staticRun=spawnSync(process.execPath,['--no-warnings',join(root,'tools/ci_evidence/tests/inert_loader.mjs')],{cwd:root,encoding:'utf8',timeout:30000,maxBuffer:131072,env});
 need(!staticRun.error&&staticRun.status===0&&staticRun.signal===null&&staticRun.stderr==='');const staticResult=JSON.parse(staticRun.stdout);need(Object.keys(staticResult).sort().join(',')==='controls,liveAuth,status'&&staticResult.controls===92&&staticResult.status==='PASS_STATIC_SOURCE_ONLY'&&staticResult.liveAuth==='NOT_RUN');
 phase='E_HOSTED_ROLES';const files=[...new Set(plan.roles.filter(role=>role.kind==='HOSTED').map(role=>role.target))];need(files.length===8);
 const reporter=pathToFileURL(join(root,'tools/ci_evidence_role_matrix/reporter.mjs')).href;
 const tests=spawnSync(process.execPath,['--no-warnings','--test','--test-concurrency=1','--test-reporter='+reporter,...files.map(path=>join(root,path))],{cwd:root,encoding:'utf8',timeout:120000,maxBuffer:1048576,env});
 need(!tests.error&&tests.status===0&&tests.signal===null&&tests.stderr==='');const terminals=parseTerminals(tests.stdout,plan);
 phase='E_POST_SOURCE';sourceBytes();
 const receipt=makeReceipt(plan,context,{cell:cell.cell,actualNode:process.versions.node.split('.')[0],pgVersion:version,terminals,staticPassed:true});validateReceipt(receipt,plan,context);
 phase='E_OUTPUT';const output=join(temp,'ci-evidence-role-matrix');mkdirSync(output,{mode:0o700});writeFileSync(join(output,'roles-'+cell.cell+'.json'),JSON.stringify(receipt)+'\n',{flag:'wx',mode:0o600});console.log('ROLE_MATRIX_UNIT_PASS');
}catch{console.error('ROLE_MATRIX_BLOCKED:'+phase);process.exitCode=1;}
