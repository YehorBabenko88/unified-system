import hashlib, io, json, os, pathlib, stat, subprocess, sys, unittest
root=pathlib.Path.cwd().resolve()
output=pathlib.Path(os.environ['RUNNER_TEMP'])/'node-supervisor-v2'
output.mkdir(exist_ok=True)
assert not output.is_relative_to(root)
assert sys.version_info[:3]==(3,12,10)
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sys.pycache_prefix is None
git=pathlib.Path('C:/Program Files/Git/cmd/git.exe' if sys.platform=='win32' else '/usr/bin/git')
git_hash=hashlib.sha256(git.read_bytes()).hexdigest()
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
def g(*args, input=None):
    assert hashlib.sha256(git.read_bytes()).hexdigest()==git_hash
    return subprocess.check_output([str(git),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,*args],cwd=root,env=env,input=input,timeout=30)
assert g('rev-parse','HEAD').decode().strip()==os.environ['EXPECTED_HEAD']
assert not g('for-each-ref','--format=%(refname)','refs/replace').strip()
def source():
    assert g('rev-parse','HEAD').decode().strip()==os.environ['EXPECTED_HEAD']
    assert not g('for-each-ref','--format=%(refname)','refs/replace').strip()
    assert not g('status','--porcelain','--untracked-files=all').strip()
    entries=[]
    for row in g('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
        if not row: continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.split()
        assert mode in (b'100644',b'100755') and kind==b'blob'
        relative=pathlib.Path(name.decode())
        assert not relative.is_absolute() and '..' not in relative.parts
        entries.append((relative.as_posix(),mode.decode(),oid.decode()))
    stream=io.BytesIO(g('cat-file','--batch',input=''.join(oid+'\n' for _,_,oid in entries).encode()))
    files={}
    for name,mode,oid in entries:
        actual,kind,size=stream.readline().split(); data=stream.read(int(size))
        assert actual.decode()==oid and kind==b'blob' and stream.read(1)==b'\n'
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
        target=root/name
        for parent in (*reversed(target.parents),target):
            facts=parent.lstat()
            assert not stat.S_ISLNK(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&1024
        assert target.is_file() and target.read_bytes()==data
        files[name]=dict(mode=mode,blob_oid=oid,sha256=hashlib.sha256(data).hexdigest())
    assert not stream.read()
    for item in root.rglob('*'):
        relative=item.relative_to(root)
        if '.git' in relative.parts: continue
        facts=item.lstat()
        assert not stat.S_ISLNK(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&1024
        assert item.suffix not in ('.pyc','.pyo') and item.name!='__pycache__'
        if item.is_file(): assert relative.as_posix() in files
    return dict(head=os.environ['EXPECTED_HEAD'],tree=g('rev-parse','HEAD^{tree}').decode().strip(),files=files)
before=source()
(output/'source-before.json').write_text(json.dumps(before,sort_keys=True),encoding='utf8')
sys.path.insert(0,str(root))
loader=unittest.TestLoader()
suite=unittest.TestSuite(loader.discover(str(root/'tests'),pattern=p) for p in ('test_node_task_journal.py','test_node_supervisor_v2.py'))
def ids(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite): yield from ids(test)
        else: yield test.id()
test_ids=list(ids(suite))
with (output/'tests.log').open('w',encoding='utf8') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
after=source()
receipt=dict(schema='unified.node-supervisor-qualification.v1',head=os.environ['EXPECTED_HEAD'],tree=before['tree'],python=sys.version,platform=sys.platform,git_sha256=git_hash,tests=test_ids,count=result.testsRun,skips=len(result.skipped),errors=len(result.errors),failures=len(result.failures),source_after=after,physical_acceptance='NOT_RUN',native_authority='UNAVAILABLE')
(output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True),encoding='utf8')
print((output/'tests.log').read_text(encoding='utf8'))
assert before==after and result.wasSuccessful() and result.testsRun==30 and len(test_ids)==len(set(test_ids))==30 and not result.skipped
