"""Verify inert historical custody; never execute retired source or grant release."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
INVENTORY='docs/migration/retired-six-owner/role-inventory.json'
def verify(root=ROOT):
 root=pathlib.Path(root).resolve();raw_inventory=(root/INVENTORY).read_bytes()
 if hashlib.sha256(raw_inventory).hexdigest()!='fbe43f169ac50828c75b9d8aa2baf5feb2a2f870d2d01b512705c6a9b898601b':raise ValueError('RETIRED_COMPLETE_OBLIGATION_MAP_CHANGED')
 inventory=json.loads(raw_inventory)
 if inventory['root_head']!='186a723aea60aaeb9eb51a59a66999bc485a06e1' or len(inventory['bundle'])!=6:raise ValueError('RETIRED_SOURCE_INVENTORY_REJECTED')
 for key,count in (('source_roles',14),('runtime_roles',16),('browser_roles',4)):
  roles=inventory[key]
  if type(roles) is not list or len(roles)!=count or any(type(role) is not dict or type(role.get('status')) is not str for role in roles):raise ValueError('RETIRED_ROLE_INVENTORY_REJECTED')
  if not any(role['status'].startswith(('NOT_TRANSFERRED','PARTIAL')) for role in roles):raise ValueError('UNTRANSFERRED_OBLIGATIONS_MUST_REMAIN_EXPLICIT')
 for member in inventory['bundle']:
  old=root/member['path'];archive=root/member['archive']
  if old.exists() or old.is_symlink():raise ValueError('RETIRED_ENTRYPOINT_REINTRODUCED')
  if not archive.resolve().is_relative_to(root/'docs/migration/retired-six-owner/raw') or archive.is_symlink():raise ValueError('RETIRED_ARCHIVE_ORIGIN_REJECTED')
  raw=archive.read_bytes()
  if len(raw)!=member['bytes'] or hashlib.sha256(raw).hexdigest()!=member['sha256']:raise ValueError('RETIRED_RAW_BYTES_CHANGED')
 return {'archive_custody':'PASS','source_roles':14,'runtime_roles':16,'browser_roles':4,'remaining_obligations':'NOT_TRANSFERRED_OR_PARTIAL','runtime':'NOT_RUN','release_status':'NO_GO','execution_authority':False,'trading_authorized':False}
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
