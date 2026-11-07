"""Executable scheduler handoff loop; native adapters are explicit dependencies.

No implementation of authority, reservations or publication lives here. Port
fixtures exercise local orchestration, not distributed authority qualification.
"""
from .domain_v1 import encode_command
from typing import Protocol


class AuthorityPort(Protocol):
    """Native implementation owned by A2; Protocol conformance is not proof."""
    def execute(self, original_command: bytes) -> tuple[str, bytes | None]: ...
    def reconcile(self, original_command: bytes) -> tuple[str, bytes | None]: ...
    def verify_outcome(self, original_command: bytes, state: str, receipt: bytes) -> None: ...
    def require_dispatch(self, original_command: bytes, receipt: bytes) -> None: ...


class WorkerPort(Protocol):
    """Admitted worker must revalidate original grant before execution/effects."""
    def start(self, request_id: str, original_command: bytes, grant: bytes) -> bytes: ...
    def inspect(self, request_id: str) -> bytes | None: ...
    def pause(self, request_id: str) -> None: ...


class Unavailable(RuntimeError):
    pass


class SchedulerRuntime:
    def __init__(self, registry, authority=None, worker=None):
        self.registry, self.authority, self.worker = registry, authority, worker

    def submit(self, command, *, active=True, capacity_fresh=True, resources_available=True):
        raw = encode_command(command)
        if self.authority is None or self.worker is None:
            raise Unavailable('native authority and worker adapters required')
        # Planning hints can reject; they never grant dispatch permission.
        if any(value is not True for value in (active, capacity_fresh, resources_available)):
            raise Unavailable('new assignment blocked by local admission policy')
        row = self.registry.prepare(raw)
        if self.registry.seal(row['request_id']):
            self._invoke(row, self.authority.execute)
        return self._dispatch(row['request_id'])

    def _invoke(self, row, operation):
        try:
            state, receipt = operation(row['raw'])
            if state != 'UNKNOWN':
                # Adapter must verify committed native record/proof, full intent,
                # revision/epoch/fencing, original request identity and effects.
                self.authority.verify_outcome(row['raw'], state, receipt)
            self.registry.resolve(row['request_id'], state, receipt)
        except Exception:
            # Lost reply, malformed proof and unavailable quorum all retain intent.
            # Never manufacture REJECTED or a new request/lease/reservation.
            if self.registry.get(row['request_id'])['state'] not in ('COMMITTED', 'REJECTED'):
                self.registry.resolve(row['request_id'], 'UNKNOWN', None)

    def reconcile(self, request_id):
        if self.authority is None or self.worker is None:
            raise Unavailable('native adapters required')
        row = self.registry.get(request_id)
        if row['state'] in ('SUBMITTED', 'UNKNOWN'):
            self._invoke(row, self.authority.reconcile)
        return self._dispatch(request_id)

    def _dispatch(self, request_id):
        row = self.registry.get(request_id)
        if row['state'] != 'COMMITTED': return row
        try:
            if row['drain_requested']:
                if row['dispatch_state'] != 'NONE': self.worker.pause(request_id)
                return self.registry.get(request_id)
            # Reverify persisted receipt on recovery, not just on original reply.
            self.authority.verify_outcome(row['raw'], row['state'], row['receipt'])
            if row['dispatch_state'] == 'SENDING':
                reply = self.worker.inspect(request_id)
                if reply is not None: self.registry.record_started(request_id, reply)
            elif row['dispatch_state'] == 'NONE' and not row['drain_requested']:
                self.authority.require_dispatch(row['raw'], row['receipt'])
                if self.registry.claim_dispatch(request_id):
                    # Worker must validate this grant again at execution/each effect;
                    # an earlier scheduler check cannot close the network race.
                    reply = self.worker.start(request_id, row['raw'], row['receipt'])
                    self.registry.record_started(request_id, reply)
        except Exception:
            pass  # SENDING stays uncertain; query only, no blind restart/refund.
        return self.registry.get(request_id)

    def drain(self, request_id):
        if self.worker is None: raise Unavailable('worker adapter required')
        row = self.registry.request_drain(request_id)
        if row['dispatch_state'] != 'NONE': self.worker.pause(request_id)
        # Pausing does not publish/adopt a checkpoint, release a grant, or complete
        # a job. Those effects require future native A2/A4 receipts.
        return self.registry.get(request_id)
