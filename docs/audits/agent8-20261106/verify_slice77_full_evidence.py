import pathlib,json,hashlib,subprocess,xml.etree.ElementTree as ET
r=pathlib.Path.cwd();o=r/'outputs/phase97';o.mkdir(exist_ok=True);owner=r.parent/'codex-agent-7-distributed-research-math/outputs';indexraw=(owner/'agent7-final-gateway-evidence-index.json').read_bytes();idx=json.loads(indexraw);(o/'owner-final-index.original.json').write_bytes(indexraw);verified=[]
for label,result in idx['results'].items():
 for name,pin in result['files'].items():
  p=pathlib.Path(name);b=p.read_bytes();assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'];verified.append(dict(result=label,name=p.name,bytes=len(b),sha256=pin['sha256']))
receiptb=(owner/'persistence-887e3ee-full-receipt.json').read_bytes();d=json.loads(receiptb);(o/'owner-full-receipt.original.json').write_bytes(receiptb)
for name,pin in d['files'].items():
 p=pathlib.Path(name);b=p.read_bytes();assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'];(o/('owner-'+p.name)).write_bytes(b)
x=ET.fromstring((owner/'persistence-887e3ee-full.xml').read_bytes());cases=list(x.iter('testcase'));assert len(cases)==2163 and sum(c.find('skipped') is not None for c in cases)==36 and not any(c.find(k) is not None for c in cases for k in ['failure','error'])
rawmap=json.loads((r/'outputs/phase95/primary-verification.json').read_text())['source_raw'];clone=owner/'persistence-887e3ee-qualified';assert subprocess.check_output(['git','--no-replace-objects','-C',str(clone),'rev-parse','HEAD']).decode().strip()==d['head']
for name,sha in rawmap.items():assert hashlib.sha256((clone/name).read_bytes()).hexdigest()==sha
for p in clone.rglob('*'):
 rel=p.relative_to(clone)
 if rel.parts[0]!='.git' and p.is_file():assert rel.as_posix() in rawmap
out=dict(head=d['head'],tree=d['tree'],owner_receipt_sha256=hashlib.sha256(receiptb).hexdigest(),combined_index_sha256=hashlib.sha256(indexraw).hexdigest(),index_payloads_verified=verified,XML_cases=2163,passed_cases=2127,skips=36,subtests_owner=35,XML_failures_errors=0,current_owner_primary_files=806,current_extras=[],independent_full_pytest=False,own_prior_phase95_tests=45,scope='ORIGINAL_EVIDENCE_INTEGRITY_AND_CURRENT_READONLY_SNAPSHOT_NOT_OWNER_EXECUTION_ADOPTION')
(o/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
