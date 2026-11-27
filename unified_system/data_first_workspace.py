"""Service-bound DataFirst workspace consistency, not activation authority.

The caller must fully admit the capsule and provide its manifest and a live
kernel-protected grant. The service root/state parent must already have the
approved private service ACL. No ACL attestation or hostile same-service/admin
containment is supplied here. No databases, network clients or caches are opened.
"""
import copy,hashlib,os,re,stat
from pathlib import Path
from .data_first_policy import validate_data_first_grant
from .service_bootstrap import canonical,local,parse,stamp

MARKER='data-first-owned.json'
MAX_MARKER_BYTES=4096
MAX_TOP_LEVEL_ENTRIES=10000
CODES=frozenset(('DATA_FIRST_WORKSPACE_REJECTED','DATA_FIRST_WORKSPACE_GRANT_REQUIRED','DATA_FIRST_WORKSPACE_OWNERSHIP_REJECTED','DATA_FIRST_WORKSPACE_UNAVAILABLE'))
class WorkspaceBlocked(ValueError):
 def __init__(self,code='DATA_FIRST_WORKSPACE_REJECTED'):
  self.code=code if code in CODES else 'DATA_FIRST_WORKSPACE_REJECTED';super().__init__(self.code)
def need(value,code='DATA_FIRST_WORKSPACE_OWNERSHIP_REJECTED'):
 if not value:raise WorkspaceBlocked(code)
def directory(path):
 path=local(path);info=path.lstat();need(stat.S_ISDIR(info.st_mode));return [info.st_dev,info.st_ino]
def binding(grant,manifest):
 need(grant is not None and not isinstance(grant,dict) and callable(getattr(grant,'require_current',None)),'DATA_FIRST_WORKSPACE_GRANT_REQUIRED')
 need(grant.require_current() is True,'DATA_FIRST_WORKSPACE_GRANT_REQUIRED')
 validate_data_first_grant(grant.profile.get('data_first'),manifest)
 plan=grant.descriptor['service_plan'];root=local(plan['root']);state=local(plan['state'])
 need(state==root/'state' and grant.service_sid==plan['service_sid'] and grant.computer_name.casefold()==plan['computer_name'].casefold())
 for field in ('installation_id','node_id','service_name','computer_name'):
  need(type(plan[field]) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}',plan[field]))
 need(type(plan['service_sid']) is str and re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+',plan['service_sid']))
 return dict(version=2,scope='SERVICE_DATA_FIRST_WORKSPACE',installation_id=plan['installation_id'],node_id=plan['node_id'],service_name=plan['service_name'],service_sid=plan['service_sid'],computer_name=plan['computer_name'],service_root=str(root),state_root=str(state),workspace_root=str(state/'data-first'),service_root_identity=directory(root),state_root_identity=directory(state))
def read_marker(path):
 before=stamp(path);need(0<before[2]<=MAX_MARKER_BYTES)
 with path.open('rb') as stream:
  opened=os.fstat(stream.fileno());need((opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns,opened.st_nlink)==before)
  raw=stream.read(MAX_MARKER_BYTES+1)
  after=os.fstat(stream.fileno());need((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_nlink)==before)
 need(stamp(path)==before and len(raw)==before[2]);return parse(raw),before,hashlib.sha256(raw).hexdigest()
def closure(root):
 # Only the immediate namespace is bounded/enumerated; millions of admitted
 # market records below these fixed directories are deliberately not scanned.
 with os.scandir(root) as entries:
  for count,entry in enumerate(entries,1):
   need(count<=MAX_TOP_LEVEL_ENTRIES);path=local(root/entry.name)
   if entry.name==MARKER:need(path.is_file());continue
   need(entry.name in ('market','results','logs','state') or re.fullmatch('data-first-[A-Za-z0-9_-]{1,128}',entry.name))
   need(stat.S_ISDIR(path.lstat().st_mode))

 # Check only the finite factory path slots, never recursive market contents.
 slots={'state/data-first.sqlite3':False}
 for category in ('linear','inverse','spot'):
  slots.update({'market/'+category:True,'market/'+category+'/shards':True,'market/'+category+'/market.sqlite3':False})
 for relative,is_directory in slots.items():
  path=local(root/relative)
  if path.exists():need(stat.S_ISDIR(path.lstat().st_mode) if is_directory else stat.S_ISREG(path.lstat().st_mode))

class DataFirstWorkspace:
 def __init__(self,grant,manifest,identity,marker_stamp,marker_hash):
  self._grant=grant;self._manifest=copy.deepcopy(manifest);self._identity=copy.deepcopy(identity);self._marker_stamp=marker_stamp;self._marker_hash=marker_hash
 @property
 def root(self):return Path(self._identity['workspace_root'])
 def require_current(self):
  try:
   expected=binding(self._grant,self._manifest);expected['workspace_identity']=directory(self.root)
   need(expected==self._identity)
   value,identity,digest=read_marker(self.root/MARKER)
   need(value==expected and identity==self._marker_stamp and digest==self._marker_hash);closure(self.root);return True
  except WorkspaceBlocked:raise
  except Exception:raise WorkspaceBlocked('DATA_FIRST_WORKSPACE_UNAVAILABLE') from None

def admit_data_first_workspace(grant,manifest):
 try:
  manifest=copy.deepcopy(manifest);identity=binding(grant,manifest);root=Path(identity['workspace_root'])
  if not root.exists():
   # An interrupted directory without a marker is retained and cannot be adopted.
   root.mkdir(exist_ok=False);identity['workspace_identity']=directory(root)
   again=binding(grant,manifest);again['workspace_identity']=directory(root);need(again==identity)
   raw=canonical(identity);need(len(raw)<=MAX_MARKER_BYTES)
   with (root/MARKER).open('xb') as stream:
    need(directory(root)==identity['workspace_identity']);stream.write(raw);stream.flush();os.fsync(stream.fileno())
  else:identity['workspace_identity']=directory(root)
  value,marker_stamp,marker_hash=read_marker(root/MARKER);need(value==identity)
  result=DataFirstWorkspace(grant,manifest,identity,marker_stamp,marker_hash);result.require_current();return result
 except WorkspaceBlocked:raise
 except Exception:raise WorkspaceBlocked('DATA_FIRST_WORKSPACE_UNAVAILABLE') from None
