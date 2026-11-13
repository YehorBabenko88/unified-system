"""Owned finite asyncio lifecycle over existing Grid/Storage, never admission.

The caller owns the default loop and source/runtime custody. This module owns
only its transferred local context/log and three finite tasks. Awaitable local
Storage currently performs synchronous I/O; cooperative deadlines are not hard
I/O retirement, native handle or process-family proofs.
"""
import hashlib
import json
import time
from dataclasses import asdict
from .collector_profile import CollectorProfile, decode_collector_profile


class CollectorAsyncBlocked(ValueError):
    pass


def _need(value, code='COLLECTOR_ASYNC_BLOCKED'):
    if not value:
        raise CollectorAsyncBlocked(code)


def validate_frames(frames, limits):
    for name, ceiling in (('frames',4),('frame_bytes',1048576),('raw_bytes',4194304)):
        _need(type(limits[name]) is int and 1<=limits[name]<=ceiling)
    _need(type(frames) is tuple and 1<=len(frames)<=limits['frames'])
    sizes=[]
    for frame in frames:
        _need(type(frame) in (str,bytes) and len(frame)<=limits['frame_bytes'])
        size=len(frame.encode('utf-8')) if type(frame) is str else len(frame)
        _need(size<=limits['frame_bytes'])
        sizes.append(size)
    _need(sum(sizes)<=limits['raw_bytes'])
    return tuple(sizes)


def select_mode(current, requested, now, deadline):
    """First outcome wins; a starved timer cannot admit an overdue receive."""
    _need(current in ('UNDECIDED','NORMAL','ABORT') and requested in ('NORMAL','ABORT'))
    if current!='UNDECIDED':
        return current
    return 'ABORT' if requested=='ABORT' or now>=deadline else 'NORMAL'


def _combined(errors):
    unique=[]
    for error in errors:
        if not any(error is prior for prior in unique):
            unique.append(error)
    return unique[0] if len(unique)==1 else BaseExceptionGroup('Collector async outcomes',unique)


def input_counters(sizes, receive_completed):
    _need(type(receive_completed) is bool)
    return dict(input_frames_supplied=len(sizes),input_bytes_supplied=sum(sizes),
        raw_frames_received=len(sizes) if receive_completed else None,
        raw_received_bytes=sum(sizes) if receive_completed else None)


def require_storage_profile(profile):
    """Own adapter support restriction, not an A4 schema or capacity promise."""
    expected=dict(raw_profile=dict(max_observations=16,max_payload_occurrence_bytes=4194304,
        max_state_bytes=16777216,sqlite_headroom_bytes=262144,inventory_file_limit=128),
        lifecycle_headroom_bytes=65536,max_lifecycle_records=128,max_context_bytes=16777216)
    code='COLLECTOR_ASYNC_STORAGE_PROFILE_UNSUPPORTED'
    _need(type(profile) is dict and all(type(key) is str for key in profile)
        and set(profile)==set(expected),code)
    raw=profile['raw_profile']
    _need(type(raw) is dict and all(type(key) is str for key in raw)
        and set(raw)==set(expected['raw_profile']),code)
    for key,value in expected['raw_profile'].items():
        _need(type(raw[key]) is int and raw[key]==value,code)
    for key in ('lifecycle_headroom_bytes','max_lifecycle_records','max_context_bytes'):
        _need(type(profile[key]) is int and profile[key]==expected[key],code)
    return 'unified.collector.async-storage.fixed.v1'


def _control(path, limit=32768):
    # Existing owners validate their formats; this read only binds transferred
    # owners to the selected profile, never establishes writer/source authority.
    _need(type(limit) is int and 1<=limit<=32768)
    with path.open('rb') as stream:
        raw=stream.read(limit+1)
    _need(len(raw)<=limit)
    def unique(pairs):
        value={}
        for key,item in pairs:
            _need(key not in value)
            value[key]=item
        return value
    def no_number(_):
        raise CollectorAsyncBlocked('COLLECTOR_ASYNC_CONTROL_NUMBER')
    return json.loads(raw,object_pairs_hook=unique,parse_float=no_number,parse_constant=no_number)


class _AsyncSink:
    """Sequential scheduling adapter, not a background writer or async disk."""
    def __init__(self, context):
        self.context=context
        self.active=0
        self.errors=[]

    async def store_capture(self, *, observation_bytes, payload_bytes):
        import asyncio
        _need(self.active==0,'COLLECTOR_ASYNC_IO_INFLIGHT')
        self.active=1
        try:
            await asyncio.sleep(0)
            result=await self.context.store_capture(
                observation_bytes=observation_bytes,payload_bytes=payload_bytes)
            await asyncio.sleep(0)
            return result
        except BaseException as error:
            self.errors.append(error)
            raise
        finally:
            self.active=0


class CollectorAsyncSession:
    """One-shot ownership transfer via start; all waiters observe one retirement.

    context/log are caller-created actual owners, not duck-typed stores. Root's
    external source/runtime admission remains mandatory. Never wrap this around
    OwnedWorkerService.run_offline, which already owns its Worker task.
    """
    def __init__(self, profile, *, manifest_bytes, frames, context, log, observed_at_ms):
        _need(type(profile) is CollectorProfile)
        _need(type(manifest_bytes) is bytes and 0<len(manifest_bytes)<=262144)
        checked=decode_collector_profile(profile.encoded,
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
        _need(type(observed_at_ms) is int and 0<observed_at_ms<2**63)
        self._sizes=validate_frames(frames,checked.document['limits'])
        self._profile=checked
        self._config=checked.document
        self._manifest=manifest_bytes
        self._frames=frames
        self._context=context
        self._log=log
        self._observed=observed_at_ms
        self._state='NEW'
        self._mode='UNDECIDED'
        self._loop=None
        self._receive_task=None
        self._timer_task=None
        self._retirement_task=None
        self._trigger=None
        self._errors=[]
        self._cancel_requested=False
        self._cancel_notes=[]
        self._sink=None
        self._worker=None
        self._received=None
        self._previous=None
        self._facts=None
        self._outcome=None
        self._outcome_error=None
        self._storage_profile_id=None

    def _same_loop(self):
        import asyncio
        loop=asyncio.get_running_loop()
        _need(self._loop is None or loop is self._loop,'COLLECTOR_ASYNC_WRONG_LOOP')
        return loop

    def _spawn(self, coroutine, name):
        try:
            return self._loop.create_task(coroutine,name=name)
        except BaseException:
            coroutine.close()
            raise

    def start(self):
        self._same_loop()
        _need(self._state=='NEW','COLLECTOR_ASYNC_ALREADY_USED')
        from .storage.collector_context import CollectorContext
        from .collector_logging import CollectorLog
        _need(type(self._context) is CollectorContext and type(self._log) is CollectorLog,
              'COLLECTOR_ASYNC_OWNER_TYPE')
        self._loop=self._same_loop()
        self._started=time.monotonic()
        self._deadline=self._started+self._config['limits']['duration_seconds']
        self._state='OWNED'
        try:
            self._trigger=self._loop.create_future()
            # Retirement is retained before any receive can run. If this very
            # first creation fails, no async I/O/task exists: close synchronously.
            self._retirement_task=self._spawn(self._retire(),'collector-async-retirement')
            self._receive_task=self._spawn(self._receive(),'collector-async-receive')
            self._timer_task=self._spawn(self._timer(),'collector-async-deadline')
        except BaseException as error:
            self._errors.append(error)
            self._request('ABORT')
            if self._retirement_task is None:
                closed=self._close_owners()
                self._finish(None,closed)
            # Ownership is NOT returned. wait/stop observes retained cleanup.
            raise

    def _request(self, mode):
        self._mode=select_mode(self._mode,mode,time.monotonic(),self._deadline)
        if self._mode=='ABORT' and not self._errors and time.monotonic()>=self._deadline:
            self._errors.append(TimeoutError('COLLECTOR_ASYNC_DURATION_EXCEEDED'))
        if self._trigger is not None and not self._trigger.done():
            self._trigger.set_result(None)

    async def _timer(self):
        import asyncio
        await asyncio.sleep(max(0,self._deadline-time.monotonic()))
        if self._mode=='UNDECIDED':
            self._errors.append(TimeoutError('COLLECTOR_ASYNC_DURATION_EXCEEDED'))
            self._request('ABORT')
        # Never await retirement: retirement joins this timer.

    def _history_values(self, facts):
        from grid.raw_capture import decode_observation
        values=[]
        for fact in facts:
            _need(hashlib.sha256(fact.observation_bytes).hexdigest()==fact.observation_sha256)
            if fact.payload_bytes is not None:
                _need(hashlib.sha256(fact.payload_bytes).hexdigest()==fact.payload_sha256)
            value=decode_observation(fact.observation_bytes)
            _need(value['source_kind']=='SYNTHETIC'
                and value['producer_source_revision']==self._revision
                and value['endpoint']=='synthetic://bybit/linear'
                and value['instrument']==dict(exchange='bybit',category='linear',symbol='BTCUSDT',instrument_version='1')
                and value['payload_sha256']==fact.payload_sha256
                and int(value['payload_bytes'])==fact.payload_byte_count)
            values.append(value)
        return values

    async def _preflight(self):
        from .collector_offline import _grid_revision
        self._revision=_grid_revision(self._manifest)
        config=self._config
        _need(self._context.context_id==config['context_id'],'COLLECTOR_ASYNC_CONTEXT_BINDING')
        # require_ready returns None, not a profile/authority token. The public
        # owner checks bracket THIS bounded marker read under caller-owned
        # exclusive namespace custody; no private marker/profile/Journal access.
        self._context.require_ready()
        marker=_control(self._context.root/'collector-owned.json',8192)
        _need(type(marker) is dict and set(marker)=={'schema','context_id','store_id',
            'binding_sha256','root','root_identity','raw_identity','writer_lock_identity','profile'}
            and marker['schema']=='unified.storage.collector-context.v1'
            and marker['root']==str(self._context.root)
            and marker['context_id']==config['context_id'] and marker['store_id']==config['store_id']
            and marker['binding_sha256']==config['source_manifest_sha256'],'COLLECTOR_ASYNC_CONTEXT_BINDING')
        profile_id=require_storage_profile(marker['profile'])
        self._context.require_ready()
        self._storage_profile_id=profile_id
        log_marker=_control(self._log.root/'context.json')
        _need(log_marker['context_id']==config['context_id']
            and log_marker['limits']['file_bytes']==config['logging']['max_file_bytes']
            and log_marker['limits']['file_count']==config['logging']['file_count'],
            'COLLECTOR_ASYNC_LOG_BINDING')
        self._context.require_ready()
        facts=await self._context.read_history()
        self._history_values(facts)
        self._previous=None if not facts else asdict(await self._context.checkpoint())
        _need(len(facts)+2*len(self._frames)<=14
            and sum(f.payload_byte_count for f in facts)+sum(self._sizes)<=4194304,
            'COLLECTOR_ASYNC_CONTEXT_BUDGET')
        self._log.emit(event='STARTUP',state='STARTING',digest=self._profile.sha256)
        self._log.emit(event='READY',state='RUNNING',count=len(facts))

    async def _receive(self):
        try:
            await self._preflight()
            from grid.worker import Worker,COLLECTOR_PROFILE
            from grid.raw_capture import RawCaptureRecorder,RawCaptureProfile
            self._sink=_AsyncSink(self._context)
            calls=[]
            def factory(symbol,endpoint):
                _need(not calls);calls.append((symbol,endpoint))
                self._context.require_ready()
                return RawCaptureRecorder(self._sink,
                    instrument=dict(exchange='bybit',category='linear',symbol='BTCUSDT',instrument_version='1'),
                    producer_source_revision=self._revision,source_kind='SYNTHETIC',endpoint=endpoint,
                    profile=RawCaptureProfile(16,4194304,1048576,16384,2))
            self._worker=Worker(launch_profile=COLLECTOR_PROFILE,raw_capture_factory=factory)
            self._received=await self._worker.receive_offline(self._frames,symbol='BTCUSDT',
                endpoint='synthetic://bybit/linear',observed_at_ms=self._observed)
            _need(len(calls)==1)
            # Actual monotonic comparison here, not merely the timer callback.
            self._request('NORMAL')
            return self._received
        except BaseException as error:
            self._errors.append(error)
            self._request('ABORT')
            raise

    async def _retire(self):
        try:
            await self._retire_owned()
        except BaseException as error:
            self._errors.append(error)
            # No close while delegated operation retirement is uncertain.
            closed={'context':False,'log':False}
            try:
                status=self._context.status()
                if (self._receive_task is None or self._receive_task.done()) and not status.operation_active and (self._sink is None or self._sink.active==0):
                    closed=self._close_owners()
            except BaseException as cleanup:
                self._errors.append(cleanup)
            self._finish(None,closed)

    async def _retire_owned(self):
        import asyncio
        await self._trigger
        self._state='RETIRING'
        # Timer cannot await us; no self-join or cycle.
        if self._timer_task is not None:
            if not self._timer_task.done():
                self._timer_task.cancel()
            results=await asyncio.gather(self._timer_task,return_exceptions=True)
            for error in results:
                if isinstance(error,BaseException) and not isinstance(error,asyncio.CancelledError):
                    self._errors.append(error)
        if self._receive_task is not None:
            preexisting_cancel=self._receive_task.cancelling()>0
            self._cancel_requested=self._mode=='ABORT' and not self._receive_task.done() and not preexisting_cancel
            if self._cancel_requested:
                self._receive_task.cancel()
            results=await asyncio.gather(self._receive_task,return_exceptions=True)
            for error in results:
                if isinstance(error,BaseException):
                    # _receive retains it already, including unexpected cancellation.
                    if not (self._cancel_requested and isinstance(error,asyncio.CancelledError)):
                        self._errors.append(error)
            if self._cancel_requested:
                for error in self._errors:
                    if isinstance(error,asyncio.CancelledError):
                        self._cancel_notes.extend(getattr(error,'__notes__',()))
                self._errors=[error for error in self._errors if not isinstance(error,asyncio.CancelledError)]
        _need(self._sink is None or self._sink.active==0,'COLLECTOR_ASYNC_IO_NOT_RETIRED')
        if self._sink is not None:
            self._errors.extend(error for error in self._sink.errors
                if not (self._cancel_requested and isinstance(error,asyncio.CancelledError)))
        lifecycle=None
        if self._mode=='NORMAL' and not self._errors:
            try:
                self._facts=await self._context.read_history()
                values=self._history_values(self._facts)
                checkpoint=asdict(await self._context.checkpoint())
                gap_count=sum(value['kind']=='gap_observation' for value in values)
                self._result=dict(checkpoint=checkpoint,previous_checkpoint=self._previous,
                    raw_observations_stored=len(self._facts),
                    raw_payload_occurrence_bytes=sum(f.payload_byte_count for f in self._facts),
                    gap_count=gap_count,gap_open=gap_count>0,
                    parsed_trade_occurrences=sum(len(batch) for batch in self._received['batches']))
                self._log.emit(event='CHECKPOINT',state='RUNNING',digest=checkpoint['raw_journal_digest'])
                status=await self._context.stop()
                _need(status.state=='STOPPED' and not status.operation_active,'COLLECTOR_ASYNC_STOP_UNKNOWN')
                lifecycle=status.state
                self._log.emit(event='SHUTDOWN',state='STOPPED',count=len(self._facts))
            except BaseException as error:
                self._errors.append(error)
        if lifecycle is None:
            try:
                status=self._context.status()
                _need(not status.operation_active,'COLLECTOR_ASYNC_IO_NOT_RETIRED')
                lifecycle=status.state
            except BaseException as error:
                self._errors.append(error)
        closed=self._close_owners()
        self._finish(lifecycle,closed)

    def _close_owners(self):
        closed={}
        for name,owner in (('context',self._context),('log',self._log)):
            try:
                owner.close()
                closed[name]=True
            except BaseException as error:
                self._errors.append(error)
                closed[name]=False
        return closed

    def _finish(self,lifecycle,closed):
        overrun=time.monotonic()>=self._deadline
        if overrun and not any(isinstance(error,TimeoutError) for error in self._errors):
            self._errors.append(TimeoutError('COLLECTOR_ASYNC_RETIREMENT_OVERRUN'))
        self._outcome=dict(schema='unified.collector.async-result.v1',scope='SYNTHETIC_OFFLINE',
            classification='LOCAL_UNATTESTED',mode=self._mode,
            retirement_outcome='UNKNOWN' if self._errors or self._mode!='NORMAL' else 'STOPPED',
            context_lifecycle_before_close=lifecycle,resource_closed=closed,
            context_id=self._config['context_id'],store_id=self._config['store_id'],
            source_manifest_sha256=self._config['source_manifest_sha256'],
            profile_sha256=self._profile.sha256,elapsed_seconds=time.monotonic()-self._started,
            supported_storage_profile_id='unified.collector.async-storage.fixed.v1',
            storage_profile_verified=self._storage_profile_id is not None,
            duration_overrun=overrun,continuity='UNKNOWN',raw_durability='UNKNOWN',
            expected_receive_cancellation_notes=tuple(self._cancel_notes),
            native_outcome='UNKNOWN',publication_confirmed=False,provider_sends=0,
            service_running=False,physical_accepted=False)
        self._outcome.update(input_counters(self._sizes,self._received is not None))
        if self._mode=='NORMAL' and not self._errors:
            self._outcome.update(self._result)
        self._outcome_error=_combined(self._errors) if self._errors else None
        self._state='RETIRED'

    @property
    def outcome(self):
        _need(self._state=='RETIRED' and self._outcome is not None,'COLLECTOR_ASYNC_NOT_RETIRED')
        import copy
        return copy.deepcopy(self._outcome)

    async def _observe(self):
        import asyncio
        cancellations=[]
        if self._retirement_task is not None:
            while True:
                try:
                    await asyncio.shield(self._retirement_task)
                    break
                except asyncio.CancelledError as error:
                    # If the owner task itself is cancelled, this is NOT ordinary
                    # waiter cancellation or evidence of successful retirement.
                    if self._retirement_task.cancelled():
                        raise
                    cancellations.append(error)
                    self._request('ABORT')
                except BaseException:
                    raise
        if cancellations:
            errors=[cancellations[0]]
            if self._outcome_error is not None:
                errors.append(self._outcome_error)
            raise _combined(errors)
        if self._outcome_error is not None:
            raise self._outcome_error
        return self.outcome

    async def wait(self):
        self._same_loop()
        _need(self._state not in ('NEW','UNSTARTED_STOP'),'COLLECTOR_ASYNC_NOT_STARTED')
        return await self._observe()

    async def stop(self):
        self._same_loop()
        if self._state=='NEW':
            self._state='UNSTARTED_STOP'
            return dict(mode='ABORT',retirement_outcome='NOT_STARTED',ownership_transferred=False)
        if self._state=='UNSTARTED_STOP':
            return dict(mode='ABORT',retirement_outcome='NOT_STARTED',ownership_transferred=False)
        if self._state!='RETIRED':
            self._request('ABORT')
        return await self._observe()
