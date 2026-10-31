"""Node-local process lifecycle. Grid remains the distributed fleet authority.

This durable journal is NOT distributed consensus. Drivers must implement
idempotent start by operation_id, owned-process stop and functional readiness.
No commands, credentials or private driver errors enter the status protocol.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid

from .module_catalog import MODULE_IDS


@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    version: str
    api_major: int = 1
    dependencies: tuple = ()
    start_timeout: float = 30.


def _valid(spec):
    if (not isinstance(spec,ModuleSpec) or type(spec.module_id) is not str
            or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',spec.module_id)
            or type(spec.version) is not str
            or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,40})?',spec.version)
            or type(spec.api_major) is not int or spec.api_major!=1
            or not isinstance(spec.dependencies,(tuple,list))
            or any(type(x) is not str for x in spec.dependencies)
            or len(spec.dependencies)!=len(set(spec.dependencies))
            or spec.module_id in spec.dependencies
            or type(spec.start_timeout) not in (int,float)
            or not math.isfinite(spec.start_timeout) or not 0<spec.start_timeout<=60):
        raise ValueError('invalid module contract')


def _encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


class _LocalGate:
    """Serialize a complete side effect across local supervisor processes.

    Separate from the journal: committing an operation id must not release the
    actuator gate. SQLite OS locks are released automatically on process death.
    This lock provides no distributed authority.
    """
    def __init__(self,path):
        self.path=str(path)+'.gate';self.mutex=threading.RLock();self.local=threading.local()
    def __enter__(self):
        self.mutex.acquire()
        try:
            if not getattr(self.local,'depth',0):
                db=sqlite3.connect(self.path,timeout=2)
                try:db.execute('BEGIN IMMEDIATE')
                except BaseException:db.close();raise
                self.local.db=db
            self.local.depth=getattr(self.local,'depth',0)+1
            return self
        except BaseException:self.mutex.release();raise
    def __exit__(self,*args):
        try:
            self.local.depth-=1
            if not self.local.depth:
                try:self.local.db.rollback()
                finally:self.local.db.close();del self.local.db
        finally:self.mutex.release()


class RuntimeSupervisor:
    def __init__(self,path,driver,specs,*,release_id,release_sha256,node_id,clock=time.time,max_restarts=3):
        if (type(release_id) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',release_id)
                or type(release_sha256) is not str or not re.fullmatch(r'[a-f0-9]{64}',release_sha256)
                or type(node_id) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',node_id)
                or type(max_restarts) is not int or not 0<=max_restarts<=10):
            raise ValueError('invalid runtime identity')
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.driver=driver;self.release_id=release_id;self.release_sha256=release_sha256
        self.node_id=node_id;self.clock=clock;self.max_restarts=max_restarts;self.lock=_LocalGate(self.path)
        if not isinstance(specs,(list,tuple)) or len(specs)!=len(MODULE_IDS):raise ValueError('six core modules required')
        initial={}
        for spec in specs:
            _valid(spec)
            if spec.module_id in initial:raise ValueError('duplicate module')
            initial[spec.module_id]=spec
        if set(initial)!=MODULE_IDS:raise ValueError('six core modules required')
        self._order(initial)
        with self.lock,self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS identity(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,revision INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS modules(id TEXT PRIMARY KEY,spec TEXT NOT NULL,state TEXT NOT NULL)')
            identity=_encoded(dict(release_id=release_id,release_sha256=release_sha256,node_id=node_id))
            row=db.execute('SELECT body FROM identity WHERE id=1').fetchone()
            if row and row[0]!=identity:raise ValueError('explicit release transition required')
            if not row:db.execute('INSERT INTO identity VALUES(1,?,0)',(identity,))
            for name,spec in initial.items():
                old=db.execute('SELECT spec FROM modules WHERE id=?',(name,)).fetchone()
                if old and old[0]!=_encoded(asdict(spec)):raise ValueError('explicit module transition required')
                if not old:db.execute('INSERT INTO modules VALUES(?,?,?)',(name,_encoded(asdict(spec)),_encoded(self._initial())))
            self._order(self._specs(db))
    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path,timeout=2)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:yield db
        finally:db.close()
    @staticmethod
    def _initial():return dict(desired='STOPPED',admin_stop=False,state='STOPPED',handle=None,attempt=0,next_at=0.,started_at=0.,reason='NONE')
    @staticmethod
    def _specs(db):
        return {name:ModuleSpec(**json.loads(raw)) for name,raw in db.execute('SELECT id,spec FROM modules')}
    @staticmethod
    def _order(specs):
        order=[];active=set();done=set()
        def visit(name):
            if name not in specs:raise ValueError('missing dependency')
            if name in active:raise ValueError('dependency cycle')
            if name in done:return
            _valid(specs[name]);active.add(name)
            for dep in specs[name].dependencies:visit(dep)
            active.remove(name);done.add(name);order.append(name)
        for name in sorted(specs):visit(name)
        return order
    @staticmethod
    def _states(db):return {n:json.loads(raw) for n,raw in db.execute('SELECT id,state FROM modules')}
    @staticmethod
    def _put(db,name,state):
        raw=_encoded(state);old=db.execute('SELECT state FROM modules WHERE id=?',(name,)).fetchone()[0]
        if old!=raw:
            db.execute('UPDATE modules SET state=? WHERE id=?',(raw,name))
            db.execute('UPDATE identity SET revision=revision+1 WHERE id=1')
    def register(self,spec):
        _valid(spec)
        with self.lock,self._db() as db:
            specs=self._specs(db)
            if spec.module_id in specs or len(specs)>=64:raise ValueError('module already registered or limit')
            specs[spec.module_id]=spec;self._order(specs)
            db.execute('INSERT INTO modules VALUES(?,?,?)',(spec.module_id,_encoded(asdict(spec)),_encoded(self._initial())))
            db.execute('UPDATE identity SET revision=revision+1 WHERE id=1')
    def unregister(self,name):
        with self.lock,self._db() as db:
            specs=self._specs(db);states=self._states(db)
            if (name not in specs or name in MODULE_IDS or states[name]['state']!='STOPPED'
                    or any(name in s.dependencies for s in specs.values())):raise ValueError('module in use')
            db.execute('DELETE FROM modules WHERE id=?',(name,));db.execute('UPDATE identity SET revision=revision+1 WHERE id=1')
    def start(self):
        with self.lock,self._db() as db:
            for name,state in self._states(db).items():
                if not state['admin_stop']:
                    state['desired']='RUNNING';self._put(db,name,state)
    def start_module(self,name):
        with self.lock,self._db() as db:
            states=self._states(db)
            if name not in states:raise ValueError('unknown module')
            if states[name]['admin_stop']:raise ValueError('explicit resume required')
            states[name]['desired']='RUNNING';self._put(db,name,states[name])
    def resume(self):
        with self.lock,self._db() as db:
            if any(s['reason']=='STOP_FAILED' and s['handle'] is not None for s in self._states(db).values()):
                raise ValueError('owned process cleanup required')
            for name,state in self._states(db).items():
                state.update(admin_stop=False,desired='RUNNING',attempt=0,next_at=0.,reason='NONE')
                self._put(db,name,state)
    def _stop_one(self,db,name,state,administrative):
        if state['handle'] is not None:
            try:self.driver.stop(state['handle'])
            except Exception:
                state.update(state='FAILED',reason='STOP_FAILED',desired='STOPPED',admin_stop=state['admin_stop'] or administrative)
                self._put(db,name,state);return False
        state.update(state='STOPPED',reason='NONE',handle=None,desired='STOPPED',admin_stop=state['admin_stop'] or administrative)
        self._put(db,name,state)
        return True
    def stop(self,administrative=True):
        with self.lock:
            failed=False
            with self._db() as db:
                specs=self._specs(db);states=self._states(db)
                for name in reversed(self._order(specs)):
                    if not self._stop_one(db,name,states[name],administrative):failed=True
            # Persist failed cleanup and administrative STOP before signaling it.
            if failed:raise ValueError('owned process cleanup required')
    def stop_module(self,name,*,cascade=False,administrative=True):
        with self.lock:
            failed=False
            with self._db() as db:
                specs=self._specs(db);states=self._states(db)
                if name not in specs:raise ValueError('unknown module')
                targets={name}
                while True:
                    more={n for n,s in specs.items() if targets.intersection(s.dependencies) and
                          (states[n]['desired']=='RUNNING' or states[n]['handle'] is not None)}
                    if more<=targets:break
                    targets|=more
                if len(targets)>1 and not cascade:raise ValueError('running dependents')
                for n in reversed(self._order(specs)):
                    if n in targets and not self._stop_one(db,n,states[n],administrative):failed=True
            if failed:raise ValueError('owned process cleanup required')
    def restart(self):
        with self.lock,self._db() as db:
            if any(s['admin_stop'] for s in self._states(db).values()):raise ValueError('explicit resume required')
            self.stop(administrative=False)
            with self._db() as stopped:
                states=self._states(stopped)
                if any(s['reason']=='STOP_FAILED' and s['handle'] is not None for s in states.values()):
                    raise ValueError('owned process cleanup required')
                for name,state in states.items():
                    state.update(attempt=0,next_at=0.)
                    self._put(stopped,name,state)
            self.start()
    def tick(self):
        with self.lock,self._db() as db:
            now=float(self.clock())
            if not math.isfinite(now) or now<0:raise ValueError('invalid clock')
            specs=self._specs(db);states=self._states(db)
            for name in self._order(specs):
                spec=specs[name];s=states[name]
                if s['desired']!='RUNNING' or s['admin_stop'] or s['reason']=='STOP_FAILED':continue
                if any(states[d]['state']!='READY' for d in spec.dependencies):
                    if s['handle'] is not None:
                        try:self.driver.stop(s['handle'])
                        except Exception:s.update(state='FAILED',reason='STOP_FAILED');self._put(db,name,s);continue
                    s.update(handle=None,state='WAITING',reason='DEPENDENCY_NOT_READY');self._put(db,name,s);continue
                try:
                    if s['handle'] is None:
                        if now<s['next_at'] or s['attempt']>self.max_restarts:continue
                        op=str(uuid.uuid4())
                        # Persist the idempotency key before a process-side effect.
                        s.update(handle=op,state='STARTING',started_at=now,reason='NONE');self._put(db,name,s)
                        db.commit()
                        actual=self.driver.start(spec,self.release_id,op)
                        if actual!=op:raise ValueError('driver changed operation identity')
                    if not self.driver.alive(s['handle']):raise RuntimeError('owned process exited')
                    ready=self.driver.ready(spec,s['handle'],self.release_id)
                    valid=(isinstance(ready,dict) and ready.get('ready') is True
                           and ready.get('module_id')==name and ready.get('version')==spec.version
                           and ready.get('release_id')==self.release_id)
                    if valid:s.update(state='READY',reason='NONE')
                    elif now-s['started_at']>=spec.start_timeout:raise RuntimeError('startup deadline')
                    else:s.update(state='STARTING',reason='FUNCTIONAL_READINESS_REQUIRED')
                except Exception:
                    stopped=True
                    if s['handle'] is not None:
                        try:self.driver.stop(s['handle'])
                        except Exception:stopped=False
                    s.update(state='BACKOFF' if stopped else 'FAILED',reason='DRIVER_FAILURE' if stopped else 'STOP_FAILED',
                             attempt=s['attempt']+1,next_at=now+min(60,2**min(s['attempt']+1,6)))
                    if stopped:
                        s['handle']=None
                        if s['attempt']>self.max_restarts:s['state']='FAILED'
                self._put(db,name,s)
    def snapshot(self):
        with self.lock,self._db() as db:
            specs=self._specs(db);states=self._states(db)
            modules={n:dict(version=specs[n].version,api_major=specs[n].api_major,dependencies=list(specs[n].dependencies),
                            state=s['state'],ready=s['state']=='READY',attempt=s['attempt'],reason=s['reason'],
                            administrative_stop=s['admin_stop']) for n,s in sorted(states.items())}
            return dict(schema='unified.runtime.v2',api_version={'major':2,'minor':0},producer='unified-system',
                        node_id=self.node_id,release_id=self.release_id,release_sha256=self.release_sha256,
                        revision=db.execute('SELECT revision FROM identity WHERE id=1').fetchone()[0],
                        mode='LOCAL_RUNTIME_PREDEPLOYMENT',modules=modules,
                        ready=all(modules[n]['ready'] for n in MODULE_IDS),fleet_authority='grid',
                        trading_authorized=False,physical='NOT_RUN',physical_deployment_allowed=False)
    def health_release(self,release_id):
        view=self.snapshot()
        return dict(release_id=self.release_id,release_sha256=self.release_sha256,
                    ready=release_id==self.release_id and view['ready'],
                    modules={n:{'version':view['modules'][n]['version'],'ready':view['modules'][n]['ready']} for n in sorted(MODULE_IDS)})
