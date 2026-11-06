"""Pre-dispatch source/model review only. Never launch native observer/Main."""
import base64,hashlib,io,json,os,pathlib,subprocess,sys,textwrap
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review-math113';out=root/'outputs/phase17';out.mkdir(exist_ok=True)
head='40c158797dd22581ae20dea03b2aa9f06dda8042';base='917d99672e37db59835a8ab23b03c99826b12d78'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(ref,path):return git('show',ref+':'+path)
paths=git('diff','--name-only',base,head).decode().splitlines();assert set(paths)=={'.github/workflows/agent7-loader-init-trace.yml','docs/audits/agent7-loader-init-trace-evidence.json','scripts/agent7-loader-init/build.ps1','scripts/agent7-loader-init/report.mjs','tests/agent7-replay-research.test.mjs','tests/fixtures/agent7-loader-init/HostedLoaderInitTrace.cs'}
oldtest=blob(base,'tests/agent7-replay-research.test.mjs');newtest=blob(head,'tests/agent7-replay-research.test.mjs');assert newtest.startswith(oldtest[:-4]) and newtest.endswith(b'\n});\n')
proof=json.loads(blob(head,'scripts/platform-source-proof.json'));assert blob(base,'scripts/platform-source-proof.json')==blob(head,'scripts/platform-source-proof.json')
for item in proof['testFiles']:
 raw=b''.join(blob(head,p['path'])[p['start']:p['end']] for p in proof['recipes'][item['path']]);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['blob']
def identity():
 code="import {verifySourceIdentity} from './scripts/verify-source-identity.mjs';console.log(JSON.stringify(verifySourceIdentity(process.argv[1])));"
 return json.loads(subprocess.check_output(['node','--input-type=module','-e',code,head],cwd=repo))
before=identity();assert before['trackedSourceSha256']=='f104b0b1facbcae1cc3b1b195bb29bad8f3f3ba608c0128e62dd69e106fbb112'
run=subprocess.run(['node','--test','--test-reporter=tap','tests/platform-coverage.test.mjs','tests/agent7-replay-research.test.mjs'],cwd=repo,capture_output=True,timeout=60)
(out/'selected-tests.tap.log').write_bytes(run.stdout);(out/'selected-tests.stderr.log').write_bytes(run.stderr);assert run.returncode==0 and b'# pass 13' in run.stdout and b'# skipped 0' in run.stdout
extra=r'''
namespace A8Independent {
 using System;using System.Collections.Generic;using MathUniverse.Agent7;
 public class P:ITracePlatform {
  public Queue<TraceEvent> Q=new Queue<TraceEvent>();public List<uint> S=new List<uint>();public long Clock;public bool Child=true,FailBegin,FailFinish,FailClose,ExitStop=true;public int Stops,Finishes;public uint Budget;
  public long Now{get{return Clock;}}public bool HasChild{get{return Child;}}
  public bool Begin(){if(FailBegin)throw new Exception();return true;}
  public bool Wait(out TraceEvent e,uint ms){if(ms>100)throw new Exception();Clock+=ms;e=Q.Count==0?null:Q.Dequeue();return e!=null;}
  public bool Continue(TraceEvent e,uint status){S.Add(status);return true;}
  public bool CloseImage(TraceEvent e){return !FailClose;}
  public bool Stop(){Stops++;if(ExitStop)Q.Enqueue(E(5,0));return true;}
  public bool Finish(uint ms,bool exit){Finishes++;Budget=ms;return !FailFinish&&(!Child||exit);}
  public static TraceEvent E(uint kind,uint code){return new TraceEvent{Kind=kind,Pid=7,Tid=9,Code=code,FirstChance=1,Module="OS_NTDLL"};}
 }
 public static class Checks {
  static void Need(bool b){if(!b)throw new Exception("A8_MODEL_FAIL");}
  public static string Run(){int n=0;
   var p=new P();p.Q.Enqueue(P.E(3,0));p.Q.Enqueue(P.E(1,0x80000003));p.Q.Enqueue(P.E(1,0x80000003));p.Q.Enqueue(P.E(5,71));var r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&p.S[1]==0x10002&&p.S[2]==0x80010001&&r.FirstException=="BREAKPOINT"&&r.Outcome=="DEBUGGER_PERTURBED_BASELINE");n++;
   p=new P();p.Q.Enqueue(P.E(1,0xc0000005));r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&r.Outcome=="PROTOCOL_FAILURE"&&p.S[0]==0x80010001);n++;
   p=new P();p.Child=false;p.FailBegin=true;r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&p.Stops==1&&p.Finishes==1&&r.Outcome=="PROTOCOL_FAILURE");n++;
   p=new P();p.Q.Enqueue(P.E(3,0));r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&r.Outcome=="DEADLINE"&&p.Clock<=15000&&p.Budget<=5000);n++;
   p=new P();p.FailFinish=true;p.Q.Enqueue(P.E(3,0));p.Q.Enqueue(P.E(5,0));r=LoaderInitTrace.Observe(p);Need(!r.Cleanup&&r.Outcome=="CLEANUP_UNCONFIRMED");n++;
   p=new P();p.FailClose=true;p.Q.Enqueue(P.E(3,0));p.Q.Enqueue(P.E(5,0));r=LoaderInitTrace.Observe(p);Need(!r.Cleanup&&r.Outcome=="CLEANUP_UNCONFIRMED");n++;
   p=new P();p.ExitStop=false;p.Q.Enqueue(P.E(3,0));r=LoaderInitTrace.Observe(p);Need(!r.Cleanup&&p.Clock<=15000&&p.Stops==1&&p.Finishes==1);n++;
   return "A8_MODEL_ONLY cases="+n+" nativeInvocations=0";
  }
 }
}
'''
model=out/'auditor-model.cs';model.write_text(extra)
ps="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$r=$env:A8_SOURCE;$s=[IO.File]::ReadAllText((Join-Path $r 'scripts/q01-lab/WindowsJobContainment.cs'))+[char]10+[IO.File]::ReadAllText((Join-Path $r 'tests/fixtures/adminit-containment/HostedPrivateDesktop.cs'))+[char]10+[IO.File]::ReadAllText((Join-Path $r 'tests/fixtures/agent7-loader-init/HostedLoaderInitTrace.cs'))+[char]10+[IO.File]::ReadAllText($env:A8_MODEL);Add-Type -TypeDefinition $s;[MathUniverse.Agent7.LoaderInitTrace]::RunModelTests();[A8Independent.Checks]::Run()"
env=os.environ.copy();env.update(A8_SOURCE=str(repo),A8_MODEL=str(model))
run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(ps.encode('utf-16le')).decode()],env=env,capture_output=True,timeout=30)
(out/'models.stdout.log').write_bytes(run.stdout);(out/'models.stderr.log').write_bytes(run.stderr);assert run.returncode==0 and b'MODEL_ONLY cases=17' in run.stdout and b'A8_MODEL_ONLY cases=7 nativeInvocations=0' in run.stdout
guard_env={k:v for k,v in os.environ.items() if not k.startswith(('GITHUB_','RUNNER_'))};guards={}
commands={'build':['powershell.exe','-NoProfile','-NonInteractive','-File',str(repo/'scripts/agent7-loader-init/build.ps1'),'-OutputRoot',str(root/'work/never-built-local-observer'),'-ExpectedHead',head,'-ExpectedTree',git('rev-parse','HEAD^{tree}').decode().strip()],'report':['node',str(repo/'scripts/agent7-loader-init/report.mjs'),str(root/'work/never-built-local-observer'),head,git('rev-parse','HEAD^{tree}').decode().strip()]}
for name,cmd in commands.items():
 run=subprocess.run(cmd,cwd=repo,env=guard_env,capture_output=True,timeout=15);assert run.returncode!=0
 (out/(name+'-local-refusal.stdout.log')).write_bytes(run.stdout);(out/(name+'-local-refusal.stderr.log')).write_bytes(run.stderr);guards[name]=run.returncode
after=identity();assert before==after
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'base':base,'changed_paths':paths,'source_before':before,'source_after':after,'original_source_files_reconstructed':188,'old_test_assertions_retained':True,'tests':13,'pass':13,'skip':0,'built_in_model_cases':17,'auditor_derived_model_cases':7,'local_entry_refusals':guards,'native_Main_or_backend_invocations':0,'dispatch':'NOT_RUN_ROOT_CONCRETE_AUTHORIZATION_PENDING','A8_review':'SOURCE_MODEL_ACK_FOR_NONQUALIFYING_HOSTED_OBSERVATION_ONLY','external_record_digest':'REFERENCE_NOT_AUTHORIZATION_PROOF','native_acceptance':'BLOCKED_ORIGINAL_FAILURE_UNRESOLVED','physical':'BLOCKED','overall':'NO_GO'}
(out/'loader-pre-dispatch-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
