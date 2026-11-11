"""OWN local Journal/lock P2 reproduction. No A2 source edits or native RPC."""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import uuid

OUT=Path(__file__).parent/'AGENT5-CUSTODY-ENTER-2F94DA5-GREEN'
OUT.mkdir(exist_ok=True)
GRID=Path(__file__).parents[1]/'work/custody-enter-grid-2f94da5'
SUPPORT=Path(__file__).parents[1]/'work/custody-enter-support-1f6b0b5'
GH='2f94da511681811588e0f850a0a0e9dc4479c8b8'
SH='1f6b0b5c231853607f5bec780f1544cd32bf577d'

def git(root,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*args])
def primary(root,head):
    assert git(root,'rev-parse','HEAD').decode().strip()==head
    entries=[x.split(b'\t') for x in git(root,'ls-tree','-rz','HEAD').split(b'\0') if x]
    oids=[meta.split()[2] for meta,path in entries]
    data=subprocess.run(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],input=b'\n'.join(oids)+b'\n',stdout=subprocess.PIPE,check=True).stdout
    offset=0;expected={}
    for (meta,path),oid in zip(entries,oids):
        end=data.index(b'\n',offset);h=data[offset:end].split();assert h[:2]==[oid,b'blob']
        size=int(h[2]);raw=data[end+1:end+1+size];offset=end+size+2
        assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest().encode()==oid
        expected[path.decode()]=hashlib.sha256(raw).hexdigest()
    assert offset==len(data)
    return expected
def check(root,expected):
    assert {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}==expected
    assert not git(root,'ls-files','--others','--exclude-standard').strip()

gp=primary(GRID,GH);sp=primary(SUPPORT,SH);check(GRID,gp);check(SUPPORT,sp)
assert gp['grid/authority_assignment_v1.py']=='5b972b6d81eeaf6f2283584c5b0482552fa9bf0717a4379838900a72da791491'
assert sp['unified_system/journal.py']=='9f170cf33f8cdd79baef6fa633d03bebf9eb4b594c54c9cf8dd6c7cb9810bbc3'
sys.path[:0]=[str(GRID),str(SUPPORT)]
from grid.authority_assignment_v1 import RootRegistrationCustody,RegistrationCustodyUnavailable
from grid.authority_runtime_v1 import canonical
from unified_system.journal import Journal

def original():
    return canonical(dict(schema='unified.authority.unqualified-worker-registration-intent.v1-review1',operation='COMMISSION_UNQUALIFIED_WORKER',
        cluster_id=str(uuid.uuid4()),cluster_generation=str(uuid.uuid4()),realm_id=str(uuid.uuid4()),node_id=str(uuid.uuid4()),
        worker_inventory_incarnation_id=str(uuid.uuid4()),worker_module_sha256='a'*64,original_registration_request_id=str(uuid.uuid4())))
CHILD='''import sys,base64,json
sys.path[:0]=sys.argv[1:3]
from unified_system.journal import Journal
from grid.authority_assignment_v1 import RootRegistrationCustody
with RootRegistrationCustody(Journal(sys.argv[3]),original_intent_bytes=base64.b64decode(sys.argv[4],validate=True)) as held:
 state=held.read_state()
 print(json.dumps(dict(status='ACQUIRED_LOCAL_LOCK_ONLY',resources_reserved=state['resources_reserved'],effect_permitted=state['effect_permitted'])))
'''
def contender(path,raw):
    p=subprocess.Popen([sys.executable,'-I','-B','-c',CHILD,str(GRID),str(SUPPORT),str(path),base64.b64encode(raw).decode()],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:output,error=p.communicate(timeout=5)
    except BaseException:
        p.kill();p.communicate(timeout=5);raise
    assert p.returncode==0 and not error and 0<len(output)<=4096
    value=json.loads(output);assert value['status']=='ACQUIRED_LOCAL_LOCK_ONLY' and value['effect_permitted'] is False and value['resources_reserved'] is False
    value.update(own_launch_pid=p.pid,launch_exit_code=0,native_pid_identity_qualified=False)
    return value
def closed(descriptors):
    proof=[]
    for fd in descriptors:
        try:os.fstat(fd)
        except OSError as error:proof.append(dict(former_fd=fd,error_type=type(error).__name__,errno=error.errno))
        else:raise AssertionError('retained descriptor still open')
    return proof

private=Path(tempfile.mkdtemp(prefix='a5-custody-enter-green-'));root_id=private.lstat()
identities={};held_objects=[];sidecar=None;sidecar_identity=None;cases=[];failure=None;cleanup=[]
def allocate(name):
    path=private/name;raw=original();journal=Journal(path);held=RootRegistrationCustody(journal,original_intent_bytes=raw)
    held_objects.append(held);held.retain_original()
    for p in (path,path.with_name(path.name+'.registration-owner.lock')):
        info=p.lstat();identities[p]=(info.st_dev,info.st_ino)
    return path,raw,journal,held
try:
    path,raw,journal,held=allocate('path-case.sqlite');before=Journal(path).read();descriptors=(held._db_fd,held._lock_fd)
    journal.path=private/'unallocated-foreign-path.sqlite'
    try:
        with held:raise AssertionError('entry body ran')
    except RegistrationCustodyUnavailable as error:
        assert str(error)=='JOURNAL_PATH_CHANGED';entry_error=(type(error).__name__,str(error))
    else:raise AssertionError('entry guard did not fail')
    finally:journal.path=path
    assert held._closed and held._db_fd is None and held._lock_fd is None
    proof=closed(descriptors)
    acquired=contender(path,raw)  # No explicit/manual close before contender.
    assert Journal(path).read()==before
    cases.append(dict(case='path_mutation_failed_entry',entry_error=entry_error,body_not_run=True,closed_before_contender=proof,
        manual_close_before_contender=False,contender=acquired,original_rows_unchanged=True))
    held.close();held.close();check(GRID,gp);check(SUPPORT,sp)

    path2,raw2,journal2,second=allocate('sidecar-case.sqlite');before2=Journal(path2).read();descriptors2=(second._db_fd,second._lock_fd)
    sidecar=path2.with_name(path2.name+'-journal');sidecar.write_bytes(b'OWN_LOCAL_TEST_SIDECAR');info=sidecar.lstat();sidecar_identity=(info.st_dev,info.st_ino)
    actual_close=second.close;close_calls=[]
    def close_then_report_failure():
        actual_close();close_calls.append('actual_own_close_completed');raise OSError('OWN_TEST_CLOSE_REPORT_FAULT')
    second.close=close_then_report_failure
    try:
        try:
            with second:raise AssertionError('entry body ran')
        except RegistrationCustodyUnavailable as error:
            assert str(error)=='SIDECAR_REQUIRES_EXPLICIT_OWNER_RECOVERY'
            notes=getattr(error,'__notes__',[]);assert any('Custody entry cleanup' in note for note in notes)
            entry_error2=(type(error).__name__,str(error))
        else:raise AssertionError('entry guard did not fail')
        assert close_calls==['actual_own_close_completed'];proof2=closed(descriptors2)
        info=sidecar.lstat();assert (info.st_dev,info.st_ino)==sidecar_identity and sidecar.parent==private and stat.S_ISREG(info.st_mode) and info.st_nlink==1
        sidecar.unlink();sidecar=None
        acquired2=contender(path2,raw2)  # Only known own sidecar removed; no manual close.
        assert Journal(path2).read()==before2
        cases.append(dict(case='sidecar_entry_and_close_report_fault',entry_error=entry_error2,cleanup_notes=notes,
            body_not_run=True,closed_before_contender=proof2,manual_close_before_contender=False,
            contender=acquired2,original_rows_unchanged=True))
    finally:second.close=actual_close
except BaseException as error:failure=(type(error).__name__,str(error))
finally:
    for held in held_objects:
        try:held.close()
        except BaseException as error:cleanup.append(('owned_adapter_close',type(error).__name__,str(error)))
    try:
        info=private.lstat();assert (info.st_dev,info.st_ino)==(root_id.st_dev,root_id.st_ino) and not getattr(info,'st_file_attributes',0)&1024
        if sidecar is not None:
            info=sidecar.lstat();assert (info.st_dev,info.st_ino)==sidecar_identity and sidecar.parent==private and stat.S_ISREG(info.st_mode)
            sidecar.unlink()
        for p,identity in identities.items():
            info=p.lstat();assert p.parent==private and (info.st_dev,info.st_ino)==identity and stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&1024
            p.unlink()  # Only exact owned files after all handles/children retired.
        private.rmdir()
    except BaseException as error:cleanup.append(('owned_known_file_cleanup',type(error).__name__,str(error)))
check(GRID,gp);check(SUPPORT,sp)
receipt=dict(scope='ACTUAL_LOCAL_FAILED_ENTRY_CLEANUP_GREEN_NOT_NATIVE_API',grid_head=GH,grid_tree=git(GRID,'rev-parse','HEAD^{tree}').decode().strip(),support_head=SH,
    grid_primary_files=len(gp),support_primary_files=len(sp),primary_pre_post_unchanged=True,module_sha256=gp['grid/authority_assignment_v1.py'],core_dependency_sha256=gp['grid/authority_runtime_v1.py'],journal_sha256=sp['unified_system/journal.py'],
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),runtime=sys.version,interpreter=sys.executable,bootstrap_venv_not_native_pid_identity=True,
    focused_local_cases=cases,unexpected_failure=failure,cleanup_errors=cleanup,owner13_not_rerun=True,proxy_tests_not_run=True,native_rpc_calls=0,workers_run=0,native_api_ack=False,effect_ack=False,go_no_go='NO-GO')
r=OUT/'receipt.json';r.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print('receipt_sha256',hashlib.sha256(r.read_bytes()).hexdigest())
raise SystemExit(bool(failure or cleanup or len(cases)!=2))

