import pathlib,types,sys,importlib.util,json,hashlib
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
