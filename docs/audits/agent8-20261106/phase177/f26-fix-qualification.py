"""Exact one Root-authorized disposable 2-arm experiment. No product fix."""
import collections,contextlib,json,os,pathlib,runpy,subprocess,sys,threading,time,unittest
from unittest.mock import patch

if __name__=='__main__':
    guard=runpy.run_path(str(pathlib.Path(__file__).with_name('f26-fix-source-guard.py')))
    output=guard['output'];source=guard['source'];before=source()
    (output/'source-before.json').write_text(json.dumps(before,sort_keys=True),encoding='utf8')
    sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests')]
    from tests.test_lan_transport import TLSIsolationTests
    from unified_system import lan_transport as lan,network_budget as budget
    assert lan.HEARTBEAT_INTERVAL==10 and lan.IDLE_TIMEOUT==30
    original_tx=budget._Store.transaction;original_wait=budget.NodeBudget.wait_take
    original_hb=lan.Connection._heartbeat;original_emit=lan.Connection._emit
    original_send=lan.Connection._send;original_init=lan.Connection.__init__
    original_setup=TLSIsolationTests.setUp;original_popen=subprocess.Popen
    lock=threading.RLock();rows=collections.deque(maxlen=2048);total=[0];arm=['PREP'];period=[.05]
    connections=[];children=[];baseline_threads=set(threading.enumerate());owned_root=[None];scope_violation=[None];done=threading.Event();start=time.monotonic()
    delay=threading.Event();outcomes=[]
    def record(phase,**fields):
        with lock:total[0]+=1;rows.append(dict(arm=arm[0],phase=phase,ms=round((time.monotonic()-start)*1000,3),**fields))
    def code(exc):
        args=exc.args
        return args[0] if type(args) is tuple and len(args)==1 and type(args[0]) is str and args[0] in ('DEADLINE','DISCONNECTED','DELIVERY_UNKNOWN','CANCELLED','CLOSED','BUDGET_STORE_UNAVAILABLE','BUDGET_CLOCK_UNCERTAIN') else 'OTHER'
    def dump():
        with lock:data=dict(events=list(rows),total=total[0],retained=len(rows),dropped=max(0,total[0]-len(rows)))
        (output/'per-call-phases.json').write_text(json.dumps(data,sort_keys=True),encoding='utf8')
    def retire_children():
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            if child.poll() is None:
                try:child.wait(2)
                except subprocess.TimeoutExpired:child.kill();child.wait(2)
    def retirement():
        for connection in connections:
            if hasattr(connection,'cv') and hasattr(connection,'closed'):connection.close('CLOSED')
        for connection in connections:
            for thread in getattr(connection,'threads',()):thread.join(1)
        TLSIsolationTests.doClassCleanups();retire_children()
        extras=[t for t in threading.enumerate() if t not in baseline_threads and t is not timer]
        for thread in extras:thread.join(1)
        return dict(threads_alive=sum(t.is_alive() for t in extras),children_alive=sum(c.poll() is None for c in children))
    def watchdog():
        if not done.wait(float(os.environ['CASE_SAFETY_SECONDS'])):
            retire_children();record('OUTER_SAFETY_STOP');dump()
            (output/'timeout.json').write_text(json.dumps(dict(timeout=True,seconds=84,outcomes=outcomes)),encoding='utf8')
            os._exit(124)
    class OwnedPopen(original_popen):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);children.append(self)
    def owned_setup(case):
        original_setup(case);owned_root[0]=pathlib.Path(case.store.name).resolve(strict=True)
    def own_init(connection,*args,**kwargs):
        connections.append(connection);original_init(connection,*args,**kwargs)
    def ensure_store(store):
        if owned_root[0] is None or pathlib.Path(store.path).resolve().parent!=owned_root[0] or type(store) is not budget.NodeBudget:
            scope_violation[0]='STORE_SCOPE';raise RuntimeError('OWNED_STORE_SCOPE_VIOLATION')
    @contextlib.contextmanager
    def matched_tx(store):
        ensure_store(store);begin=time.monotonic();acquired=None;body_end=None;delay_end=None;success=False
        try:
            with original_tx(store) as con:
                acquired=time.monotonic()
                try:yield con
                finally:
                    body_end=time.monotonic()
                    if not store.lock._is_owned():scope_violation[0]='LOCK_PLACEMENT';raise RuntimeError('OWNED_LOCK_PLACEMENT')
                    delay.wait(0 if arm[0]=='N' else .05);delay_end=time.monotonic()
            success=True
        finally:
            end=time.monotonic();record('TX_CALL',entry_ms=round(((acquired or end)-begin)*1000,3),body_ms=round(((body_end or end)-(acquired or end))*1000,3),injected_ms=round(((delay_end or end)-(body_end or end))*1000,3),exit_ms=round((end-(delay_end or end))*1000,3),total_ms=round((end-begin)*1000,3),completed=success,requested_extra_ms=0 if arm[0]=='N' else 50)
    def measured_wait(store,*args,**kwargs):
        begin=time.monotonic();success=False
        try:
            result=original_wait(store,*args,**kwargs);success=True;return result
        finally:record('BUDGET_CALL',direction=args[0] if args else 'OTHER',traffic=args[2] if len(args)>2 else 'OTHER',size=args[3] if len(args)>3 else 0,total_ms=round((time.monotonic()-begin)*1000,3),completed=success)
    def measured_emit(connection,kind,stream,traffic,payload=b'',value=0,**kwargs):
        begin=time.monotonic();success=False
        try:
            result=original_emit(connection,kind,stream,traffic,payload,value,**kwargs);success=True;return result
        finally:record('EMIT_CALL',kind=kind,stream=stream,traffic=traffic,size=len(payload),credit=value if kind=='CREDIT' else 0,total_ms=round((time.monotonic()-begin)*1000,3),completed=success)
    def measured_send(connection,payload,traffic_class,**kwargs):
        begin=time.monotonic()
        try:
            result=original_send(connection,payload,traffic_class,**kwargs);record('APP_CALL',size=len(payload),completed=True,total_ms=round((time.monotonic()-begin)*1000,3));return result
        except BaseException as exc:
            state=dict(lock_busy=True)
            if connection.cv.acquire(False):
                try:state=dict(closed=connection.closed,streams=[[key,item['opened'],item['grant'],item['sent']] for key,item in list(connection.tx_streams.items())[:2]],jobs=[[j['started'],code(exc)] for j in list(connection.outgoing)[:2]])
                finally:connection.cv.release()
            record('APP_ERROR',size=len(payload),error=code(exc),total_ms=round((time.monotonic()-begin)*1000,3),state=state);raise
    def matched_heartbeat(connection):
        # SAME skeleton/initial real50ms in both arms. ONLY subsequent cadence differs.
        try:
            if connection.closed_event.wait(.05):return
            while True:
                connection._emit('PING',0,'control')
                if connection.closed_event.wait(period[0]):return
        except (OSError,ValueError) as exc:connection.close(str(exc))
    original_read=lan._read_frame;mutant_calls=[0]
    def mutant_read(sock,store,peer,deadline,on_idle=None):
        if arm[0]=='M' and on_idle is not None and any(sock is c.channels.get('data') for c in connections):
            def disabled():
                mutant_calls[0]+=1;record('MUTANT_RENEWAL_DISABLED');return False
            on_idle=disabled
        return original_read(sock,store,peer,deadline,on_idle=on_idle)
    timer=threading.Thread(target=watchdog,daemon=True,name='own-matched-family-safety');timer.start()
    harness_error=None;after=None
    try:
        for label,cadence in ((os.environ['QUAL_CASE'],10.0),):
            arm[0]=label;period[0]=cadence;owned_root[0]=None;record('ARM_START',periodic_seconds=cadence)
            began=time.monotonic()
            with contextlib.ExitStack() as stack:
                for target,name,value in ((subprocess,'Popen',OwnedPopen),(TLSIsolationTests,'setUp',owned_setup),(budget._Store,'transaction',matched_tx),(budget.NodeBudget,'wait_take',measured_wait),(lan.Connection,'__init__',own_init),(lan.Connection,'_emit',measured_emit),(lan.Connection,'_send',measured_send),(lan,'_read_frame',mutant_read)):
                    stack.enter_context(patch.object(target,name,value))
                suite=unittest.TestSuite([TLSIsolationTests('test_expired_idle_peer_without_activity_still_closes_real_tls' if label=='N' else 'test_active_control_heartbeats_keep_idle_data_channel_healthy')])
                with (output/(label+'-tests.log')).open('w',encoding='utf8') as log,(output/(label+'-stderr.log')).open('w',encoding='utf8') as err,contextlib.redirect_stderr(err):
                    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
            retired=retirement()
            outcome=dict(arm=label,periodic_seconds=cadence,initial_seconds=.05,extra_transaction_service_ms=0 if label=='N' else 50,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),elapsed_seconds=round(time.monotonic()-began,3),retirement=retired)
            outcomes.append(outcome);record('ARM_DONE',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))
            dump();(output/'outcomes.json').write_text(json.dumps(outcomes,sort_keys=True),encoding='utf8')
            print(json.dumps(outcome),flush=True)
            if scope_violation[0] or retired['threads_alive'] or retired['children_alive']:raise RuntimeError('SCOPE_OR_RETIREMENT_VIOLATION')
            for path in (output/(label+'-tests.log'),output/(label+'-stderr.log')):
                text=path.read_text(encoding='utf8')
                if any(marker in text for marker in ('-----BEGIN PRIVATE KEY','-----BEGIN EC PRIVATE KEY','-----BEGIN CERTIFICATE','Authorization:','X-Consul-Token:')):
                    scope_violation[0]='LOG_PRIVACY';raise RuntimeError('LOG_PRIVACY_VIOLATION')
    except BaseException as exc:harness_error=type(exc).__name__
    finally:
        retired=retirement();dump()
        try:after=source()
        except BaseException as exc:harness_error=harness_error or ('SOURCE_POST_'+type(exc).__name__)
        receipt=dict(schema='unified.f26.matched-cadence-service.experiment.v1',head=before['head'],tree=before['tree'],source_before=before,source_after=after,source_unchanged=before==after,python=sys.version,outcomes=outcomes,mutant_invocations=mutant_calls[0],harness_error=harness_error,scope_violation=scope_violation[0],phase_event_limit=2048,event_count=total[0],events_retained=len(rows),owned_processes_created=len(children),retirement=retired,original_deadlines_budgets_security_unchanged=True,simulation='OWN_DISPOSABLE_50MS_PRE_EXIT_TRANSACTION_COST_BOTH_ARMS_POSTFIRST_HEARTBEAT_CADENCE_ONLY_VARIABLE',historical_cause='NOT_ESTABLISHED',code_fix='TEST_ONLY_CADENCE_RESTORE',physical='NOT_RUN',production='NO_GO',lane='RETIRED' if not retired['threads_alive'] and not retired['children_alive'] else 'CLEANUP_FAILED',family_seconds=round(time.monotonic()-start,3))
        (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True),encoding='utf8');done.set();timer.join(1)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_before','source_after')}),flush=True)
    sys.exit(0 if len(outcomes)==1 and not harness_error and not scope_violation[0] and before==after and not retired['threads_alive'] and not retired['children_alive'] else 1)
