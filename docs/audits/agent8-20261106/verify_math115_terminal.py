import pathlib,subprocess,json,hashlib,re
r=pathlib.Path.cwd();private=r/'work/math115-terminal-a8-private';out=r/'outputs/phase79';out.mkdir(exist_ok=True);owner=r.parent/'codex-agent-7-distributed-research-math/outputs/math115-terminal-attempt1';repo=r/'work/review7-math-917';head='2446d04624469e34aa96ed766be7a4887d6d654c';tree='12c4e3cbd3557c7f4f634f5241c7e4b51eafba4f'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
assert git('rev-parse',head+'^{tree}').decode().strip()==tree
assert git('rev-parse',head+':.github/workflows/agent7-loader-init-trace.yml').decode().strip()=='612a6300071b478a823da076ca015782caabb9ca'
metadata={name:json.loads((private/(name+'.json')).read_bytes()) for name in ['run','jobs','artifacts']};run=metadata['run'];jobs=metadata['jobs'];assert run['id']==42352374979 and run['run_attempt']==1 and run['head_sha']==head and run['status']=='completed' and run['conclusion']=='success' and run['workflow_id']==409676563
assert run['actor']['login']==run['triggering_actor']['login']=='YehorBabenko88' and run['event']=='pull_request'
assert jobs['total_count']==1 and len(jobs['jobs'])==1;job=jobs['jobs'][0];assert job['id']==128343065197 and job['run_attempt']==1 and job['run_id']==42352374979 and job['status']=='completed' and job['conclusion']=='success'
assert all(s['status']=='completed' and s['conclusion']=='success' for s in job['steps']);assert metadata['artifacts']=={'total_count':0,'artifacts':[]}
index=json.loads((owner/'index.json').read_bytes());correlation=[]
for row in index['files']:
 b=(private/row['name']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'] and (owner/row['name']).read_bytes()==b;correlation.append(row)
raw=(private/'job-original.log').read_bytes();log=raw.decode('utf-8-sig');expected_marker='TRACE_COMPILED qualification=NONE nativeAcceptance=BLOCKED'
# Require actual timestamped output; command echo contains quoted Write-Output form.
compile_lines=[line for line in log.splitlines() if re.match(r'^\d{4}-\d\d-\d\dT\S+ '+re.escape(expected_marker)+r'$',line)];assert len(compile_lines)==1
found={}
for line in log.splitlines():
 for m in re.finditer(r'\{',line):
  try:v,end=json.JSONDecoder().raw_decode(line[m.start():])
  except (ValueError,TypeError):continue
  if type(v) is dict and v.get('schema') in ('math.loader-init-event.v1','math.loader-init-trace.v1'):
   key=v['schema'];found.setdefault(key,[]).append((line[m.start():m.start()+end]+'\n').encode())
assert all(len(v)==1 for v in found.values()) and len(found)==2
trace_raw=found['math.loader-init-trace.v1'][0];event_raw=found['math.loader-init-event.v1'][0]
assert hashlib.sha256(trace_raw).hexdigest()=='ba38dc522ee45b09f00a31a2b20b8f1c1390e6230b1c353f5ea4dc5065a5ff5e';assert hashlib.sha256(event_raw).hexdigest()=='1a99ca5ecc38de9ed2a413aed6dabe028819fd657372cc7991fba5ebea4cc063'
assert trace_raw==(owner/'trace-public.json').read_bytes() and event_raw==(owner/'event-public.json').read_bytes();(private/'trace-extracted.json').write_bytes(trace_raw)
event=json.loads(event_raw);assert event==dict(schema='math.loader-init-event.v1',sourceHead=head,sourceTree=tree,eventSha='d5d5d7ac9ba31d9d13f246a6d1d293570001ad4f',reviewRecordSha256='2d438482c5242e4fe69fe54b1f195524fca1141adc6fc5e588d9bff330cc2e74',qualification='NONE',nativeAcceptance='BLOCKED')
assert git('cat-file','-t',event['eventSha']).strip()==b'commit'
parser=private/'frozen-report.mjs';parser.write_bytes(git('show',head+':scripts/agent7-loader-init/report.mjs'))
code="import {readFileSync} from 'node:fs';import {pathToFileURL} from 'node:url';const m=await import(pathToFileURL(process.argv[2]));const v=m.parseTrace(readFileSync(process.argv[3],'utf8'),{head:process.argv[4],tree:process.argv[5]});console.log(JSON.stringify(v));"
env=__import__('os').environ.copy();env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None)
p=subprocess.run(['node','--input-type=module','-e',code,'A8_EXPORT_PARSE_ONLY',str(parser),str(private/'trace-extracted.json'),head,tree],env=env,capture_output=True,check=True,timeout=20);trace=json.loads(p.stdout)
assert trace==dict(schema='math.loader-init-trace.v1',head=head,tree=tree,qualification='NONE',nativeAcceptance='BLOCKED',outcome='DLL_INITIALIZATION_FAILED',events=7,breakpointHandled=False,firstException='NONE',lastModule='OS_KERNELBASE',cleanup='CONFIRMED')
model_counts={}
for key in ['tests','suites','pass','fail','cancelled','skipped','todo']:
 values=[]
 for line in log.splitlines():
  clean=re.sub(r'^\d{4}-\d\d-\d\dT\S+\s*','',line)
  match=re.fullmatch(r'(?:#|ℹ)\s+'+key+r'\s+(\d+)',clean)
  if match:values.append(int(match.group(1)))
 assert len(values)==1
 model_counts[key]=values[0]
assert model_counts=={'tests':8,'suites':0,'pass':8,'fail':0,'cancelled':0,'skipped':0,'todo':0}
(out/'terminal-verification.json').write_text(json.dumps(dict(requirement='ORIGINAL_SINGLE_USE_TERMINAL_RECONCILIATION_ONLY',run_id=run['id'],attempt=1,job_id=job['id'],source_head=head,source_tree=tree,event=event,trace=trace,CI_status=run['status'],CI_conclusion=run['conclusion'],job_started_UTC=job['started_at'],job_completed_UTC=job['completed_at'],successful_steps=len(job['steps']),hosted_MODEL_counts=model_counts,artifacts=0,original_primary_files_reacquired_and_owner_byte_equal=correlation,compile_actual_output_markers=1,parser='ORIGINAL_PRIMARY2446_EXPORT_ONLY_NO_RUN_ENTRYPOINT',parser_raw_sha256=hashlib.sha256(parser.read_bytes()).hexdigest(),trace_raw_sha256=hashlib.sha256(trace_raw).hexdigest(),event_raw_sha256=hashlib.sha256(event_raw).hexdigest(),raw_log_publication='PRIVATE_LOCAL_ONLY_NO_PRIVACY_REVIEW_NO_UPLOAD',authorization='CONSUMED_NO_RETRY_OR_ACTIVATION',native_acceptance='BLOCKED',qualification='NONE',RCA='NOT_ESTABLISHED_BY_LAST_MODULE'),indent=2),encoding='utf-8');print(json.dumps(dict(primary_metadata_and_log_matches_owner=True,compile_output_markers=1,outcome=trace['outcome'],events=7,cleanup=trace['cleanup'],native_acceptance='BLOCKED',artifacts=0)))
