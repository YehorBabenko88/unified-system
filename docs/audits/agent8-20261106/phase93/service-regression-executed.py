import pathlib,sys,os,json,subprocess
root=pathlib.Path.cwd();sys.path.insert(0,str(root));parent=pathlib.Path(sys.argv[1]);red=parent/'red-cwd';green=parent/'green-cwd';tmp=parent/'green-tmp';
for p in (red,green,tmp):p.mkdir()
def blocked(*a,**k):raise AssertionError('A8_REAL_PROCESS_FORBIDDEN')
subprocess.run=blocked;subprocess.Popen=blocked
old=bytes.fromhex(sys.argv[2]);new=(root/'tests/runtime/test_service_manager.py').read_bytes()
for label,source,cwd in [('old',old,red),('new',new,green)]:
 namespace={};exec(compile(source,label,'exec'),namespace);os.chdir(cwd)
 if label=='old':namespace['test_manager_targets_only_worker']()
 else:namespace['test_manager_targets_only_worker'](tmp)
os.chdir(root)
assert sorted(p.name for p in (red/'state').iterdir())==['worker-control.sqlite3','worker-intent.json']
assert not (green/'state').exists() and not (root/'state/worker-intent.json').exists() and not (root/'state/worker-control.sqlite3').exists()
assert json.loads((tmp/'state/worker-intent.json').read_bytes())=={'schema':1,'desired':'running'}
print(json.dumps(dict(original_test_default_cwd_state_created=True,current_test_explicit_tmp_state_only=True,real_process_calls=0,actual_original_test_function_executed=True,full_pytest=False)))
