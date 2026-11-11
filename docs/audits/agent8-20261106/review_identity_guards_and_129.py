"""Independent exact composed workflow and pure identity-record seam review."""
import ast,hashlib,json,os,pathlib,subprocess,textwrap,uuid
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/review-integration75';out=r/'outputs/phase35';out.mkdir(exist_ok=True)
composed='237722bb1d5c8bc671a498609729261bdd3c9fce';head='cc286bce5e51e3670bd8a6cdfd3b663307268703';prior='18085568df01bdbc4df74404e3c650ec30bb7d6b'
def git(repo,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args])
def read(ref,path):return git(seed,'show',ref+':'+path)
assert git(seed,'rev-parse',composed+'^{tree}').decode().strip()=='0bc635d822a3702e43b45fbd513a8e0bf2cb3ab6'
assert git(seed,'rev-parse',head+'^{tree}').decode().strip()=='6255c0620a4257d7f8fd82e0fee5d944e052a1b6'
for label,owner in [('lan','1541af3b0e99fdb671f59c205696faab40e283e4'),('storage','10157fed4d28606adf587be3494d2f6d42887ce9')]:
 metadata=json.loads((r/'outputs/phase31'/label/'primary-pr.json').read_text())
 for item in metadata['files']:assert read(composed,item['path'])==read(owner,item['path']),item['path']
inv=json.loads(read(composed,'release/component-test-inventory.json'));old=json.loads(read(prior,'release/component-test-inventory.json'))
assert inv['expected_count']==129 and len(inv['expected_test_ids'])==len(set(inv['expected_test_ids']))==129
assert inv['preserved_prior_ids']==old['expected_test_ids'] and len(inv['preserved_prior_ids'])==75
for module in old['modules']:
 path=module.replace('.','/')+'.py';assert read(prior,path)==read(composed,path),path
code=textwrap.dedent(read(composed,'.github/workflows/final-integration.yml').decode().split('        shell: python\n        run: |\n',1)[1].split('      - uses:',1)[0]);assert "source_git = ['git', '--no-replace-objects']" in code
owner_receipt=json.loads(read(head,'release/evidence/runtime-129-237722b/partial-integration-ci-evidence.json'))
assert owner_receipt['head']==composed and owner_receipt['tree']=='0bc635d822a3702e43b45fbd513a8e0bf2cb3ab6' and owner_receipt['tests']==129 and owner_receipt['failures']==owner_receipt['errors']==owner_receipt['skipped']==0
assert owner_receipt['source_before']==owner_receipt['source_after'] and sorted(owner_receipt['mandatory_test_ids'])==inv['expected_test_ids']
ownerlog=read(head,'release/evidence/runtime-129-237722b/partial-integration-ci-tests.log');assert hashlib.sha256(ownerlog).hexdigest()==owner_receipt['test_log_sha256']
for path,entry in owner_receipt['source_before']['files'].items():
 raw=read(composed,path);assert hashlib.sha256(raw).hexdigest()==entry['raw_sha256']==entry['blob_sha256'] and git(seed,'rev-parse',composed+':'+path).decode().strip()==entry['git_blob']
(out/'owner-original-receipt.json').write_text(json.dumps(owner_receipt,indent=2));(out/'owner-original-tests.log').write_bytes(ownerlog)
def clone(label,sha):
 p=r/'work'/('identity-129-'+label+'-'+uuid.uuid4().hex[:8]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(p)],check=True,capture_output=True);subprocess.run(['git','-C',str(p),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',sha],check=True,capture_output=True)
 assert (p/'.git').is_dir() and not (p/'.git/objects/info/alternates').exists();assert (p/git(p,'rev-parse','--git-common-dir').decode().strip()).resolve()==(p/'.git').resolve();return p
def identity(p,sha):
 rows={}
 for item in filter(None,git(p,'ls-tree','-rz',sha).split(b'\0')):
  meta,name=item.split(b'\t',1);raw=(p/name.decode()).read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==meta.split()[2].decode();rows[name.decode()]=hashlib.sha256(raw).hexdigest()
 return dict(files=len(rows),sha256=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())
def run(p,label,script,envextra=None):
 env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(PYTHONDONTWRITEBYTECODE='1',**(envextra or {}));temp=r/'work'/('identity-temp-'+uuid.uuid4().hex[:8]);temp.mkdir();env.update(TEMP=str(temp),TMP=str(temp))
 boot="import sys,os,ipaddress\nsys.path[:0]=[os.getcwd(),"+repr(str(r/'work/integration-review-deps'))+"]\ndef a8guard(event,args):\n if event in ('socket.connect','socket.bind') and (not isinstance(args[1],tuple) or not ipaddress.ip_address(args[1][0]).is_loopback):raise RuntimeError('A8_NONLOOPBACK_DENIED')\nsys.addaudithook(a8guard)\n"
 result=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',boot+script],cwd=p,env=env,capture_output=True,timeout=120);(out/(label+'.stdout.log')).write_bytes(result.stdout);(out/(label+'.stderr.log')).write_bytes(result.stderr);assert result.returncode==0,(label,result.stderr.decode(errors='replace')[-2000:])
p=clone('composed',composed);before=identity(p,composed);run(p,'independent-129',code,dict(EXPECTED_HEAD=composed,GITHUB_RUN_ID='A8_LOCAL_NOT_HOSTED',GITHUB_RUN_ATTEMPT='LOCAL_ONLY'));after=identity(p,composed);assert before==after
receipt=json.loads((p/'partial-integration-ci-evidence.json').read_text());assert receipt['tests']==129 and receipt['failures']==receipt['errors']==receipt['skipped']==0 and receipt['source_before']==receipt['source_after'];assert sorted(receipt['mandatory_test_ids'])==inv['expected_test_ids'];(out/'independent-129-receipt.json').write_text(json.dumps(receipt,indent=2));(out/'independent-129-tests.log').write_bytes((p/'partial-integration-ci-tests.log').read_bytes())
p=clone('guard',head);guardbefore=identity(p,head)
script='''import unittest,json,copy,dataclasses,socket,subprocess,builtins
from unittest.mock import patch
from tests.test_security_identity_records import fixtures,encode
from unified_system.security_identity_records import IdentityBinding,IdentityRecordError,guard_keys,decode_guard_records
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('tests.test_security_identity_records'));assert result.wasSuccessful() and result.testsRun==8 and not result.skipped
b,values=fixtures();negative=0
def reject(v):
 global negative
 try:decode_guard_records(b,encode(v))
 except IdentityRecordError:negative+=1
 else:raise AssertionError('guard negative accepted')
for kind in values:
 for revision in ('0','01',str(2**63),True,None):
  v=copy.deepcopy(values);v[kind]['revision']=revision;reject(v)
 for state in ('REVOKED','EXPIRED','UNKNOWN',True):
  v=copy.deepcopy(values);v[kind]['state']=state;reject(v)
 for extra in ('ModifyIndex','authenticated','expires_at','caller_path'):
  v=copy.deepcopy(values);v[kind][extra]='1';reject(v)
v=copy.deepcopy(values);v['policy']['permissions']=['REAL_ORDER'];reject(v)
v=copy.deepcopy(values);v['session']['native_logon_id']='0x000000000000001a';reject(v)
for name in b.__dataclass_fields__:
 try:guard_keys(dataclasses.replace(b,**{name:'../outside'}))
 except IdentityRecordError:negative+=1
 else:raise AssertionError('path injection accepted')
with patch.object(builtins,'open',side_effect=AssertionError('unexpected file IO')),patch.object(socket,'socket',side_effect=AssertionError('unexpected socket')),patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected process')):
 parsed=decode_guard_records(b,encode(values));keys=guard_keys(b)
 assert len(keys)==4 and 'authenticated' not in parsed and not hasattr(parsed,'execution_authorized')
for kind in values:
 try:parsed[kind]['state']='ACTIVE'
 except TypeError:pass
 else:raise AssertionError('mutable guard')
# This parser is structural: it does not validate a SID against the kernel.
sid_residual=[]
for sid in ('S-1-0005-21','S-1-5-4294967296'):
 v=copy.deepcopy(values);v['principal']['sid']=sid
 decode_guard_records(b,encode(v));sid_residual.append(sid)
print(json.dumps(dict(owner_cases=8,skips=0,independent_negative_vectors=negative,pure_no_io=True,immutable=True,not_a_native_sid_validator=sid_residual,native_authentication='NOT_QUALIFIED')))
'''
run(p,'identity-guard',script);guardafter=identity(p,head);assert guardbefore==guardafter
report=dict(composed_head=composed,composed_tree='0bc635d822a3702e43b45fbd513a8e0bf2cb3ab6',guard_head=head,guard_tree='6255c0620a4257d7f8fd82e0fee5d944e052a1b6',owner_component_paths_match=True,prior75_ids_and_whole_test_module_bytes_preserved=True,independent_composed_tests=129,skips=0,composed_raw_before=before,composed_raw_after=after,owner_receipt_original_log_and_primary_inputs_verified=True,independent_guard_tests=8,independent_guard_negative_vectors=60,guard_raw_before=guardbefore,guard_raw_after=guardafter,qualification='EXACT_CODE_AND_ISOLATED_COMPONENTS_ONLY',native_authentication='NOT_QUALIFIED',atomic_guard_CAS='NOT_IMPLEMENTED_OR_TESTED',integrated_endpoint='BLOCKED',windows_hosted='NOT_QUALIFIED',physical='BLOCKED',F16_global='OPEN',overall='NO_GO')
(out/'identity-and-129-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
