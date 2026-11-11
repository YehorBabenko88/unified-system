"""Additive exact-source Scheduler preparation qualification; no authority.

The legacy crash child retains its command and is not -I/-S isolated. Its scoped
environment disables bytecode. No Scheduler fixture is imported by pure controls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import unittest
import zipfile

LEGACY='docs/scheduler/component-test-inventory-v2.json'
INVENTORY='docs/ci/preparation-integrity-inventory-v1.json'
MAX_FILES=20000
MAX_BYTES=256*1024*1024
TZDATA_SHA256='1a403fada01ff9221ca8044d701868fa132215d84beb92242d9acd2147f667a8'
CRASH_CASE_ID='test_agent5_scheduler_components.DurablePreparationTests.test_process_crash_before_event_commit_recovers_without_partial_hold'
OBSERVER_IDS=tuple('test_preparation_child_observer.PreparationChildObserverControls.'+name for name in (
    'test_buffer_hash_is_only_bounded_prefix_not_full_output',
    'test_event_budget_exhaustion_does_not_sample_child_again',
    'test_exit23_with_live_stdout_reader_is_recorded_not_reinterpreted',
    'test_export_is_a_detached_bounded_copy_with_no_child_effects',
    'test_failed_constructor_and_two_observed_communicate_calls_do_not_do_cleanup',
    'test_fixed_limits_and_constructor_registration_are_observation_only',
    'test_invalid_timing_or_unknown_token_never_polls_or_mutates_history',
    'test_missing_or_empty_cpython_buffers_and_threads_are_explicit',
    'test_poll_or_thread_error_is_unknown_without_exception_text',
    'test_second_constructor_is_declined_without_observing_another_child',
    'test_timeout_samples_poll_then_threads_without_pipe_or_cleanup_calls',
    'test_unsupported_buffers_are_not_coerced_hashed_or_iterated'))


def validate_inventory(old,new,ids):
    def exact(value,count):
        return type(value) is list and len(value)==count and all(type(x) is str and x for x in value) and len(set(value))==count
    if set(new)!={'schema','expected_count','preserved_legacy_ids','added_integrity_ids','expected_ids'}:
        raise ValueError('closed inventory required')
    legacy=old.get('expected_ids')
    if old.get('schema')!='agent5.component-test-inventory.v2' or type(old.get('expected_count')) is not int or old['expected_count']!=30 or not exact(legacy,30):
        raise ValueError('invalid original30 inventory')
    if new['preserved_legacy_ids']!=legacy:raise ValueError('original30 must be preserved in order')
    if new['schema']!='preparation-integrity-inventory.v1' or type(new['expected_count']) is not int or new['expected_count']!=36:
        raise ValueError('invalid inventory schema/count')
    added=new['added_integrity_ids'];expected=new['expected_ids']
    if not exact(added,6) or not exact(expected,36) or set(added)&set(legacy) or set(expected)!=set(legacy+added):
        raise ValueError('exact disjoint30+6 required')
    if not exact(ids,36) or set(ids)!=set(expected):raise ValueError('missing/duplicate/extra test IDs')


def validate_result(result,expected):
    if (type(result) is not dict or set(result)!={'ids','tests','skips','failures','errors'}
        or any(type(result[k]) is not int for k in ('tests','skips','failures','errors'))
        or tuple(result[k] for k in ('tests','skips','failures','errors'))!=(36,0,0,0)
        or type(result['ids']) is not list or len(result['ids'])!=36 or len(set(result['ids']))!=36 or set(result['ids'])!=set(expected)):
        raise ValueError('exact36/zero-skips qualification required')


def parse_blobs(entries,output):
    cursor=0;blobs=[]
    for oid,size in entries:
        end=output.find(b'\n',cursor)
        if end<0 or output[cursor:end]!=f'{oid} blob {size}'.encode():raise ValueError('invalid Git batch header')
        cursor=end+1;blob=output[cursor:cursor+size];cursor+=size
        if len(blob)!=size or output[cursor:cursor+1]!=b'\n':raise ValueError('truncated Git blob')
        cursor+=1
        if hashlib.sha1(b'blob '+str(size).encode()+b'\0'+blob).hexdigest()!=oid:raise ValueError('Git blob identity mismatch')
        blobs.append(blob)
    if cursor!=len(output):raise ValueError('extra Git batch data')
    return blobs


def check_files(root,files):
    dirs=set();hashes={}
    if len(files)>MAX_FILES or sum(map(len,files.values()))>MAX_BYTES:raise ValueError('source bounds exceeded')
    for name in files:
        parts=name.split('/')
        if not name or name.startswith('/') or '\\' in name or ':' in name or '\0' in name or any(p in ('','.','..','__pycache__') for p in parts) or name.endswith(('.pyc','.pyo')):
            raise ValueError('unsafe source path')
        for index in range(1,len(parts)):dirs.add('/'.join(parts[:index]))
    for name in sorted(dirs,key=lambda item:item.count('/')):
        path=root/name;info=path.lstat()
        if not stat.S_ISDIR(info.st_mode) or path.is_symlink() or getattr(info,'st_file_attributes',0)&1024:
            raise ValueError('nonordinary source parent')
    for name,raw in files.items():
        path=root/name;info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or getattr(info,'st_file_attributes',0)&1024:raise ValueError('nonordinary source file')
        if path.read_bytes()!=raw:raise ValueError('raw Git source mismatch')
        hashes[name]=hashlib.sha256(raw).hexdigest()
    actual_files=set();actual_dirs=set()
    for current,directories,names in os.walk(root,followlinks=False):
        base=Path(current)
        if base==root:
            if '.git' in directories:directories.remove('.git')
            if '.git' in names:names.remove('.git')
        for name in directories:
            path=base/name;info=path.lstat()
            if not stat.S_ISDIR(info.st_mode) or path.is_symlink() or getattr(info,'st_file_attributes',0)&1024:raise ValueError('nonordinary source directory')
            actual_dirs.add(path.relative_to(root).as_posix())
        for name in names:actual_files.add((base/name).relative_to(root).as_posix())
    if actual_files!=set(files) or actual_dirs!=dirs:raise ValueError('extra/missing source files or directories')
    return hashes


def validate_zoneinfo(zone,wheel):
    info=wheel.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or getattr(info,'st_file_attributes',0)&1024 or info.st_size>2*1024*1024:
        raise ValueError('nonordinary bounded tzdata wheel')
    raw=wheel.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=TZDATA_SHA256:raise ValueError('tzdata2025.2 wheel pin mismatch')
    with zipfile.ZipFile(wheel) as archive:
        prefix='tzdata/zoneinfo/'
        files={name[len(prefix):]:archive.read(name) for name in archive.namelist() if name.startswith(prefix) and not name.endswith('/')}
    return dict(version='2025.2',wheel_sha256=TZDATA_SHA256,zoneinfo_files=check_files(zone,files))


def selected_git_path(platform):
    return 'C:/Program Files/Git/bin/git.exe' if platform=='nt' else '/usr/bin/git'


def approved_git(root,path=None,*,evidence_path=None):
    candidate=Path(path) if path is not None else Path(selected_git_path(os.name))
    record=dict(selected_git=str(candidate),passed=False,raw_sha256=None,ancestors=[])
    errors=[]
    def inspect(item):
        entry=dict(path=str(item))
        try:
            info=item.lstat()
            entry.update(mode=info.st_mode,dev=info.st_dev,inode=info.st_ino,nlink=info.st_nlink,
                         size=info.st_size,mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns,
                         attributes=getattr(info,'st_file_attributes',0),symlink=item.is_symlink())
        except OSError as error:
            entry['error']=type(error).__name__;errors.append('unavailable Git path')
        return entry
    record['file']=None
    if not candidate.is_absolute() or candidate.is_relative_to(root):
        errors.append('approved Git must be absolute and external')
    if not errors:
        for parent in reversed(candidate.parents):
            entry=inspect(parent);record['ancestors'].append(entry)
            if 'mode' not in entry or not stat.S_ISDIR(entry['mode']) or entry['symlink'] or entry['attributes']&1024:
                errors.append('nonordinary Git parent');break
    if not errors:
        file=inspect(candidate);record['file']=file
        if ('mode' not in file or not stat.S_ISREG(file['mode']) or file['symlink']
                or file['nlink']!=1 or file['attributes']&1024 or file['size']>64*1024*1024):
            errors.append('nonordinary Git executable')
        if os.name!='nt' and ('mode' not in file or not file['mode']&0o111):errors.append('Git is not executable')
    # Never traverse below an unsafe parent or hash bytes before every gate.
    if not errors:
        try:record['raw_sha256']=hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError as error:errors.append('unreadable Git bytes: '+type(error).__name__)
    record['errors']=errors
    # Persist observations before any refusal or subprocess invocation.
    if evidence_path is not None:Path(evidence_path).write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    if errors:raise ValueError('; '.join(errors))
    record['passed']=True
    if evidence_path is not None:Path(evidence_path).write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    return str(candidate)


def snapshot(root,git,expected):
    def call(*args,data=None):
        return subprocess.run([git,'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-C',str(root),*args],input=data,capture_output=True,check=True,timeout=30).stdout
    head=call('rev-parse','HEAD').decode().strip()
    if head!=expected:raise ValueError('HEAD mismatch')
    tree=call('rev-parse','HEAD^{tree}').decode().strip();entries=[];names=[]
    for row in call('ls-tree','-rlz','--full-tree',head).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid,size=meta.split()
        if mode not in (b'100644',b'100755') or kind!=b'blob':raise ValueError('nonordinary committed source')
        entries.append((oid.decode(),int(size)));names.append(name.decode('utf-8'))
    if len(entries)>MAX_FILES or sum(size for _,size in entries)>MAX_BYTES:raise ValueError('Git source bounds exceeded')
    blobs=parse_blobs(entries,call('cat-file','--batch',data=''.join(oid+'\n' for oid,_ in entries).encode()))
    return dict(head=head,tree=tree,files=check_files(root,dict(zip(names,blobs))),primary_git=git)


def case_ids(suite):
    for case in suite:
        if isinstance(case,unittest.TestSuite):yield from case_ids(case)
        else:yield case.id()


def observer_controls(root,out):
    """Separate in-process pure lane: no recursive test-package discovery."""
    previous=list(sys.path)
    started=time.perf_counter_ns()
    try:
        sys.path.insert(0,str(root/'tests'))
        loader=unittest.TestLoader()
        suite=loader.loadTestsFromName('test_preparation_child_observer')
        ids=list(case_ids(suite))
        expected=list(OBSERVER_IDS)
        if ids!=expected:
            # Preserve setup evidence without pretending failed import is12 cases.
            with (out/'observer-controls.log').open('w',encoding='utf-8') as log:
                log.write('OBSERVER_CONTROL_IMPORT_OR_ID_MISMATCH\n')
                for error in loader.errors:log.write(error[:262144])
            (out/'observer-controls.json').write_text(json.dumps(dict(
                schema='preparation.observer-controls.v2',status='IMPORT_OR_ID_MISMATCH',
                ids=ids,started_ids=[],succeeded_ids=[],tests=0,skips=None,failures=None,
                errors=None,expected_failures=None,unexpected_successes=None,
                elapsed_ns=time.perf_counter_ns()-started),sort_keys=True)+'\n')
            raise ValueError('exact12 observer control IDs required')
        # Nested so the frozen admission3 AST fixture extracts a standalone
        # actual observer_controls definition, with no new private dependency.
        class Result(unittest.TextTestResult):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs)
                self.started_ids=[];self.succeeded_ids=[]
            def startTest(self,test):
                self.started_ids.append(test.id());super().startTest(test)
            def addSuccess(self,test):
                self.succeeded_ids.append(test.id());super().addSuccess(test)
        with (out/'observer-controls.log').open('w',encoding='utf-8') as log:
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
        qualified=(result.testsRun==12 and result.wasSuccessful() and not result.skipped
                   and not result.failures and not result.errors
                   and not result.expectedFailures and not result.unexpectedSuccesses
                   and result.started_ids==expected and result.succeeded_ids==expected)
        record=dict(schema='preparation.observer-controls.v2',
                    status='QUALIFIED' if qualified else 'NOT_QUALIFIED',
                    ids=ids,started_ids=result.started_ids,succeeded_ids=result.succeeded_ids,
                    tests=result.testsRun,skips=len(result.skipped),
                    failures=len(result.failures),errors=len(result.errors),
                    expected_failures=len(result.expectedFailures),
                    unexpected_successes=len(result.unexpectedSuccesses),
                    elapsed_ns=time.perf_counter_ns()-started)
        (out/'observer-controls.json').write_text(json.dumps(record,sort_keys=True)+'\n')
        if not qualified:
            raise ValueError('exact12 observer controls failed')
        return record
    finally:
        sys.path[:]=previous


def observer_admission_controls(root,out,source_hashes):
    """Mandatory actual3 against this verified qualifier, before actual36."""
    started=time.perf_counter_ns()
    fixture='tests/test_preparation_observer_admission.py'
    qualifier='tools/ci/qualify_preparation_integrity.py'
    sources={}
    for name in (fixture,qualifier):
        with (root/name).open('rb') as stream:raw=stream.read(65537)
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=source_hashes[name]:
            raise ValueError('bounded admission source identity mismatch')
        sources[name]=raw
    if source_hashes[fixture]!='15c5ced54f3c569bd1d8fdc7a752a1e7147efae80c91853b2f1ba0cddc4c80a1':
        raise ValueError('frozen actual3 fixture required')
    namespace=dict(__name__='test_preparation_observer_admission',__file__=str(root/fixture))
    exec(compile(sources[fixture],str(root/fixture),'exec'),namespace)
    suite=namespace['make_suite'](sources[qualifier],expected_source_sha256=source_hashes[qualifier])
    expected=['test_preparation_observer_admission.PreparationObserverAdmissionControls.'+name
              for name in ('test_actual_observer_controls_accepts_normal_twelve_successes',
                           'test_actual_observer_controls_rejects_expected_failure',
                           'test_actual_observer_controls_rejects_unexpected_success')]
    ids=list(case_ids(suite))
    if ids!=expected:raise ValueError('exact3 admission control IDs required')
    class Result(unittest.TextTestResult):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.started_ids=[];self.succeeded_ids=[]
        def startTest(self,test):
            self.started_ids.append(test.id());super().startTest(test)
        def addSuccess(self,test):
            self.succeeded_ids.append(test.id());super().addSuccess(test)
    with (out/'observer-admission-controls.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
    qualified=(result.testsRun==3 and result.wasSuccessful() and not result.skipped
               and not result.failures and not result.errors
               and not result.expectedFailures and not result.unexpectedSuccesses
               and result.started_ids==expected and result.succeeded_ids==expected)
    record=dict(schema='preparation.observer-admission-controls.v1',
                status='QUALIFIED' if qualified else 'NOT_QUALIFIED',
                ids=ids,started_ids=result.started_ids,succeeded_ids=result.succeeded_ids,
                tests=result.testsRun,skips=len(result.skipped),failures=len(result.failures),
                errors=len(result.errors),expected_failures=len(result.expectedFailures),
                unexpected_successes=len(result.unexpectedSuccesses),
                elapsed_ns=time.perf_counter_ns()-started)
    (out/'observer-admission-controls.json').write_text(json.dumps(record,sort_keys=True)+'\n')
    if not qualified:raise ValueError('exact3 observer admission controls failed')
    return record


def worker(root,result_path,zone):
    sys.path.insert(0,str(root))
    sys.path.insert(0,str(root/'tests'))
    from preparation_child_observer import PreparationChildObserver
    observer=PreparationChildObserver()
    import zoneinfo
    zoneinfo.reset_tzpath([str(zone)]);zoneinfo.ZoneInfo.clear_cache()
    old=json.loads((root/LEGACY).read_bytes());inventory=json.loads((root/INVENTORY).read_bytes())
    suite=unittest.TestSuite(unittest.defaultTestLoader.discover(str(root/'tests'),pattern=pattern)
        for pattern in ('test_agent5_scheduler_components.py','test_preparation_integrity.py'))
    ids=list(case_ids(suite));validate_inventory(old,inventory,ids)
    children=[];lock=threading.Lock();original=subprocess.Popen
    active_case=[None]
    observation=dict(incomplete=False,observer_failures=0,constructors=0,communicates=0,timeouts=0)
    def increment(name):observation[name]=min(observation[name]+1,2147483647)
    def observe(method,*args):
        # No output, locks or cleanup here; never mask an original exception.
        try:return getattr(observer,method)(*args,at_ns=time.perf_counter_ns())
        except BaseException:
            observation['incomplete']=True;increment('observer_failures')
            return None
    class ObservedResult(unittest.TextTestResult):
        def startTest(self,test):
            active_case[0]=test.id();super().startTest(test)
        def stopTest(self,test):
            try:super().stopTest(test)
            finally:active_case[0]=None
    class OwnedPopen(original):
        def __init__(self,*args,**kwargs):
            self._preparation_observed=active_case[0]==CRASH_CASE_ID
            self._preparation_observer_token=None
            if self._preparation_observed:
                increment('constructors')
                self._preparation_observer_token=observe('begin_constructor')
            try:
                with lock:
                    super().__init__(*args,**kwargs);children.append(self)
            except BaseException:
                if self._preparation_observed:observe('constructor_failed',self._preparation_observer_token)
                raise
            if self._preparation_observed:observe('end_constructor',self._preparation_observer_token,self)
        def communicate(self,*args,**kwargs):
            selected=self._preparation_observed
            token=self._preparation_observer_token
            if selected:
                increment('communicates');observe('begin_communicate',token)
            try:
                result=super().communicate(*args,**kwargs)
            except subprocess.TimeoutExpired:
                if selected:
                    increment('timeouts');observe('communicate_timeout',token)
                raise
            except BaseException:
                if selected:observation['incomplete']=True
                raise
            else:
                if selected:observe('end_communicate',token)
                return result
    subprocess.Popen=OwnedPopen
    def cancel():
        if sys.stdin.readline()!='CANCEL\n':return
        with lock:
            for child in children:
                if child.poll() is None:child.kill()
            for child in children:
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:pass
        os._exit(124)
    threading.Thread(target=cancel,daemon=True).start()
    observer_ok=False
    try:
        result=unittest.TextTestRunner(verbosity=2,resultclass=ObservedResult).run(suite)
        with lock:
            if any(p.poll() is None for p in children):raise ValueError('owned child not retired')
    finally:
        # Only after suite/standard cleanup, before exact36 validation can raise.
        # Diagnostic export failure cannot replace a suite/cleanup exception.
        try:
            raw=observer.export_json()
            if type(raw) is not bytes or len(raw)>16384:raise ValueError('observer export bound')
            value=json.loads(raw)
            observation['incomplete']=(observation['incomplete'] or value['incomplete']
                or value['retained_children']!=1 or value['dropped_events']!=0
                or observation['constructors']!=1 or not 1<=observation['communicates']<=2
                or observation['timeouts']>1)
            (result_path.parent/'child-observer.json').write_bytes(raw)
            observation['export_status']='EXPORTED'
            (result_path.parent/'child-observer-adapter.json').write_text(json.dumps(observation,sort_keys=True)+'\n')
            observer_ok=not observation['incomplete']
        except BaseException:
            observation['incomplete']=True;observation['export_status']='UNAVAILABLE'
            try:(result_path.parent/'child-observer-adapter.json').write_text(json.dumps(observation,sort_keys=True)+'\n')
            except BaseException:pass
    record=dict(ids=ids,tests=result.testsRun,skips=len(result.skipped),failures=len(result.failures),errors=len(result.errors))
    result_path.write_text(json.dumps(record,sort_keys=True));validate_result(record,inventory['expected_ids'])
    if not observer_ok:raise ValueError('child observation incomplete; no qualification')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected-head');parser.add_argument('--evidence',type=Path)
    parser.add_argument('--zoneinfo',type=Path,required=True);parser.add_argument('--tzdata-wheel',type=Path,required=True);parser.add_argument('--worker',type=Path)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if sys.version_info[:3]!=(3,12,10) or not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode or sys.pycache_prefix is not None:
        raise ValueError('CP312.10 -I-S-B/no cache prefix required')
    zone=args.zoneinfo.resolve()
    if not (zone/'Europe/Berlin').is_file() or zone.is_relative_to(root):raise ValueError('external pinned zoneinfo required')
    dependency=validate_zoneinfo(zone,args.tzdata_wheel.resolve())
    if args.worker:worker(root,args.worker,zone);return
    if not args.expected_head or re.fullmatch('[0-9a-f]{40}',args.expected_head) is None:raise ValueError('exact expected HEAD required')
    out=args.evidence.resolve()
    if out.is_relative_to(root):raise ValueError('evidence must be external')
    out.mkdir(parents=True,exist_ok=False)
    before=None;git=None
    receipt=dict(passed=False,scope='LOCAL_SQLITE_PREPARATION_ONLY',native_authority=False,runtime_admission=False,
        physical_execution_authorization=False,public_submit='DENY',run_id=os.getenv('GITHUB_RUN_ID'),
        attempt=os.getenv('GITHUB_RUN_ATTEMPT'),job=os.getenv('GITHUB_JOB'),runner_os=sys.platform,
        python=sys.version,legacy_child_isolated_flags=False,dependency=dependency)
    try:
        git=approved_git(root,evidence_path=out/'git-preflight.json');before=snapshot(root,git,args.expected_head);receipt['source_before']=before
        controls=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_preparation_qualification.py')
        with (out/'controls.log').open('w',encoding='utf-8') as log:
            controls_result=unittest.TextTestRunner(stream=log,verbosity=2).run(controls)
        if not controls_result.wasSuccessful() or controls_result.skipped or controls_result.testsRun!=12:
            raise ValueError('pure guard controls failed')
        receipt['pure_controls']=12
        receipt['observer_admission_controls']=observer_admission_controls(root,out,before['files'])
        receipt['observer_controls']=observer_controls(root,out)
        env=os.environ.copy()
        for key in ('PYTHONPATH','PYTHONHOME','PYTHONPYCACHEPREFIX'):env.pop(key,None)
        env['PYTHONDONTWRITEBYTECODE']='1'
        result_path=out/'result.json'
        command=[sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--zoneinfo',str(zone),'--tzdata-wheel',str(args.tzdata_wheel.resolve()),'--worker',str(result_path)]
        with (out/'tests.log').open('wb') as log:
            child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log,env=env);receipt['worker_pid']=child.pid
            try:code=child.wait(timeout=120)
            except subprocess.TimeoutExpired:
                receipt['timeout']=True
                try:child.communicate(input=b'CANCEL\n',timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill();child.wait(timeout=5);receipt['descendant_cleanup']='UNKNOWN'
                raise ValueError('suite timeout; no qualification')
            finally:
                if child.stdin:child.stdin.close()
        if code!=0:raise ValueError('suite worker failed')
        result=json.loads(result_path.read_bytes());inventory=json.loads((root/INVENTORY).read_bytes())
        validate_result(result,inventory['expected_ids']);receipt['result']=result
        after=snapshot(root,git,args.expected_head);receipt['source_after']=after
        if dependency!=validate_zoneinfo(zone,args.tzdata_wheel.resolve()):raise ValueError('dependency changed')
        if before!=after:raise ValueError('source changed')
        receipt['passed']=True
    except BaseException as error:
        receipt['error']=type(error).__name__+': '+str(error);raise
    finally:
        if before is not None and 'source_after' not in receipt:
            try:receipt['source_after']=snapshot(root,git,args.expected_head)
            except BaseException as post_error:
                receipt['source_after_error']=type(post_error).__name__+': '+str(post_error)
        receipt['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
        (out/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
