"""Explicit suites: PureAsyncRules is loop-free; AsyncLifecycleE2E needs a separate lease."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'unified_system/collector_async.py'


def pure_rules(extra=()):
    if not SOURCE.is_file():
        raise AssertionError('FEATURE_NOT_IMPLEMENTED: owned async lifecycle source absent')
    tree=ast.parse(SOURCE.read_bytes())
    names={'CollectorAsyncBlocked','_need','validate_frames','select_mode'}
    names.update(extra)
    selected=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
    if {node.name for node in selected}!=names:
        raise AssertionError('FEATURE_NOT_IMPLEMENTED: pure lifecycle rules absent')
    scope={}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'),scope)
    return scope


class PureAsyncRules(unittest.TestCase):
    """AST-selected actual pure function bodies only, not a module/runtime qualification."""
    def test_frame_byte_budget_is_utf8_and_exact(self):
        rule=pure_rules()['validate_frames']
        self.assertEqual(rule(('é',b'ab'),dict(frames=2,frame_bytes=2,raw_bytes=4)),(2,2))
        with self.assertRaises(ValueError):rule(('éé',),dict(frames=1,frame_bytes=3,raw_bytes=4))

    def test_invalid_shape_and_aggregate_are_rejected(self):
        rule=pure_rules()['validate_frames']
        limits=dict(frames=4,frame_bytes=1048576,raw_bytes=4194304)
        for frames in ([],(),(bytearray(b'a'),),(b'a',)*5):
            with self.subTest(frames=type(frames).__name__):
                with self.assertRaises(ValueError):rule(frames,limits)
        with self.assertRaises(ValueError):rule((b'ab',b'cd'),dict(frames=2,frame_bytes=2,raw_bytes=3))

    def test_profile_limits_cannot_exceed_fixed_ceiling_or_use_bool(self):
        rule=pure_rules()['validate_frames']
        for limits in (dict(frames=True,frame_bytes=1,raw_bytes=1),
                       dict(frames=5,frame_bytes=1,raw_bytes=1),
                       dict(frames=1,frame_bytes=1048577,raw_bytes=4194304)):
            with self.assertRaises(ValueError):rule((b'a',),limits)

    def test_overdue_receive_cannot_beat_starved_timer(self):
        choose=pure_rules()['select_mode']
        self.assertEqual(choose('UNDECIDED','NORMAL',12,10),'ABORT')
        self.assertEqual(choose('UNDECIDED','NORMAL',10,10),'ABORT')
        self.assertEqual(choose('UNDECIDED','NORMAL',9,10),'NORMAL')

    def test_first_mode_is_immutable(self):
        choose=pure_rules()['select_mode']
        self.assertEqual(choose('NORMAL','ABORT',12,10),'NORMAL')
        self.assertEqual(choose('ABORT','NORMAL',9,10),'ABORT')
        self.assertEqual(choose('UNDECIDED','ABORT',9,10),'ABORT')
        with self.assertRaises(ValueError):choose('UNDECIDED','OTHER',1,10)

    def test_supplied_input_is_not_reported_as_received_before_completion(self):
        count=pure_rules(('input_counters',))['input_counters']
        pending=count((2,3),False)
        self.assertEqual(pending['input_frames_supplied'],2)
        self.assertEqual(pending['input_bytes_supplied'],5)
        self.assertIsNone(pending['raw_frames_received'])
        self.assertIsNone(pending['raw_received_bytes'])
        complete=count((2,3),True)
        self.assertEqual(complete['raw_frames_received'],2)
        self.assertEqual(complete['raw_received_bytes'],5)

    def test_narrower_storage_profiles_reject_before_worker_writes(self):
        import copy
        check=pure_rules(('require_storage_profile',))['require_storage_profile']
        supported=dict(raw_profile=dict(max_observations=16,max_payload_occurrence_bytes=4194304,
            max_state_bytes=16777216,sqlite_headroom_bytes=262144,inventory_file_limit=128),
            lifecycle_headroom_bytes=65536,max_lifecycle_records=128,max_context_bytes=16777216)
        self.assertEqual(check(supported),'unified.collector.async-storage.fixed.v1')
        for key,value in (('max_observations',4),('max_payload_occurrence_bytes',1048576),
                          ('max_state_bytes',8388608)):
            narrower=copy.deepcopy(supported);narrower['raw_profile'][key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):check(narrower)
        narrower=copy.deepcopy(supported);narrower['max_context_bytes']=8388608
        with self.assertRaises(ValueError):check(narrower)
        class IntegerSubclass(int):pass
        for value in (True,16.0,IntegerSubclass(16)):
            invalid=copy.deepcopy(supported);invalid['raw_profile']['max_observations']=value
            with self.assertRaises(ValueError):check(invalid)
        for nested in (False,True):
            invalid=copy.deepcopy(supported)
            (invalid['raw_profile'] if nested else invalid)['extra']=1
            with self.assertRaises(ValueError):check(invalid)


class AsyncLifecycleE2E(unittest.TestCase):
    """NOT_RUN until Root/A8 allocation. Real default loop and real local store.

    A reviewed external custodian sets all three fields. Test-only prospective
    manifest metadata binds actual new application maps; it grants no admission.
    """
    scratch_parent=None
    manifest_bytes=None
    source_map_sha256=None
    loop_observations=[]

    def setUp(self):
        import hashlib,json,re,sys
        from uuid import uuid4
        self.assertIsNotNone(self.scratch_parent,'explicit retained own scratch required')
        self.assertIs(type(self.manifest_bytes),bytes,'prospective source manifest required')
        self.assertIs(type(self.source_map_sha256),str,'external actual application-map digest required')
        self.assertRegex(self.source_map_sha256,r'^[a-f0-9]{64}$')
        provenance=json.loads(self.manifest_bytes)['async_test_provenance']
        self.assertEqual(provenance,dict(scope='PROSPECTIVE_TEST_ONLY_NOT_ADMISSION',
            actual_application_map_sha256=self.source_map_sha256))
        sys.path.insert(0,str(ROOT))
        from unified_system import collector_async as subject
        from unified_system.collector_profile import validate_collector_profile
        from unified_system.storage.collector_context import CollectorContext,CollectorContextProfile
        from unified_system.storage.raw_capture import RawCaptureProfile
        from unified_system.collector_logging import CollectorLog,LogLimits
        self.subject=subject
        self.CollectorContext=CollectorContext
        self.root=Path(self.scratch_parent)/self._testMethodName
        self.root.mkdir(exist_ok=False)
        self.context_id=uuid4().hex
        self.store_id=str(uuid4())
        self.binding=hashlib.sha256(self.manifest_bytes).hexdigest()
        self.context_profile=CollectorContextProfile(
            raw_profile=RawCaptureProfile(
                max_observations=4 if self._testMethodName=='test_narrow_context_profile_rejects_before_worker' else 16,
                sqlite_headroom_bytes=262144,inventory_file_limit=128),
            lifecycle_headroom_bytes=65536)
        self.context=CollectorContext.create(self.root/'context',context_id=self.context_id,
            store_id=self.store_id,binding_sha256=self.binding,profile=self.context_profile)
        self.log=CollectorLog.create(self.root/'logs',state_root=self.root,code_root=ROOT,
            context_id=self.context_id,limits=LogLimits(file_bytes=65536,file_count=4))
        document=dict(schema='unified.data-only-collector.profile.v1',mode='SYNTHETIC_OFFLINE',
            grid_launch_profile='grid.data-only-collector.v1',context_id=self.context_id,
            store_id=self.store_id,source_manifest_sha256=self.binding,
            instrument_identity='synthetic-btcusdt-v1',
            limits=dict(frames=4,frame_bytes=1048576,raw_bytes=4194304,duration_seconds=120),
            network=dict(rest=False,websocket=False),
            features={key:False for key in ('trading','training','math','public_submit','authority_mutation')},
            logging=dict(schema='unified.collector.logging.v1',max_file_bytes=65536,file_count=4))
        self.profile=validate_collector_profile(document,manifest_sha256=self.binding)
        self.frame=json.dumps(dict(topic='publicTrade.BTCUSDT',data=[dict(
            T=1794441600000,s='BTCUSDT',p='100',v='2',S='Buy',i='synthetic-async-1')]),
            separators=(',',':')).encode()
        self.session=self.new_session((self.frame,))

    def new_session(self,frames):
        return self.subject.CollectorAsyncSession(self.profile,manifest_bytes=self.manifest_bytes,
            frames=frames,context=self.context,log=self.log,observed_at_ms=1794441600001)

    def tearDown(self):
        # Only synchronous release of owned resources; any failure is a test
        # error, never suppression of an unretired writer. Artifacts retained.
        errors=[]
        for owner in (getattr(self,'context',None),getattr(self,'log',None)):
            if owner is not None:
                try:owner.close()
                except BaseException as error:errors.append(error)
        if errors:raise BaseExceptionGroup('test owner cleanup',errors)

    def run_owned(self,body):
        import asyncio
        import inspect
        primary=[];cleanup=[];loop_errors=[]
        runner=None;loop=None;proactor=None;sockets=[]
        socket_snapshot_complete=False;proactor_snapshot_complete=False
        close_succeeded=None;result=None
        try:
            runner=asyncio.Runner()
            loop=runner.get_loop()
            for name in ('_ssock','_csock'):
                sock=getattr(loop,name,None)
                if sock is not None:sockets.append(sock)
            socket_snapshot_complete=len(sockets)==2
            proactor=getattr(loop,'_proactor',None)
            proactor_snapshot_complete=True
            loop.set_exception_handler(lambda _,context:loop_errors.append(context))
            result=runner.run(body)
            pending=[task.get_name() for task in asyncio.all_tasks(loop) if not task.done()]
            self.assertEqual(pending,[],'no unrelated or owned background tasks permitted')
        except BaseException as error:
            primary.append(error)
        finally:
            if runner is not None:
                try:
                    runner.close()
                    close_succeeded=True
                except BaseException as error:
                    cleanup.append(error);close_succeeded=False
            # Initialization/task-submission failure can leave an unsubmitted
            # coroutine. Never close a suspended body as an I/O-retirement shortcut.
            try:
                if inspect.iscoroutine(body) and inspect.getcoroutinestate(body)==inspect.CORO_CREATED:
                    body.close()
            except BaseException as error:
                cleanup.append(error)
            loop_closed=None;fds=[];proactor_closed=None
            if loop is not None:
                try:loop_closed=loop.is_closed()
                except BaseException as error:cleanup.append(error)
            for sock in sockets:
                try:fds.append(sock.fileno())
                except BaseException as error:
                    cleanup.append(error);fds.append(None)
            if proactor is not None:
                try:proactor_closed=getattr(proactor,'_iocp') is None
                except BaseException as error:cleanup.append(error)
            facts_closed=(runner is not None and loop_closed is True and close_succeeded is True
                and socket_snapshot_complete and all(fd==-1 for fd in fds)
                and proactor_snapshot_complete and (proactor is None or proactor_closed is True))
            if not primary and not cleanup and (not facts_closed or loop_errors):
                cleanup.append(AssertionError('RUNNER_RETIREMENT_UNKNOWN'))
            observation=dict(test=self.id(),status='CLOSED_OBSERVED' if facts_closed and not primary and not cleanup and not loop_errors else 'UNKNOWN',
                runner_acquired=runner is not None,runner_close_succeeded=close_succeeded,
                loop_class=None if loop is None else type(loop).__name__,loop_closed=loop_closed,
                control_socket_fds=fds,socket_snapshot_complete=socket_snapshot_complete,
                proactor_applicable=None if not proactor_snapshot_complete else proactor is not None,
                proactor_closed_observed=proactor_closed,loop_errors=len(loop_errors),
                primary_error_types=[type(error).__name__ for error in primary],
                cleanup_error_types=[type(error).__name__ for error in cleanup],
                scope='PYTHON_CONTROL_RESOURCE_OBSERVATION_NOT_OS_HANDLE_PROOF')
            type(self).loop_observations.append(observation)
        errors=primary+cleanup
        if errors:
            raise errors[0] if len(errors)==1 else BaseExceptionGroup('Runner primary/cleanup outcomes',errors)
        return result

    def inspect_context(self):
        return self.CollectorContext.inspect(self.context.root,context_id=self.context_id,
            store_id=self.store_id,binding_sha256=self.binding,profile=self.context_profile)

    def test_normal_actual_history_checkpoint_and_resources(self):
        async def body():
            self.session.start()
            result=await self.session.wait()
            self.assertEqual(result['retirement_outcome'],'STOPPED')
            self.assertEqual(result['context_lifecycle_before_close'],'STOPPED')
            self.assertEqual(result['resource_closed'],dict(context=True,log=True))
            self.assertEqual(result['raw_observations_stored'],3)
            self.assertIsNone(result['previous_checkpoint'])
            self.assertEqual(result['parsed_trade_occurrences'],1)
            self.assertEqual(result['provider_sends'],0)
            self.assertTrue(result['storage_profile_verified'])
            self.assertEqual(result['supported_storage_profile_id'],'unified.collector.async-storage.fixed.v1')
            self.assertEqual(result['continuity'],'UNKNOWN')
            self.assertEqual(await self.session.stop(),result)
            return result
        self.run_owned(body())
        self.assertEqual(self.inspect_context().state,'STOPPED')

    def test_suspended_real_sink_enforces_backpressure(self):
        async def body():
            import asyncio
            from unittest.mock import patch
            entered=asyncio.Event();release=asyncio.Event();calls=[]
            original=self.subject._AsyncSink.store_capture
            async def gate(sink,**values):
                calls.append(values)
                if len(calls)==1:
                    entered.set()
                    await release.wait()
                return await original(sink,**values)
            self.session=self.new_session((self.frame,self.frame))
            with patch.object(self.subject._AsyncSink,'store_capture',gate):
                self.session.start()
                await asyncio.wait_for(entered.wait(),2)
                await asyncio.sleep(0)
                self.assertEqual(len(calls),1)
                self.assertFalse(self.session._receive_task.done())
                release.set()
                result=await self.session.wait()
                self.assertEqual(result['raw_frames_received'],2)
                self.assertEqual(len(calls),5)
        self.run_owned(body())

    def test_abort_joins_suspended_writer_before_close(self):
        async def body():
            import asyncio
            from unittest.mock import patch
            entered=asyncio.Event()
            original=self.subject._AsyncSink.store_capture
            async def suspended(sink,**values):
                entered.set()
                await asyncio.Event().wait()
                return await original(sink,**values)
            with patch.object(self.subject._AsyncSink,'store_capture',suspended):
                self.session.start()
                await asyncio.wait_for(entered.wait(),2)
                result=await self.session.stop()
                self.assertEqual(result['retirement_outcome'],'UNKNOWN')
                self.assertTrue(self.session._receive_task.done())
                self.assertEqual(result['resource_closed'],dict(context=True,log=True))
        self.run_owned(body())
        self.assertEqual(self.inspect_context().state,'UNKNOWN')

    def test_repeated_waiter_cancel_observes_one_retirement(self):
        async def body():
            import asyncio
            from unittest.mock import patch
            entered=asyncio.Event()
            async def suspended(sink,**values):
                entered.set()
                await asyncio.Event().wait()
            with patch.object(self.subject._AsyncSink,'store_capture',suspended):
                self.session.start()
                await asyncio.wait_for(entered.wait(),2)
                waiter=asyncio.create_task(self.session.wait(),name='test-cancel-waiter')
                await asyncio.sleep(0)
                waiter.cancel()
                await asyncio.sleep(0)
                waiter.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await waiter
                self.assertTrue(self.session._retirement_task.done())
                result=await self.session.stop()
                self.assertEqual(result['retirement_outcome'],'UNKNOWN')
        self.run_owned(body())

    def _lost_ack(self,kind):
        async def body():
            from unittest.mock import patch
            from grid.raw_capture import decode_observation
            original=self.CollectorContext.store_capture
            calls=[]
            async def lost(context,**values):
                result=await original(context,**values)
                if decode_observation(values['observation_bytes'])['kind']==kind:
                    calls.append(values['observation_bytes'])
                    raise RuntimeError('TEST_RESPONSE_LOST_AFTER_REAL_STORE')
                return result
            with patch.object(self.CollectorContext,'store_capture',lost):
                self.session.start()
                with self.assertRaises(BaseException):
                    await self.session.wait()
                self.assertEqual(len(calls),1,'no replay/retry after actual write')
                self.assertEqual(self.session.outcome['retirement_outcome'],'UNKNOWN')
                self.assertTrue(self.session.outcome['resource_closed']['context'])
        self.run_owned(body())
        state=self.inspect_context()
        self.assertEqual(state.state,'UNKNOWN')
        self.assertIsNotNone(state.checkpoint)

    def test_frame_ack_loss_retains_unknown_checkpoint(self):
        self._lost_ack('frame')

    def test_final_disconnect_ack_loss_retains_unknown_checkpoint(self):
        self._lost_ack('disconnect')

    def test_stop_before_start_and_wait_reject_are_one_shot(self):
        async def body():
            result=await self.session.stop()
            self.assertFalse(result['ownership_transferred'])
            with self.assertRaises(ValueError):self.session.start()
            with self.assertRaises(ValueError):await self.session.wait()
        self.run_owned(body())

    def test_starved_timer_cannot_select_normal_after_deadline(self):
        async def body():
            from types import SimpleNamespace
            from unittest.mock import patch
            from grid.raw_capture import decode_observation
            now=[100.0]
            original=self.subject._AsyncSink.store_capture
            async def delayed(sink,**values):
                result=await original(sink,**values)
                if decode_observation(values['observation_bytes'])['kind']=='disconnect':
                    now[0]=221.0
                return result
            with patch.object(self.subject,'time',SimpleNamespace(monotonic=lambda:now[0])),patch.object(
                    self.subject._AsyncSink,'store_capture',delayed):
                self.session.start()
                with self.assertRaises(TimeoutError):await self.session.wait()
                self.assertEqual(self.session.outcome['mode'],'ABORT')
        self.run_owned(body())
        self.assertEqual(self.inspect_context().state,'UNKNOWN')

    def test_persisted_stopped_is_not_erased_by_log_close_failure(self):
        async def body():
            from unittest.mock import patch
            from unified_system.collector_logging import CollectorLog
            original=CollectorLog.close
            def response_lost(log):
                original(log)
                raise RuntimeError('TEST_LOG_CLOSE_RESPONSE_LOST')
            with patch.object(CollectorLog,'close',response_lost):
                self.session.start()
                with self.assertRaises(RuntimeError):await self.session.wait()
                result=self.session.outcome
                self.assertEqual(result['context_lifecycle_before_close'],'STOPPED')
                self.assertEqual(result['retirement_outcome'],'UNKNOWN')
                self.assertFalse(result['resource_closed']['log'])
        self.run_owned(body())
        self.assertEqual(self.inspect_context().state,'STOPPED')

    def _creation_failure(self,position):
        async def body():
            import asyncio
            from unittest.mock import patch
            loop=asyncio.get_running_loop()
            original=loop.create_task
            count=[0]
            rejected=[]
            def fail(coroutine,*,name=None,context=None):
                if name is not None and name.startswith('collector-async-'):
                    count[0]+=1
                    if count[0]==position:
                        rejected.append(coroutine)
                        raise RuntimeError('TEST_TASK_CREATION_FAILED')
                return original(coroutine,name=name,context=context)
            with patch.object(loop,'create_task',fail):
                with self.assertRaises(RuntimeError):self.session.start()
                with self.assertRaises(RuntimeError):await self.session.wait()
                self.assertEqual(len(rejected),1)
                self.assertIsNone(rejected[0].cr_frame,'actual _spawn must close unsubmitted coroutine')
                self.assertEqual(self.session.outcome['retirement_outcome'],'UNKNOWN')
                self.assertTrue(self.session.outcome['resource_closed']['context'])
                self.assertEqual(self.session.outcome['input_frames_supplied'],1)
                self.assertIsNone(self.session.outcome['raw_frames_received'])
        self.run_owned(body())
        self.assertEqual(self.inspect_context().state,'UNKNOWN')

    def test_retirement_task_creation_failure_keeps_cleanup_owner(self):
        self._creation_failure(1)

    def test_receive_task_creation_failure_keeps_cleanup_owner(self):
        self._creation_failure(2)

    def test_timer_task_creation_failure_keeps_cleanup_owner(self):
        self._creation_failure(3)

    def test_invalid_frame_gap_survives_clean_resume(self):
        async def first():
            self.session=self.new_session((b'not-json',))
            self.session.start()
            result=await self.session.wait()
            self.assertTrue(result['gap_open'])
            self.assertGreaterEqual(result['gap_count'],1)
        self.run_owned(first())
        # A separate cleanly reopened lifetime; original history is retained.
        from unified_system.collector_logging import CollectorLog
        self.context=self.CollectorContext.open(self.root/'context',context_id=self.context_id,
            store_id=self.store_id,binding_sha256=self.binding,profile=self.context_profile)
        self.log=CollectorLog.open(self.root/'logs',state_root=self.root,code_root=ROOT,context_id=self.context_id)
        async def second():
            self.session=self.new_session((self.frame,))
            self.session.start()
            result=await self.session.wait()
            self.assertTrue(result['gap_open'])
            self.assertIsNotNone(result['previous_checkpoint'])
            self.assertEqual(result['raw_frames_received'],1)
            self.assertGreater(result['raw_observations_stored'],3)
        self.run_owned(second())

    def _cancel_after_real_write(self,kind):
        async def body():
            import asyncio
            from unittest.mock import patch
            from grid.raw_capture import decode_observation
            original=self.CollectorContext.store_capture
            entered=asyncio.Event();writes=[]
            async def suspended_ack(context,**values):
                result=await original(context,**values)
                if decode_observation(values['observation_bytes'])['kind']==kind:
                    writes.append(values['observation_bytes'])
                    entered.set()
                    await asyncio.Event().wait()
                return result
            with patch.object(self.CollectorContext,'store_capture',suspended_ack):
                self.session.start()
                await asyncio.wait_for(entered.wait(),2)
                result=await self.session.stop()
                self.assertEqual(result['retirement_outcome'],'UNKNOWN')
                self.assertEqual(len(writes),1)
                self.assertIsNone(result['raw_frames_received'])
                self.assertTrue(result['resource_closed']['context'])
                # Existing Recorder returns False on already-failed/disconnected
                # cleanup; no exception note is invented for that result.
                self.assertEqual(result['expected_receive_cancellation_notes'],())
        self.run_owned(body())
        state=self.inspect_context()
        self.assertEqual(state.state,'UNKNOWN')
        self.assertIsNotNone(state.checkpoint)

    def test_cancel_after_real_frame_write_before_ack(self):
        self._cancel_after_real_write('frame')

    def test_cancel_after_real_disconnect_write_before_ack(self):
        self._cancel_after_real_write('disconnect')

    def test_primary_and_log_cleanup_failures_are_both_preserved(self):
        async def body():
            from unittest.mock import patch
            from unified_system.collector_logging import CollectorLog
            original_close=CollectorLog.close
            async def failure(context,**values):
                raise RuntimeError('TEST_ACTUAL_OWNER_CALL_FAILURE')
            def failed_close(log):
                original_close(log)
                raise RuntimeError('TEST_LOG_CLOSE_FAILURE')
            def leaves(error):
                if isinstance(error,BaseExceptionGroup):
                    return [leaf for child in error.exceptions for leaf in leaves(child)]
                return [error]
            with patch.object(self.CollectorContext,'store_capture',failure),patch.object(
                    CollectorLog,'close',failed_close):
                self.session.start()
                with self.assertRaises(BaseExceptionGroup) as caught:
                    await self.session.wait()
                messages=[str(error) for error in leaves(caught.exception)]
                self.assertIn('TEST_ACTUAL_OWNER_CALL_FAILURE',messages)
                self.assertIn('TEST_LOG_CLOSE_FAILURE',messages)
                self.assertEqual(self.session.outcome['retirement_outcome'],'UNKNOWN')
        self.run_owned(body())

    def test_narrow_context_profile_rejects_before_worker(self):
        async def body():
            self.session=self.new_session((self.frame,)*4)
            self.session.start()
            with self.assertRaises(self.subject.CollectorAsyncBlocked) as caught:
                await self.session.wait()
            self.assertEqual(str(caught.exception),'COLLECTOR_ASYNC_STORAGE_PROFILE_UNSUPPORTED')
            self.assertIsNone(self.session._worker)
            result=self.session.outcome
            self.assertEqual(result['retirement_outcome'],'UNKNOWN')
            self.assertIsNone(result['raw_frames_received'])
            self.assertFalse(result['storage_profile_verified'])
        self.run_owned(body())
        state=self.inspect_context()
        self.assertEqual(state.state,'UNKNOWN')
        self.assertEqual(state.history,())


def inert_runner_method(fake_asyncio):
    """Execute the ACTUAL method AST with only its asyncio import substituted.

    These are fault controls, never a default-loop/runtime qualification.
    No sys.modules/global import or event-loop policy is changed.
    """
    import builtins
    tree=ast.parse(Path(__file__).read_bytes())
    owner=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='AsyncLifecycleE2E')
    method=next(node for node in owner.body if isinstance(node,ast.FunctionDef) and node.name=='run_owned')
    original_import=builtins.__import__
    def controlled_import(name,*args,**kwargs):
        if name=='asyncio':return fake_asyncio
        return original_import(name,*args,**kwargs)
    scope={'__builtins__':dict(vars(builtins),__import__=controlled_import)}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(Path(__file__)),'exec'),scope)
    return scope['run_owned']


class InertRunnerControls(unittest.TestCase):
    """Actual run_owned fault paths with inert objects; ZERO loop/IOCP claims."""
    def exercise(self,phase):
        from types import SimpleNamespace
        primary=RuntimeError('INERT_PRIMARY_'+phase)
        cleanup=RuntimeError('INERT_CLOSE_FAILURE')
        calls=[]
        class Loop:
            closed=False
            def set_exception_handler(self,callback):
                if phase=='setup':raise primary
            def is_closed(self):return self.closed
        loop=Loop()
        class Runner:
            def __init__(self):
                if phase=='constructor':raise primary
            def get_loop(self):
                if phase=='get_loop':raise primary
                return loop
            def run(self,body):
                if phase in ('body','body_and_close'):raise primary
                return 'INERT_RESULT'
            def close(self):
                calls.append('close')
                loop.closed=True
                if phase in ('close','body_and_close'):raise cleanup
        fake=SimpleNamespace(Runner=Runner,all_tasks=lambda ignored:())
        class Owner(unittest.TestCase):
            loop_observations=[]
        owner=Owner()
        async def never_started():
            raise AssertionError('inert fault control must not execute coroutine body')
        body=never_started()
        method=inert_runner_method(fake)
        caught=None
        try:method(owner,body)
        except BaseException as error:caught=error
        finally:
            if body.cr_frame is not None:body.close()
        return primary,cleanup,calls,owner.loop_observations,caught,body

    def test_get_loop_failure_still_closes_owned_runner(self):
        primary,_,calls,observations,caught,body=self.exercise('get_loop')
        self.assertEqual(calls,['close'])
        self.assertIs(caught,primary)
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0]['status'],'UNKNOWN')
        self.assertIsNone(observations[0]['loop_closed'])
        self.assertIsNone(body.cr_frame)

    def test_setup_failure_after_loop_acquisition_still_closes(self):
        primary,_,calls,observations,caught,_=self.exercise('setup')
        self.assertEqual(calls,['close'])
        self.assertIs(caught,primary)
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0]['status'],'UNKNOWN')
        self.assertTrue(observations[0]['loop_closed'])

    def test_body_and_close_errors_are_preserved_together(self):
        primary,cleanup,calls,observations,caught,_=self.exercise('body_and_close')
        self.assertEqual(calls,['close'])
        self.assertIsInstance(caught,BaseExceptionGroup)
        self.assertEqual(caught.exceptions,(primary,cleanup))
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0]['status'],'UNKNOWN')
        self.assertFalse(observations[0]['runner_close_succeeded'])

    def test_constructor_failure_retains_unknown_observation(self):
        primary,_,calls,observations,caught,_=self.exercise('constructor')
        self.assertEqual(calls,[])
        self.assertIs(caught,primary)
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0]['status'],'UNKNOWN')
        self.assertFalse(observations[0]['runner_acquired'])

    def test_body_failure_preserves_primary_after_successful_close(self):
        primary,_,calls,observations,caught,_=self.exercise('body')
        self.assertEqual(calls,['close'])
        self.assertIs(caught,primary)
        self.assertEqual(observations[0]['status'],'UNKNOWN')
        self.assertTrue(observations[0]['runner_close_succeeded'])

    def test_close_failure_without_primary_retains_cleanup_and_unknown(self):
        _,cleanup,calls,observations,caught,_=self.exercise('close')
        self.assertEqual(calls,['close'])
        self.assertIs(caught,cleanup)
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0]['status'],'UNKNOWN')
        self.assertFalse(observations[0]['runner_close_succeeded'])
