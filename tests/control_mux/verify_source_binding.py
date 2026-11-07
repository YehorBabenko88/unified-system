"""Inert source/bytecode negatives in independent newly initialized git repos."""
import argparse,hashlib,json,os,py_compile,subprocess,sys,types
from pathlib import Path
if not sys.flags.isolated or not sys.dont_write_bytecode:raise RuntimeError('ISOLATED_REQUIRED')
root=Path(__file__).absolute().parents[2]
module=types.ModuleType('source_guard_under_test');exec(compile((root/'tests/control_mux/source_runner.py').read_bytes(),'<source-guard>','exec'),module.__dict__)

def git(folder,*args,input=None):return subprocess.run(['git','--no-replace-objects','-C',str(folder),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

def repo(parent,name):
    folder=parent/name;folder.mkdir();git(folder,'init')
    file=folder/'poc.py';file.write_bytes(b"MARKER='clean'\n")
    git(folder,'add','poc.py');git(folder,'-c','user.name=ControlMuxFixture','-c','user.email=fixture@example.invalid','-c','core.hooksPath=disabled-fixture-hooks','commit','-m','inert fixture')
    assert (folder/'.git').is_dir() and git(folder,'rev-parse','--git-common-dir').strip()==b'.git'
    head=git(folder,'rev-parse','HEAD').decode().strip();assert module.source_receipt(folder,head)
    return folder,file,head

def deny(folder,head):
    try:module.source_receipt(folder,head)
    except (AssertionError,OSError):return
    raise AssertionError('SOURCE_NEGATIVE_ACCEPTED')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.scratch.mkdir(parents=True,exist_ok=False);cases=[]
    folder,file,head=repo(a.scratch,'shadow');(folder/'jsonschema.py').write_bytes(b"MARKER='inert-shadow'\n");deny(folder,head);cases.append('UNTRACKED_IMPORT_SHADOW_REJECTED')
    folder,file,head=repo(a.scratch,'cache');clean=file.read_bytes();stamp=file.stat();file.write_bytes(b"MARKER='other'\n");os.utime(file,ns=(stamp.st_atime_ns,stamp.st_mtime_ns));py_compile.compile(str(file),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP);file.write_bytes(clean);os.utime(file,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    assert file.read_bytes()==git(folder,'show',head+':poc.py')
    observed=subprocess.check_output([sys.executable,'-I','-B','-c','import sys;sys.path.insert(0,sys.argv[1]);import poc;print(poc.MARKER)',str(folder)],text=True).strip();assert observed=='other','MATCHED_CACHE_NOT_REPRODUCED'
    deny(folder,head);cases.append('TIMESTAMP_SIZE_MATCHED_BYTECODE_EXECUTION_REPRODUCED_THEN_REJECTED')
    folder,file,head=repo(a.scratch,'hidden');git(folder,'update-index','--assume-unchanged','poc.py');file.write_bytes(b"MARKER='other'\n");deny(folder,head);cases.append('HIDDEN_INDEX_BIT_DOES_NOT_HIDE_RAW_CHANGE')
    folder,file,head=repo(a.scratch,'blob');old=git(folder,'rev-parse',head+':poc.py').decode().strip();replacement=b"MARKER='other'\n";new=git(folder,'hash-object','-w','--stdin',input=replacement).decode().strip();git(folder,'replace',old,new);file.write_bytes(replacement);deny(folder,head);cases.append('BLOB_REPLACE_CANNOT_OVERRIDE_RAW_PIN')
    folder,file,head=repo(a.scratch,'tree');old=git(folder,'rev-parse',head+'^{tree}').decode().strip();new=git(folder,'mktree',input=b'').decode().strip();git(folder,'replace',old,new);file.unlink();deny(folder,head);cases.append('TREE_REPLACE_CANNOT_HIDE_MISSING_SOURCE')
    folder,file,head=repo(a.scratch,'crlf');file.write_bytes(file.read_bytes().replace(b'\n',b'\r\n'));deny(folder,head);cases.append('CRLF_ALIAS_REJECTED')
    folder,file,head=repo(a.scratch,'prefix');previous=sys.pycache_prefix
    try:sys.pycache_prefix=str(a.scratch/'foreign-prefix');deny(folder,head)
    finally:sys.pycache_prefix=previous
    cases.append('PYCACHE_PREFIX_REJECTED')
    folder,file,head=repo(a.scratch,'link-target');link=a.scratch/'linked-source'
    if sys.platform=='win32':
        # Only an owned temporary junction; never touch a service or security setting.
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(folder)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    else:link.symlink_to(folder,target_is_directory=True)
    deny(link,head);cases.append('ANCESTOR_LINK_OR_REPARSE_REJECTED')
    report=dict(scope='INERT_INDEPENDENT_GIT_FIXTURES_ONLY',cases=cases,result='PASS',cached_marker=observed,production='NO_GO')
    a.output.write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report))
