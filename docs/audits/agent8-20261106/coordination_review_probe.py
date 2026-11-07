"""Independent read-only review of PR22 exact Git blobs and Windows ownership aliases."""
import copy,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=ROOT/'work/coordination-review';sha='34a2adf94b0e2170bf91f8641766e23481e269b2'
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha
def blob(name):return git('show',sha+':'+name)
raw=blob('coordination/integration-manifest.v1.json');manifest=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()=='7eb23f46ef0feba853400acad2285dd69103d67fb5d8932c52e40fc871b2f696'
assert git('rev-parse',sha+'^{tree}').decode().strip()=='96a9211ccf8d2ba42e60e00ef9572e0aaa86adbb'
refs={}
for name,field in [('api-contracts.v1.json','contracts_sha256'),('ownership.v1.json','ownership_sha256'),
 ('repository-audit.json','repository_audit_sha256'),('integration-matrix.v1.json','matrix_sha256'),('mandatory-gates.v1.json','mandatory_gates_sha256')]:
    refs[name]=hashlib.sha256(blob('coordination/'+name)).hexdigest()==manifest[field]
assert all(refs.values())
# Load the exact committed module bytes, avoiding checkout newline ambiguity.
ns={'__name__':'independent_registry_probe'}
exec(compile(blob('unified_system/integration_registry.py'),'exact-git-blob:integration_registry.py','exec'),ns)
owners=json.loads(blob('coordination/ownership.v1.json'))
assert ns['verify_ownership'](owners)
results={}
for case,path in [('windows_case_alias','UNIFIED_SYSTEM/LAN_TRANSPORT.PY'),
                  ('parent_component_reserved_file','unified_system/../unified_system/contracts.py'),
                  ('windows_backslash_reserved_file',r'unified_system\contracts.py')]:
    value=copy.deepcopy(owners);value['agents'][1]['allowed_files'].append(path)
    try:ns['verify_ownership'](value)
    except ns['RegistryRejected']:results[case]='REJECTED'
    else:results[case]='ACCEPTED_ALIAS'
gates=json.loads(blob('coordination/mandatory-gates.v1.json'))
print(json.dumps({'pr':22,'head':sha,'tree':'96a9211ccf8d2ba42e60e00ef9572e0aaa86adbb',
 'manifest_sha256':hashlib.sha256(raw).hexdigest(),'git_blob_reference_hashes':refs,
 'ownership_alias_probes':results,'runtime_admission':manifest['runtime_admission'],
 'all_gate_statuses':[g.get('status') for g in gates.get('gates',[])],
 'scope':'OFFLINE_REVIEW_ONLY; NO_RUNTIME_AUTHORITY'},indent=2))
