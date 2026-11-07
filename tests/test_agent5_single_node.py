"""MODEL_ONLY owner doubles; no process/service/network or accepted execution grant."""
from pathlib import Path
import tempfile
import unittest
import gc
import warnings

from scheduler_components.attempt_registry import AttemptRegistry
from scheduler_components.domain_v1 import encode_command
from scheduler_components.runtime import Unavailable
from scheduler_components.single_node import PilotContext, SingleNodeScheduler


def uid(n): return '00000000-0000-4000-8000-' + str(n).zfill(12)


def context(**changes):
    value = dict(node_name='LS5', mode='SINGLE_NODE_LOCAL_OFFLINE', cluster_id=uid(1),
                 cluster_generation=uid(2), node_id=uid(3), worker_incarnation_id=uid(4),
                 authority_namespace='unified/'+uid(1))
    value.update(changes); return PilotContext(**value)


def request():
    return dict(schema='unified.scheduler.command.v1-c3.review1', operation='ASSIGN', request_id=uid(5),
                idempotency_key=uid(5), scope=dict(cluster_id=uid(1), cluster_generation=uid(2),
                    job_id='job', dataset_id=uid(6), source_id='offline-fixture', partition_id='partition'),
                node_id=uid(3), worker_incarnation_id=uid(4), assignment_id=uid(7),
                expected_assignment_revision='0', resources=dict(cpu_millicores='1000', ram_bytes='4096',
                    scratch_bytes='4096', disk_bytes_per_second='1024', network_bytes_per_second='1024'),
                resource_units='LOGICAL_PROCESSOR_1000_MILLICORES_BYTES_BYTES_PER_SECOND',
                storage_reservation_id=uid(8), storage_budget_revision='17')


class ModelWorker:
    def __init__(self): self.starts, self.pauses = [], []
    def start(self, *args):
        self.starts.append(args); raise AssertionError('MODEL worker must NEVER execute')
    def inspect(self, request_id): return None
    def pause(self, request_id): self.pauses.append(request_id)


class ModelOwners:
    """Control-path simulation only; all forged/fixture grants fail verification."""
    def __init__(self):
        self.worker = ModelWorker(); self.calls = []; self.namespace = 'unified/'+uid(1)
        self.fail = set(); self.outcome = ('UNKNOWN', None)
    def require_current_pilot(self, ctx, operation):
        self.calls.append(('pilot', operation))
        if ctx.authority_namespace != self.namespace or 'pilot' in self.fail: raise Unavailable('model pilot gate')
    def require_single_node_capability(self, ctx, operation):
        self.calls.append(('capability', operation))
        if 'capability' in self.fail: raise Unavailable('no actual capability')
    def attach_owned_worker(self, ctx, ref, proof):
        if ref != b'MODEL_REF' or proof != b'MODEL_CONTROL_ONLY': raise Unavailable('no native proof')
        return self.worker
    def require_current_attachment(self, ctx, ref, proof, worker):
        if 'native' in self.fail or worker is not self.worker: raise Unavailable('native ownership unavailable')
    def execute(self, raw): self.calls.append(('execute', raw)); return self.outcome
    def reconcile(self, raw): self.calls.append(('reconcile', raw)); return self.outcome
    def verify_outcome(self, *args): raise Unavailable('MODEL/fabricated receipt is not issued authority')
    def require_dispatch(self, *args): raise Unavailable('no actual issued grant')
    def require_dispatch_reservation(self, *args): raise Unavailable('no actual storage grant')


class SingleNodeModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.registry = AttemptRegistry(Path(self.tmp.name)/'attempts.db')
        self.owners = ModelOwners()
    def tearDown(self):
        self.assertEqual(self.owners.worker.starts, [])
        self.registry.close(); self.tmp.cleanup()
    def pilot(self, **changes):
        ports = dict(admission=self.owners, authority=self.owners, storage=self.owners, native=self.owners)
        ports.update(changes); return SingleNodeScheduler(context(), self.registry, **ports)
    def attached(self):
        pilot = self.pilot(); pilot.attach_owned_worker(b'MODEL_REF', b'MODEL_CONTROL_ONLY'); return pilot

    def test_construction_and_readiness_never_start_or_admit(self):
        pilot = SingleNodeScheduler(context(), self.registry)
        self.assertEqual(pilot.readiness()['status'], 'UNVERIFIED_NOT_ADMISSION')
        self.assertEqual(self.owners.calls, [])
        with self.assertRaises(Unavailable): pilot.submit(request())
    def test_each_missing_owner_port_blocks_attachment(self):
        for name in ('admission','authority','storage','native'):
            with self.assertRaises(Unavailable): self.pilot(**{name:None}).attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
    def test_readiness_boolean_and_caller_worker_are_not_proofs(self):
        for proof in (True, {'ready':True}, 'process-ref', b'fixture-proof'):
            with self.assertRaises((ValueError,Unavailable)): self.pilot().attach_owned_worker(b'MODEL_REF',proof)
        with self.assertRaises((ValueError,Unavailable)): self.pilot().attach_owned_worker(self.owners.worker,b'MODEL_CONTROL_ONLY')
    def test_foreign_namespace_fails_owner_admission(self):
        with self.assertRaises(ValueError):context(authority_namespace='office/live')
        self.owners.namespace='unified/'+uid(99)
        with self.assertRaises(Unavailable):self.pilot().attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
    def test_other_node_and_nonoffline_mode_reject(self):
        for change in ({'node_name':'PC1'},{'mode':'OFFICE_CLUSTER'},{'node_id':'LS5'}):
            with self.assertRaises(ValueError): context(**change)
    def test_request_foreign_node_or_generation_never_handoffs(self):
        pilot = self.attached()
        for field in ('node_id','worker_incarnation_id'):
            c = request(); c[field] = uid(99)
            with self.assertRaises(ValueError): pilot.submit(c)
        c=request();c['scope']['cluster_generation']=uid(99)
        with self.assertRaises(ValueError):pilot.submit(c)
        self.assertFalse(any(x[0]=='execute' for x in self.owners.calls))
    def test_synthetic_assignment_is_not_a_request_or_grant(self):
        pilot=self.attached()
        with self.assertRaises(ValueError):pilot.submit(dict(schema='unified.scheduler.assignment.v1-c3.review2',state='ACTIVE',fencing_token={'ready':True}))
    def test_forged_committed_receipt_remains_unknown_and_never_dispatches(self):
        pilot=self.attached();self.owners.outcome=('COMMITTED',b'fixture-grant')
        self.assertEqual(pilot.submit(request())['state'],'UNKNOWN')
        self.assertEqual(self.owners.worker.starts,[])
    def test_owner_capability_checked_again_inside_authority_handoff(self):
        pilot=self.attached();original=self.registry.seal
        def seal(key):
            value=original(key);self.owners.fail.add('capability');return value
        self.registry.seal=seal
        self.assertEqual(pilot.submit(request())['state'],'UNKNOWN')
        self.assertFalse(any(x[0]=='execute' for x in self.owners.calls))
    def test_missing_actual_capability_never_executes(self):
        pilot=self.attached();self.owners.fail.add('capability')
        with self.assertRaises(Unavailable):pilot.submit(request())
        self.assertFalse(any(x[0]=='execute' for x in self.owners.calls))
    def test_unknown_reconciliation_uses_original_intent_and_does_not_restart(self):
        pilot=self.attached();pilot.submit(request());pilot.submit(request());pilot.reconcile(uid(5))
        without_worker=self.pilot();without_worker.reconcile(uid(5))
        executed=[x[1] for x in self.owners.calls if x[0]=='execute'];reconciled=[x[1] for x in self.owners.calls if x[0]=='reconcile']
        self.assertEqual(executed,[encode_command(request())]);self.assertEqual(reconciled,executed*2)
    def test_native_proof_revocation_blocks_without_worker_effect(self):
        pilot=self.attached();pilot.submit(request());self.owners.fail.add('native')
        self.assertEqual(pilot.reconcile(uid(5))['state'],'UNKNOWN')
        with self.assertRaises(Unavailable):pilot.submit(request())
    def test_drain_intent_persists_without_attachment(self):
        self.registry.prepare(encode_command(request()));pilot=self.pilot()
        with self.assertRaises(Unavailable):pilot.drain(uid(5))
        self.assertEqual(self.registry.get(uid(5))['drain_requested'],1)
    def test_local_containment_does_not_require_quorum_capability(self):
        pilot=self.attached();pilot.submit(request());self.owners.fail.add('capability')
        pilot.drain(uid(5));self.assertEqual(self.owners.worker.pauses,[uid(5)])
    def test_bound_journal_cannot_move_to_another_namespace(self):
        self.attached();self.owners.namespace='unified/'+uid(99)
        pilot=SingleNodeScheduler(context(cluster_id=uid(99),authority_namespace=self.owners.namespace),self.registry,
            admission=self.owners,authority=self.owners,storage=self.owners,native=self.owners)
        with self.assertRaises(Unavailable):pilot.attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
    def test_legacy_unscoped_attempts_cannot_be_adopted(self):
        self.registry.prepare(encode_command(request()))
        with self.assertRaises(Unavailable):self.pilot().attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
    def test_foreign_namespace_cannot_mark_bound_intent_draining(self):
        pilot=self.attached();pilot.submit(request());self.owners.namespace='unified/'+uid(99)
        other=SingleNodeScheduler(context(cluster_id=uid(99),authority_namespace=self.owners.namespace),self.registry,
            admission=self.owners,authority=self.owners,storage=self.owners,native=self.owners)
        with self.assertRaises((ValueError,Unavailable)):other.drain(uid(5))
        self.assertEqual(self.registry.get(uid(5))['drain_requested'],0)
    def test_boolean_owner_result_is_not_current_capability(self):
        for flag in (True,False):
            self.owners.require_current_pilot=lambda *args:flag
            with self.assertRaises(Unavailable):self.pilot().attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
        class Pending:
            def __await__(self):yield
        self.owners.require_current_pilot=lambda *args:Pending()
        with self.assertRaises(Unavailable):self.pilot().attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
        class AsyncGuard:
            async def __call__(self,*args):return None
        self.owners.require_current_pilot=AsyncGuard()
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter('always',RuntimeWarning)
            with self.assertRaises(Unavailable):self.pilot().attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
            gc.collect()
        self.assertEqual([w for w in notices if issubclass(w.category,RuntimeWarning)],[])
        finalized=[]
        async def owner_pending():
            try:await Pending()
            finally:finalized.append('OWNER_FINALLY')
        pending=owner_pending();pending.send(None)
        self.owners.require_current_pilot=lambda *args:pending
        try:
            with self.assertRaises(Unavailable):self.pilot().attach_owned_worker(b'MODEL_REF',b'MODEL_CONTROL_ONLY')
            self.assertEqual(finalized,[])  # Do not run an owner's suspended cleanup.
        finally:pending.close()


if __name__=='__main__':unittest.main()
