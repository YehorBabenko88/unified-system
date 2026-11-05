"""Owned inactive capsule staging transaction, never an installation actuator.

The caller admits private new parent namespaces and the external manifest pin.
The caller also supplies a single local operation writer. CAS detects stale
receipts; exclusive target creation prevents overwriting concurrent resources.
Receipts prove local consistency, not ACL/owner attestation or distributed
consensus. Source Git consistency and resource capacity are NOT_EVALUATED.
Service creation, ACLs, migrations, enrollment and activation are absent.
"""
import copy
import os
from pathlib import Path
import sqlite3
import stat
from contextlib import closing
from . import lab_release
from .contracts import canonical,seal
from .journal import Journal
from .installation_progress import identifier,safe as safe_journal
from .lab_capsule_acl import _safe as safe_path

SCHEMA='unified.installation-transaction.v1'
MAX_RECORDS=64
MAX_RECEIPT_BYTES=65536
PLAN_KEYS={'schema','installation_id','node_id','operation_id','role','manifest_sha256',
 'capsule_root','install_root','state_root','release_id','sources','source_proof',
 'activation','grid_boundary','service_boundary','capacity_gate','capsule_source_provenance'}


def need(ok):
 if not ok:raise ValueError('INSTALLATION_TRANSACTION_REJECTED')


def root(path):
 p=safe_path(path)
 need(p.parent.is_dir())
 return p


def stamp(path):
 p=root(path);s=p.lstat()
 need(stat.S_ISDIR(s.st_mode) and s.st_dev>0 and s.st_ino>0)
 return {'device':s.st_dev,'inode':s.st_ino}


def validate_plan(plan):
 need(type(plan) is dict and set(plan)==PLAN_KEYS and len(canonical(plan))<=32768)
 need(plan['schema']==SCHEMA)
 for field in ('installation_id','node_id','operation_id'):identifier(plan[field])
 need(plan['role'] in ('CONTROL','WORKER','SINGLE_PC'))
 lab_release.digest(plan['manifest_sha256'])
 paths=[root(plan[field]) for field in ('capsule_root','install_root','state_root')]
 for left in paths:
  for right in paths:
   if left!=right:need(left not in right.parents)
 need(len(set(paths))==3)
 need(plan['source_proof']=='NOT_EVALUATED' and plan['activation']=='BLOCKED' and
      plan['grid_boundary']=='EXISTING_EPHEMERAL_GUARD_UNCHANGED' and
      plan['service_boundary']=='BLOCKED_NSSM_CLOSURE_SCOPED_ACL_GIT_IDENTITY_PENDING' and
      plan['capacity_gate']=='NOT_EVALUATED' and plan['capsule_source_provenance']=='PINNED_METADATA_ONLY_VERIFY_SOURCES_BEFORE_EXECUTION')
 need(type(plan['sources']) is dict and set(plan['sources'])==lab_release.MODULE_IDS)
 for source in plan['sources'].values():
  need(type(source) is dict and set(source)=={'commit','tree'})
  lab_release.digest(source['commit'],40);lab_release.digest(source['tree'],40)
 need(type(plan['release_id']) is str and 1<=len(plan['release_id'])<=80)
 return copy.deepcopy(plan)


def admit(plan,path=None):
 report=lab_release.verify_capsule(path or plan['capsule_root'],plan['manifest_sha256'])
 manifest=report['manifest']
 need(manifest['release_id']==plan['release_id'] and
      {key:{field:value[field] for field in ('commit','tree')} for key,value in manifest['sources'].items()}==plan['sources'])
 return report


def source_plan(*,capsule_root,install_root,state_root,installation_id,node_id,operation_id,role,manifest_sha256):
 """Verify exact closed bytes, bind role/roots; no mutation or runtime admission."""
 need(type(role) is str)
 if role=='SINGLE-PC':role='SINGLE_PC'
 report=lab_release.verify_capsule(capsule_root,manifest_sha256);m=report['manifest']
 return validate_plan(dict(schema=SCHEMA,installation_id=installation_id,node_id=node_id,
  operation_id=operation_id,role=role,manifest_sha256=manifest_sha256,
  capsule_root=str(root(capsule_root)),install_root=str(root(install_root)),state_root=str(root(state_root)),
  release_id=m['release_id'],sources={key:{field:value[field] for field in ('commit','tree')} for key,value in m['sources'].items()},
  source_proof='NOT_EVALUATED',activation='BLOCKED',capacity_gate='NOT_EVALUATED',
  capsule_source_provenance=report['source_provenance'],
  grid_boundary='EXISTING_EPHEMERAL_GUARD_UNCHANGED',
  service_boundary='BLOCKED_NSSM_CLOSURE_SCOPED_ACL_GIT_IDENTITY_PENDING'))


class InstallationTransaction:
 def __init__(self,plan):
  self.plan=validate_plan(plan);self.plan_hash=seal(self.plan)
  self.state=Path(self.plan['state_root']);self.install=Path(self.plan['install_root']);self.release=self.install/'release'
  self.journal=Journal(self.state/'transaction.sqlite')
 @classmethod
 def create(cls,plan):
  tx=cls(plan);admit(tx.plan)
  need(not tx.state.exists() and not tx.install.exists())
  tx.state.mkdir(exist_ok=False)
  fd=os.open(tx.journal.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
  tx.journal.initialize()
  tx.journal.append('OBSERVING',{'kind':'IDENTITY','plan':tx.plan,'state_fingerprint':stamp(tx.state)},expected_sequence=0)
  return tx
 @classmethod
 def open(cls,plan):
  tx=cls(plan);tx._read();return tx
 def _read(self):
  safe_journal(self.journal.path)
  need(self.journal.path.stat().st_size<=8*1024*1024)
  try:
   with closing(sqlite3.connect(self.journal.path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
    count=db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0];need(1<=count<=MAX_RECORDS)
    need(db.execute('SELECT COUNT(*) FROM transitions WHERE typeof(receipt)!=\'text\' OR length(CAST(receipt AS BLOB))>?',(MAX_RECEIPT_BYTES,)).fetchone()[0]==0)
   records=self.journal.read()
  except sqlite3.DatabaseError as exc:raise ValueError('INSTALLATION_TRANSACTION_REJECTED') from exc
  first=records[0]
  need(first['state']=='OBSERVING' and first['receipt']=={'kind':'IDENTITY','plan':self.plan,'state_fingerprint':stamp(self.state)})
  status='PREPARED';owned=None;release_owned=None
  for row in records[1:]:
   receipt=row['receipt']
   need(row['state']=='OBSERVING' and type(receipt) is dict and set(receipt)=={'kind','plan_sha256','fingerprint'} and receipt['plan_sha256']==self.plan_hash)
   kind=receipt['kind'];fingerprint=receipt['fingerprint']
   if kind=='RESERVED':
    need(status=='PREPARED' and fingerprint==stamp(self.install));owned=fingerprint;status='RESERVED'
   elif kind=='STAGE_INTENT':
    need(status=='RESERVED' and fingerprint==owned);status='STAGE_INTENT'
   elif kind=='STAGED_INACTIVE':
    need(status=='STAGE_INTENT' and fingerprint==stamp(self.release));release_owned=fingerprint;status='STAGED_INACTIVE'
   elif kind=='ROLLED_BACK_RETAINED':
    need(status in ('PREPARED','RESERVED','STAGE_INTENT','STAGED_INACTIVE') and fingerprint==owned);status=kind
   else:need(False)
  if owned is None:need(not self.install.exists())
  else:need(stamp(self.install)==owned)
  if release_owned is not None:need(stamp(self.release)==release_owned)
  return records,status,owned
 def _append(self,records,kind,fingerprint):
  need(len(records)<MAX_RECORDS)
  self.journal.append('OBSERVING',{'kind':kind,'plan_sha256':self.plan_hash,'fingerprint':fingerprint},expected_sequence=len(records))
 def snapshot(self):
  records,status,_=self._read()
  if status=='STAGED_INACTIVE':admit(self.plan,self.release)
  return dict(schema=SCHEMA,installation_id=self.plan['installation_id'],node_id=self.plan['node_id'],
   operation_id=self.plan['operation_id'],role=self.plan['role'],manifest_sha256=self.plan['manifest_sha256'],
   plan_sha256=self.plan_hash,transaction_receipt_sha256=seal(records[-1]),sequence=records[-1]['sequence'],status=status,
   activation='BLOCKED',installed='NOT_PROVEN',readiness='NOT_PROVEN',source_proof='NOT_EVALUATED',
   capacity_gate='NOT_EVALUATED',capsule_source_provenance=self.plan['capsule_source_provenance'],execution_authority=False,physical_acceptance='NOT_RUN',
   public_progress_projection='NOT_CONNECTED',rollback='NO_ACTIVATION_RESOURCES_RETAINED')
 def stage(self):
  records,status,owned=self._read();need(status!='ROLLED_BACK_RETAINED')
  if status=='STAGED_INACTIVE':return self.snapshot()
  admit(self.plan)
  if status=='PREPARED':
   need(not self.install.exists())
   self.install.mkdir(exist_ok=False)
   self._append(records,'RESERVED',stamp(self.install))
   records,status,owned=self._read()
  if status=='RESERVED':
   need(not self.release.exists())
   self._append(records,'STAGE_INTENT',owned)
   records,status,owned=self._read()
  need(status=='STAGE_INTENT' and not self.release.exists())
  # Existing stage_capsule exclusively creates its target. A crash after target
  # creation but before its completion receipt is ambiguous and never adopted.
  lab_release.stage_capsule(self.plan['capsule_root'],self.release,self.plan['manifest_sha256'])
  admit(self.plan,self.release)
  self._append(records,'STAGED_INACTIVE',stamp(self.release))
  return self.snapshot()
 def resume(self):return self.stage()
 def rollback(self):
  """Logical rollback only: no activation ever occurred; retain every byte.

  No recursive deletion, service changes, data/configuration or ACL mutation.
  This receipt is not proof that a running service was stopped or uninstalled.
  """
  records,status,owned=self._read()
  if status!='ROLLED_BACK_RETAINED':self._append(records,'ROLLED_BACK_RETAINED',owned)
  return self.snapshot()
