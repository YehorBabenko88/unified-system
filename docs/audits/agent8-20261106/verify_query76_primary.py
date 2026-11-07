import pathlib,subprocess,json,hashlib,io,xml.etree.ElementTree as ET,shutil
r=pathlib.Path.cwd();repo=r/'work/review-query76-6e58';o=r/'outputs/phase90';owner=r.parent/'codex-agent-7-distributed-research-math/outputs';checks={}
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
rows=[]
for row in g('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));rawmap={}
for name,oid in rows:
 actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b;rawmap[name]=hashlib.sha256(b).hexdigest()
assert len(rows)==819
packet=repo/'docs/gateway/research/evidence/query-v2-onebar';manifest=json.loads((packet/'MANIFEST.json').read_bytes())
for name,facts in manifest['files'].items():
 b=(packet/name).read_bytes();assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256']
for name in ['upstream-request.json','upstream-result.json','request.json','meta-result.json','descriptor.json']:
 assert (packet/name).read_bytes()==(r/'work/query76-a8-temp/gateway-query-v2-computation'/name).read_bytes(),name
checks['packet_manifest_members']=len(manifest['files']);checks['generated_five_packet_files']='BYTE_IDENTICAL_TO_ORIGINAL_5b_EXECUTION';checks['original_execution_head']=manifest['execution_head']
receipt=json.loads((owner/'query-v2-6e58eb8-full-receipt.json').read_bytes());(o/'owner-full-receipt.original.json').write_bytes((owner/'query-v2-6e58eb8-full-receipt.json').read_bytes());originals=[]
for name,facts in receipt['files'].items():
 p=pathlib.Path(name);b=p.read_bytes();assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];originals.append(dict(name=p.name,bytes=len(b),sha256=facts['sha256']))
 if p.suffix in ('.log','.xml'):(o/('owner-'+p.name)).write_bytes(b)
root=ET.fromstring((owner/'query-v2-6e58eb8-full.xml').read_bytes());suites=list(root.iter('testsuite'));cases=list(root.iter('testcase'));checks['owner_XML_suite_attributes']=[x.attrib for x in suites];checks['owner_XML_cases']=len(cases);checks['owner_XML_skipped']=sum(c.find('skipped') is not None for c in cases);checks['owner_XML_failures']=sum(c.find('failure') is not None for c in cases);checks['owner_XML_errors']=sum(c.find('error') is not None for c in cases)
assert checks['owner_XML_skipped']==36 and checks['owner_XML_failures']==checks['owner_XML_errors']==0
checks['owner_original_files_digest_verified']=originals;checks['full_suite_rerun_by_A8']=False;checks['primary_raw']=rawmap;checks['head']=g('rev-parse','HEAD').decode().strip();checks['tree']=g('rev-parse','HEAD^{tree}').decode().strip()
(o/'primary-verification.json').write_text(json.dumps(checks,indent=2));target=o/'generated-query-evidence';target.mkdir(exist_ok=True)
for p in (r/'work/query76-a8-temp/gateway-query-v2-computation').glob('*.json'):shutil.copy2(p,target/p.name)
print(json.dumps({k:v for k,v in checks.items() if k!='primary_raw'}))
