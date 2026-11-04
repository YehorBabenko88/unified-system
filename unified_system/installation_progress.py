"""Local durable installer display receipts over Journal, never installation authority.

The caller must admit a private parent directory and externally pin the release
manifest. This library does not attest or modify ACLs, run installers, or provide
distributed consensus. Identifiers must be public opaque labels, never secrets.
"""
import os
import re
import stat
import sqlite3
from pathlib import Path
from .contracts import ContractError, canonical
from .journal import Journal

PHASES=('PREPARE','DOWNLOAD','VERIFY','DEPENDENCIES','DATABASE','SERVICES',
        'READINESS','WORKER','HISTORY','RESEARCH','TERMINAN_HANDOFF')
OUTCOMES=frozenset(('PASS','FAIL','BLOCKED','NOT_RUN'))
ERROR_CODES=frozenset(('NONE','INVALID_INPUT','INTEGRITY_FAILED','DEPENDENCY_FAILED',
    'DATABASE_FAILED','SERVICE_FAILED','READINESS_FAILED','WORKER_UNAVAILABLE',
    'SOURCE_UNAVAILABLE','INTERRUPTED','OWNER_APPROVAL_REQUIRED','IO_FAILED'))
SCHEMA='unified.installation-progress.v1'
_ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
_IDENTITY={'schema','kind','installation_id','node_id','release_manifest_sha256'}
_EVENT=_IDENTITY|{'receipt_id','operation_id','correlation_id','timestamp_ms','phase','outcome','error_code'}


def need(value):
    if not value:raise ContractError('invalid installation progress')


def identifier(value):
    need(type(value) is str and _ID.fullmatch(value) is not None)
    return value


def safe(path, *, exists=True):
    path=Path(path)
    need(path.is_absolute() and '..' not in path.parts)
    for item in (path,*path.parents):
        if not item.exists():
            need(item==path and not exists and not item.is_symlink());continue
        info=item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0)&0x400))
        if item==path:
            need(stat.S_ISREG(info.st_mode) and info.st_nlink==1)
        else:need(stat.S_ISDIR(info.st_mode))
    # SQLite sidecars must not redirect accesses to another owner's files.
    for suffix in ('-journal','-wal','-shm'):
        side=Path(str(path)+suffix)
        if side.exists() or side.is_symlink():
            info=side.lstat()
            need(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode) and info.st_nlink==1 and not (getattr(info,'st_file_attributes',0)&0x400))
    return path


class InstallationProgress:
    def __init__(self,path,installation_id,node_id,release_manifest_sha256):
        self.path=Path(path)
        need(type(release_manifest_sha256) is str and re.fullmatch('[a-f0-9]{64}',release_manifest_sha256) is not None)
        self.identity=dict(schema=SCHEMA,kind='identity',installation_id=identifier(installation_id),
            node_id=identifier(node_id),release_manifest_sha256=release_manifest_sha256)
        self.journal=Journal(self.path)

    @classmethod
    def create(cls,path,installation_id,node_id,release_manifest_sha256):
        progress=cls(path,installation_id,node_id,release_manifest_sha256)
        safe(progress.path,exists=False)
        try:
            fd=os.open(progress.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except OSError as exc:raise ContractError('progress creation rejected') from exc
        os.close(fd)
        # A failed initialization remains an unadoptable file; never overwrite it.
        progress.journal.initialize()
        progress.journal.append('OBSERVING',progress.identity,expected_sequence=0)
        return progress

    @classmethod
    def open(cls,path,installation_id,node_id,release_manifest_sha256):
        progress=cls(path,installation_id,node_id,release_manifest_sha256)
        progress._read()
        return progress

    def _validate_event(self,event,previous):
        need(type(event) is dict and set(event) in (_EVENT,_EVENT|{'done','total'}))
        need({key:event[key] for key in _IDENTITY}==dict(self.identity,kind='progress'))
        for name in ('receipt_id','operation_id','correlation_id'):identifier(event[name])
        need(type(event['timestamp_ms']) is int and 0<=event['timestamp_ms']<=253402300799999)
        need(type(event['phase']) is str and event['phase'] in PHASES)
        need(type(event['outcome']) is str and event['outcome'] in OUTCOMES)
        need(type(event['error_code']) is str and event['error_code'] in ERROR_CODES)
        need((event['outcome']=='PASS' and event['error_code']=='NONE') or event['outcome']!='PASS')
        if 'done' in event:
            need(type(event['done']) is int and type(event['total']) is int and 0<=event['done']<=event['total']<=2**53-1 and event['total']>0)
        if previous:
            need(event['operation_id']==previous['operation_id'] and event['correlation_id']==previous['correlation_id'])
            need(event['timestamp_ms']>=previous['timestamp_ms'])
            need(PHASES.index(event['phase'])>=PHASES.index(previous['phase']))
            if event['phase']==previous['phase'] and 'done' in previous:
                need('done' in event and event['total']==previous['total'] and event['done']>=previous['done'])

    def _read(self):
        safe(self.path)
        try:rows=self.journal.read()
        except (OSError,ValueError,TypeError,sqlite3.DatabaseError) as exc:raise ContractError('progress journal rejected') from exc
        need(rows and rows[0]['state']=='OBSERVING' and rows[0]['receipt']==self.identity)
        events=[];ids=set()
        for row in rows[1:]:
            need(row['state']=='OBSERVING')
            event=row['receipt'];self._validate_event(event,events[-1] if events else None)
            need(event['receipt_id'] not in ids);ids.add(event['receipt_id']);events.append(event)
        return rows,events

    def append(self,*,receipt_id,operation_id,correlation_id,timestamp_ms,phase,outcome,error_code='NONE',**counts):
        need(set(counts) in (set(),{'done','total'}))
        event=dict(self.identity,kind='progress',receipt_id=receipt_id,operation_id=operation_id,
            correlation_id=correlation_id,timestamp_ms=timestamp_ms,phase=phase,outcome=outcome,error_code=error_code,**counts)
        rows,events=self._read()
        # Validate duplicate shape before comparing, and never echo rejected input.
        self._validate_event(event,None)
        for old in events:
            if old['receipt_id']==receipt_id:
                need(canonical(old)==canonical(event));return old
        self._validate_event(event,events[-1] if events else None)
        safe(self.path)
        self.journal.append('OBSERVING',event,expected_sequence=len(rows))
        return event

    def snapshot(self):
        rows,events=self._read()
        public=[]
        for event in events:
            item=dict(event)
            if 'done' in item:item['percentage']=100*item['done']/item['total']
            public.append(item)
        return dict(schema=SCHEMA,installation_id=self.identity['installation_id'],node_id=self.identity['node_id'],
            release_manifest_sha256=self.identity['release_manifest_sha256'],sequence=rows[-1]['sequence'],
            last_timestamp_ms=events[-1]['timestamp_ms'] if events else None,events=public,
            authority=False,installed='NOT_PROVEN',readiness='NOT_PROVEN',durability='LOCAL_JOURNAL_ONLY')
