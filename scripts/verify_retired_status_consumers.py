"""Bounded raw archive custody only; never executes retired sources or qualifies runtime."""
import argparse,ast,hashlib,json,pathlib,stat
INVENTORY=pathlib.Path('docs/migration/retired-status-consumers-20261120/role-inventory.json')
INVENTORY_SHA256='6c6d17314bbe88d2f1c5e4b1dbe4f51a7b4d4af0820e0cd7c9176f712d1cd055'
HELD_ROLES=("PARTIAL_TO_TERMINAL_GAP_DISPLAY","UNAVAILABLE_TERMINAL_DISPLAY","WRONG_PRODUCER_HTTP_REFUSAL","WRONG_PRODUCER_HTTP_RETIREMENT","WRONG_PRODUCER_ENV_PATH_RESTORATION","ROOT_BLOCKED_TO_TERMINAL_MONITOR_HTTP","MONITOR_UNVERIFIED_NO_TRADE","MONITOR_HTTP_RETIREMENT","MONITOR_ENV_PATH_RESTORATION",)

def _raw(path,limit):
 info=path.lstat()
 if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_nlink!=1 or getattr(info,'st_file_attributes',0)&1024:raise ValueError('ARCHIVE_FILE_ALIAS_OR_SPECIAL')
 with path.open('rb') as stream:raw=stream.read(limit+1)
 if len(raw)>limit:raise ValueError('ARCHIVE_BYTE_BOUND')
 return raw

def _preserved_ast_dump(node):
 # Python3.13 defaults to omitting empty optional lists. Keep the original
 # fingerprint representation; older interpreters do not accept show_empty.
 try:return ast.dump(node,include_attributes=False,show_empty=True)
 except TypeError:return ast.dump(node,include_attributes=False)

def verify_inventory(root):
 root=pathlib.Path(root).resolve();raw=_raw(root/INVENTORY,65536)
 if hashlib.sha256(raw).hexdigest()!=INVENTORY_SHA256:raise ValueError('INVENTORY_SOURCE_PIN_MISMATCH')
 value=json.loads(raw);assertions=[]
 if value['schema']!='unified.retired-status-consumer-inventory.v1' or len(value['archived'])!=8:raise ValueError('CLOSED_ARCHIVE_ROSTER_REQUIRED')
 for item in value['archived']:
  if (root/item['path']).exists():raise ValueError('RETIRED_ACTIVE_PATH_PRESENT')
  path=root/item['archive']
  if not path.resolve().is_relative_to(root):raise ValueError('ARCHIVE_PATH_ESCAPE')
  data=_raw(path,item['bytes'])
  if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('ARCHIVE_RAW_BYTES_MISMATCH')
  if item['path'].endswith('.py'):
   tree=ast.parse(data);compile(data,item['path'],'exec',dont_inherit=True)
   for n in ast.walk(tree):
    if isinstance(n,ast.Assert):assertions.append(dict(path=item['path'],line=n.lineno,expression=ast.unparse(n.test),ast_sha256=hashlib.sha256(_preserved_ast_dump(n).encode()).hexdigest()))
 if assertions!=value['assertions'] or len(assertions)!=14:raise ValueError('ORIGINAL_ASSERTIONS_NOT_PRESERVED')
 roles=value['roles'];held=tuple(r['id'] for r in roles if r['status']=='HELD')
 if held!=HELD_ROLES or len(roles)!=16 or len({r['id'] for r in roles})!=16:raise ValueError('REQUIRED_RUNTIME_OBLIGATIONS_MISSING')
 for workflow in sorted((root/'.github/workflows').glob('*')):
  if workflow.suffix not in ('.yml','.yaml'):continue
  text=_raw(workflow,1048576).decode('utf8').casefold()
  # Conservative text policy, not a shell parser or execution detector.
  if any(pathlib.Path(p).stem.casefold() in text for p in value['retired_scripts']):raise ValueError('RETIRED_SCRIPT_STEM_IN_ACTIVE_WORKFLOW')
 return dict(archive_files=8,assertions=14,roles=16,held_roles=list(held),transferred_pure=4,partial=3,executed_retired_sources=False)

def archive_report(summary):
 return dict(schema='unified.retired-status-consumer-custody.v1',status='PASS_ARCHIVE_CUSTODY_ONLY',scope='RAW_BYTES_AND_ROLE_INVENTORY_NOT_RUNTIME_ACCEPTANCE',inventory_sha256=INVENTORY_SHA256,**summary,runtime_qualification='NOT_RUN',native='NOT_RUN',release_status='NO_GO',execution_authority=False,trading_authorized=False,source_capability=False)

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default=str(pathlib.Path(__file__).resolve().parents[1]));parser.add_argument('--output')
 args=parser.parse_args(argv);root=pathlib.Path(args.root).resolve();report=archive_report(verify_inventory(root));raw=json.dumps(report,sort_keys=True,indent=2)+'\n'
 if args.output:
  output=pathlib.Path(args.output).absolute()
  if output.resolve().is_relative_to(root):raise ValueError('EXTERNAL_ARCHIVE_EVIDENCE_REQUIRED')
  with output.open('x',encoding='utf8') as stream:stream.write(raw)
 print(raw,end='');return 0

if __name__=='__main__':raise SystemExit(main())
