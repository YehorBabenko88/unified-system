import pathlib,subprocess,os,json,hashlib,io,struct
r=pathlib.Path.cwd();repo=r/'work/review-worker51-480';o=r/'outputs/phase91';o.mkdir(exist_ok=True);head='480109277c1e80a666f3dbba84b5807cacd2b460';base='3e498de973536c2d6393f83abe7d59cb1452a9b4'
if not repo.exists():subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(r/'work/unified-audit'),str(repo)],check=True,capture_output=True)
subprocess.run(['git','-c','core.autocrlf=false','-c','core.eol=lf','-C',str(repo),'checkout','--detach',head],check=True,capture_output=True)
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
def inventory():
 rows=[]
 for row in g('ls-tree','-rz','HEAD').split(b'\0'):
  if row:
   meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
 s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));result={}
 for name,oid in rows:
  actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;result[name]=hashlib.sha256(b).hexdigest()
 for p in repo.rglob('*'):
  rel=p.relative_to(repo)
  if rel.parts[0]!='.git' and p.is_file():assert rel.as_posix() in result
 return result
before=inventory();assert len(before)==1400
p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',"import sys,unittest;sys.path.insert(0,'.');s=unittest.defaultTestLoader.discover('tests/gateway_jobs',pattern='test_worker_limits.py');r=unittest.TextTestRunner(verbosity=2).run(s);assert r.testsRun==5 and r.wasSuccessful() and not r.skipped"],cwd=repo,capture_output=True,timeout=30);(o/'unit5.stdout.log').write_bytes(p.stdout);(o/'unit5.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;assert inventory()==before
owner=r.parent/'codex-agent-5-resource-aware-distributed/outputs/AGENT5-WORKER-4801092';b=(owner/'receipt.json').read_bytes();assert hashlib.sha256(b).hexdigest()=='d3470fdcba3252e568b5ee8a28747b2df69d19f6973ada25141012726486825d';(o/'owner-receipt.original.json').write_bytes(b);d=json.loads(b);assert all(before[name]==sha for name,sha in d['source_hashes'].items());observations=[]
for row in d['actual_owned_windows_probes']:
 mode=row['mode'];raw=(owner/(mode+'.stdout')).read_bytes();assert json.loads(raw)==row['observation'];(o/('owner-'+mode+'.stdout.json')).write_bytes(raw);v=row['observation']
 if mode!='bad_profile':
  rd=v['limit_readback_before_resume'];ex=bytes.fromhex(rd['extended_readback_hex']);cpu=bytes.fromhex(rd['cpu_readback_hex']);assert len(ex)==144 and len(cpu)==8;assert struct.unpack_from('<I',ex,16)[0]==8712 and struct.unpack_from('<I',ex,40)[0]==8 and struct.unpack_from('<Q',ex,120)[0]==268435456 and struct.unpack('<II',cpu)==(5,1000);assert rd['job_membership_verified'] is True
 if mode=='memory':
  m=bytes.fromhex(v['memory_accounting_struct_hex']);assert len(m)==144 and struct.unpack_from('<Q',m,136)[0]==v['native_peak_job_committed_bytes']==544940032 and struct.unpack_from('<Q',m,128)[0]==v['native_peak_process_memory_bytes']==543735808;assert v['peak_exceeds_configured_limit'] and not v['memory_limit_cause_and_peak_semantics_qualified']
 observations.append(dict(mode=mode,owner_stdout_sha256=hashlib.sha256(raw).hexdigest(),original_observation_verified=True))
gridraw=subprocess.check_output(['git','--no-replace-objects','-C',str(r/'work/read815-a8-grid-f19'),'show','40e9c8dc274a2746018bc1aa08d103cd0187cecc:grid/ml_windows_job.py']);assert hashlib.sha1(b'blob '+str(len(gridraw)).encode()+b'\0'+gridraw).hexdigest()=='f30a09a3af647518d69f7787879defc4d5fa8ab5';assert hashlib.sha256(gridraw).hexdigest()=='7fd6223de3e28052b1254fa9e33e638132c6db89388bbb2d994b35970802a25c';(o/'grid-primary-source.py').write_bytes(gridraw)
result=dict(head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),base=base,delta=g('diff','--name-status',base,head).decode().splitlines(),tests_A8=5,skips=0,primary_raw_prepost=1400,owner_receipt_sha256=hashlib.sha256(b).hexdigest(),owner_observations=observations,A8_actual_native_probes=0,scope='SOURCE_UNIT_AND_ORIGINAL_RECEIPT_INTEGRITY_NOT_NATIVE_RESOURCE_ADMISSION',source_raw=before)
(o/'primary-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='source_raw'}))
