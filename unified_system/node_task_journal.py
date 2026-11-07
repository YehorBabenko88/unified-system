"""Bounded typed node receipts over Journal. No authorization or consensus."""
import copy
import os
from contextlib import closing
import re
import sqlite3
import stat
from pathlib import Path
from .contracts import canonical, ContractError
from .journal import Journal

SCHEMA = 'unified.node-operation.v2'
RECEIPT_SCHEMA = 'unified.node-task-journal.v1'
OPERATIONS = frozenset(('READ_INVENTORY','VERIFY_ARTIFACT','VERIFY_CONFIGURATION','CHECK_SERVICE','CHECK_HEALTH','PREPARE_INSTALL','PREPARE_UPDATE','VERIFY_RELEASE','COLLECT_LOGS','REPORT_STATUS','REQUEST_DRAIN','VERIFY_BACKUP','PREPARE_ROLLBACK'))
FIELDS = frozenset(('schema','task_id','cluster_id','node_id','node_incarnation','release_id','artifact_sha256','operation_type','approval_reference','authority_generation','lease_fencing_proof','preconditions','expected_postconditions','timeout_seconds','rollback_policy','idempotency_key','result_receipt'))
CHAIN = ('CREATED','VERIFIED','AUTHORIZED','PREPARED','RUNNING','VERIFYING','COMPLETED')
TERMINAL = frozenset(('BLOCKED','FAILED','INTERRUPTED','RECOVERY_REQUIRED','ROLLBACK_REQUIRED','CANCELLED','UNKNOWN_OUTCOME','COMPLETED'))
STATES = frozenset(CHAIN) | TERMINAL

class NodeJournalError(ValueError):
    """Closed diagnostic; never includes untrusted contents or native error text."""


def need(condition):
    if not condition:
        raise NodeJournalError('NODE_OPERATION_REJECTED')


def identifier(value):
    need(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}',value) is not None)


class NodeOperation:
    @staticmethod
    def parse(value):
        need(type(value) is dict and set(value) == FIELDS)
        need(value['schema'] == SCHEMA)
        for name in ('task_id','cluster_id','node_id','node_incarnation','release_id','approval_reference','idempotency_key'):
            identifier(value[name])
        need(type(value['artifact_sha256']) is str and re.fullmatch('[a-f0-9]{64}',value['artifact_sha256']) is not None)
        need(type(value['operation_type']) is str and value['operation_type'] in OPERATIONS)
        # Canonical UUIDv4 reference only; provenance UNKNOWN, never authority.
        need(type(value['authority_generation']) is str and re.fullmatch('[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',value['authority_generation']) is not None)
        need(type(value['timeout_seconds']) is int and 1 <= value['timeout_seconds'] <= 60)
        need(type(value['rollback_policy']) is str and value['rollback_policy'] in ('NONE','PLAN_ONLY'))
        # References only: opaque proof payloads and arbitrary predicates are not accepted.
        proof=value['lease_fencing_proof']
        need(type(proof) is dict and set(proof)=={'reference'})
        identifier(proof['reference'])
        for name in ('preconditions','expected_postconditions'):
            need(type(value[name]) is list and len(value[name]) <= 16)
            for item in value[name]:
                need(type(item) is dict and set(item)=={'check','expected'})
                need(type(item['check']) is str and item['check'] in ('LOCAL_RECEIPT_INTEGRITY','LOCAL_JOURNAL_AVAILABLE'))
                need(type(item['expected']) is str and item['expected'] in ('PASS','UNKNOWN'))
        need(value['result_receipt'] is None)
        need(len(canonical(value)) <= 8192)
        return copy.deepcopy(value)


def validate_receipt(value):
    need(type(value) is dict and set(value) <= {'code','authority','source','freshness','effects_authorized','journal_integrity','physical_acceptance'})
    for key,item in value.items():
        if key=='effects_authorized': need(item is False)
        elif key in ('authority','source','freshness'): need(item=='UNKNOWN')
        elif key=='physical_acceptance': need(item=='NOT_RUN')
        elif key=='journal_integrity': need(item=='PASS')
        else: need(type(item) is str and re.fullmatch('[A-Z_]{1,64}',item) is not None)
    return copy.deepcopy(value)


class NodeTaskJournal:
    """Private single-writer lifecycle. Capacity exhaustion blocks; never prunes evidence.

    Parent directory ownership/ACL is a deployment prerequisite. File checks are
    namespace hygiene, not protection against a hostile local administrator.
    """
    def __init__(self,path,*,max_records=10000,max_bytes=16*1024*1024):
        need(type(max_records) is int and 1 <= max_records <= 100000)
        need(type(max_bytes) is int and 4096 <= max_bytes <= 64*1024*1024)
        self.path=Path(path).absolute()
        self.max_records=max_records;self.max_bytes=max_bytes
        self._journal=Journal(self.path)
        self._identity=None
        self._safe_path()
        if self.path.exists(): self._identity=self._file_identity()

    def _file_identity(self):
        info=self.path.lstat()
        need(info.st_nlink==1 and info.st_ino!=0)
        return (info.st_dev,info.st_ino)

    def _safe_path(self):
        need(len(str(self.path)) <= 1024 and not str(self.path).startswith(('\\\\','//')))
        for part in (*reversed(self.path.parents),self.path):
            if not part.exists() and not part.is_symlink():
                need(part == self.path and self._identity is None)
                continue
            info=part.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
            need(stat.S_ISREG(info.st_mode) if part==self.path else stat.S_ISDIR(info.st_mode))
        if self.path.exists():
            need(self.path.stat().st_size <= self.max_bytes)
            identity=self._file_identity()
            if self._identity is not None: need(identity==self._identity)

    def _inventory(self):
        # Read-only schema inventory: Journal.read alone ignores foreign tables.
        with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
            need(db.execute('PRAGMA quick_check').fetchmany(2)==[('ok',)])
            objects=db.execute('SELECT type,name,tbl_name FROM sqlite_master ORDER BY name LIMIT 3').fetchall()
            need(objects==[('table','transitions','transitions')])
            columns=db.execute('PRAGMA table_info(transitions)').fetchall()
            need(columns==[(0,'sequence','INTEGER',0,None,1),(1,'state','TEXT',1,None,0),(2,'receipt','TEXT',0,None,0),(3,'previous_hash','TEXT',1,None,0),(4,'digest','TEXT',1,None,0)])


    def _records(self):
        try:
            self._safe_path()
            if self.path.exists(): self._inventory()
            rows=self._journal.read()
            if self.path.exists(): need(bool(rows))
            need(len(rows) <= self.max_records)
            latest={};keys={}
            for row in rows:
                record=row['receipt']
                need(row['state']=='OBSERVING' and type(record) is dict and set(record)=={'schema','intent','state','receipt'})
                need(record['schema']==RECEIPT_SCHEMA and record['state'] in STATES)
                intent=NodeOperation.parse(record['intent']);validate_receipt(record['receipt'])
                task=intent['task_id'];key=intent['idempotency_key']
                if task in latest:
                    need(latest[task]['intent']==intent)
                    self._check_transition(latest[task]['state'],record['state'])
                else:
                    need(record['state']=='CREATED' and key not in keys)
                keys[key]=task;latest[task]=record
            return rows,latest,keys
        except NodeJournalError: raise
        except (OSError,sqlite3.Error,ContractError,ValueError,TypeError,KeyError):
            raise NodeJournalError('NODE_JOURNAL_UNAVAILABLE') from None

    @staticmethod
    def _check_transition(old,new):
        need(old not in TERMINAL)
        need(new in TERMINAL-{'COMPLETED'} or (old in CHAIN[:-1] and new==CHAIN[CHAIN.index(old)+1]))

    def _append(self,record,count):
        need(count < self.max_records)
        need(len(canonical(record)) <= 12288)
        # Reserve worst-case SQLite page growth before writes. No deletion/rotation.
        current=self.path.stat().st_size if self.path.exists() else 0
        need(current + 32768 <= self.max_bytes)
        descriptor=None
        try:
            self._safe_path()
            if self._identity is None:
                descriptor=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)
                facts=os.fstat(descriptor)
                need(facts.st_nlink==1 and facts.st_ino!=0)
                self._identity=(facts.st_dev,facts.st_ino)
                self._safe_path()
                self._journal.initialize()
                self._safe_path()
            self._inventory()
            self._safe_path()
            self._journal.append('OBSERVING',record,expected_sequence=count)
        except (OSError,sqlite3.Error,ContractError):
            raise NodeJournalError('NODE_JOURNAL_WRITE_FAILED') from None
        finally:
            if descriptor is not None: os.close(descriptor)
        self._safe_path()
        return copy.deepcopy(record)

    def create(self,intent):
        intent=NodeOperation.parse(intent)
        rows,latest,keys=self._records();task=intent['task_id'];key=intent['idempotency_key']
        if task in latest:
            need(latest[task]['intent']==intent)
            return copy.deepcopy(latest[task])
        need(key not in keys)
        return self._append(dict(schema=RECEIPT_SCHEMA,intent=intent,state='CREATED',receipt={}),len(rows))

    def get(self,task_id):
        identifier(task_id)
        _,latest,_=self._records();need(task_id in latest)
        return copy.deepcopy(latest[task_id])

    def transition(self,task_id,state,receipt=None):
        identifier(task_id);need(type(state) is str and state in STATES)
        rows,latest,_=self._records();need(task_id in latest)
        old=latest[task_id];self._check_transition(old['state'],state)
        record=dict(old,state=state,receipt=validate_receipt({} if receipt is None else receipt))
        return self._append(record,len(rows))

    def snapshot(self):
        return copy.deepcopy(list(self._records()[1].values()))

    def reconcile(self):
        # Observations here prove only receipt integrity. No execution is replayed.
        for record in self.snapshot():
            state=record['state']
            if state not in TERMINAL:
                target='UNKNOWN_OUTCOME' if state in ('RUNNING','VERIFYING') else 'INTERRUPTED'
                self.transition(record['intent']['task_id'],target,{'code':'RESTART_RECONCILIATION','authority':'UNKNOWN','source':'UNKNOWN','freshness':'UNKNOWN','effects_authorized':False})
        return self.snapshot()
