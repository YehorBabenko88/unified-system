"""Root's serial test-only LS5 launcher. Never an installer or native issuer.

The --execute option is a local test mode, NOT authorization. Root must first
review exact GitHub sources/package/isolation and retain that evidence. Package
integrity DATA itself grants neither physical nor native runtime permission.
"""
import argparse,hashlib,json,os,queue,secrets,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.physical_dev.package import verify_package
from tools.physical_dev.supervisor import WindowsSmokeJob,WindowsAPI,OwnWatchdog,SmokeBlocked,child_environment,validate_bootstrap,stop_reason,cleanup_summary

ARTIFACT='f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940'

def need(value,code):
    if not value:raise SmokeBlocked(code)

def digest(path):
    with Path(path).open('rb') as source:
        result=hashlib.sha256()
        while chunk:=source.read(65536):result.update(chunk)
    return result.hexdigest()

class PrimaryGit:
    """The old verifier's batch subprocess also gets the pinned executable.

    Read-only provenance preparation, not a target or worker launch. The guard
    source is fixed by a separate SHA; it cannot select another command/root.
    """
    PIPE=subprocess.PIPE
    def __init__(self,executable,environment,roots):
        self.executable=str(executable);self.environment=dict(environment);self.roots=frozenset(roots)
    def Popen(self,argv,**options):
        need(type(argv) is list and len(argv)==6 and argv[:3]==['git','--no-replace-objects','-C']
             and argv[3] in self.roots and argv[4:]==['cat-file','--batch'],'PRIMARY_BATCH_COMMAND')
        need(set(options)=={'stdin','stdout'} and all(v==subprocess.PIPE for v in options.values()),'PRIMARY_BATCH_OPTIONS')
        return subprocess.Popen([self.executable,'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*argv[2:]],
            **options,env=self.environment,shell=False,close_fds=True,cwd=argv[3])

def validate_captures(captures):
    need(all(capture.error is None for _,capture in captures),'CAPTURE_FAILED_OR_OVERFLOW')
    need(sum(capture.count for _,capture in captures)<=16384,'OUTPUT_BOUND')

def retire_unassigned(processes):
    """Never let one own-handle cleanup failure skip the remaining evidence."""
    errors=[]
    for process in processes:
        try:
            if process.poll() is None:
                process.terminate();process.wait(timeout=5)
                errors.append('PREASSIGN_BOOTSTRAP_ABORTED')
        except BaseException as error:errors.append(type(error).__name__)
    return errors

class Capture:
    def __init__(self,process):
        self.ready=queue.Queue(maxsize=1);self.lock=threading.Lock();self.count=0;self.error=None
        self.logs={'stdout':bytearray(),'stderr':bytearray()};self.threads=[]
        for label,stream in [('stdout',process.stdout),('stderr',process.stderr)]:
            thread=threading.Thread(target=self._read,args=(label,stream),daemon=True);thread.start();self.threads.append(thread)
    def _read(self,label,stream):
        pending=bytearray();first=True
        try:
            while True:
                chunk=os.read(stream.fileno(),4096)
                if not chunk:break
                with self.lock:
                    remaining=max(0,16384-sum(map(len,self.logs.values())))
                    self.logs[label].extend(chunk[:remaining]);self.count+=len(chunk)
                    if self.count>16384:self.error='OUTPUT_BOUND'
                if label=='stdout' and first:
                    pending.extend(chunk)
                    if b'\n' in pending:
                        frame=bytes(pending[:pending.index(10)+1]);first=False
                        if len(frame)>256:self.error='BOOTSTRAP_BOUND'
                        else:self.ready.put_nowait(frame)
                    elif len(pending)>256:self.error='BOOTSTRAP_BOUND';first=False
        except BaseException:self.error='CAPTURE_FAILED'
    def save(self,root,name):
        for thread in self.threads:thread.join(2)
        need(all(not thread.is_alive() for thread in self.threads),'OWN_PIPE_NOT_RETIRED')
        for label,raw in self.logs.items():(root/(name+'.'+label+'.log')).write_bytes(raw)

def source_bindings(package,manifest):
    expected={'runtime-unified':'ba2b1cec0c2b114586afb73696e282117eede987',
        'strattester':'aed8a7c8a952f96803c207d5e90b133969a47f04','meta_analyse':'f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1','terminan':'161ea1e0fc3a3a4cd64783b0e111e1e119e14d71'}
    refs={entry['name']:entry for entry in manifest['source_metadata']['sources']}
    for name,commit in expected.items():need(refs.get(name,{}).get('commit')==commit,'FIXED_SOURCE_REFERENCE')
    # Exact executable/source admission, not a claimed loaded-DLL attestation.
    for relative,sha in [('tooling/python/python.exe','4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'),
        ('tooling/git/cmd/git.exe','78211c7ed73988da93a6d8a33d47ec6187f464d7ea2a9a00c182bbd7a1ecf30f'),
        ('tooling/node/node.exe','d702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5'),
        ('tooling/chromium/chrome-win/headless_shell.exe','ed19d88b4486c39c0265b0c07cbf1d6835d06069e600bede1adb09db0df46c8e'),
        ('sources/terminan/tests/fresh_render/bootstrap.cjs','50ad787d3c506e1fc4ce247891ee716f108b8f2cab20b64d9af2e691527b92b4'),
        ('sources/terminan/tests/fresh_render/harness.cjs','f9566565cfc4cd0b09067900defec274a833b6850d05d39945baffb4c0dbbce1'),
        ('sources/terminan/tests/fresh_render/sync_spawn_guard.cjs','f14689e5a92c1704f974fdf8cf9cc9aaf79881ca7a6b16f1bcc7487037580810'),
        ('sources/terminan/terminan/target_adapter_result.js','574dbf0882577708ab1e4c0ed73d6401eb6fabce3b3dc1b1375fc5952689241f')]:
        need(digest(package/relative)==sha,'FIXED_TOOL_OR_RENDERER_PIN')
    for relative in ('tools/physical_dev/bootstrap.py','tools/physical_dev/ls5_smoke.py','tools/physical_dev/supervisor.py','tools/physical_dev/package.py'):
        need(digest(package/'sources/harness'/relative)==digest(Path(__file__).resolve().parents[2]/relative),'REVIEWED_HARNESS_SOURCE_MISMATCH')
    # Metadata is not Git provenance. Execute only the independently pinned
    # old primary-source guard, with fixed trusted system Git/no overrides.
    trusted=Path('C:/Program Files/Git/cmd/git.exe').resolve(strict=True)
    need(digest(trusted)=='78211c7ed73988da93a6d8a33d47ec6187f464d7ea2a9a00c182bbd7a1ecf30f','TRUSTED_GIT_BOOTSTRAP')
    helper=package/'sources/runtime-unified/docs/intelligence/identity/run_qualification.py'
    raw=helper.read_bytes();need(hashlib.sha256(raw).hexdigest()=='e3733379da5e0cde84573f3279d265c91e16eceb8c94aeeda8983b51031216fe','PRIMARY_GUARD_PIN')
    namespace={'__name__':'physical_pilot_primary_guard','__file__':str(helper)};exec(compile(raw,str(helper),'exec'),namespace)
    clean={'SystemRoot':os.environ.get('SystemRoot','C:\\Windows'),'PATH':str(trusted.parent)+';C:\\Windows\\System32','GIT_OPTIONAL_LOCKS':'0'}
    def git(root,*args):return subprocess.check_output([str(trusted),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-C',str(root),*args],env=clean,timeout=15)
    namespace['git']=git
    namespace['subprocess']=PrimaryGit(trusted,clean,{str(package/'sources'/name) for name in ('runtime-unified','strattester','meta_analyse','terminan','harness')})
    for name in ('runtime-unified','strattester','meta_analyse','terminan','harness'):
        source=package/'sources'/name;head=git(source,'rev-parse','HEAD').decode().strip()
        need(head==refs.get(name,{}).get('commit'),'ACTUAL_PRIMARY_SOURCE_HEAD')
        need(git(source,'rev-parse','HEAD^{tree}').decode().strip()==refs[name]['tree'],'ACTUAL_PRIMARY_SOURCE_TREE')
        namespace['inventory'](source)
    return refs

def launch(job,argv,image,env,root,name,started,all_processes,all_captures):
    nonce=secrets.token_hex(16);argv=[nonce if value=='ROOT_NONCE' else value for value in argv]
    process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        cwd=root,env=env,shell=False,close_fds=True,creationflags=subprocess.CREATE_NO_WINDOW)
    all_processes.append(process);capture=Capture(process);all_captures.append((name,capture))
    try:
        try:frame=capture.ready.get(timeout=5)
        except queue.Empty:raise SmokeBlocked('BOOTSTRAP_READY_TIMEOUT') from None
        validate_bootstrap(frame,process.pid,nonce)
        validate_captures(all_captures)
        identity=job.attach_before_go(process,image)
        need(stop_reason(started,time.perf_counter_ns(),sum(c.count for _,c in all_captures)) is None,'BEFORE_GO_BUDGET')
        process.stdin.write(('GO '+nonce+'\n').encode('ascii'));process.stdin.flush()
        while process.poll() is None:
            reason=stop_reason(started,time.perf_counter_ns(),sum(c.count for _,c in all_captures))
            need(not reason and not capture.error,reason or capture.error or 'CAPTURE_UNKNOWN')
            time.sleep(.05)
        need(process.returncode==0,'OWN_STAGE_EXIT_FAILED')
        need(stop_reason(started,time.perf_counter_ns(),sum(c.count for _,c in all_captures)) is None,'STAGE_COMPLETION_BUDGET')
        return identity
    finally:
        if process.poll() is not None and process.stdin:process.stdin.close()

def execute(package,manifest_raw,pin,root):
    package=Path(package).resolve(strict=True);root=Path(root)
    need(root.is_absolute() and root==root.resolve() and not root.exists(),'NEW_OWN_STATE_REQUIRED')
    safe_parent=Path('C:/Users/LS-5/.codex/native-e2e-evidence-20261109').resolve(strict=True)
    need(root.parent==safe_parent and root.name.startswith('ls5-smoke-'),'FIXED_PRIVATE_LS5_STATE_PARENT')
    need(root!=package and not root.is_relative_to(package),'STATE_OUTSIDE_PACKAGE_REQUIRED')
    preflight=WindowsAPI();preflight.nonadmin(preflight.k.GetCurrentProcess())
    before=verify_package(package,manifest_raw,pin);manifest=json.loads(manifest_raw);refs=source_bindings(package,manifest)
    root.mkdir();env=child_environment(root);job=None;watchdog=None;processes=[];captures=[];failure=None
    result={'schema':'unified.ls5.disposable-smoke.v1','package_sha256':pin,'source_refs':refs,
        'public_submit':'DENY','publication':'LOCAL_UNATTESTED','resource_qualification':'NOT_GRANTED',
        'parent_chain':'UNKNOWN_MAY_BE_STRICTER','native_job_admission':False,'physical_cluster_admission':False,
        'target':'NOT_RUN','render':'NOT_RUN','cleanup':'PENDING','result':'NOT_PASSED'}
    started=time.perf_counter_ns()
    try:
        # This is the FIRST mutating Job call; sources/isolation must be reviewed.
        job=WindowsSmokeJob();result['parent_token']=job.parent_token;result['configured_limits']=job.readback
        watchdog=OwnWatchdog(job,started);watchdog.start()
        python=package/'tooling/python/python.exe';git=package/'tooling/git/cmd/git.exe';node=package/'tooling/node/node.exe'
        backend=package/'sources/harness/tools/physical_dev/bootstrap.py'
        result['backend_identity']=launch(job,[str(python),'-I','-S','-B',str(backend),'ROOT_NONCE',str(package),str(root),str(git),'SYNTHETIC_DIRECT_ONLY'],python,env,root,'backend',started,processes,captures)
        request=root/'fresh-request.json';envelope=root/'fresh-envelope.json';artifact=root/'fresh-artifact.json'
        need(artifact.stat().st_size==2070 and digest(artifact)==ARTIFACT,'ACTUAL_TARGET_ARTIFACT')
        result['target']='ACTUAL_DIRECT_TARGET_BYTES_MATCH';result['artifact_sha256']=ARTIFACT
        bootstrap=package/'sources/terminan/tests/fresh_render/bootstrap.cjs';module=package/'tooling/node_modules/@playwright/test';browser=package/'tooling/chromium/chrome-win/headless_shell.exe'
        result['render_identity']=launch(job,[str(node),'--no-addons',str(bootstrap),'ROOT_NONCE',str(root),str(request),str(envelope),str(artifact),digest(request),digest(envelope),digest(artifact),str(module),str(browser)],node,env,root,'render',started,processes,captures)
        receipts=list(root.glob('fresh-render-*/render-receipt.json'));need(len(receipts)==1,'FRESH_RENDER_RECEIPT_REQUIRED')
        view=json.loads(receipts[0].read_bytes());need(view.get('result')=='LOCAL_RENDER_PASS_NOT_AUTH_OR_PHYSICAL_ACCEPTANCE' and view.get('cleanup',{}).get('confirmed') is True,'FRESH_RENDER_OR_SDK_CLEANUP_NOT_PASSED')
        need(view.get('input_sha256')==dict(request=digest(request),envelope=digest(envelope),artifact=digest(artifact)),'FRESH_RENDER_INPUT_BINDING')
        result['render']='FRESH_LOCAL_UNATTESTED_BYTES_AND_DOM_MATCH';result['render_receipt_sha256']=digest(receipts[0])
    except BaseException as error:
        failure=error;result['failure_type']=type(error).__name__;result['failure_code']=str(error) if isinstance(error,SmokeBlocked) else 'DETAILS_WITHHELD'
    finally:
        if job is not None:
            try:
                if job.accounting()['active']:
                    job.terminate_own()
                result['accounting']=job.wait_empty(10)
                for process in processes:process.wait(timeout=5)
                result['cleanup']=cleanup_summary(result['accounting']['active'],[p.returncode for p in processes])
            except BaseException as error:
                result['cleanup']='FAILED_OR_UNCONFIRMED';result['cleanup_error']=type(error).__name__
                if failure is None:failure=error
            finally:
                safe_to_close=True
                if watchdog is not None:
                    try:watchdog.finish()
                    except BaseException as error:
                        failure=failure or error;result['watchdog']='EXPIRED_FAILED_OR_UNCONFIRMED'
                        safe_to_close=not watchdog.thread.is_alive()
                try:
                    # No handle-close/reuse race with an unjoined native call.
                    # A live watcher retains the Job until controller exit.
                    if safe_to_close:job.close()
                except BaseException as error:
                    result['job_close']='FAILED_OR_UNCONFIRMED';failure=failure or error
        # A pre-Assign failure still owns a direct bootstrap handle. No target/child
        # is allowed before GO; terminate ONLY that retained Popen if still alive.
        orphan_errors=retire_unassigned(processes)
        if orphan_errors:
            result['retained_process_cleanup_errors']=orphan_errors;failure=failure or SmokeBlocked('OWN_PROCESS_CLEANUP_FAILED_OR_ABORTED')
        for name,capture in captures:
            try:capture.save(root,name)
            except BaseException as error:
                failure=failure or error;result['pipe_cleanup']='FAILED_OR_UNCONFIRMED'
        try:validate_captures(captures)
        except BaseException as error:
            failure=failure or error;result['capture_status']='FAILED_OR_OVERFLOW'
        try:
            after=verify_package(package,manifest_raw,pin);need(before==after,'PROTECTED_PACKAGE_CHANGED')
            result['package_before_after_equal']=True
        except BaseException as error:
            result['package_before_after_equal']=False;failure=failure or error
        result['result']='SCOPED_FUNCTIONAL_SMOKE_PASS_NOT_NATIVE_RESOURCE_OR_CLUSTER_ACCEPTANCE' if failure is None else 'FAIL_OR_UNCONFIRMED'
        (root/'smoke-receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if failure is not None:raise SmokeBlocked('DISPOSABLE_SMOKE_FAILED') from failure
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',required=True);parser.add_argument('--manifest',required=True);parser.add_argument('--sha256',required=True);parser.add_argument('--state',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    path=Path(args.manifest);need(path.stat().st_size<=8*1024*1024,'MANIFEST_BOUND')
    with path.open('rb') as stream:raw=stream.read(8*1024*1024+1)
    need(len(raw)<=8*1024*1024,'MANIFEST_BOUND')
    if not args.execute:
        print(json.dumps(verify_package(Path(args.package),raw,args.sha256)));return
    print(json.dumps(execute(args.package,raw,args.sha256,Path(args.state))))

if __name__=='__main__':main()
