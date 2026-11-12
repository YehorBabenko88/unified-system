"""Bounded local effect bookkeeping over Journal; never an approval/capability.

The genuine owner factory must separately admit protected namespace custody and
hold its phase lock around admission/effects. This object performs no effects
beyond its own files, and cannot authorize an operation or reconstruct a Job.
"""
from contextlib import closing
from dataclasses import dataclass
import sqlite3

from .collector_logging import _new, _read, _plain
from .collector_service_plan import _digest, _label, _need
from .lab_capsule_acl import _safe
from .lab_release import canonical
from .journal import Journal

SCHEMA='unified.collector.phase-effects.v2'
# Structural ceiling for the fixed finite graph, not a performance claim.
MAX_EVENTS=128
MAX_BYTES=2*1024*1024
EFFECT_ACTIONS=frozenset(('BEGIN','WRITE_RECEIPT','STAGE','SEAL','REGISTER',
 'CREATE_ACTIVATION_REVISION','WRITE_ACTIVATION_ARTIFACT','SEAL_ACTIVATION_REVISION',
 'COMMIT_ACTIVATION_POINTER','SERVICE_START','SERVICE_STOP',
 'REVOKE_COLLECTOR_ACTIVATION','RUN_FINITE_CAPTURE','RETIRE_OWNED_CHILD'))


@dataclass(frozen=True)
class _Ticket:
 phase_id:str
 effect_key:str
 action:str
 plan_sha256:str


class CollectorEffectJournal:
 @classmethod
 def create(cls,root,*,phase_id,intent_sha256):
  _label(phase_id);_digest(intent_sha256);root=_safe(root)
  _need(root.parent.is_dir() and not root.exists());root.mkdir(exist_ok=False)
  value=cls(root,phase_id,intent_sha256)
  _new(root/'phase-owned.json',value._marker)
  value._journal.initialize();value._scan();return value

 @classmethod
 def open(cls,root,*,phase_id,intent_sha256):
  _label(phase_id);_digest(intent_sha256);root=_safe(root);_need(root.is_dir())
  value=cls(root,phase_id,intent_sha256);value._scan();return value

 def __init__(self,root,phase_id,intent_sha256):
  self.root=root;self.phase_id=phase_id;self.intent_sha256=intent_sha256
  info=_plain(root,True);self._root_identity=(info.st_dev,info.st_ino)
  self._marker=canonical(dict(schema=SCHEMA,phase_id=phase_id,intent_sha256=intent_sha256,
                              root_identity=list(self._root_identity)))
  self._journal=Journal(root/'effects.sqlite');self._ticket=None

 def _scan(self):
  info=_plain(self.root,True);_need((info.st_dev,info.st_ino)==self._root_identity)
  _need(_read(self.root/'phase-owned.json',8192)==self._marker)
  path=self._journal.path;before=_plain(path);_need(before.st_size<=MAX_BYTES)
  _need({p.name for p in self.root.iterdir()}=={'phase-owned.json','effects.sqlite'})
  header=_read(path,MAX_BYTES)
  _need(len(header)>=100 and header[:16]==b'SQLite format 3\0' and header[18:20]==b'\x01\x01')
  with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
   _need(db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]<=MAX_EVENTS)
   _need(db.execute("SELECT COUNT(*) FROM transitions WHERE typeof(receipt)!='text' OR length(CAST(receipt AS BLOB))>65536").fetchone()[0]==0)
  rows=self._journal.read();after=_plain(path)
  _need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
        (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns))
  effects={};pending=None;unknown=False
  fields={'schema','phase_id','intent_sha256','event','effect_key','action','plan_sha256','outcome_sha256','reason_code'}
  for row in rows:
   r=row['receipt'];_need(row['state']=='OBSERVING' and type(r) is dict and set(r)==fields)
   _need(r['schema']==SCHEMA and r['phase_id']==self.phase_id and r['intent_sha256']==self.intent_sha256)
   _label(r['effect_key']);_digest(r['plan_sha256'])
   _need(type(r['action']) is str and r['action'] in EFFECT_ACTIONS)
   key=r['effect_key'];event=r['event']
   if event=='ATTEMPTED':
    _need(key not in effects and pending is None and not unknown and r['outcome_sha256'] is None and r['reason_code'] is None)
    effects[key]=r;pending=key
   else:
    _need(event in ('CONFIRMED','UNKNOWN') and pending==key and key in effects)
    _need(all(r[k]==effects[key][k] for k in ('action','plan_sha256')))
    if event=='CONFIRMED':_digest(r['outcome_sha256']);_need(r['reason_code'] is None)
    else:_label(r['reason_code']);_need(r['outcome_sha256'] is None);unknown=True
    effects[key]=r;pending=None
  return rows,effects,pending,unknown

 def _append(self,event,ticket,*,expected_sequence,outcome=None,reason=None):
  rows,_,_,_=self._scan();_need(len(rows)==expected_sequence and len(rows)<MAX_EVENTS)
  receipt=dict(schema=SCHEMA,phase_id=self.phase_id,intent_sha256=self.intent_sha256,
   event=event,effect_key=ticket.effect_key,action=ticket.action,plan_sha256=ticket.plan_sha256,
   outcome_sha256=outcome,reason_code=reason)
  self._journal.append('OBSERVING',receipt,expected_sequence=expected_sequence)

 def attempt(self,effect_key,action,plan_sha256):
  _label(effect_key);_digest(plan_sha256);_need(type(action) is str and action in EFFECT_ACTIONS)
  rows,effects,pending,unknown=self._scan()
  _need(self._ticket is None and pending is None and not unknown and effect_key not in effects and len(rows)+2<=MAX_EVENTS)
  ticket=_Ticket(self.phase_id,effect_key,action,plan_sha256)
  self._append('ATTEMPTED',ticket,expected_sequence=len(rows));self._ticket=ticket;return ticket

 def _owned(self,ticket):
  _need(type(ticket) is _Ticket and self._ticket is ticket)
  rows,effects,pending,unknown=self._scan()
  _need(not unknown and pending==ticket.effect_key and effects[pending]['event']=='ATTEMPTED')
  return len(rows)

 def confirm(self,ticket,outcome_sha256):
  _digest(outcome_sha256);sequence=self._owned(ticket)
  self._append('CONFIRMED',ticket,expected_sequence=sequence,outcome=outcome_sha256);self._ticket=None

 def unknown(self,ticket,reason_code):
  _label(reason_code);sequence=self._owned(ticket)
  self._append('UNKNOWN',ticket,expected_sequence=sequence,reason=reason_code);self._ticket=None

 def status(self):
  rows,effects,pending,unknown=self._scan()
  return dict(schema=SCHEMA,phase_id=self.phase_id,intent_sha256=self.intent_sha256,
   state='UNKNOWN' if pending is not None or unknown else 'READY',events=len(rows),
   confirmed_effects=sum(r['event']=='CONFIRMED' for r in effects.values()),
   execution_authority=False)
