import pathlib,json,hashlib,ast
r=pathlib.Path.cwd();o=r/'outputs/phase141';b=pathlib.Path('C:/Users/LS-5/.codex/native-e2e-evidence-20261109');p=b/'ls5-package-461ee1d-b';sdk=pathlib.Path('C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-6-distributed-terminan-control/work/terminan-sync-v1-manual/node_modules');manifest=json.loads((b/'ls5-package-461-b.manifest.json').read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
original={x.relative_to(sdk).as_posix():sha(x.read_bytes()) for x in sdk.rglob('*') if x.is_file()};selected={k.removeprefix('tooling/node_modules/'):v['sha256'] for k,v in manifest['files'].items() if k.startswith('tooling/node_modules/')};assert original==selected
old=json.loads((r/'outputs/phase138/installed-sdk-reference.json').read_text()) if (r/'outputs/phase138/installed-sdk-reference.json').exists() else None
record=dict(current_original_and_copied_sdk_byte_equal=True,current_original_files=len(original),old_reference=old)
for name in ['LS5-PRE-MATERIALIZE-ACL-461-b.json','ls5-package461-b-plan-only.log','ls5-git-export-f6f3418-a.receipt.json']:
 raw=(b/name).read_bytes();record[name]=dict(bytes=len(raw),sha256=sha(raw));(o/name).write_bytes(raw) if name!='LS5-PRE-MATERIALIZE-ACL-461-b.json' else None
code=(p/'sources/harness/tools/physical_dev/ls5_smoke.py').read_bytes();tree=ast.parse(code);record['controller_sha256']=sha(code);record['cleanup_functions']={n.name:ast.unparse(n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['execute','retire_unassigned','Capture']}
record['core_hashes']={name:sha((p/'sources/harness/tools/physical_dev'/name).read_bytes()) for name in ['bootstrap.py','ls5_smoke.py','supervisor.py','package.py','materialize.py','export_git.py']}
(o/'source-cleanup-and-reference-review.json').write_text(json.dumps(record,indent=2));print('copied SDK matches current original',len(original));print(record['core_hashes'])
