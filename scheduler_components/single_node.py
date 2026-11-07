"""Callable local/offline pilot composition. No clients, worker spawn or authority.

Only admitted owner implementations may supply capabilities. Method presence,
context/readiness, proof bytes and local journal state are never admission.
Actual A2/A4/ROOT adapters and shared composition still require joint agreement.
"""
from dataclasses import asdict, dataclass
import json
import inspect
import re
import uuid

from .domain_v1 import decode_command, encode_command
from .runtime import SchedulerRuntime, Unavailable


def _uuid(value):
    try:
        parsed = uuid.UUID(value) if type(value) is str else None
    except ValueError:
        parsed = None
    if parsed is None or parsed.version != 4 or str(parsed) != value:
        raise ValueError('registered canonical UUIDv4 required; no alias conversion')


def _opaque(value):
    if type(value) is not bytes or not value:
        raise ValueError('opaque bytes are required inputs, never proof by themselves')


def _method(owner, name):
    method = getattr(owner, name, None)
    if not callable(method):
        raise Unavailable('actual owner adapter missing: ' + name)
    if inspect.iscoroutinefunction(method) or inspect.iscoroutinefunction(getattr(method, '__call__', None)):
        raise Unavailable('async owner requires separately reviewed ABI/facade, not direct sync binding')
    return method


def _sync_call(owner, name, *args):
    result = _method(owner, name)(*args)
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result) and inspect.getcoroutinestate(result) == inspect.CORO_CREATED:
            result.close()  # Discard unstarted coroutine; never await/run an event loop.
        raise Unavailable('awaitable is not a receipt, worker adapter or capability')
    return result


def _require(owner, name, *args):
    if _sync_call(owner, name, *args) is not None:
        raise Unavailable('owner must verify or raise; readiness/boolean is not admission')


@dataclass(frozen=True)
class PilotContext:
    node_name: str
    mode: str
    cluster_id: str
    cluster_generation: str
    node_id: str
    worker_incarnation_id: str
    authority_namespace: str

    def __post_init__(self):
        if self.node_name != 'LS5' or self.mode != 'SINGLE_NODE_LOCAL_OFFLINE':
            raise ValueError('initial pilot selector is LS5 local/offline only')
        for key in ('cluster_id', 'cluster_generation', 'node_id', 'worker_incarnation_id'):
            _uuid(getattr(self, key))
        if (type(self.authority_namespace) is not str or
                not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*(?:/[A-Za-z0-9][A-Za-z0-9_.:-]*)*', self.authority_namespace)):
            raise ValueError('exact namespace selector required; owner must verify isolation')
        if self.authority_namespace != 'unified/' + self.cluster_id:
            raise ValueError('selector must equal existing authority namespace; no path-selected alias')


@dataclass(frozen=True)
class _Attachment:
    reference: bytes
    proof: bytes
    worker: object


class SingleNodeScheduler:
    def __init__(self, context, registry, *, admission=None, authority=None, storage=None, native=None):
        if type(context) is not PilotContext:
            raise ValueError('typed pilot context required, not a readiness document')
        self.context, self.registry = context, registry
        self.admission, self.authority, self.storage, self.native = admission, authority, storage, native
        self._attachment = None
        self._runtime = SchedulerRuntime(registry, _Authority(self, None), _Worker(self, None))
        self._context_bytes = json.dumps(asdict(context), sort_keys=True, separators=(',', ':'))

    def readiness(self):
        return dict(status='UNVERIFIED_NOT_ADMISSION', context=asdict(self.context),
                    missing_owner_ports=[name for name in ('admission','authority','storage','native')
                                         if getattr(self, name) is None],
                    required_actual_gates=['ROOT_CURRENT_PILOT_STAGE_MANIFEST_AND_ROLLBACK',
                        'A2_SEPARATELY_ADMITTED_LOCAL_NAMESPACE_AND_ACTUAL_GRANT',
                        'A4_ISSUED_STORAGE_AND_CURRENT_HOLD_DELEGATION',
                        'ROOT_CURRENT_NATIVE_OWNED_WORKER_PROCESS_PROOF'])

    def _ports(self):
        if any(owner is None for owner in (self.admission, self.authority, self.storage, self.native)):
            raise Unavailable('actual admission/authority/storage/native adapters required')

    def _journal_binding(self, *, allow_empty=False, local_containment=False):
        exists = self.registry.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='single_node_context'").fetchone()
        row = self.registry.db.execute('SELECT context FROM single_node_context WHERE singleton=1').fetchone() if exists else None
        if row is not None:
            if row[0] != self._context_bytes:
                raise Unavailable('journal belongs to another context; preserve/reconcile original work')
        elif not local_containment and (not allow_empty or self.registry.db.execute('SELECT COUNT(*) FROM scheduler_attempts').fetchone()[0]):
            raise Unavailable('unscoped existing intents cannot be adopted into this pilot')

    def _bind_journal(self):
        # This is local recovery metadata, not registration, authority or a lease.
        with self.registry.transaction():
            self._journal_binding(allow_empty=True)
            self.registry.db.execute('CREATE TABLE IF NOT EXISTS single_node_context (singleton INTEGER PRIMARY KEY CHECK(singleton=1), context TEXT NOT NULL)')
            self.registry.db.execute('INSERT OR IGNORE INTO single_node_context VALUES (1,?)', (self._context_bytes,))

    def attach_owned_worker(self, worker_ref, process_proof):
        _opaque(worker_ref); _opaque(process_proof)
        self._ports()
        if self._attachment is not None:
            raise Unavailable('attachment cannot be silently replaced')
        _require(self.admission, 'require_current_pilot', self.context, 'ATTACH')
        self._journal_binding(allow_empty=True)
        # Native owner resolves an ALREADY-owned adapter; no caller worker object.
        worker = _sync_call(self.native, 'attach_owned_worker', self.context, worker_ref, process_proof)
        for operation in ('start','inspect','pause'): _method(worker, operation)
        attachment = _Attachment(worker_ref, process_proof, worker)
        self._verify_attachment(attachment)
        self._bind_journal()
        self._attachment = attachment
        self._runtime = SchedulerRuntime(self.registry, _Authority(self, attachment), _Worker(self, attachment))

    def _verify_attachment(self, attachment):
        if attachment is None:
            raise Unavailable('historical reconciliation is not a current worker attachment')
        _require(self.native, 'require_current_attachment', self.context, attachment.reference, attachment.proof, attachment.worker)

    def _effects(self, operation, attachment):
        self._ports(); self._journal_binding()
        _require(self.admission, 'require_current_pilot', self.context, operation)
        _require(self.authority, 'require_single_node_capability', self.context, operation)
        _require(self.storage, 'require_single_node_capability', self.context, operation)
        self._verify_attachment(attachment)

    def _history(self, operation):
        # Original immutable history is not current dispatch permission. A dead
        # worker/storage provider cannot turn it into a new attempt or rebase.
        if self.admission is None or self.authority is None:
            raise Unavailable('actual historical read/disclosure owners required')
        self._journal_binding()
        _require(self.admission, 'require_current_pilot', self.context, operation)
        _require(self.authority, 'require_single_node_capability', self.context, operation)

    def _bound_request(self, raw):
        command = decode_command(raw)
        for key in ('node_id','worker_incarnation_id'):
            if command[key] != getattr(self.context, key): raise ValueError('foreign worker binding')
        for key in ('cluster_id','cluster_generation'):
            if command['scope'][key] != getattr(self.context, key): raise ValueError('foreign authority scope')
        _uuid(command['scope']['dataset_id']); _uuid(command['storage_reservation_id'])
        return command

    def _attached(self):
        if self._attachment is None:
            raise Unavailable('no actual native-owned worker attachment')
        return self._attachment

    def _dispatch(self, raw, grant, attachment):
        self._bound_request(raw); self._effects('DISPATCH', attachment)
        _require(self.authority, 'require_dispatch', raw, grant)
        _require(self.storage, 'require_dispatch_reservation', self.context, raw, grant)
        # The actual worker must validate the grant again at execution/effects.

    def submit(self, command, **planning_hints):
        self._bound_request(encode_command(command))
        self._effects('SUBMIT', self._attached())
        return self._runtime.submit(command, **planning_hints)

    def reconcile(self, request_id):
        self._bound_request(self.registry.get(request_id)['raw'])
        self._history('RECONCILE')
        return self._runtime.reconcile(request_id)

    def drain(self, request_id):
        self._bound_request(self.registry.get(request_id)['raw'])
        self._journal_binding(local_containment=True)
        self.registry.request_drain(request_id)
        attachment = self._attached()  # Missing attachment leaves durable intent.
        self._verify_attachment(attachment)
        # Containment is not a new assignment: do not require quorum/storage here.
        _require(attachment.worker, 'pause', request_id)
        return self.registry.get(request_id)


class _Authority:
    def __init__(self, owner, attachment): self.owner, self.attachment = owner, attachment
    def execute(self, raw):
        self.owner._bound_request(raw); self.owner._effects('EXECUTE', self.attachment)
        return _sync_call(self.owner.authority, 'execute', raw)
    def reconcile(self, raw):
        self.owner._bound_request(raw); self.owner._history('RECONCILE_COMMAND')
        return _sync_call(self.owner.authority, 'reconcile', raw)
    def verify_outcome(self, raw, state, receipt):
        self.owner._bound_request(raw); self.owner._history('VERIFY_OUTCOME')
        _require(self.owner.authority, 'verify_outcome', raw, state, receipt)
    def require_dispatch(self, raw, grant): self.owner._dispatch(raw, grant, self.attachment)


class _Worker:
    def __init__(self, owner, attachment): self.owner, self.attachment = owner, attachment
    def start(self, request_id, raw, grant):
        self.owner._dispatch(raw, grant, self.attachment)
        if self.owner._bound_request(raw)['request_id'] != request_id: raise ValueError('request identity mismatch')
        return _sync_call(self.attachment.worker, 'start', request_id, raw, grant)
    def inspect(self, request_id):
        self.owner._bound_request(self.owner.registry.get(request_id)['raw'])
        self.owner._verify_attachment(self.attachment)
        return _sync_call(self.attachment.worker, 'inspect', request_id)
    def pause(self, request_id):
        self.owner._bound_request(self.owner.registry.get(request_id)['raw'])
        self.owner._verify_attachment(self.attachment)
        return _require(self.attachment.worker, 'pause', request_id)
