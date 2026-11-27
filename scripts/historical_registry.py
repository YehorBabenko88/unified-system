"""Pinned coordination identity check; NEVER runtime/deployment authorization.

The caller's expected manifest hash must come from separately trusted review,
not the candidate JSON. Actual runtime admission remains unwired and blocked.
"""
import hashlib
import json
from pathlib import Path
import re

MODULES=frozenset(('unified-system','bybit-cluster-grid','strattester','math','meta_analyse','Terminan'))

class RegistryRejected(ValueError):pass

def need(value,reason):
    if value is not True:raise RegistryRejected(reason)

def decode(raw):
    need(type(raw) is bytes and 0<len(raw)<=2*1024*1024,'REGISTRY_BYTE_BOUND')
    def pairs(items):
        out={}
        for key,value in items:
            need(key not in out,'DUPLICATE_JSON_KEY');out[key]=value
        return out
    try:return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda _:need(False,'NONFINITE_JSON'))
    except (UnicodeError,json.JSONDecodeError,RecursionError) as exc:raise RegistryRejected('REGISTRY_JSON_REJECTED') from exc

def verify_identity(registry_root,candidate,*,expected_manifest_sha256):
    root=Path(registry_root)
    need(type(expected_manifest_sha256) is str and re.fullmatch('[a-f0-9]{64}',expected_manifest_sha256) is not None,'EXTERNAL_MANIFEST_PIN_REQUIRED')
    raw=(root/'integration-manifest.v1.json').read_bytes()
    need(hashlib.sha256(raw).hexdigest()==expected_manifest_sha256,'MANIFEST_PIN_MISMATCH')
    manifest=decode(raw)
    need(manifest.get('schema')=='unified.integration-manifest.v1' and type(manifest.get('revision')) is int and manifest['revision']>0,'MANIFEST_SCHEMA_REJECTED')
    need(manifest.get('mode')=='LAB_SIMULATION' and manifest.get('runtime_admission')=='BLOCKED','UNSUPPORTED_ADMISSION_PROFILE')
    for name,field in (('api-contracts.v1.json','contracts_sha256'),('ownership.v1.json','ownership_sha256'),('repository-audit.json','repository_audit_sha256'),('integration-matrix.v1.json','matrix_sha256'),('mandatory-gates.v1.json','mandatory_gates_sha256')):
        need(hashlib.sha256((root/name).read_bytes()).hexdigest()==manifest.get(field),'REGISTRY_REFERENCE_MISMATCH')
    need(type(candidate) is dict and set(candidate)=={'schema','mode','modules','contracts_sha256'},'CANDIDATE_FIELDS_REJECTED')
    need(candidate['schema']=='unified.integration-candidate.v1' and candidate['mode']=='LAB_SIMULATION','CANDIDATE_MODE_REJECTED')
    need(candidate['contracts_sha256']==manifest['contracts_sha256'],'CONTRACT_VERSION_MISMATCH')
    need(type(candidate['modules']) is dict and set(candidate['modules'])==MODULES and set(manifest['modules'])==MODULES,'MODULE_SET_MISMATCH')
    for name,pin in candidate['modules'].items():
        need(type(pin) is dict and set(pin)=={'head','tree'},'MODULE_PIN_FIELDS_REJECTED')
        for key in ('head','tree'):
            need(type(pin[key]) is str and re.fullmatch('[a-f0-9]{40}',pin[key]) is not None,'MODULE_PIN_REJECTED')
            need(pin[key]==manifest['modules'][name][key],'INCOMPATIBLE_MODULE_'+name)
    return {'identity':'MATCHED_AUDIT_BASELINE_ONLY','runtime_admission':'BLOCKED','deployment_authorized':False,'trading_authorized':False}

def _path_key(value,*,prefix=False):
    need(type(value) is str and re.fullmatch(r'[A-Za-z0-9_./-]+',value) is not None,'NONCANONICAL_REPOSITORY_PATH')
    need(not value.startswith('/') and (not value.endswith('/') or prefix),'NONCANONICAL_REPOSITORY_PATH')
    body=value[:-1] if prefix and value.endswith('/') else value
    parts=body.split('/')
    reserved={'con','prn','aux','nul',*('com'+str(i) for i in range(1,10)),*('lpt'+str(i) for i in range(1,10))}
    need(bool(body) and all(part not in ('','.','..') and not part.endswith(('.',' ')) and part.split('.')[0].casefold() not in reserved for part in parts),'NONCANONICAL_REPOSITORY_PATH')
    need(parts[0].casefold()!='.git','GIT_METADATA_RESERVED')
    return value.casefold()

def verify_ownership(ownership):
    need(ownership.get('schema')=='unified.ownership.v1','OWNERSHIP_SCHEMA_REJECTED')
    agents=ownership.get('agents');need(type(agents) is list and len(agents)==8,'EIGHT_OWNERS_REQUIRED')
    need({a['agent_id'] for a in agents}=={'A'+str(i) for i in range(1,9)},'UNIQUE_OWNERS_REQUIRED')
    allocations=[]
    for agent in agents:
        extras=agent.get('additional_allocations',[])
        need(type(extras) is list,'ALLOCATION_LIST_REQUIRED')
        for allocation in [agent,*extras]:
            need(type(allocation) is dict and allocation['repository'] in MODULES,'UNKNOWN_REPOSITORY_OWNER')
            paths=[_path_key(p) for p in allocation['allowed_files']]+[_path_key(p,prefix=True) for p in allocation['allowed_new_path_prefixes']]
            allocations.append((allocation,paths))
    need(len({a['branch'].casefold() for a,_ in allocations})==len(allocations) and len({a['worktree'].replace('\\','/').casefold() for a,_ in allocations})==len(allocations),'ISOLATION_COLLISION')
    shared_paths=[_path_key(p,prefix=p.endswith('/')) for p in ownership['shared_paths']]
    def overlaps(left,right):return left==right or left.startswith(right) or right.startswith(left)
    for agent,paths in allocations:
        for owned in paths:
            for shared in shared_paths:
                need(not overlaps(owned,shared),'ROOT_SHARED_FILE_RESERVED')
    for i,(a,a_paths) in enumerate(allocations):
        for b,b_paths in allocations[i+1:]:
            if a['repository']!=b['repository']:continue
            for left in a_paths:
                for right in b_paths:
                    need(not overlaps(left,right),'FILE_OWNERSHIP_COLLISION')
    return True

def verify_acceptance_package(package_root,*,expected_index_sha256):
    """Verify immutable preparation bytes; successful verification grants nothing."""
    root=Path(package_root);raw=(root/'package-index.json').read_bytes()
    need(type(expected_index_sha256) is str and hashlib.sha256(raw).hexdigest()==expected_index_sha256,'ACCEPTANCE_INDEX_PIN_MISMATCH')
    index=decode(raw)
    need(index.get('schema')=='unified.acceptance-package-index.v1' and index.get('runtime_admission')=='BLOCKED' and index.get('physical_acceptance')=='BLOCKED_NO_GO','ACCEPTANCE_PROFILE_REJECTED')
    files=index.get('files');need(type(files) is dict and 10<=len(files)<=256,'ACCEPTANCE_INVENTORY_REJECTED')
    names=set();total=0
    for name,digest in files.items():
        key=_path_key(name);need(key not in names,'ACCEPTANCE_PATH_ALIAS');names.add(key)
        need(type(digest) is str and re.fullmatch('[a-f0-9]{64}',digest) is not None,'ACCEPTANCE_DIGEST_REJECTED')
        path=root/name;need(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink() and path.is_file(),'ACCEPTANCE_PATH_ESCAPE')
        need(path.stat().st_size<=4*1024*1024,'ACCEPTANCE_FILE_BOUND');data=path.read_bytes();total+=len(data)
        need(total<=32*1024*1024 and hashlib.sha256(data).hexdigest()==digest,'ACCEPTANCE_MEMBER_MISMATCH')
    required={'release-manifest.json','integration-baseline.json','ownership-registry.json','node-inventory.json','contract-status.json','ci-evidence-index.json','rollback-plan.md','physical-acceptance-plan.json','approval-status.json'}
    need(required<=set(files),'ACCEPTANCE_REQUIRED_MEMBERS_MISSING')
    approval=decode((root/'approval-status.json').read_bytes());release=decode((root/'release-manifest.json').read_bytes());baseline=decode((root/'integration-baseline.json').read_bytes())
    need(release.get('schema')=='unified.release-acceptance-manifest.v1','RELEASE_SCHEMA_REJECTED')
    for value in (approval,release):
        need(value.get('runtime_admission')=='BLOCKED' and value.get('installable') is False and value.get('physical_fault_injection')=='NOT_AUTHORIZED' and value.get('production_deployment')=='NOT_AUTHORIZED' and value.get('tailscale_removal')=='BLOCKED' and value.get('go')=='NO-GO','UNAUTHORIZED_ACCEPTANCE_UPGRADE')
    need(release.get('source_modules')==baseline.get('modules') and set(baseline['modules'])==MODULES,'ACCEPTANCE_SOURCE_SET_MISMATCH')
    for field,name in [('coordination_manifest_sha256','integration-baseline.json'),('ownership_sha256','ownership-registry.json'),('node_inventory_sha256','node-inventory.json'),('contract_status_sha256','contract-status.json'),('ci_evidence_index_sha256','ci-evidence-index.json'),('rollback_plan_sha256','rollback-plan.md'),('physical_plan_sha256','physical-acceptance-plan.json')]:
        need(release.get(field)==files[name],'ACCEPTANCE_REFERENCE_MISMATCH')
    verify_ownership(decode((root/'ownership-registry.json').read_bytes()))
    return {'integrity':'VERIFIED_PREPARATION_ONLY','runtime_admission':'BLOCKED','physical_authorized':False,'go':'NO-GO'}
