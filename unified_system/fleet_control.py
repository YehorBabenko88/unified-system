"""Durable disposable PLAN_ONLY model; caller votes are not consensus evidence."""
from contextlib import contextmanager
import copy
import json
import math
from pathlib import Path
import sqlite3
import uuid

class FleetError(ValueError): pass

def resources(v):
    if not isinstance(v,dict) or set(v)!={'cpu','memory','disk'} or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in v.values()): raise FleetError('resource schema')
    return dict(v)

def integer(v):
    if type(v) is not int or v<0: raise FleetError('integer required')
    return v

@contextmanager
def connection(*args,**kwargs):
    c=sqlite3.connect(*args,**kwargs)
    try:
        with c: yield c
    finally: c.close()

class FleetControl:
    def __init__(self,path,voters,*,max_pages=None):
        self.path=Path(path)
        self.max_pages=max_pages
        if not voters or len(voters)!=len(set(voters)): raise FleetError('voters')
        self.voters=sorted(voters)
        with connection(self.path) as c:
            c.execute('CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
            state={'voters':self.voters,'nodes':{},'jobs':{},'leader':None,'term':0,'clock':0,'incarnation':uuid.uuid4().hex,'counter':0}
            c.execute('INSERT OR IGNORE INTO ledger VALUES(1,?)',(json.dumps(state),))
            if json.loads(c.execute('SELECT body FROM ledger').fetchone()[0])['voters']!=self.voters: raise FleetError('voter configuration mismatch')
    def _transaction(self,fn,*,readonly=False):
        try:
            with connection(self.path.resolve().as_uri()+('?mode=ro' if readonly else '?mode=rw'),uri=True,timeout=1) as c:
                if not readonly and self.max_pages is not None: c.execute(f'PRAGMA max_page_count={integer(self.max_pages)}')
                c.execute('BEGIN' if readonly else 'BEGIN IMMEDIATE')
                s=json.loads(c.execute('SELECT body FROM ledger WHERE id=1').fetchone()[0])
                self._validate(s)
                out=fn(s)
                self._validate(s)
                if not readonly: c.execute('UPDATE ledger SET body=? WHERE id=1',(json.dumps(s,sort_keys=True),))
                return copy.deepcopy(out)
        except (sqlite3.Error,OSError,TypeError,json.JSONDecodeError) as e: raise FleetError('ledger unavailable') from e
    def _validate(self,s):
        """Reject corrupt persisted authority/schema; hashes are not host attestation."""
        try:
            if set(s)!={'voters','nodes','jobs','leader','term','clock','incarnation','counter'} or s['voters']!=self.voters:
                raise FleetError('ledger schema')
            for key in ('term','clock','counter'): integer(s[key])
            if type(s['incarnation']) is not str or not s['incarnation']: raise FleetError('incarnation')
            for ident,n in s['nodes'].items():
                if set(n)!={'id','epoch','domain','approval','state','sequence','heartbeat','available'} or n['id']!=ident or n['state'] not in ('APPROVED','ACTIVE','DRAINING'): raise FleetError('node schema')
                if integer(n['epoch'])<1 or not n['approval'] or not n['domain']: raise FleetError('node identity')
                integer(n['sequence'])
                if n['heartbeat'] is not None: integer(n['heartbeat']); resources(n['available'])
            if s['leader'] is not None:
                if set(s['leader'])!={'id','expires'} or s['leader']['id'] not in self.voters: raise FleetError('leader schema')
                integer(s['leader']['expires'])
            for j in s['jobs'].values():
                if set(j)!={'spec','lease'} or set(j['spec'])!={'requirements','avoid_domains'}: raise FleetError('job schema')
                resources(j['spec']['requirements'])
                if type(j['spec']['avoid_domains']) is not list or any(type(x) is not str for x in j['spec']['avoid_domains']): raise FleetError('domains')
                lease=j['lease']
                if lease is not None:
                    if set(lease)!={'node','epoch','term','expires','token','execution_authorized'} or lease['execution_authorized'] is not False or lease['node'] not in s['nodes'] or type(lease['token']) is not str: raise FleetError('lease schema')
                    for key in ('epoch','term','expires'): integer(lease[key])
        except (KeyError,TypeError,AttributeError) as exc: raise FleetError('ledger corrupt') from exc
    @staticmethod
    def _time(s,now):
        integer(now)
        if now<s['clock']: raise FleetError('clock rollback')
        s['clock']=now
    def approve_node(self,machine_id,identity_epoch,failure_domain,owner_approval):
        if not all(type(x) is str and x for x in (machine_id,failure_domain,owner_approval)) or integer(identity_epoch)<1: raise FleetError('approval required')
        def op(s):
            old=s['nodes'].get(machine_id)
            if old and identity_epoch<=old['epoch']: raise FleetError('epoch must advance')
            s['nodes'][machine_id]={'id':machine_id,'epoch':identity_epoch,'domain':failure_domain,'approval':owner_approval,'state':'APPROVED','sequence':0,'heartbeat':None,'available':None}
        return self._transaction(op)
    def heartbeat(self,machine_id,identity_epoch,sequence,now,available):
        available=resources(available); integer(sequence); integer(identity_epoch)
        def op(s):
            self._time(s,now); n=s['nodes'].get(machine_id)
            if not n or n['epoch']!=identity_epoch or sequence<=n['sequence']: raise FleetError('identity/sequence')
            if n['state'] not in ('APPROVED','ACTIVE','DRAINING'): raise FleetError('node unavailable')
            n.update(sequence=sequence,heartbeat=now,available=available)
            if n['state']!='DRAINING': n['state']='ACTIVE'
        return self._transaction(op)
    def elect(self,term,leader,votes,now,ttl):
        integer(term); integer(ttl)
        def op(s):
            self._time(s,now)
            if term<=s['term'] or leader not in self.voters or len(votes)!=len(set(votes)) or not set(votes)<=set(self.voters) or len(votes)<=len(self.voters)//2 or ttl<1: raise FleetError('no new quorum term')
            s.update(term=term,leader={'id':leader,'expires':now+ttl})
        return self._transaction(op)
    def submit(self,job_id,requirements,avoid_domains=()):
        spec={'requirements':resources(requirements),'avoid_domains':sorted(set(avoid_domains))}
        if not isinstance(job_id,str) or not job_id or any(not isinstance(x,str) or not x for x in avoid_domains): raise FleetError('job schema')
        def op(s):
            old=s['jobs'].get(job_id)
            if old and old['spec']!=spec: raise FleetError('idempotency conflict')
            if not old: s['jobs'][job_id]={'spec':spec,'lease':None}
        return self._transaction(op)
    def place(self,job_id,now,term,ttl=60):
        integer(ttl); integer(term)
        def op(s):
            self._time(s,now)
            if term!=s['term'] or not s['leader'] or s['leader']['expires']<=now or ttl<1: raise FleetError('no leader')
            job=s['jobs'].get(job_id)
            if not job: raise FleetError('unknown job')
            old=job['lease']
            if old and old['expires']>now:
                if self._valid(s,old,now): return old
                raise FleetError('previous lease must expire')
            used={n:{k:0 for k in ('cpu','memory','disk')} for n in s['nodes']}
            for j in s['jobs'].values():
                lease=j['lease']
                if lease and lease['expires']>now:
                    for k,v in j['spec']['requirements'].items(): used[lease['node']][k]+=v
            for ident,n in sorted(s['nodes'].items()):
                if n['state']!='ACTIVE' or n['heartbeat'] is None or not 0<=now-n['heartbeat']<=30 or n['domain'] in job['spec']['avoid_domains']: continue
                if any(used[ident][k]+v>n['available'][k]*.85 for k,v in job['spec']['requirements'].items()): continue
                s['counter']+=1
                lease={'node':ident,'epoch':n['epoch'],'term':term,'expires':now+ttl,'token':f"{s['incarnation']}:{s['counter']}",'execution_authorized':False}
                job['lease']=lease; return lease
            raise FleetError('no safe capacity')
        return self._transaction(op)
    @staticmethod
    def _valid(s,lease,now):
        n=s['nodes'].get(lease['node'])
        return bool(n and n['epoch']==lease['epoch'] and n['heartbeat'] is not None and 0<=now-n['heartbeat']<=30 and n['state'] in ('ACTIVE','DRAINING') and lease['term']==s['term'] and lease['expires']>now and s['leader'] and s['leader']['expires']>now)
    def validate_lease(self,job_id,token,now):
        def op(s):
            self._time(s,now); lease=s['jobs'].get(job_id,{}).get('lease')
            return bool(lease and lease['token']==token and self._valid(s,lease,now))
        return self._transaction(op)
    def drain(self,machine_id):
        def op(s):
            if machine_id not in s['nodes']: raise FleetError('unknown node')
            s['nodes'][machine_id]['state']='DRAINING'
        return self._transaction(op)
    def snapshot(self,now):
        integer(now)
        def op(s):
            out=copy.deepcopy(s)
            for n in out['nodes'].values():
                if n['heartbeat'] is not None and n['state']=='ACTIVE':
                    age=now-n['heartbeat']; n['state']='OFFLINE' if age>60 else ('SUSPECT' if age>30 else ('QUARANTINED' if age<0 else 'ACTIVE'))
            return {'mode':'PLAN_ONLY','execution_authorized':False,'source_provenance':'NOT_EVALUATED','physical':'NOT_RUN','production':'NO_GO',**out}
        return self._transaction(op,readonly=True)
    def status_snapshot(self,now_ms):
        """Read-only display adapter; unknown utilization/database sizes stay null."""
        integer(now_ms)
        raw=self.snapshot(now_ms//1000)
        nodes=[]
        for n in raw['nodes'].values():
            nodes.append({'id':n['id'],'epoch':n['epoch'],'sequence':n['sequence'],
                          'state':n['state'],'zone':n['domain'],'modules':[],
                          'last_heartbeat_ms':None if n['heartbeat'] is None else n['heartbeat']*1000,
                          'cpu':None,'memory':None,'disk':None,'available_resources':n['available'],
                          'db_sizes':None,'identity_verified':False})
        return {'mode':'PLAN_ONLY','status':'PLAN_ONLY','execution_authorized':False,
                'nodes':sorted(nodes,key=lambda n:n['id']),'links':[],'databases':[],
                'alerts':[],'source_provenance':'NOT_EVALUATED','physical':'NOT_RUN','production':'NO_GO'}
    def backup(self,target):
        if Path(target).exists(): raise FleetError('backup target exists')
        try:
            with connection(self.path.resolve().as_uri()+'?mode=ro',uri=True) as src, connection(target) as dst: src.backup(dst)
        except sqlite3.Error as e: raise FleetError('backup failed') from e
    @classmethod
    def restore(cls,backup,target,voters):
        if Path(target).exists(): raise FleetError('restore target exists')
        try:
            with connection(Path(backup).resolve().as_uri()+'?mode=ro',uri=True) as src, connection(target) as dst: src.backup(dst)
            f=cls(target,voters)
            def invalidate(s):
                s.update(incarnation=uuid.uuid4().hex,leader=None)
                for j in s['jobs'].values(): j['lease']=None
                for n in s['nodes'].values(): n.update(state='APPROVED',heartbeat=None)
            f._transaction(invalidate); return f
        except sqlite3.Error as e: raise FleetError('restore failed') from e
