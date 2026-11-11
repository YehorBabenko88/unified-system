import pathlib,subprocess,json,hashlib,zlib,ast,traceback
r=pathlib.Path.cwd();o=r/'outputs/phase86';rows=[]
for label,folder in [('old2cb','review-identity2cb6'),('final063','review-identity063a')]:
 repo=r/'work'/('identity-a8-loose-fixture-'+label);repo.mkdir(exist_ok=False);subprocess.run(['git','init','-q',str(repo)],check=True,capture_output=True);(repo/'tracked.txt').write_bytes(b'original\n');subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','add','tracked.txt'],check=True,capture_output=True);subprocess.run(['git','-C',str(repo),'-c','user.name=A8','-c','user.email=a8@example.invalid','-c','core.hooksPath=NUL','commit','-qm','inert fixture'],check=True,capture_output=True)
 helper=r/'work'/folder/'docs/intelligence/identity/run_qualification.py';raw=helper.read_bytes();tree=ast.parse(raw);selected=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]);ns={'root':repo};exec(compile(selected,str(helper),'exec'),ns)
 def inventory():return ns['inventory']() if label=='old2cb' else ns['inventory'](repo)
 clean=inventory();assert len(clean)==1
 oid=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse','HEAD:tracked.txt']).decode().strip();changed=b'inert changed\n';obj=repo/'.git/objects'/oid[:2]/oid[2:];assert obj.resolve().is_relative_to((repo/'.git/objects').resolve());obj.chmod(0o600);obj.write_bytes(zlib.compress(b'blob '+str(len(changed)).encode()+b'\0'+changed));(repo/'tracked.txt').write_bytes(changed);actual=hashlib.sha1(b'blob '+str(len(changed)).encode()+b'\0'+changed).hexdigest();assert actual!=oid
 if label=='old2cb':assert inventory()['tracked.txt']==hashlib.sha256(changed).hexdigest();status='INVALID_PRIMARY_OBJECT_ACCEPTED_BY_ACTUAL_OLD_INVENTORY'
 else:
  try:inventory();raise RuntimeError('INVALID_OID_ACCEPTED')
  except AssertionError:(o/'loose-blob-final-rejection.log').write_text(traceback.format_exc(),encoding='utf-8')
  status='REJECTED_BY_ACTUAL_FINAL_INVENTORY'
 rows.append(dict(label=label,source_helper_sha256=hashlib.sha256(raw).hexdigest(),clean_positive=1,nominal_oid=oid,actual_changed_oid=actual,result=status,tests_executed=0))
(o/'primary-blob-negative-recheck.json').write_text(json.dumps(dict(scope='ACTUAL_GUARD_FUNCTION_ON_OWN_MINIMAL_UNPACKED_GIT_FIXTURE_NOT_NATIVE_AUTH_OR24TESTS',fixtures=rows,full_repo_initial_probe='OLD_FULL_PACKED_CLONE_RAW_MISMATCH_REJECTED_BEFORE_TESTS_RETAINED_SEPARATELY',global_F16='OPEN'),indent=2),encoding='utf-8');print('actualguard minimalunpacked control:old accepts invalidOID/new063rejects;0native/tests')
