"""APP_ONLY removal of a separately receipted stopped service and closed code.

Private parents, a single operation writer and exact owner phase approval are
external prerequisites. This is not host/ACL ownership attestation. Every byte
of mutable state and both ownership journals is retained. Missing files after
an owned INTENT are observed absence, not proof of who deleted them. No Grid
legacy guard, activation, forced stop, configuration purge or full purge exists.
"""
import copy,hashlib,json,os,sqlite3,stat,base64
from contextlib import closing,contextmanager
from pathlib import Path
from . import installation_service as service,lab_release
from .contracts import seal,canonical
from .journal import Journal
from .installation_progress import safe as safe_journal
from .lab_capsule_acl import _safe

MODULE=Path(__file__).resolve().parents[1]/'scripts/UnifiedOwnedServiceRemoval.psm1'
SCHEMA='unified.app-only-uninstall.v1'
MAX_MEMBERS=40000
MAX_RECORDS=80010


def need(ok):
 if not ok:raise ValueError('APP_ONLY_UNINSTALL_REJECTED')


def identity(path):
 p=_safe(path);s=p.lstat();need(s.st_dev>0 and s.st_ino>0)
 return {'device':s.st_dev,'inode':s.st_ino}


def fingerprint(value):
 need(type(value) is dict and set(value)=={'device','inode'} and all(type(v) is int and v>0 for v in value.values()))


def image(path):
 p=lab_release.regular(path);a=p.stat();h=lab_release.hash_file(p);b=p.stat()
 need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_nlink)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_nlink))
 return dict(identity(p),bytes=a.st_size,mtime_ns=a.st_mtime_ns,sha256=h['sha256'])


class WindowsRemovalBoundary:
 """One admitted operation; Delete uses full proof, observation uses WinAPI only."""
 def __init__(self):self._admitted=None;self._api=None
 def _binding(self,plan,record):
  p=record['plan'];need(service.current_computer_name().casefold()==p['computer_name'].casefold()==plan['computer_name'].casefold())
  need(plan.get('schema')==SCHEMA and plan.get('mode')=='APP_ONLY' and plan.get('plan_sha256')==seal({k:v for k,v in plan.items() if k!='plan_sha256'}) and plan.get('service_plan_sha256')==p['plan_sha256'] and plan.get('service_receipt_sha256')==record['receipt_sha256'])
  return plan['plan_sha256'],seal(record)
 def admit(self,plan,record,guard):
  plan=copy.deepcopy(plan);record=copy.deepcopy(record)
  need(callable(guard) and guard('ADMIT_REMOVAL',plan['plan_sha256']) is True and os.name=='nt')
  key=self._binding(plan,record);p=record['plan']
  need(service.ServiceResource.open(p,service.WindowsServiceBoundary()).recorded()==record and service._native_tools()==p['native_tools'])
  need(hashlib.sha256(lab_release.regular(MODULE).read_bytes()).hexdigest()==plan['removal_executor_sha256'])
  need(hashlib.sha256(lab_release.regular(service.MODULE).read_bytes()).hexdigest()==p['executor_sha256'])
  self._admitted=key
 def _fast_observe(self,name):
  if self._api is None:
   import ctypes
   library=ctypes.WinDLL(str(service._system_directory()/'advapi32.dll'),use_last_error=True)
   manager=library.OpenSCManagerW;manager.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32];manager.restype=ctypes.c_void_p
   opened=library.OpenServiceW;opened.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint32];opened.restype=ctypes.c_void_p
   close=library.CloseServiceHandle;close.argtypes=[ctypes.c_void_p];close.restype=ctypes.c_int
   self._api={'manager':manager,'open':opened,'close':close,'error':ctypes.get_last_error}
  api=self._api;manager=api['manager'](None,None,1);need(bool(manager))
  try:
   handle=api['open'](manager,name,4)
   if handle:need(bool(api['close'](handle)));return 'PRESENT_REVIEW_REQUIRED'
   error=api['error']();need(error in (1060,1072));return 'ABSENT' if error==1060 else 'MARKED_PENDING'
  finally:need(bool(api['close'](manager)))
 def call(self,action,plan,record,guard):
  plan=copy.deepcopy(plan);record=copy.deepcopy(record)
  need(action in ('REMOVE_SERVICE','OBSERVE_SERVICE') and callable(guard) and guard(action,plan['plan_sha256']) is True and os.name=='nt')
  if action=='OBSERVE_SERVICE':
   need(self._admitted==self._binding(plan,record));return {'service':self._fast_observe(record['plan']['service_name'])}
  # Re-admit full source/record/tool/module pins immediately before actual Delete.
  # This path is O(1) per operation, never used for per-member observation.
  self.admit(plan,record,guard);p=record['plan']
  code="$ErrorActionPreference='Stop';[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);try{Import-Module -Name ([WildcardPattern]::Escape($env:UNIFIED_REMOVAL_MODULE)) -Force;$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;Invoke-UnifiedOwnedServiceRemoval $r|ConvertTo-Json -Compress}catch{[Console]::Out.Write('{\"error\":\"REMOVAL_REJECTED\"}');exit 1}"
  env=service._environment();env.update(UNIFIED_REMOVAL_MODULE=str(MODULE),UNIFIED_SERVICE_MODULE=str(service.MODULE))
  payload=canonical({'action':action,'plan':p,'proof':record['proof']});need(len(payload)<=65536)
  ps=p['native_tools']['powershell'];need(service._native_hash(ps['path'])==ps['sha256'])
  raw,status=service._run([ps['path'],'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode('ascii')],env=env,payload=payload,timeout=60)
  need(status==0);value=json.loads(raw);need(type(value) is dict and set(value)=={'service'} and value['service'] in ('ABSENT','MARKED_PENDING','PRESENT_REVIEW_REQUIRED'));return value


class Uninstaller:
 def __init__(self,resource,boundary):
  self.resource=resource;self.boundary=boundary;self.audit=Journal(resource.root/'ownership/uninstall.sqlite')
  self._db=None;self._cached=None;self._active=False
 def _record(self):return self.resource.recorded()
 def _members(self):
  r=self._record();p=r['plan'];m=lab_release.verify_capsule(p['capsule_root'],p['manifest_sha256'])['manifest']
  files={k:dict(v) for k,v in m['files'].items()};raw=(Path(p['capsule_root'])/'lab-release.json').read_bytes();files['lab-release.json']={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  dirs=set(m['directories'])|{'.'};need(len(files)+len(dirs)<=MAX_MEMBERS)
  return r,files,dirs
 def _host(self,plan):need(self.resource.boundary.computer_name().casefold()==plan['computer_name'].casefold())
 def _permit(self,action,plan,guard):
  self._host(plan);need(callable(guard) and guard(action,plan['plan_sha256']) is True);self._host(plan)
 def _rows(self):
  if self._cached is not None:return self._cached
  safe_journal(self.audit.path);need(self.audit.path.stat().st_size<=128*1024*1024)
  with closing(sqlite3.connect(self.audit.path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
   need(1<=db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]<=MAX_RECORDS)
   need(db.execute("SELECT COUNT(*) FROM transitions WHERE typeof(receipt)!='text' OR length(CAST(receipt AS BLOB))>65536").fetchone()[0]==0)
  rows=self.audit.read();first=rows[0];need(first['state']=='OBSERVING' and set(first['receipt'])=={'kind','plan'} and first['receipt']['kind']=='UNINSTALL_IDENTITY')
  return rows
 def _plan(self,record,files):
  if self.audit.path.exists():
   plan=self._rows()[0]['receipt']['plan'];need(type(plan) is dict)
   expected={'schema','mode','computer_name','service_plan_sha256','service_receipt_sha256','root_fingerprint','code_fingerprint','code_bytes','removal_executor_sha256','plan_sha256'};need(set(plan)==expected)
   need(plan['plan_sha256']==seal({k:v for k,v in plan.items() if k!='plan_sha256'}))
  else:
   p=record['plan'];lab_release.verify_capsule(p['code'],p['manifest_sha256'])
   body=dict(schema=SCHEMA,mode='APP_ONLY',computer_name=p['computer_name'],service_plan_sha256=p['plan_sha256'],service_receipt_sha256=record['receipt_sha256'],root_fingerprint=record['root_fingerprint'],code_fingerprint=identity(p['code']),code_bytes=sum(x['bytes'] for x in files.values()),removal_executor_sha256=hashlib.sha256(lab_release.regular(MODULE).read_bytes()).hexdigest())
   plan=dict(body,plan_sha256=seal(body))
  fingerprint(plan['code_fingerprint']);need(type(plan['code_bytes']) is int and plan['code_bytes']==sum(v['bytes'] for v in files.values()))
  need(plan['computer_name']==record['plan']['computer_name'])
  need(plan['schema']==SCHEMA and plan['mode']=='APP_ONLY' and plan['service_plan_sha256']==record['plan']['plan_sha256'] and plan['service_receipt_sha256']==record['receipt_sha256'] and plan['root_fingerprint']==record['root_fingerprint'])
  need(plan['removal_executor_sha256']==hashlib.sha256(lab_release.regular(MODULE).read_bytes()).hexdigest())
  return copy.deepcopy(plan)
 def _roots(self,plan,record):
  self._host(plan)
  root=record['plan']['root'];need(identity(root)=={'device':plan['root_fingerprint']['root_device'],'inode':plan['root_fingerprint']['root_inode']})
  code=_safe(record['plan']['code'])
  if code.exists():need(stat.S_ISDIR(code.lstat().st_mode) and identity(code)==plan['code_fingerprint'])
 def _state(self,plan,files,dirs):
  rows=self._rows();need(rows[0]['receipt']['plan']==plan);intents={};service_intent=False;absent=False;complete=False
  for row in rows[1:]:
   r=row['receipt'];need(row['state']=='OBSERVING' and type(r) is dict and set(r)=={'kind','plan_sha256','data'} and r['plan_sha256']==plan['plan_sha256'] and not complete)
   kind,data=r['kind'],r['data']
   if kind=='SERVICE_INTENT':need(not service_intent and data is None);service_intent=True
   elif kind=='SERVICE_ABSENCE':need(service_intent and not absent and data=='OBSERVED_ABSENCE_NO_ACTOR_ATTRIBUTION');absent=True
   elif kind=='MEMBER_INTENT':
    need(absent and type(data) is dict and set(data)=={'path','kind','identity','parent_identity'} and data['path'] not in intents)
    fingerprint(data['parent_identity']);path=data['path'];need((data['kind']=='FILE' and path in files) or (data['kind']=='DIRECTORY' and path in dirs))
    if data['kind']=='FILE':
     member=data['identity'];need(type(member) is dict and set(member)=={'device','inode','bytes','mtime_ns','sha256'});fingerprint({k:member[k] for k in ('device','inode')});need(type(member['bytes']) is int and type(member['mtime_ns']) is int and member['mtime_ns']>=0 and member['sha256']==files[path]['sha256'] and member['bytes']==files[path]['bytes'])
    else:fingerprint(data['identity'])
    intents[path]=data
   elif kind=='INTERRUPTED':need(data=='LOCAL_EFFECT_INTERRUPTED')
   elif kind=='COMPLETE':need(absent and data=='OBSERVED_OWNED_ABSENCE_STATE_RETAINED');complete=True
   else:need(False)
  return rows,intents,service_intent,absent,complete
 def _open_audit(self,plan,record):
  safe_journal(self.audit.path);self._audit_identity=identity(self.audit.path);self._context=(plan,record)
  self._db=sqlite3.connect(self.audit.path,isolation_level=None,timeout=1)
  self._db.execute('PRAGMA synchronous=FULL');self._db.execute('BEGIN IMMEDIATE')
  try:
   self._version=self._db.execute('PRAGMA data_version').fetchone()[0]
   # Full chain/schema validation while external SQLite writers are excluded.
   self._cached=self._rows();self._tail=seal(self._cached[-1]);self._db.commit()
  except Exception:self._db.rollback();raise
 @contextmanager
 def _critical(self):
  need(self._db is not None);safe_journal(self.audit.path)
  need(identity(self.audit.path)==self._audit_identity and self.audit.path.stat().st_size<=128*1024*1024)
  try:
   self._db.execute('BEGIN IMMEDIATE')
   need(self._db.execute('PRAGMA data_version').fetchone()[0]==self._version)
   head=self._db.execute('SELECT sequence,digest FROM transitions ORDER BY sequence DESC LIMIT 1').fetchone()
   need(head==(self._cached[-1]['sequence'],self._tail));self._roots(*self._context)
   yield
   self._db.commit()
  except sqlite3.DatabaseError as exc:
   self._db.rollback();raise ValueError('UNINSTALL_AUDIT_SQL_CHANGED_OR_UNAVAILABLE') from exc
  except Exception:self._db.rollback();raise
 def _append(self,plan,kind,data,guard):
  self._permit('WRITE_RECEIPT',plan,guard);need(len(self._cached)<MAX_RECORDS)
  receipt=copy.deepcopy({'kind':kind,'plan_sha256':plan['plan_sha256'],'data':data});need(len(canonical(receipt))<=65536)
  body={'sequence':len(self._cached)+1,'state':'OBSERVING','receipt':receipt,'previous_hash':self._tail};digest=seal(body)
  with self._critical():
   self._db.execute('INSERT INTO transitions VALUES (?,?,?,?,?)',(body['sequence'],body['state'],canonical(receipt).decode('ascii'),body['previous_hash'],digest))
  self._cached.append(body);self._tail=digest
 def _verify_final(self):
  with self._critical():need(self.audit.read()==self._cached)
 def _scan(self,record,plan,files,dirs,intents):
  self._roots(plan,record);code=_safe(record['plan']['code']);found_files=set();found_dirs=set()
  if code.exists():
   found_dirs.add('.')
   for directory,subdirs,names in os.walk(code,followlinks=False):
    _safe(directory)
    for n in subdirs:
     path=_safe(Path(directory)/n);relative=path.relative_to(code).as_posix();need(relative in dirs);found_dirs.add(relative)
    for n in names:
     path=_safe(Path(directory)/n);relative=path.relative_to(code).as_posix();need(relative in files)
     actual=image(path);need(actual['sha256']==files[relative]['sha256'] and actual['bytes']==files[relative]['bytes'])
     if relative in intents:need(actual==intents[relative]['identity'])
     found_files.add(relative)
  for missing in (set(files)-found_files)|(dirs-found_dirs):need(missing in intents)
 def preview(self):
  record,files,dirs=self._members();plan=self._plan(record,files);self._roots(plan,record)
  return dict(plan,public_progress_projection='NOT_CONNECTED',state='PRESERVE_ENTIRE_NAMESPACE',remove_config='BLOCKED_UNCLASSIFIED',full='BLOCKED_CLASSIFICATION_AND_SEPARATE_APPROVAL_REQUIRED')
 def _observe(self,record,plan,guard):
  self._permit('OBSERVE_SERVICE',plan,guard);result=self.boundary.call('OBSERVE_SERVICE',copy.deepcopy(plan),copy.deepcopy(record),guard)
  need(type(result) is dict and set(result)=={'service'} and result['service'] in ('ABSENT','MARKED_PENDING','PRESENT_REVIEW_REQUIRED'));need(result['service']!='PRESENT_REVIEW_REQUIRED');return result['service']
 def _result(self,status,plan):return dict(schema=SCHEMA,status=status,mode='APP_ONLY',plan_sha256=plan['plan_sha256'],state='PRESERVED_NO_CONTENT_ASSERTION',ownership='PRESERVED',absence_evidence='OBSERVATION_NOT_ACTOR_ATTRIBUTION',execution_authority=False,physical_acceptance='NOT_RUN',public_progress_projection='NOT_CONNECTED',remove_config='BLOCKED_UNCLASSIFIED',full='BLOCKED_CLASSIFICATION_AND_SEPARATE_APPROVAL_REQUIRED')
 def _run(self,mode='APP_ONLY',guard=None):
  if mode in ('REMOVE_CONFIG','FULL'):raise ValueError('UNINSTALL_MODE_BLOCKED_UNCLASSIFIED_CONFIG_DATABASE_BACKUPS_AND_SEPARATE_FULL_APPROVAL')
  need(mode=='APP_ONLY');record,files,dirs=self._members();plan=self._plan(record,files);self._roots(plan,record)
  self._permit('WRITE_RECEIPT',plan,guard)
  if hasattr(self.boundary,'admit'):self.boundary.admit(copy.deepcopy(plan),copy.deepcopy(record),guard)
  if not self.audit.path.exists():
   self._scan(record,plan,files,dirs,{})
   # Exclusive creation; never initialize/adopt an unrelated existing audit.
   fd=os.open(self.audit.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd);self.audit.initialize()
   self.audit.append('OBSERVING',{'kind':'UNINSTALL_IDENTITY','plan':plan},expected_sequence=0)
  self._open_audit(plan,record)
  rows,intents,requested,absent,complete=self._state(plan,files,dirs)
  self._scan(record,plan,files,dirs,intents)
  try:
   if not requested:
    self._permit('INSPECT_SERVICE',plan,guard)
    def service_guard(action,pin):need(pin==record['plan']['plan_sha256']);self._permit('INSPECT_SERVICE',plan,guard);return True
    self.resource.inspect(service_guard)
    self._append(plan,'SERVICE_INTENT',None,guard);self._permit('REMOVE_SERVICE',plan,guard)
    with self._critical():
     answer=self.boundary.call('REMOVE_SERVICE',copy.deepcopy(plan),copy.deepcopy(record),guard);need(type(answer) is dict and set(answer)=={'service'} and answer['service'] in ('ABSENT','MARKED_PENDING'))
    if answer['service']=='MARKED_PENDING':return self._result('SERVICE_REMOVAL_PENDING',plan)
   with self._critical():current=self._observe(record,plan,guard)
   if current=='MARKED_PENDING':return self._result('SERVICE_REMOVAL_PENDING',plan)
   if not absent:self._append(plan,'SERVICE_ABSENCE','OBSERVED_ABSENCE_NO_ACTOR_ATTRIBUTION',guard)
   if complete:
    need(not _safe(record['plan']['code']).exists());self._verify_final();return self._result('APP_ONLY_REMOVED',plan)
   code=_safe(record['plan']['code'])
   members=[(p,'FILE') for p in sorted(files)]+[(p,'DIRECTORY') for p in sorted(dirs,key=lambda x:(x.count('/'),len(x)),reverse=True) if p!='.']+[('.','DIRECTORY')]
   for relative,kind in members:
    path=_safe(code if relative=='.' else code/relative)
    self._roots(plan,record)
    if not path.exists():need(relative in intents);continue
    self._permit('REMOVE_CODE',plan,guard)
    actual=image(path) if kind=='FILE' else identity(path)
    if relative not in intents:
     if kind=='FILE':need(actual['sha256']==files[relative]['sha256'] and actual['bytes']==files[relative]['bytes'])
     else:need(not any(path.iterdir()))
     data={'path':relative,'kind':kind,'identity':actual,'parent_identity':identity(path.parent)}
     self._append(plan,'MEMBER_INTENT',data,guard);intents[relative]=data
    data=intents[relative];self._permit('REMOVE_CODE',plan,guard)
    # The INTENT above is already durably committed. This separate short
    # transaction excludes SQL writers through the fresh checks and unlink.
    with self._critical():
     need(self._observe(record,plan,guard)=='ABSENT');self._roots(plan,record)
     need(identity(path.parent)==data['parent_identity'] and (image(path) if kind=='FILE' else identity(path))==data['identity'])
     if kind=='FILE':path.unlink()
     else:need(not any(path.iterdir()));path.rmdir()
   self._append(plan,'COMPLETE','OBSERVED_OWNED_ABSENCE_STATE_RETAINED',guard);self._verify_final()
   return self._result('APP_ONLY_REMOVED',plan)
  except (OSError,ValueError):
   try:self._append(plan,'INTERRUPTED','LOCAL_EFFECT_INTERRUPTED',guard)
   except (OSError,ValueError):pass
   raise

 def run(self,mode='APP_ONLY',guard=None):
  need(not self._active);self._active=True
  try:return self._run(mode,guard)
  finally:
   if self._db is not None:self._db.close()
   self._db=None;self._cached=None;self._active=False
