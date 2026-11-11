import hashlib,io,json,os,pathlib,subprocess,sys,unittest
root=pathlib.Path.cwd()
git=pathlib.Path('C:/Program Files/Git/cmd/git.exe' if sys.platform=='win32' else '/usr/bin/git')
def g(*args):
    return subprocess.check_output([str(git),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=root)
assert sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None
assert g('rev-parse','HEAD').decode().strip()==os.environ['EXPECTED_HEAD']
def receipt():
    entries=[]
    for row in g('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
        if not row: continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.split()
        assert mode in (b'100644',b'100755') and kind==b'blob'
        entries.append((name.decode(),oid.decode()))
    raw=subprocess.check_output([str(git),'--no-replace-objects','cat-file','--batch'],cwd=root,input=''.join(oid+'\n' for _,oid in entries).encode())
    stream=io.BytesIO(raw);result={}
    for name,oid in entries:
        actual,kind,size=stream.readline().split();data=stream.read(int(size))
        assert actual.decode()==oid and kind==b'blob' and stream.read(1)==b'\n'
        path=root/name
        assert path.is_file() and not path.is_symlink() and path.read_bytes()==data
        result[name]=hashlib.sha256(data).hexdigest()
    for path in root.rglob('*'):
        rel=path.relative_to(root)
        if '.git' in rel.parts: continue
        assert not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&1024)
        if path.is_file(): assert rel.as_posix() in result and path.suffix not in ('.pyc','.pyo')
    return result
before=receipt()
sys.path.insert(0,str(root))
loader=unittest.TestLoader();suite=unittest.TestSuite(loader.discover(str(root/'tests'),pattern=p) for p in ['test_lan_transport.py','test_network_budget.py','test_lan_mux_channel.py'])
ids=[]
def collect(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite): collect(item)
        else: ids.append(item.id())
collect(suite);assert len(ids)==len(set(ids))==50
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun==50 and not result.skipped
assert before==receipt()
out=pathlib.Path(os.environ['RUNNER_TEMP'])/'lan-mux-integrated-evidence.json'
out.write_text(json.dumps({'head':os.environ['EXPECTED_HEAD'],'tests':ids,'skips':0,'source_sha256':before,'qualification':'LOOPBACK_LAN_MUX_COMPONENT_ONLY','native_admission':False,'installation_admission':False},indent=2)+'\n',encoding='utf-8')
