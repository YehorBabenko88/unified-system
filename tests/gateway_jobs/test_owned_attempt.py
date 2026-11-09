"""Local owned OS attempt tests, NOT native admission/worker profile qualification.
Native selection is explicit; no A2 broker/Consul/Meta/PR52 allocation calls.
"""
import copy
import json
import os
from pathlib import Path
import pickle
import unittest
import uuid
from unittest.mock import patch
import unified_system.gateway_worker as worker_module
from unified_system.gateway_worker import GatewayWorker, OwnedWorkerAttempt, WorkerUnavailable

FIX=Path(__file__).with_name('target_native_mapping_fixtures')
GRID='C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-2-high-availability-distributed/work/grid-assignment-native-20261107'

def raw():return (FIX/'a2-native13.FORMAT_ONLY.json').read_bytes()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')

class OwnedAttemptBoundary(unittest.TestCase):
    def test_default_start_still_denies(self):
        with self.assertRaises(WorkerUnavailable):GatewayWorker().start()
    def test_attempt_cannot_be_constructed_or_forged_into_inventory(self):
        with self.assertRaises(TypeError):OwnedWorkerAttempt()
        forged=object.__new__(OwnedWorkerAttempt);worker=GatewayWorker(node_id=str(uuid.uuid4()))
        for call in (worker.inspect_attempt,worker.abort_attempt):
            with self.assertRaises(WorkerUnavailable):call(forged)
        with self.assertRaises(WorkerUnavailable):GatewayWorker.require_owned_attempt(worker,forged,original_lab13_bytes=raw())
    def test_original_bytes_are_strict_before_any_process_creation(self):
        worker=GatewayWorker(node_id=str(uuid.uuid4()))
        for b in (raw()+b' ',b'{"request_id":1,"request_id":2}',b'x'*16385,b'[]'):
            with self.assertRaises(WorkerUnavailable):worker.prepare_attempt(b,grid_source_root=GRID)
    def test_missing_declared_node_denies_preparation(self):
        with self.assertRaisesRegex(WorkerUnavailable,'WORKER_NODE_LABEL_REQUIRED'):
            GatewayWorker().prepare_attempt(raw(),grid_source_root=GRID)
    def test_all_frozen_native13_constraints_precede_native_access(self):
        mutations=[('commissioned_profile_sha256','z'*64),('input_request_sha256','0'*64),
                   ('producer_head','0'*40),('resources',{}),('resources',{'cpu_millicores':'999'})]
        for field,value in mutations:
            original=json.loads(raw());original[field]=value
            with self.subTest(field=field,value=value),patch.object(worker_module,'_attempt_api',side_effect=AssertionError('native access')) as api:
                with self.assertRaises(WorkerUnavailable):
                    GatewayWorker(node_id=str(uuid.uuid4())).prepare_attempt(canonical(original),grid_source_root=GRID)
                api.assert_not_called()
    def test_preparation_headroom_and_pin_faults_never_create_process(self):
        # Deterministic refusal assertions only: inert kernel is not OS evidence.
        original=raw()
        class NoCreate:
            def CreateProcessW(self,*args):
                raise AssertionError('process creation crossed refusal gate')
        host={'available_commit_bytes':'2952790016','available_physical_bytes':'1073741824'}
        cases=[('OWNED_PREPARATION_HEADROOM_REFUSED',
                patch.object(worker_module,'_attempt_host',return_value={**host,'available_commit_bytes':'0'})),
               ('OWNED_INTERPRETER_PIN_MISMATCH',
                patch.object(worker_module,'_DIRECT_INTERPRETER_SHA','0'*64)),
               ('OWNED_GRID_SOURCE_MISMATCH',
                patch.object(worker_module.subprocess,'check_output',return_value=b'wrong source'))]
        for code,fault in cases:
            with self.subTest(code=code),patch.object(worker_module,'_attempt_api',return_value=NoCreate()),patch.object(worker_module,'_attempt_host',return_value=host),fault:
                worker=GatewayWorker(node_id=str(uuid.uuid4()))
                with self.assertRaises(WorkerUnavailable) as caught:
                    worker.prepare_attempt(original,grid_source_root=GRID)
                self.assertEqual(caught.exception.origin_diagnostic[1],code)
                self.assertEqual(caught.exception.cleanup_diagnostics,())

class NativeOwnedAttempt(unittest.TestCase):
    def test_actual_suspended_duplicate_inspect_abort_without_resume(self):
        worker=GatewayWorker(node_id=str(uuid.uuid4()));original=raw()
        attempt=worker.prepare_attempt(original,grid_source_root=GRID)
        self.addCleanup(worker.abort_attempt,attempt)
        self.assertIs(worker.prepare_attempt(original,grid_source_root=GRID),attempt)
        snapshot=GatewayWorker.require_owned_attempt(worker,attempt,original_lab13_bytes=original)
        self.assertEqual(snapshot.state,'PREPARED_SUSPENDED_LOCAL_ONLY')
        self.assertEqual(snapshot.native_authority,'NOT_GRANTED')
        details=json.loads(snapshot.os_observation_json)
        self.assertTrue(details['job_membership']);self.assertEqual(details['resume_calls'],0)
        self.assertFalse(details['resource_profile_qualified'])
        for operation in (copy.copy,copy.deepcopy,pickle.dumps):
            with self.assertRaises(TypeError):operation(attempt)
        retired=worker.abort_attempt(attempt);self.assertEqual(retired.state,'OWNED_QUIESCENCE_CONFIRMED')
        self.assertIs(worker.abort_attempt(attempt),retired)
        with self.assertRaises(WorkerUnavailable):worker.prepare_attempt(original,grid_source_root=GRID)
        with self.assertRaises(WorkerUnavailable):GatewayWorker.require_owned_attempt(worker,attempt,original_lab13_bytes=original)
    def test_foreign_inventory_and_changed_original_do_not_adopt_child(self):
        worker=GatewayWorker(node_id=str(uuid.uuid4()));original=raw();attempt=worker.prepare_attempt(original,grid_source_root=GRID)
        self.addCleanup(worker.abort_attempt,attempt)
        foreign=GatewayWorker(node_id=str(uuid.uuid4()))
        with patch.object(worker_module,'_attempt_api',side_effect=AssertionError('second native access')) as api:
            with self.assertRaises(WorkerUnavailable):foreign.prepare_attempt(original,grid_source_root=GRID)
            api.assert_not_called()
        with self.assertRaises(WorkerUnavailable):foreign.abort_attempt(attempt)
        changed=json.loads(original);changed['job_id']=str(uuid.uuid4());different=canonical(changed)
        with self.assertRaises(WorkerUnavailable):worker.prepare_attempt(different,grid_source_root=GRID)
        with self.assertRaises(WorkerUnavailable):GatewayWorker.require_owned_attempt(worker,attempt,original_lab13_bytes=different)
        self.assertEqual(worker.inspect_attempt(attempt).state,'PREPARED_SUSPENDED_LOCAL_ONLY')

def load_tests(loader,tests,pattern):
    suite=loader.loadTestsFromTestCase(OwnedAttemptBoundary)
    if os.environ.get('AGENT5_RUN_OWNED_ATTEMPT_NATIVE')=='1':
        suite.addTests(loader.loadTestsFromTestCase(NativeOwnedAttempt))
    else:print('OWNED_ATTEMPT_NATIVE_NOT_RUN_EXPLICIT_SELECTION_REQUIRED')
    return suite
