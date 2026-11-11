"""Decode archived fixture as bytes only; never import, marshal or execute."""
import base64,hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/unified-audit';out=r/'outputs/phase50';head='aefa2a9039349445bd3eaee25b12f9b6bec4c01d';old='38c39092a30be51f8f554bac48f3fad5a87a6c25';prefix='release/evidence/control-mux-integrated-a77a5bd/'
def read(pin,path):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'show',pin+':'+prefix+path])
raw=read(head,'publication-correction.json');c=json.loads(raw);original=read(head,'root-result.json');assert original==read(old,'root-result.json') and hashlib.sha256(original).hexdigest()==c['original_receipt_sha256'];o=json.loads(original)
members=c['directly_published_original_members'];assert len(members)==15 and set(members)|{c['local_only_original_member']['path']}==set(o['evidence_sha256'])
for name,digest in members.items():assert digest==o['evidence_sha256'][name] and hashlib.sha256(read(head,name)).hexdigest()==digest
safe=c['safe_encoded_member'];encoded=read(head,safe['path']);assert encoded.endswith(b'\n') and b'\n' not in encoded[:-1] and hashlib.sha256(encoded).hexdigest()==safe['encoded_sha256'];decoded=base64.b64decode(encoded[:-1],validate=True)
assert len(decoded)==safe['decoded_size']==259 and hashlib.sha256(decoded).hexdigest()==safe['decoded_sha256']==c['local_only_original_member']['raw_sha256']==o['evidence_sha256'][c['local_only_original_member']['path']]
assert base64.b64encode(decoded)+b'\n'==encoded and not c['additional_test_execution'] and not c['runtime_admission'] and not c['physical_admission']
(out/'publication-correction.original.json').write_bytes(raw);(out/'cache-negative-fixture.pyc.base64.txt').write_bytes(encoded)
report=dict(requirement='F07_ROOT_EVIDENCE_PUBLICATION_SUBITEM',head=head,tree=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse',head+'^{tree}']).decode().strip(),original_receipt_unchanged=True,direct_original_members_hash_verified=15,archived_fixture_decoded_bytes=259,decoded_sha256=hashlib.sha256(decoded).hexdigest(),encoded_sha256=hashlib.sha256(encoded).hexdigest(),bytecode_executed_or_imported=False,original_38c_completeness_failure_preserved=True,status='CORRECTION_VERIFIED_PUBLICATION_SUBITEM_CLOSED',global_F07='OPEN_OTHER_EVIDENCE_GAPS',A8_merged_runtime_execution='NOT_RUN',test_rerun='NONE_BYTE_VERIFICATION_ONLY',overall='NO_GO')
(out/'publication-correction-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
