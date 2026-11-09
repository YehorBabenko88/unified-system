import pathlib,subprocess,os
r=pathlib.Path.cwd();repo=r/'work/review-target8dc';o=r/'outputs/phase101';scratch=r/'work/target8dc-a8-audit2';scratch.mkdir(exist_ok=True)
s='''import pathlib,sys,json,os,sqlite3,socket,subprocess
sys.path.insert(0,'.');from unified_system.gateway_target_adapter import DisposableTargetStand,prepare_target,template_request
root=pathlib.Path(sys.argv[1]);standroot=root/'stand';standroot.mkdir();stratt=pathlib.Path(os.environ['TARGET_STRATT_ROOT']);meta=pathlib.Path(os.environ['TARGET_META_ROOT']);stand=DisposableTargetStand(standroot,stratt_source_root=str(stratt),meta_source_root=str(meta));ctx=stand.local_test_context();raw=json.dumps(template_request(),sort_keys=True,separators=(',',':')).encode()
state={'active':False,'calls':[]};journal=standroot/'direct-journal.db';dbs={str(journal),journal.resolve().as_uri()+'?mode=ro'};lib=pathlib.Path(sys.base_prefix).resolve()
def beneath(p,base):return p==base or base in p.parents
def audit(event,args):
 if not state['active']:return
 if event=='open' and not isinstance(args[0],int):
  p=pathlib.Path(os.fspath(args[0])).resolve();flags=args[2];writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND));allowed=beneath(p,standroot) if writing else beneath(p,standroot) or beneath(p,lib) or beneath(p,meta/'src/meta_analyse')
  if not allowed:raise RuntimeError('A8_FILE_EFFECT_DENIED')
  state['calls'].append({'event':event,'writing':writing,'path':str(p)})
 elif event=='sqlite3.connect':
  if os.fspath(args[0]) not in dbs:raise RuntimeError('A8_SQLITE_DENIED')
  state['calls'].append({'event':event,'database':os.fspath(args[0])})
 elif event=='subprocess.Popen':
  command=args[1];prefix=['git','--no-replace-objects','-C',str(stratt),'show'];allowed_commands=[prefix+[x] for x in ['aed8a7c8a952f96803c207d5e90b133969a47f04:strattester/research/gateway_adapter.py','aed8a7c8a952f96803c207d5e90b133969a47f04:docs/gateway/research/evidence/btc-v1/request.json']];allowed=command in (allowed_commands if type(command) is list else [subprocess.list2cmdline(x) for x in allowed_commands])
  if not allowed:raise RuntimeError('A8_PROCESS_DENIED')
  state['calls'].append({'event':event,'command':command})
 elif event in ['socket.connect','socket.getaddrinfo','socket.sendto','os.system']:
  raise RuntimeError('A8_NETWORK_OR_SHELL_DENIED')
sys.addaudithook(audit);state['active']=True;cal=[]
for name,fn in [('read',lambda:open(root/'outside-never-read','rb')),('write',lambda:open(root/'outside-never-created','wb')),('sqlite_sibling',lambda:sqlite3.connect(str(standroot)+'-sibling.db')),('sqlite_dotdot',lambda:sqlite3.connect(standroot/'..'/'outside.db')),('sqlite_uri_rwc',lambda:sqlite3.connect(journal.resolve().as_uri()+'?mode=rwc',uri=True)),('process',lambda:subprocess.Popen(['A8_INERT_NEVER_CREATED']))]:
 try:fn()
 except RuntimeError:cal.append(name)
 else:raise AssertionError('CALIBRATION_NOT_DENIED:'+name)
with socket.socket() as sock:
 try:sock.connect(('127.0.0.1',9))
 except RuntimeError:cal.append('network')
 else:raise AssertionError('NETWORK_CALIBRATION')
# Positive allowlist calibration executes real own read and SQLite SELECT.
with open(standroot/'stand.marker','rb') as stream:assert stream.read()
con=sqlite3.connect(journal);con.execute('SELECT 1').fetchone();con.close();state['calls'].clear()
result=stand.execute(prepare_target(raw),context=ctx);state['active']=False
assert result['status']=='DIRECT_TARGET_PASS' and stand.invocations==1 and not (root/'outside-never-created').exists()
assert len([x for x in state['calls'] if x['event']=='subprocess.Popen'])==2 and any(x['event']=='sqlite3.connect' for x in state['calls'])
stand.close();print(json.dumps({'actual_target':'DIRECT_TARGET_PASS','invocations':1,'positive_read_SQLite_calibrated':True,'negative_calibrations':cal,'observed_calls':state['calls'],'scope':'PYTHON_AUDIT_EFFECTS_ONLY_NOT_NATIVE_EGRESS_SANDBOX'},indent=2))
'''
(o/'own-effect-observer-executed.py').write_text(s);env=os.environ.copy();env.update(TARGET_STRATT_ROOT=str(r/'work/review-research75-aed8'),TARGET_META_ROOT=str(r/'work/research75-a8-temp/gateway-meta-source-f3c'));p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s,str(scratch)],cwd=repo,env=env,capture_output=True,timeout=45);(o/'own-effect-observer.stdout.json').write_bytes(p.stdout);(o/'own-effect-observer.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print('actual target passed with independently calibrated Python audit IO/process/network observer')
