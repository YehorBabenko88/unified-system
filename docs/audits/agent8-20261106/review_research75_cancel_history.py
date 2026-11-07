import pathlib,subprocess
r=pathlib.Path.cwd();repo=r/'work/review-research75-aed8';o=r/'outputs/phase88';old=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'show','f3d2877ac5e7af6f89586fcdb184974b494e46ac:strattester/research/gateway_adapter.py']);private=r/'work/research75-a8-temp/old-cancel-source.py';private.write_bytes(old)
s='''import pathlib,types,sys,importlib.util,json,hashlib
oldraw=pathlib.Path(sys.argv[1]).read_bytes();old=types.ModuleType('a8_old_cancel_only');exec(compile(oldraw,'<primary-old-f3d-cancel>','exec'),old.__dict__)
spec=importlib.util.spec_from_file_location('a8_current_cancel_only',pathlib.Path.cwd()/'strattester/research/gateway_adapter.py');new=importlib.util.module_from_spec(spec);spec.loader.exec_module(new)
results=[]
for name,module in [('old_f3d',old),('current_aed',new)]:
 effects=[]
 class Pause:
  def __await__(self):yield 'OWN_SUSPENDED'
 async def foreign():
  try:await Pause()
  finally:effects.append('OWN_CREATOR_FINALLY')
 c=foreign();c.send(None)
 try:
  try:module._cancel(lambda:c);raise AssertionError('NONBOOL_ACCEPTED')
  except module.GatewayResearchError:pass
  before_owner_close=list(effects)
 finally:c.close()
 assert len(effects)==1;assert before_owner_close==(['OWN_CREATOR_FINALLY'] if name=='old_f3d' else [])
 results.append(dict(source=name,finally_effects_before_creator_disposal=before_owner_close,finally_effects_after_creator_disposal=list(effects)))
print(json.dumps(dict(scope='OWN_SUSPENDED_COROUTINE_CANCEL_META_PROBE_ONLY_NO_AUTH_LEASE_NATIVE',old_primary_source_sha256=hashlib.sha256(oldraw).hexdigest(),cases=results,old_counterexample_reproduced=True,current_creator_only_disposal_verified=True),indent=2))
''';(o/'cancel-red-green-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',s,str(private)],cwd=repo,capture_output=True,timeout=30);(o/'cancel-red-green.stdout.json').write_bytes(p.stdout);(o/'cancel-red-green.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
