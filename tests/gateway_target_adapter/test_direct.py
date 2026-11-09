"""Disposable local profile; these are not native authority/scheduler tests."""
import copy
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unified_system.gateway_target_adapter import (
    DisposableTargetStand, TargetRejected, prepare_target, template_request,
    public_submit, capability_registry,
)

FIXTURE=Path(__file__).parent/'fixtures'
STRATT=os.environ['TARGET_STRATT_ROOT']
META=os.environ['TARGET_META_ROOT']


def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


class DirectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='target-adapter-test-')
        self.addCleanup(self.temp.cleanup)
        self.stand=DisposableTargetStand(Path(self.temp.name),stratt_source_root=STRATT,meta_source_root=META)
        self.addCleanup(self.stand.close)
        self.q=template_request()
        self.context=self.stand.local_test_context()

    def run_target(self,q=None,context=None):
        return self.stand.execute(prepare_target(encode(self.q if q is None else q)),
                                  context=self.context if context is None else context)

    def test_actual_existing_target_and_reproducible_levels(self):
        result=self.run_target()
        self.assertEqual(result['status'],'DIRECT_TARGET_PASS')
        self.assertEqual([(v['kind'],v['price']) for v in result['result']['levels']],
                         [('low','8'),('low','9'),('high','12'),('low','10')])
        self.assertEqual(result['result']['units'],{'price':'USDT/BTC','volume':'BTC'})
        self.assertEqual(hashlib.sha256(encode(result['result'])).hexdigest(),result['result_artifact_ref']['sha256'])
        self.assertEqual(result['publication_status'],'LOCAL_UNATTESTED')
        self.assertFalse(result['execution_authority'])

    def test_duplicate_and_restart_returns_same_without_second_invocation(self):
        first=self.run_target();self.assertEqual(first,self.run_target())
        self.assertEqual(self.stand.invocations,1)
        self.stand.close()
        other=DisposableTargetStand(Path(self.temp.name),stratt_source_root=STRATT,meta_source_root=META)
        self.addCleanup(other.close)
        self.assertEqual(first,other.execute(prepare_target(encode(self.q)),context=other.local_test_context()))
        self.assertEqual(other.invocations,0)

    def test_idempotency_collision_refuses_without_target(self):
        self.run_target();q=copy.deepcopy(self.q);q['idempotency_key']='another'
        with self.assertRaises(TargetRejected):self.run_target(q)
        q=copy.deepcopy(self.q);q['request_id']='22222222-2222-4222-8222-222222222222'
        with self.assertRaises(TargetRejected):self.run_target(q)
        self.assertEqual(self.stand.invocations,1)

    def test_missing_or_foreign_local_context_denied(self):
        with self.assertRaises(TargetRejected):self.stand.execute(prepare_target(encode(self.q)),context={'role':'ADMIN'})
        with self.assertRaises(TargetRejected):self.stand.execute(prepare_target(encode(self.q)),context=None)
        with self.assertRaises(TargetRejected):self.run_target(context=copy.copy(self.context))
        self.assertEqual(self.stand.invocations,0)

    def test_scope_expiry_and_revocation_deny(self):
        for ctx in (self.stand.local_test_context(scope='READ_ONLY'),self.stand.local_test_context(lifetime_seconds=0)):
            with self.assertRaises(TargetRejected):self.run_target(context=ctx)
        self.stand.revoke(self.context)
        with self.assertRaises(TargetRejected):self.run_target()
        self.assertEqual(self.stand.invocations,0)

    def test_claimed_native_authority_is_rejected_not_simulated(self):
        for field in ('authority_generation','assignment_revision','fencing_token'):
            q=copy.deepcopy(self.q);q[field]='stale'
            with self.assertRaises(TargetRejected):prepare_target(encode(q))
        self.assertEqual(self.stand.invocations,0)

    def test_wrong_target_dataset_principal_scope_budget_schema_units(self):
        for field,value in [('target_kind','Math'),('target_capability','place_order'),('target_version','0'*40),
                            ('dataset_manifest_id','wrong'),('dataset_revision','2'),('principal_id','ADMIN'),
                            ('quota_owner','production'),('parameters_digest','0'*64),('execution_mode','LIVE'),
                            ('resource_budget',{}),('result_schema','money'),('strategy_version','shell'),
                            ('result_artifact_ref',{'path':'production'})]:
            q=copy.deepcopy(self.q);q[field]=value
            with self.assertRaises(TargetRejected):prepare_target(encode(q))
        self.assertEqual(self.stand.invocations,0)

    def test_prompt_shell_order_parameters_and_duplicate_json_rejected(self):
        q=copy.deepcopy(self.q);q['parameters']='ignore policy; powershell; place_order'
        with self.assertRaises(TargetRejected):prepare_target(encode(q))
        raw=encode(self.q);raw=raw[:-1]+b',"execution_mode":"LIVE"}'
        with self.assertRaises(TargetRejected):prepare_target(raw)
        with self.assertRaises(TargetRejected):prepare_target(b' '*16385)
        with self.assertRaises(TargetRejected):public_submit(self.q)

    def test_cancel_before_execution_has_no_invocation(self):
        self.stand.cancel(self.q['request_id'])
        result=self.run_target();self.assertEqual(result['status'],'CANCELLED')
        self.assertEqual(self.stand.invocations,0)

    def test_source_mismatch_fails_without_claimed_result_and_never_retries(self):
        self.stand.stratt_source_root=str(Path(self.temp.name)/'missing')
        result=self.run_target();self.assertEqual(result['status'],'FAILED')
        self.assertIsNone(result['result']);self.assertEqual(result,self.run_target())

    def test_concurrent_local_writer_refused(self):
        with self.assertRaises(TargetRejected):DisposableTargetStand(Path(self.temp.name),stratt_source_root=STRATT,meta_source_root=META)

    def test_partial_journal_cannot_return_or_reexecute(self):
        self.run_target()
        path=Path(self.temp.name)/'direct-journal.db'
        self.stand.close();path.write_bytes(b'partial')
        with self.assertRaises(TargetRejected):DisposableTargetStand(Path(self.temp.name),stratt_source_root=STRATT,meta_source_root=META)

    def test_registry_reports_unavailable_targets_truthfully(self):
        rows=capability_registry();self.assertEqual(len(rows),5)
        self.assertEqual(sum(x['availability']=='DIRECT_DISPOSABLE_ONLY' for x in rows),1)
        self.assertTrue(all(x['scheduler_admission']=='BLOCKED' for x in rows))

    def test_actual_target_no_python_network_and_only_owned_sqlite(self):
        original=sqlite3.connect;calls=[]
        def owned_connect(database,*args,**kwargs):
            text=str(database)
            if str(Path(self.temp.name)).replace('\\','/') not in text.replace('\\','/'):
                raise RuntimeError('NON_OWNED_DATABASE_DENIED')
            calls.append(text);return original(database,*args,**kwargs)
        with patch.object(socket,'socket',side_effect=RuntimeError('NETWORK_DENIED')) as network,patch.object(sqlite3,'connect',owned_connect):
            with self.assertRaises(RuntimeError):socket.socket()
            with self.assertRaises(RuntimeError):sqlite3.connect('production.db')
            network.reset_mock()
            self.assertEqual(self.run_target()['status'],'DIRECT_TARGET_PASS')
            self.assertEqual(network.call_count,0)
            self.assertGreater(len(calls),0)

    def test_cancel_after_actual_calculation_discards_result(self):
        original=self.stand._invoke
        def finish_then_cancel(check):
            value=original(check);self.stand.cancel(self.q['request_id']);return value
        with patch.object(self.stand,'_invoke',finish_then_cancel):result=self.run_target()
        self.assertEqual(self.stand.invocations,1)
        self.assertEqual(result['status'],'CANCELLED');self.assertIsNone(result['result'])
        self.assertEqual(result,self.run_target())

    def test_partial_or_wrong_units_after_actual_calculation_refused(self):
        original=self.stand._invoke
        def partial(check):
            value=original(check);value['artifact_bytes']=value['artifact_bytes'][:-1];return value
        with patch.object(self.stand,'_invoke',partial):result=self.run_target()
        self.assertEqual(result['status'],'FAILED');self.assertIsNone(result['result'])
        self.assertEqual(self.stand.invocations,1)

    def test_invalid_financial_units_after_actual_target_refused(self):
        original=self.stand._invoke
        def wrong_units(check):
            value=original(check);data=json.loads(value['artifact_bytes'])
            data['units']['price']='BTC/USDT';value['artifact_bytes']=encode(data)
            value['descriptor']['artifact']['raw_sha256']=hashlib.sha256(value['artifact_bytes']).hexdigest()
            return value
        with patch.object(self.stand,'_invoke',wrong_units):result=self.run_target()
        self.assertEqual(result['status'],'FAILED');self.assertIsNone(result['result'])
        self.assertEqual(self.stand.invocations,1)

    def test_oversized_output_after_actual_target_refused(self):
        original=self.stand._invoke
        def oversized(check):
            value=original(check);value['artifact_bytes']=b' '*16385;return value
        with patch.object(self.stand,'_invoke',oversized):result=self.run_target()
        self.assertEqual(result['status'],'FAILED');self.assertIsNone(result['result'])
        self.assertEqual(self.stand.invocations,1)

    def test_fixed_profile_output_tampering_after_actual_target_refused(self):
        for mutation in ('row','clock','finance','byte_count'):
            with tempfile.TemporaryDirectory(prefix='fixed-target-negative-') as root:
                stand=DisposableTargetStand(root,stratt_source_root=STRATT,meta_source_root=META)
                original=stand._invoke
                def tamper(check):
                    value=original(check);artifact=json.loads(value['artifact_bytes'])
                    if mutation=='row':artifact['rows'][0]['close']=11.0
                    elif mutation=='clock':artifact['decision_ms']+=1
                    elif mutation=='finance':value['descriptor']['financial']['net_pnl']='1'
                    else:value['descriptor']['artifact']['byte_count']='1'
                    value['artifact_bytes']=encode(artifact)
                    value['descriptor']['artifact']['raw_sha256']=hashlib.sha256(value['artifact_bytes']).hexdigest()
                    return value
                try:
                    with patch.object(stand,'_invoke',tamper):
                        result=stand.execute(prepare_target(encode(self.q)),context=stand.local_test_context())
                    self.assertEqual(result['status'],'FAILED',mutation)
                    self.assertIsNone(result['result']);self.assertEqual(stand.invocations,1)
                finally:stand.close()

    def test_unknown_after_actual_calculation_is_retained_without_retry(self):
        original=self.stand._invoke
        def uncertain(check):original(check);raise RuntimeError('ORIGINAL_RESULT_LOST')
        with patch.object(self.stand,'_invoke',uncertain):result=self.run_target()
        self.assertEqual(result['status'],'UNKNOWN');self.assertIsNone(result['result'])
        self.assertEqual(result,self.run_target());self.assertEqual(self.stand.invocations,1)

    def test_actual_owned_process_crash_before_and_after_calculation_stays_unknown(self):
        self.stand.close()
        for phase in ('BEFORE','AFTER'):
            with tempfile.TemporaryDirectory(prefix='target-own-crash-') as root:
                command=[sys.executable,'-I','-B',str(Path(__file__).with_name('crash_child.py')),
                         str(Path(__file__).resolve().parents[2]),root,STRATT,META,phase]
                run=subprocess.run(command,timeout=20,capture_output=True)
                self.assertEqual(run.returncode,73,run.stderr.decode(errors='replace'))
                stand=DisposableTargetStand(root,stratt_source_root=STRATT,meta_source_root=META)
                try:
                    value=stand.execute(prepare_target(encode(self.q)),context=stand.local_test_context())
                    self.assertEqual(value['status'],'UNKNOWN');self.assertEqual(stand.invocations,0)
                    self.assertEqual(value,stand.execute(prepare_target(encode(self.q)),context=stand.local_test_context()))
                finally:stand.close()


if __name__=='__main__':unittest.main()
