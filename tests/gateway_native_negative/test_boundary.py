"""Pure negative-DATA and loopback validation; not native permission proofs."""
import hashlib
import unittest
from grid.authority_assignment_v1 import ResearchAdmissionResult

class NegativeDataTests(unittest.TestCase):
    def test_exact_negative_data_and_original_digest(self):
        from unified_system.gateway_native_negative import _negative_observation
        raw=b'original';digest=hashlib.sha256(raw).hexdigest()
        for operation,outcome,reason in [('submit','DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED'),('submit','UNKNOWN','JOB_RECONCILIATION_API_UNQUALIFIED'),('lookup','UNKNOWN','JOB_RECONCILIATION_API_UNQUALIFIED')]:
            data=ResearchAdmissionResult(outcome,reason,digest)
            self.assertIs(_negative_observation(raw,data,operation=operation),data)

    def test_unexpected_positive_commit_effect_digest_or_pair_rejected(self):
        from unified_system.gateway_native_negative import _negative_observation,NativeNegativeDenied
        digest=hashlib.sha256(b'original').hexdigest()
        cases=[('submit',ResearchAdmissionResult('COMMITTED','OK',digest)),('submit',ResearchAdmissionResult('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED',digest,'COMMITTED')),('submit',ResearchAdmissionResult('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED',digest,effect_permitted=0)),('submit',ResearchAdmissionResult('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED','0'*64)),('submit',ResearchAdmissionResult('UNKNOWN','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED',digest)),('lookup',ResearchAdmissionResult('DENIED','NATIVE_WORKER_RESOURCE_API_UNQUALIFIED',digest))]
        for operation,data in cases:
            with self.subTest(operation=operation,data=data),self.assertRaises(NativeNegativeDenied):_negative_observation(b'original',data,operation=operation)

    def test_json_and_equality_claims_are_not_native_result_type(self):
        from unified_system.gateway_native_negative import _negative_observation,NativeNegativeDenied
        class EqualityClaim:
            def __eq__(self,other):raise AssertionError('equality claim executed')
            def __hash__(self):raise AssertionError('hash claim executed')
        digest=hashlib.sha256(b'original').hexdigest()
        for value in ({'outcome':'DENIED'},object(),ResearchAdmissionResult(EqualityClaim(),'NATIVE_WORKER_RESOURCE_API_UNQUALIFIED',digest)):
            with self.assertRaises(NativeNegativeDenied):_negative_observation(b'original',value,operation='submit')

    def test_only_literal_loopback_lab_endpoints_are_accepted(self):
        from unified_system.gateway_native_negative import _loopback_endpoints,NativeNegativeDenied
        _loopback_endpoints(('http://127.0.0.1:8500','https://[::1]:8501'),True)
        for endpoints,lab in [(('https://localhost:8501',),True),(('https://192.0.2.1:8501',),True),(('http://127.0.0.1:8500/path',),True),(('http://name@127.0.0.1:8500',),True),(('http://127.0.0.1:8500',),False),(('http://127.0.0.1:8500?',),True)]:
            with self.subTest(endpoints=endpoints,lab=lab),self.assertRaises(NativeNegativeDenied):_loopback_endpoints(endpoints,lab)

    def test_different_raw_source_rejected_without_editing_primary_files(self):
        from unified_system.gateway_native_negative import _fixed_types,NativeNegativeDenied
        from pathlib import Path
        import tempfile
        from grid import authority_assignment_v1 as actual
        original=actual.__file__;raw=Path(original).read_bytes()
        with tempfile.TemporaryDirectory(prefix='negative-source-calibration-') as temp:
            changed=Path(temp).resolve()/'foreign_source.py';changed.write_bytes(b'NOT_THE_COMMISSIONED_SOURCE')
            try:
                actual.__file__=str(changed)
                with self.assertRaises(NativeNegativeDenied):_fixed_types()
            finally:actual.__file__=original
        self.assertEqual(Path(original).read_bytes(),raw)

class ClientOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_injected_client_rejected_without_network_request(self):
        import httpx
        from grid.coordination import ConsulConfig,ConsulSessionAuthority
        from unified_system.gateway_native_negative import _owned_client,NativeNegativeDenied
        client=httpx.AsyncClient(trust_env=False,follow_redirects=False)
        authority=ConsulSessionAuthority(ConsulConfig(('http://127.0.0.1:1',),'owned-boundary',isolated_lab=True),client=client)
        try:
            with self.assertRaises(NativeNegativeDenied):_owned_client(authority)
        finally:await client.aclose()
