"""Auditor-owned exact-Git-blob verification of the ownership path fix."""
import argparse,copy,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--head',required=True);a=p.parse_args()
def git(*args):return subprocess.check_output(['git','-C',str(a.source.resolve()),*args])
def blob(path):return git('show',a.head+':'+path)
manifest=json.loads(blob('coordination/integration-manifest.v1.json'))
refs={name:hashlib.sha256(blob('coordination/'+name)).hexdigest()==manifest[field] for name,field in [
 ('api-contracts.v1.json','contracts_sha256'),('ownership.v1.json','ownership_sha256'),('repository-audit.json','repository_audit_sha256'),('integration-matrix.v1.json','matrix_sha256'),('mandatory-gates.v1.json','mandatory_gates_sha256')]}
assert all(refs.values())
ns={'__name__':'auditor_exact_registry_fix'};exec(compile(blob('unified_system/integration_registry.py'),'exact-git-blob:registry','exec'),ns)
owners=json.loads(blob('coordination/ownership.v1.json'));assert ns['verify_ownership'](owners)
paths=['UNIFIED_SYSTEM/LAN_TRANSPORT.PY','unified_system/../unified_system/contracts.py',r'unified_system\contracts.py',
 '/unified_system/x.py','C:/x.py','unified_system//x.py','./unified_system/x.py','unified_system/x.py.',
 'unified_system/CON.py','unified_system/x.py:stream','.git/config','unified_system/NUL.txt',
 'unified_system/a/../../unified_system/contracts.py','unified_system/LaN_TrAnSpOrT.pY','unified_system/x.py ']
results={}
for path in paths:
    value=copy.deepcopy(owners);value['agents'][1]['allowed_files'].append(path)
    try:ns['verify_ownership'](value)
    except ns['RegistryRejected'] as exc:results[path]={'status':'REJECTED','reason':str(exc)}
    else:results[path]={'status':'ACCEPTED'}
assert all(row['status']=='REJECTED' for row in results.values()),results
assert manifest['runtime_admission']=='BLOCKED'
print(json.dumps({'head':a.head,'tree':git('rev-parse',a.head+'^{tree}').decode().strip(),
 'manifest_sha256':hashlib.sha256(blob('coordination/integration-manifest.v1.json')).hexdigest(),
 'reference_hashes':refs,'original_valid_ownership':'ACCEPTED','negative_probes':results,
 'F08':'FIX_VERIFIED_OFFLINE_EXACT_SOURCE','global_ownership_ack':'PENDING_METADATA_AND_OTHER_RULES',
 'mandatory_gate_ack':'PENDING','runtime_admission':'BLOCKED','physical':'BLOCKED'},indent=2))
