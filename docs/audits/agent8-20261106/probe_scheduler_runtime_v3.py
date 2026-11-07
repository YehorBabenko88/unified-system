"""A8 independent private outbox/synthetic-port state controls and opt-in local probe."""
import hashlib,json,os,pathlib,subprocess,tempfile
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase37';head='462935b53ef25d4d9be2371bad1cd7230c65f2e7';repo=max((r/'work').glob('a5-v3-clean-*'),key=lambda p:p.stat().st_mtime)
assert subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse','HEAD']).decode().strip()==head
scratch=r/'work'/('a5-state-probes-'+next(tempfile._get_candidate_names()));scratch.mkdir()
code='''import sys,pathlib,tempfile,json,ipaddress
sys.path.insert(0,str(pathlib.Path.cwd()))
def guard(event,args):
 if event in ('socket.connect','socket.bind') and (not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback):raise RuntimeError('A8_NONLOOPBACK_DENIED')
sys.addaudithook(guard)
from tests.test_agent5_scheduler_runtime import command,FixtureAuthority,Worker
from scheduler_components.runtime import SchedulerRuntime,Unavailable
from scheduler_components.attempt_registry import AttemptRegistry,IntentConflict
from scheduler_components.domain_v1 import encode_command
from scheduler_components.benchmarks import measure_local
events=[]
def event(name,**extra):events.append(dict(name=name,scope='LOCAL_CODE_AND_SYNTHETIC_PORTS_ONLY',**extra))
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'outbox.db';a=FixtureAuthority();w=Worker();registry=AttemptRegistry(p);runtime=SchedulerRuntime(registry,a,w)
 a.outcome=('UNKNOWN',None);first=runtime.submit(command());assert first['state']=='UNKNOWN';raw=first['raw'];runtime.submit(command());assert len(a.calls)==1
 registry.close();registry=AttemptRegistry(p);runtime=SchedulerRuntime(registry,a,w);runtime.submit(command());assert len(a.calls)==1
 a.outcome=('COMMITTED',b'fixture-grant');runtime.reconcile(command()['request_id']);assert a.calls==[raw,raw] and len(w.starts)==1;event('unknown_restart_original_bytes_no_reexecute',execute_calls=1,reconcile_calls=1)
 moved=command();moved['worker_incarnation_id']='00000000-0000-4000-8000-000000000099'
 try:runtime.submit(moved)
 except IntentConflict:pass
 else:raise AssertionError('incarnation silently rekeyed')
 event('incarnation_change_conflicts_without_new_start');registry.close()
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'outbox.db';a=FixtureAuthority();w=Worker();registry=AttemptRegistry(p);other=AttemptRegistry(p);runtime=SchedulerRuntime(registry,a,w)
 def execute(raw):other.request_drain(command()['request_id']);return 'COMMITTED',b'fixture-grant'
 a.execute=execute;row=runtime.submit(command());assert row['drain_requested'] and row['dispatch_state']=='NONE' and not w.starts;event('second_connection_drain_before_claim_blocks_start');other.close();registry.close()
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'outbox.db';a=FixtureAuthority();w=Worker();registry=AttemptRegistry(p);runtime=SchedulerRuntime(registry,a,w);original=w.start
 def lost(request,raw,grant):original(request,raw,grant);raise OSError('synthetic lost reply')
 w.start=lost;row=runtime.submit(command());assert row['dispatch_state']=='SENDING';registry.close();registry=AttemptRegistry(p)
 newworker=Worker();runtime=SchedulerRuntime(registry,a,newworker);row=runtime.reconcile(command()['request_id']);assert row['dispatch_state']=='SENDING' and not newworker.starts;event('lost_start_reply_new_worker_inspect_none_never_restarts');registry.close()
with tempfile.TemporaryDirectory() as temp:
 p=pathlib.Path(temp)/'outbox.db';a=FixtureAuthority();w=Worker();registry=AttemptRegistry(p);runtime=SchedulerRuntime(registry,a,w);a.available=False;row=runtime.submit(command());assert row['state']=='COMMITTED' and row['dispatch_state']=='NONE' and not w.starts;event('synthetic_dispatch_admission_denial_keeps_nonexecuted_committed_intent');registry.close()
measurement=measure_local(allow_local_measurement=True,cpu_duration_ms=5,scratch_bytes=4096,loopback_bytes=4096)
assert measurement['provenance']['scope']=='LOCAL_PROCESS_TEMPFILE_LOOPBACK_NOT_FLEET_CAPACITY';assert measurement['scratch']['bytes']==measurement['network']['bytes']=='4096';event('explicit_bounded_private_5ms_CPU_4KiB_scratch_4KiB_loopback_measurement',qualification='NOT_MILLICORES_OR_LAN_CAPACITY')
pathlib.Path(OUTPUT).write_text(json.dumps(dict(events=events,measurement=measurement,native_authority='NOT_RUN',native_storage='NOT_RUN',physical='BLOCKED'),indent=2))
print('A8_LOCAL_STATE_AND_MEASUREMENT_PROBES_COMPLETE cases='+str(len(events)))
'''.replace('OUTPUT',repr(str(out/'independent-state-probes.json')))
env=dict(os.environ,TEMP=str(scratch),TMP=str(scratch),PYTHONDONTWRITEBYTECODE='1');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',code],cwd=repo,env=env,capture_output=True,timeout=30);(out/'independent-state-probes.stdout.log').write_bytes(p.stdout);(out/'independent-state-probes.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')
owner=r.parent/'codex-agent-5-resource-aware-distributed/outputs/AGENT5-CI-LOCAL-462935b';raw=(owner/'receipt.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='eb92a1bdd5654c03ed8ca04b8000552c66779a9f26e2848566f6ecaacc650bc5';receipt=json.loads(raw);assert receipt['source_before']['head']==head and receipt['tests_run']==52 and receipt['skips']==0 and receipt['passed']
log=(owner/'component-tests.log').read_bytes();assert hashlib.sha256(log).hexdigest()==receipt['test_log_sha256'];(out/'owner-original-receipt.json').write_bytes(raw);(out/'owner-original-tests.log').write_bytes(log)
print('OWNER_ORIGINAL_RECEIPT_HASH_AND_LOG_VERIFIED')
