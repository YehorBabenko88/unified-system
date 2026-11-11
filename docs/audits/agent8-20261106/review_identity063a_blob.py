import pathlib,subprocess,os,json,zlib,hashlib
r=pathlib.Path.cwd();o=r/'outputs/phase86';rows=[]
for label,seed,head in [('old2cb','review-identity2cb6','2cb6b21eac5617ff39ad7a96b7e1c73118e0af00'),('final063','review-identity063a','063a004770a6d98ba78de7bbd5d4aadcc752ed55')]:
 repo=r/'work'/('identity-a8-corrupt-blob-'+label);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(r/'work'/seed),str(repo)],capture_output=True,check=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],capture_output=True,check=True)
 name='unified_system/gateway_identity.py';oid=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse',head+':'+name]).decode().strip();target=repo/name;changed=target.read_bytes()+b'\n# A8 inert primary-blob identity mismatch fixture\n';changed_oid=hashlib.sha1(b'blob '+str(len(changed)).encode()+b'\0'+changed).hexdigest();assert changed_oid!=oid
 objectfile=repo/'.git/objects'/oid[:2]/oid[2:];assert objectfile.resolve().is_relative_to((repo/'.git/objects').resolve());objectfile.parent.mkdir(exist_ok=True)
 if objectfile.exists():objectfile.chmod(0o600)
 objectfile.write_bytes(zlib.compress(b'blob '+str(len(changed)).encode()+b'\0'+changed));target.write_bytes(changed)
 assert subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'cat-file','blob',oid])==changed
 env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env['PYTHONDONTWRITEBYTECODE']='1';p=subprocess.run([str(r/'work/identity-a8-env/Scripts/python.exe'),'-I','-B',str(repo/'docs/intelligence/identity/run_qualification.py'),'--expected-head',head],cwd=repo,env=env,capture_output=True,timeout=90);(o/('corrupt-blob-'+label+'.stdout.log')).write_bytes(p.stdout);(o/('corrupt-blob-'+label+'.stderr.log')).write_bytes(p.stderr)
 if label=='old2cb':assert p.returncode==0 and json.loads(p.stdout)['tests']==24
 else:assert p.returncode!=0 and b'Ran 24' not in p.stderr
 rows.append(dict(source=head,label=label,nominal_blob_oid=oid,actual_blob_oid=changed_oid,catfile_nominal_oid_returned_matching_altered_bytes=True,qualifier_exit=p.returncode,tests_executed=24 if label=='old2cb' else 0,result='FALSE_SOURCE_QUALIFICATION_PASS' if label=='old2cb' else 'REJECTED_BEFORE_TEST_IMPORTS'))
(o/'primary-blob-negative-recheck.json').write_text(json.dumps(dict(scope='EXISTING_F16_APPLICABLE_GUARD_VECTOR_ONLY_NOT_NATIVE_AUTH_BYPASS',fixtures=rows,production_or_shared_source_modified=False),indent=2),encoding='utf-8');print('ownlooseblobtamper: old2cb false-sourcePASS24; final063rejected before0tests')
