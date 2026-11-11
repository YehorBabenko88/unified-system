import pathlib,subprocess,json,hashlib
r=pathlib.Path.cwd();o=r/'outputs/phase87';o.mkdir(exist_ok=True);repo=r/'work/unified-audit';old='063a004770a6d98ba78de7bbd5d4aadcc752ed55';new='9428e3d8a74e5ee93dcd6c3caef59dcd7b98c8ab';name='.github/workflows/gateway-identity.yml'
def g(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
assert g('rev-parse',new+'^{tree}').decode().strip()=='58d0e3950529139897ffa540a5766c1db2878395'
for label,head in [('old063',old),('new942',new)]:
 raw=g('show',head+':'+name);(o/(label+'-workflow.original.yml')).write_bytes(raw)
changes=g('diff','--name-status',old,new).decode().splitlines();assert changes==['M\t.github/workflows/gateway-identity.yml','M\tdocs/intelligence/identity/CI-SOURCE-PIN-CORRECTION.md']
paths=['unified_system/gateway_identity.py','tests/test_gateway_identity.py','docs/intelligence/identity/run_qualification.py','docs/intelligence/identity/guard_controls.py','docs/intelligence/identity/API-REVIEW3.md','docs/intelligence/identity/requirements-windows.lock','docs/intelligence/identity/requirements-linux.lock'];proof=[]
for p in paths:
 b=g('show',new+':'+p);assert g('show',old+':'+p)==b;proof.append(dict(path=p,sha256=hashlib.sha256(b).hexdigest()))
(o/'source-delta.json').write_text(json.dumps(dict(old_head=old,new_head=new,new_tree='58d0e3950529139897ffa540a5766c1db2878395',changed_paths=changes,unchanged_runtime_tests_guard_API_and_locks=proof,new_HEAD_runtime_tests_executed='NOT_RUN_NO_TRANSFER'),indent=2),encoding='utf-8')
