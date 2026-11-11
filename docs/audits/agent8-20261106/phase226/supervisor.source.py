"""One authorized pure modeled regression attempt; no project/qualifier import."""
import pathlib,os,stat,hashlib,json,subprocess,time,traceback,sys
BASE=pathlib.Path(__file__).absolute().parent
ROOT=BASE.parent/'work/projection-recovery-hosted47-20261110'
REAL=pathlib.Path('C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe')
TEST=ROOT/'docs/gateway/research/persistence/qualification47/test_qualifier_controls.py'
OUT=BASE/'hosted47-modeled28-f50-red-20261111-attempt1'
LIMIT=256*1024
def ordinary(path, leaf=False):
    path=path.absolute()
    parts=path.parts;cur=pathlib.Path(parts[0])
    for index,part in enumerate(parts):
        if index:cur=cur/part
        s=os.lstat(cur)
        need_file=leaf and index==len(parts)-1
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&1024:
            raise RuntimeError('Unsafe ancestry; stop before descendant reads')
        if not (stat.S_ISREG(s.st_mode) if need_file else stat.S_ISDIR(s.st_mode)):
            raise RuntimeError('Nonordinary path; stop before descendant reads')
    return path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
ordinary(BASE);ordinary(ROOT);ordinary(REAL,True)
if sha(REAL)!='4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a':raise RuntimeError('Interpreter drift')
ordinary(BASE/'hosted47-mandatory20-wiring-source-receipt-20261110.json',True)
receipt=json.loads((BASE/'hosted47-mandatory20-wiring-source-receipt-20261110.json').read_bytes())
approved={f['path']:f['sha256'] for f in receipt['files']}
approved[TEST.relative_to(ROOT).as_posix()]='3f7be88ebb61d20627585be4894fb116cf28dffc04fdfd1d44829146aa3bd69a'
before={}
for rel,expected in approved.items():
    p=ordinary(ROOT/rel,True);before[rel]={'sha256':sha(p),'bytes':p.stat().st_size}
    if before[rel]['sha256']!=expected:raise RuntimeError('Approved source drift')
if OUT.exists():raise RuntimeError('Attempt already claimed; no retry')
OUT.mkdir();ordinary(OUT)
record={'scope':'MODELED_REGRESSION_ACTUAL_AST_DEFINITIONS_INERT_BACKENDS_NOT47_OR_NATIVE',
        'allocation':'ROOT.A7.F50.MODELED28.RED.ONCE_MCI97','pre':before,'python_sha256':sha(REAL),'child':None,'errors':[],
        'controller_preflight':{'own_test_controllers_active':0,'shared_lane_attribution':'Root reports MODELED11 lane retired and MCI97 allocation; no global OS scan or physical action'}}
child=None;started=None;failure=None
try:
    with (OUT/'stdout.log').open('xb') as stdout,(OUT/'stderr.log').open('xb') as stderr:
        started=time.monotonic()
        child=subprocess.Popen([str(REAL),'-I','-S','-B',str(TEST)],cwd=OUT,
                               stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        record['child']={'pid':child.pid,'identity':'OWN_POPEN_HANDLE','command_flags':['-I','-S','-B']}
        while child.poll() is None:
            size=(OUT/'stdout.log').stat().st_size+(OUT/'stderr.log').stat().st_size
            if size>LIMIT:
                record['output_limit_exceeded']=True;break
            if time.monotonic()-started>=13:
                record['execution_deadline_reached']=True;break
            time.sleep(0.01)
        if child.poll() is None:
            child.kill();record['cleanup_kill_required']=True
        child.wait(timeout=max(0.01,15-(time.monotonic()-started)))
        record['child'].update(exit_code=child.returncode,retired=child.poll() is not None)
except BaseException:
    failure=traceback.format_exc();record['errors'].append(failure)
finally:
    if child is not None:
        try:
            if child.poll() is None:
                child.kill();record['cleanup_kill_required']=True
                child.wait(timeout=max(0.01,15-(time.monotonic()-started)))
            record['child'].update(exit_code=child.poll(),retired=child.poll() is not None)
        except BaseException:record['errors'].append(traceback.format_exc());record['retirement']='UNKNOWN'
    record['child_observed_seconds']=None if started is None else time.monotonic()-started
    after={}
    for rel in approved:
        try:
            p=ordinary(ROOT/rel,True);after[rel]={'sha256':sha(p),'bytes':p.stat().st_size}
        except BaseException:record['errors'].append(traceback.format_exc())
    record['post']=after;record['all_six_unchanged']=after==before
    record['original_five_unchanged']=all(after.get(rel)==before[rel] for rel in approved if rel!=TEST.relative_to(ROOT).as_posix())
    record['outputs']={}
    for name in ('stdout.log','stderr.log'):
        p=OUT/name
        if p.exists():record['outputs'][name]={'bytes':p.stat().st_size,'sha256':sha(p)}
    record['output_bytes']=sum(x['bytes'] for x in record['outputs'].values())
    record['within_output_limit']=record['output_bytes']<=LIMIT
    (OUT/'receipt.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,indent=2))
for name in ('stdout.log','stderr.log'):
    p=OUT/name
    if p.exists():print(name+':\n'+p.read_bytes()[:LIMIT].decode('utf-8',errors='replace'))
sys.exit(1 if record['errors'] or not record['all_six_unchanged'] or not record['within_output_limit'] else 0)
