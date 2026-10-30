"""Durable PLAN_ONLY lifecycle. Records intentions/observations; never launches code."""
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from .contracts import ContractError

STAGES=('INFRA_PREFLIGHT','INFRA_READY','STRAT_HISTORY_SYNC','STRAT_RESULT_SEALED',
        'HANDOFF_VERIFY','GRID_MARKET_READY','STEADY_STATE')
MODULES=frozenset(('unified-system','terminan','strattester','grid','math'))
STATUS=frozenset(('NOT_STARTED','RUNNING','WAITING','BLOCKED','COMPLETE','CANCELLED'))
REQUIRED=dict(zip(STAGES,('unified-system','unified-system','strattester','strattester','unified-system','grid','unified-system')))
ZERO='0'*64

def canonical(value):
    try:return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError,RecursionError) as exc:raise ContractError('invalid lifecycle value') from exc
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def integer(value,low=0,high=2**53-1):
    if type(value) is not int or not low<=value<=high:raise ContractError('invalid lifecycle integer')
    return value
def modules(value):
    if not isinstance(value,list) or len(value)>5 or any(type(x) is not str or x not in MODULES for x in value) or len(set(value))!=len(value):
        raise ContractError('invalid module inventory')
    return sorted(value)
def initial(available):
    return {'schema':'unified.lifecycle.v1','api_version':{'major':1,'minor':0},'producer':'unified-system',
            'mode':'PLAN_ONLY','epoch':str(uuid.uuid4()),'sequence':0,'available_modules':modules(available),
            'stages':[dict(stage=s,status='NOT_STARTED',completed=0,total=0,reason='NOT_STARTED') for s in STAGES],
            'observer':{'status':'NOT_STARTED','reason':'NOT_STARTED'},'math':{'status':'NOT_STARTED','reason':'NOT_STARTED'},
            'paper':{'status':'NOT_AUTHORIZED'},'execution_authorized':False,'trading_authorized':False,
            'physical_acceptance':'NOT_RUN','source_provenance':'UNVERIFIED'}

def validate(state):
    try:
        template=initial([])
        if not isinstance(state,dict) or set(state)!=set(template):raise ContractError('invalid lifecycle schema')
        if state['schema']!=template['schema'] or state['api_version']!=template['api_version'] or any(type(v) is not int for v in state['api_version'].values()):raise ContractError('invalid lifecycle version')
        if state['producer']!='unified-system' or state['mode']!='PLAN_ONLY' or state['execution_authorized'] is not False or state['trading_authorized'] is not False or state['physical_acceptance']!='NOT_RUN' or state['source_provenance']!='UNVERIFIED' or state['paper']!={'status':'NOT_AUTHORIZED'}:raise ContractError('invalid lifecycle authority')
        if type(state['epoch']) is not str:raise ContractError('invalid epoch')
        uuid.UUID(state['epoch']);integer(state['sequence']);modules(state['available_modules'])
        if len(state['stages'])!=len(STAGES):raise ContractError('invalid stages')
        for name,row in zip(STAGES,state['stages']):
            if set(row)!={'stage','status','completed','total','reason'} or row['stage']!=name or row['status'] not in STATUS or type(row['reason']) is not str or len(row['reason'])>128:raise ContractError('invalid progress')
            integer(row['completed']);integer(row['total'])
            if row['completed']>row['total']:raise ContractError('invalid counters')
        for key in ('observer','math'):
            if set(state[key])!={'status','reason'} or state[key]['status'] not in STATUS or type(state[key]['reason']) is not str or len(state[key]['reason'])>128:raise ContractError('invalid parallel status')
        for index,row in enumerate(state['stages']):
            if row['status'] in ('RUNNING','COMPLETE'):
                if index and state['stages'][index-1]['status']!='COMPLETE':raise ContractError('invalid stage dependency')
                if index>=2 and state['observer']['status'] not in ('RUNNING','COMPLETE'):raise ContractError('invalid observer barrier')
        if state['observer']['status'] in ('RUNNING','COMPLETE') and state['stages'][1]['status']!='COMPLETE':raise ContractError('invalid observer infrastructure')
        return state
    except (KeyError,ValueError,TypeError,AttributeError,RecursionError) as exc:raise ContractError('invalid lifecycle state') from exc

class Lifecycle:
    def __init__(self,path,available_modules,*,verifier=None,fleet_provider=None):
        self.path=Path(path);self.available=modules(available_modules)
        self.verifier=verifier;self.fleet_provider=fleet_provider;self.recovery=True
    def _db(self):
        db=sqlite3.connect(self.path,timeout=1)
        db.execute('PRAGMA busy_timeout=1000');db.execute('PRAGMA synchronous=FULL')
        return db
    def initialize(self):
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS lifecycle_state(id INTEGER PRIMARY KEY CHECK(id=1),snapshot TEXT NOT NULL,head TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS lifecycle_events(sequence INTEGER PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,snapshot_digest TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS lifecycle_operations(id TEXT PRIMARY KEY,request_digest TEXT NOT NULL,response TEXT NOT NULL,response_digest TEXT NOT NULL)')
            row=db.execute('SELECT snapshot FROM lifecycle_state WHERE id=1').fetchone()
            if row is None:
                state=initial(self.available)
                db.execute('INSERT INTO lifecycle_state VALUES(1,?,?)',(canonical(state),ZERO));self.recovery=False
            self._read(db)
        return self.snapshot()
    def _read(self,db):
        row=db.execute('SELECT snapshot,head FROM lifecycle_state WHERE id=1').fetchone()
        if row is None or not isinstance(row[0],str) or len(row[0])>65536:raise ContractError('lifecycle state unavailable')
        try:state=validate(json.loads(row[0]))
        except (ValueError,RecursionError,TypeError) as exc:raise ContractError('corrupt state') from exc
        if state['available_modules']!=self.available:raise ContractError('module inventory changed; explicit migration required')
        previous=ZERO;count=0;last=None
        for count,(seq,raw,checksum,snapshot_digest) in enumerate(db.execute('SELECT sequence,body,digest,snapshot_digest FROM lifecycle_events ORDER BY sequence LIMIT 4097'),1):
            if count>4096 or seq!=count or len(raw)>65536:raise ContractError('journal capacity or sequence invalid')
            try:body=json.loads(raw)
            except (ValueError,RecursionError) as exc:raise ContractError('corrupt event') from exc
            if not isinstance(body,dict) or body.get('previous_hash')!=previous or body.get('snapshot_digest')!=snapshot_digest or digest(body)!=checksum:raise ContractError('journal integrity failed')
            previous=checksum;last=snapshot_digest
        if count!=state['sequence'] or row[1]!=previous or (count and digest(state)!=last):raise ContractError('state/journal mismatch')
        if not count:
            pristine=initial(self.available);pristine['epoch']=state['epoch']
            if state!=pristine:raise ContractError('invalid initial state')
        return state,previous
    def snapshot(self):
        with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
            db.execute('BEGIN');state,_=self._read(db)
        state['recovery']='REVALIDATION_REQUIRED' if self.recovery else 'NONE'
        state['fleet']={'status':'UNAVAILABLE','nodes':[],'links':[]}
        if self.fleet_provider is not None:
            try:
                fleet=self.fleet_provider()
                if isinstance(fleet,dict) and isinstance(fleet.get('nodes'),list) and len(fleet['nodes'])<=256 and len(canonical(fleet))<=524288:
                    state['fleet']=json.loads(canonical(fleet))
            except Exception:pass
        return state
    def _save(self,db,state,previous,operation,request):
        if state['sequence']>=4096:raise ContractError('journal capacity reached')
        state['sequence']+=1
        body={'sequence':state['sequence'],'operation':operation,'request_digest':request,'previous_hash':previous,'snapshot_digest':digest(state)}
        checksum=digest(body)
        db.execute('INSERT INTO lifecycle_events VALUES(?,?,?,?)',(state['sequence'],canonical(body),checksum,digest(state)))
        db.execute('UPDATE lifecycle_state SET snapshot=?,head=? WHERE id=1',(canonical(state),checksum))
    def recover(self,expected_epoch,expected_sequence):
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE');state,previous=self._read(db)
            self._fence(state,expected_epoch,expected_sequence)
            # No replayed completion can restart modules: all source observations must be obtained anew.
            fresh=initial(self.available);fresh['sequence']=state['sequence']
            self._save(db,fresh,previous,'RECOVERY_RESET',digest({'epoch':expected_epoch,'sequence':expected_sequence}))
        self.recovery=False
        return self.snapshot()
    def _fence(self,state,epoch,sequence):
        integer(sequence)
        if epoch!=state['epoch'] or sequence!=state['sequence']:raise ContractError('stale epoch/sequence')
    def apply(self,operation_id,expected_epoch,expected_sequence,stage,status,evidence,*,completed=0,total=0):
        if type(operation_id) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',operation_id):raise ContractError('invalid operation id')
        if stage not in (*STAGES,'terminan','math') or status not in STATUS or status=='NOT_STARTED':raise ContractError('invalid transition')
        integer(completed);integer(total)
        if completed>total:raise ContractError('invalid progress counts')
        if len(canonical(evidence))>65536:raise ContractError('observation too large')
        request=digest([expected_epoch,expected_sequence,stage,status,evidence,completed,total])
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE');state,previous=self._read(db)
            if expected_epoch!=state['epoch']:raise ContractError('stale operation epoch')
            old=db.execute('SELECT request_digest,response,response_digest FROM lifecycle_operations WHERE id=?',(operation_id,)).fetchone()
            if old:
                if old[0]!=request:raise ContractError('operation id collision')
                try:
                    cached=json.loads(old[1])
                    core={k:v for k,v in cached.items() if k not in ('recovery','fleet')}
                    validate(core)
                    if cached['epoch']!=expected_epoch or digest(cached)!=old[2]:raise ContractError('cached response corrupt')
                    if cached.get('recovery')!='NONE' or cached.get('fleet')!={'status':'UNAVAILABLE','nodes':[],'links':[]}:raise ContractError('invalid cached envelope')
                    return cached
                except (ValueError,TypeError,KeyError,RecursionError,AttributeError) as exc:raise ContractError('cached response corrupt') from exc
            if self.recovery:raise ContractError('recovery requires source revalidation')
            self._fence(state,expected_epoch,expected_sequence)
            required=stage if stage in ('math','terminan') else REQUIRED[stage]
            if required not in self.available:raise ContractError('required module unavailable')
            if not callable(self.verifier):raise ContractError('source verifier unavailable')
            try:proof=self.verifier(stage,evidence,status=status,completed=completed,total=total)
            except Exception as exc:raise ContractError('source verification failed') from exc
            if not isinstance(proof,dict) or proof.get('verdict') not in ('VERIFIED_SYNTHETIC','VERIFIED_SOURCE_RECEIPT'):raise ContractError('source observation unqualified')
            if any(proof.get(k)!=v for k,v in dict(stage=stage,status=status,completed=completed,total=total).items()) or any(type(proof.get(k)) is not int for k in ('completed','total')):raise ContractError('observation/transition mismatch')
            rows={r['stage']:r for r in state['stages']}
            if stage in STAGES:
                index=STAGES.index(stage)
                if index and rows[STAGES[index-1]]['status']!='COMPLETE':raise ContractError('upstream stage incomplete')
                if index>=2 and state['observer']['status'] not in ('RUNNING','COMPLETE'):raise ContractError('Terminan observer unavailable')
                if rows[stage]['status']=='COMPLETE' and status in ('RUNNING','COMPLETE'):raise ContractError('completed stage requires invalidation before retry')
                rows[stage].update(status=status,completed=completed,total=total,reason='SOURCE_OBSERVATION_SOFTWARE_ONLY')
                if status in ('CANCELLED','BLOCKED','RUNNING','WAITING'):
                    for downstream in STAGES[index+1:]:rows[downstream].update(status='NOT_STARTED',completed=0,total=0,reason='UPSTREAM_INVALIDATED')
                    if index<=1:state['observer']={'status':'NOT_STARTED','reason':'INFRA_INVALIDATED'}
            else:
                if stage=='terminan' and rows['INFRA_READY']['status']!='COMPLETE':raise ContractError('infrastructure not ready')
                state['observer' if stage=='terminan' else 'math']={'status':status,'reason':'SOURCE_OBSERVATION_SOFTWARE_ONLY'}
                if stage=='terminan' and status not in ('RUNNING','COMPLETE'):
                    for downstream in STAGES[2:]:rows[downstream].update(status='NOT_STARTED',completed=0,total=0,reason='OBSERVER_UNAVAILABLE')
            self._save(db,state,previous,operation_id,request)
            response=json.loads(canonical(state));response['recovery']='NONE';response['fleet']={'status':'UNAVAILABLE','nodes':[],'links':[]}
            db.execute('INSERT INTO lifecycle_operations VALUES(?,?,?,?)',(operation_id,request,canonical(response),digest(response)))
        return response
