"""Conservative application-byte accounting and closed Egress projection.

SQLite here is single-node enforcement/projection, never distributed authority.
Runtime/native admission factories intentionally remain unavailable. Isolated
stores require an owned empty test directory; no schema of another module is used.
"""
import contextlib
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time

NODES = frozenset(('LS5','PC1','PC2','PC3','PC4','LS7'))
CLASSES = frozenset(('control','live','bulk'))
MAX_U63 = 9223372036854775807


class BudgetError(ValueError):
    pass


def _need(ok, reason='BUDGET_REJECTED'):
    if not ok:
        raise BudgetError(reason)


def _integer(value, minimum=0, maximum=10**12):
    _need(type(value) is int and minimum <= value <= maximum)
    return value


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def _path(path):
    path=Path(path).absolute()
    if path.exists():
        _need(path.is_file() and path.stat().st_nlink==1,'BUDGET_UNSAFE_PATH')
    for p in (path,*path.parents):
        if p.exists():
            _need(not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&1024,'BUDGET_UNSAFE_PATH')
    _need(path.parent.is_dir(),'BUDGET_PARENT_REQUIRED')
    return path


class BandwidthPolicy:
    def __init__(self, allocations, *, cluster_rate, cluster_burst, classes):
        _need(type(allocations) is dict and set(allocations)==NODES)
        _need(type(classes) is dict and set(classes)==CLASSES and all(type(v) is int and v>0 for v in classes.values()) and sum(classes.values())==100)
        self._allocations={}
        for node,row in allocations.items():
            _need(type(row) is dict and set(row)=={'rate','burst'})
            self._allocations[node]={k:_integer(v,100) for k,v in row.items()}
        self.cluster_rate=_integer(cluster_rate,1);self.cluster_burst=_integer(cluster_burst,1)
        _need(sum(r['rate'] for r in self._allocations.values())<=self.cluster_rate,'CLUSTER_RATE_EXCEEDED')
        _need(sum(r['burst'] for r in self._allocations.values())<=self.cluster_burst,'CLUSTER_BURST_EXCEEDED')
        self._classes=dict(classes)
        self.digest=hashlib.sha256(_canonical(dict(allocations=self._allocations,classes=classes,cluster_rate=cluster_rate,cluster_burst=cluster_burst))).hexdigest()

    def node(self,node):
        return dict(self._allocations[node])

    def class_limit(self,node,traffic_class):
        share=self._classes[traffic_class]
        return {k:v*share//100 for k,v in self._allocations[node].items()}


class _Store:
    def __init__(self,path):
        self.path=_path(path)
        self.fresh=not self.path.exists()
        if self.fresh:
            with self.path.open('xb'):pass
        self.lock=threading.RLock()

    @contextlib.contextmanager
    def transaction(self):
        with self.lock:
            _path(self.path)
            _need(self.path.stat().st_size<=16777216,'BUDGET_STORE_BOUNDS')
            con=sqlite3.connect(self.path,timeout=2,isolation_level=None)
            try:
                con.execute('PRAGMA synchronous=FULL')
                con.execute('PRAGMA trusted_schema=OFF')
                con.execute('BEGIN IMMEDIATE')
                marker=con.execute('PRAGMA application_id').fetchone()[0]
                if self.fresh and marker==0:
                    _need(not con.execute('SELECT name FROM sqlite_master').fetchall(),'FOREIGN_BUDGET_STORE')
                    con.execute('PRAGMA application_id='+str(self.APP_ID))
                else:_need(marker==self.APP_ID,'FOREIGN_BUDGET_STORE')
                yield con
                con.execute('COMMIT')
                self.fresh=False
            except (sqlite3.Error,OSError) as exc:
                raise BudgetError('BUDGET_STORE_UNAVAILABLE') from exc
            finally:
                con.close()


class NodeBudget(_Store):
    """Atomic shared-process node/class/peer buckets; static cluster allocation.

    Every process must use this same protected per-node store. Only the absent
    native admission layer can prove that invariant; the isolated factory cannot.
    Units are integer millibytes; TLS/TCP overhead is outside application bytes.
    """
    APP_ID=0x554E4257

    @classmethod
    def runtime(cls,*args,**kwargs):
        raise BudgetError('NATIVE_BUDGET_ADMISSION_REQUIRED')

    @classmethod
    def isolated(cls,path,node,policy,*,clock=time.monotonic,clock_id='isolated'):
        return cls(path,node,policy,clock=clock,clock_id=clock_id)

    def __init__(self,path,node,policy,*,clock,clock_id):
        super().__init__(path)
        _need(node in NODES and isinstance(policy,BandwidthPolicy) and type(clock_id) is str and 1<=len(clock_id)<=128)
        self.node,self.policy,self.clock,self.clock_id=node,policy,clock,clock_id
        now=int(clock()*1000);_integer(now)
        with self.transaction() as con:
            if not self.fresh:
                _need({r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={'meta','buckets','counters'},'BUDGET_SCHEMA_MISSING')
            con.execute('CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY CHECK(id=1), node TEXT, policy TEXT, clock_id TEXT, last_ms INTEGER, blocked INTEGER)')
            con.execute('CREATE TABLE IF NOT EXISTS buckets (name TEXT PRIMARY KEY, credit INTEGER, last_ms INTEGER)')
            con.execute('CREATE TABLE IF NOT EXISTS counters (direction TEXT PRIMARY KEY, bytes INTEGER)')
            row=con.execute('SELECT node,policy,clock_id FROM meta WHERE id=1').fetchone()
            if row is None:
                _need(self.fresh,'BUDGET_META_MISSING')
                con.execute('INSERT INTO meta VALUES(1,?,?,?,?,0)',(node,policy.digest,clock_id,now))
            else:
                _need(row[:2]==(node,policy.digest),'BUDGET_POLICY_OR_NODE_CHANGED')
                if row[2]!=clock_id:
                    # Reboot: no persisted monotonic timestamp reuse or new burst.
                    con.execute('UPDATE buckets SET credit=0,last_ms=?',(now,))
                    con.execute('UPDATE meta SET clock_id=?,last_ms=? WHERE id=1',(clock_id,now))
            for direction in ('tx','rx'):
                for suffix in ('node',*('class:'+c for c in CLASSES),*('peer:'+p for p in NODES if p!=node)):
                    con.execute('INSERT OR IGNORE INTO buckets VALUES(?,0,?)',(direction+':'+suffix,now))

    def try_take(self,direction,peer,traffic_class,size,*,now_ms=None):
        _need(direction in ('tx','rx') and peer in NODES and peer!=self.node and traffic_class in CLASSES)
        _integer(size,1,1048576)
        explicit_now=None if now_ms is None else _integer(now_ms)
        ok=False;clock_bad=False
        with self.transaction() as con:
            # Sampling before a contended lock can falsely appear to roll back
            # after another process commits a newer timestamp while we wait.
            now=_integer(int(self.clock()*1000)) if explicit_now is None else explicit_now
            row=con.execute('SELECT last_ms,blocked,clock_id,node,policy FROM meta WHERE id=1').fetchone()
            _need(row is not None and row[2]==self.clock_id and row[3:]==(self.node,self.policy.digest),'BUDGET_CLOCK_OR_POLICY_CHANGED')
            clock_bad=bool(row[1]) or now<row[0]
            if clock_bad:
                con.execute('UPDATE meta SET blocked=1 WHERE id=1')
            else:
                limits=(('node',self.policy.node(self.node)),
                        ('class:'+traffic_class,self.policy.class_limit(self.node,traffic_class)),
                        ('peer:'+peer,self.policy.node(self.node)))
                updates=[]
                for suffix,limit in limits:
                    name=direction+':'+suffix
                    b=con.execute('SELECT credit,last_ms FROM buckets WHERE name=?',(name,)).fetchone()
                    _need(b is not None,'BUDGET_BUCKET_MISSING')
                    credit,last=b
                    _need(type(credit) is int and 0<=credit<=limit['burst']*1000 and type(last) is int and 0<=last<=now,'BUDGET_STATE_CORRUPT')
                    credit=min(limit['burst']*1000,credit+(now-last)*limit['rate'])
                    updates.append((name,credit,now,limit['burst']))
                ok=all(credit>=size*1000 for _,credit,_,_ in updates)
                for name,credit,last,_ in updates:
                    con.execute('INSERT OR REPLACE INTO buckets VALUES(?,?,?)',(name,credit-size*1000 if ok else credit,last))
                con.execute('UPDATE meta SET last_ms=? WHERE id=1',(now,))
                if ok:
                    total=con.execute('SELECT bytes FROM counters WHERE direction=?',(direction,)).fetchone()
                    _need(total is None or type(total[0]) is int and 0<=total[0]<=MAX_U63-size,'BUDGET_COUNTER_OVERFLOW')
                    con.execute('INSERT INTO counters VALUES(?,?) ON CONFLICT(direction) DO UPDATE SET bytes=bytes+excluded.bytes',(direction,size))
        if clock_bad:
            raise BudgetError('BUDGET_CLOCK_UNCERTAIN')
        return ok

    def wait_take(self,direction,peer,traffic_class,size,*,deadline,cancel=None):
        while True:
            if cancel is not None and cancel.is_set():
                raise BudgetError('CANCELLED')
            if time.monotonic()>=deadline:
                raise BudgetError('DEADLINE')
            if self.try_take(direction,peer,traffic_class,size):
                return
            time.sleep(min(.01,max(0,deadline-time.monotonic())))

    def counters(self):
        with self.transaction() as con:
            return dict(con.execute('SELECT direction,bytes FROM counters'))


class EgressProjection(_Store):
    """Durable conservative domain event projection; NEVER a grant authority.

    A2's real multi-scope atomic adapter, provider time and sender containment
    are absent. Consequently acquire/dispatch ALWAYS deny in this closed profile.
    Test verifier callbacks exercise persistence only, not native authenticity.
    """
    APP_ID=0x554E4550

    @classmethod
    def isolated(cls,path):
        return cls(path)

    @classmethod
    def runtime(cls,*args,**kwargs):
        raise BudgetError('AUTHORITY_ADAPTER_NOT_ADMITTED')

    def __init__(self,path):
        super().__init__(path)
        with self.transaction() as con:
            if not self.fresh:
                _need({r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={'events','attempts','scopes'},'EGRESS_SCHEMA_MISSING')
            con.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, digest TEXT, payload TEXT)')
            con.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, scope TEXT, state TEXT, cost INTEGER, policy TEXT)')
            con.execute('CREATE TABLE IF NOT EXISTS scopes (id TEXT PRIMARY KEY, cooldown_ms INTEGER, frozen INTEGER)')

    def acquire(self,*args,**kwargs):
        return 'SAFETY_GATE_CLOSED'

    def prepare_dispatch(self,*args,**kwargs):
        return 'SAFETY_GATE_CLOSED'

    def apply_verified(self,event,*,verifier):
        _need(callable(verifier),'AUTHORITY_VERIFIER_REQUIRED')
        _need(type(event) is dict and set(event)=={'event_id','attempt_id','scope','state','cooldown_until_ms','cost','policy_digest'})
        for k in ('event_id','attempt_id','scope'):
            _need(type(event[k]) is str and 1<=len(event[k])<=128 and event[k].isascii())
        _need(event['state'] in ('RESERVED','CHARGED','UNKNOWN','OBSERVED','CANCELLED'))
        _need(event['state']!='CANCELLED','SAFETY_GATE_CLOSED')
        _integer(event['cost'],1,10**9)
        _need(type(event['policy_digest']) is str and len(event['policy_digest'])==64 and all(c in '0123456789abcdef' for c in event['policy_digest']))
        _integer(event['cooldown_until_ms'],0,MAX_U63)
        raw=_canonical(event);digest=hashlib.sha256(raw).hexdigest()
        event=json.loads(raw)
        # Verify an independent copy; mutation by an adapter cannot rewrite intent.
        _need(verifier(json.loads(raw)) is True,'AUTHORITY_RECEIPT_REJECTED')
        with self.transaction() as con:
            prior=con.execute('SELECT digest FROM events WHERE id=?',(event['event_id'],)).fetchone()
            if prior:
                _need(prior==(digest,),'IDEMPOTENCY_CONFLICT')
                return
            a=con.execute('SELECT scope,state,cost,policy FROM attempts WHERE id=?',(event['attempt_id'],)).fetchone()
            _need(a is not None or con.execute('SELECT count(*) FROM attempts').fetchone()[0]<1024,'EGRESS_ATTEMPT_BOUNDS')
            allowed={None:{'RESERVED','CHARGED','UNKNOWN'},'RESERVED':{'CHARGED','UNKNOWN','CANCELLED'},
                     'CHARGED':{'UNKNOWN','OBSERVED'},'UNKNOWN':{'UNKNOWN','OBSERVED'},'OBSERVED':{'OBSERVED'},'CANCELLED':set()}
            _need(a is None or a[0]==event['scope'],'ATTEMPT_SCOPE_CHANGED')
            _need(a is None or a[2:]==(event['cost'],event['policy_digest']),'ATTEMPT_COST_OR_POLICY_CHANGED')
            _need(event['state'] in allowed[None if a is None else a[1]],'UNSAFE_ATTEMPT_TRANSITION')
            s=con.execute('SELECT cooldown_ms,frozen FROM scopes WHERE id=?',(event['scope'],)).fetchone() or (0,0)
            _need(con.execute('SELECT id FROM scopes WHERE id=?',(event['scope'],)).fetchone() is not None or con.execute('SELECT count(*) FROM scopes').fetchone()[0]<8,'EGRESS_SCOPE_BOUNDS')
            frozen=bool(s[1]) or event['state']=='UNKNOWN'
            # OBSERVED never clears an earlier UNKNOWN freeze or max cooldown.
            con.execute('INSERT OR REPLACE INTO scopes VALUES(?,?,?)',(event['scope'],max(s[0],event['cooldown_until_ms']),int(frozen)))
            con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?)',(event['attempt_id'],event['scope'],event['state'],event['cost'],event['policy_digest']))
            con.execute('INSERT INTO events VALUES(?,?,?)',(event['event_id'],digest,raw.decode('ascii')))

    def snapshot(self):
        with self.transaction() as con:
            return {'attempts':{i:{'scope':s,'state':t,'cost':cost,'policy_digest':policy} for i,s,t,cost,policy in con.execute('SELECT * FROM attempts')},
                    'scopes':{i:{'cooldown_until_ms':c,'frozen':bool(f),'usage_cost':con.execute('SELECT coalesce(sum(cost),0) FROM attempts WHERE scope=?',(i,)).fetchone()[0]} for i,c,f in con.execute('SELECT * FROM scopes')}}
