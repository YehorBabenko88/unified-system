import pathlib,subprocess,json,hashlib,io,xml.etree.ElementTree as ET
r=pathlib.Path.cwd();repo=r/'work/review-query76-cdd';o=r/'outputs/phase93';head='cddf71fab478f788d7289da9648f8a2f9287d1f8';owner=r.parent/'codex-agent-7-distributed-research-math/outputs';qual=owner/'query-v2-clean-final-qualified'
def g(*a,data=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=data)
rows=[]
for row in g('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();assert kind==b'blob';rows.append((name.decode(),oid.decode()))
s=io.BytesIO(g('cat-file','--batch',data=''.join(oid+'\n' for _,oid in rows).encode()));rawmap={}
for name,oid in rows:
 actual,kind,size=s.readline().split();b=s.read(int(size));assert s.read(1)==b'\n' and actual.decode()==oid and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid and (repo/name).read_bytes()==b and (qual/name).read_bytes()==b;rawmap[name]=hashlib.sha256(b).hexdigest()
extras=[]
for base in (repo,qual):
 for p in base.rglob('*'):
  rel=p.relative_to(base)
  if rel.parts[0]!='.git' and p.is_file() and rel.as_posix() not in rawmap:extras.append(str(p))
assert not extras and len(rawmap)==819
assert subprocess.check_output(['git','--no-replace-objects','-C',str(qual),'rev-parse','HEAD']).decode().strip()==head
receiptb=(owner/'query-v2-cddf71f-full-receipt.json').read_bytes();receipt=json.loads(receiptb);(o/'owner-full-receipt.original.json').write_bytes(receiptb)
for name,facts in receipt['files'].items():
 p=pathlib.Path(name);b=p.read_bytes();assert len(b)==facts['bytes'] and hashlib.sha256(b).hexdigest()==facts['sha256'];(o/('owner-'+p.name)).write_bytes(b)
xml=ET.fromstring((owner/'query-v2-cddf71f-full.xml').read_bytes());cases=list(xml.iter('testcase'));assert len(cases)==2152 and sum(c.find('skipped') is not None for c in cases)==36 and not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
(o/'test-only-delta.original.diff').write_bytes(g('diff','6e58eb8bfa428cf88d54abd84418b58d67569814',head));delta=g('diff','--name-only','6e58eb8bfa428cf88d54abd84418b58d67569814',head).decode().splitlines();assert set(delta)=={'docs/gateway/research/QUERY-V2-EXECUTION.txt','tests/runtime/test_service_manager.py'}
result=dict(head=head,tree=g('rev-parse','HEAD^{tree}').decode().strip(),primary_raw_prepost_A8=819,owner_current_retained_checkout_primary_raw=819,owner_current_extras=extras,owner_clean_scan='INDEPENDENT_CURRENT_READONLY_SNAPSHOT_NOT_TIME_TRAVEL_PROOF',owner_receipt_sha256=hashlib.sha256(receiptb).hexdigest(),XML_cases=2152,XML_skips=36,A8_full_pytest=False,delta=delta,source_raw=rawmap)
(o/'primary-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='source_raw'}))
