"""Twelve actual Root mTLS issuer/capability query roles; mandatory hosted.

No fake issuer, old source capsule, conditional skip or local grant substitute.
Local Norton-restricted qualification compiles this source only.
"""
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_gateway_identity as identity_fixture
import test_query_owned_fixture as helpers
from unified_system import gateway_identity,market_data_query
from unified_system.storage.object_store import ObjectStore

class QueryOwnerCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]
        cls.identity=gateway_identity;cls.store_type=ObjectStore;cls.tls_helper=identity_fixture
        assert Path(gateway_identity.__file__).resolve()==root/'unified_system/gateway_identity.py'
        assert Path(market_data_query.__file__).resolve()==root/'unified_system/market_data_query.py'

    def setUp(self):
        self.m=market_data_query;self.domain=self.m.domain
        self.request=helpers.query_request();root,objects=helpers.fixture()
        self.request['dataset_revision']='7';self.request['knowledge_cut']['manifest_sha256']=helpers.sha(root)
        self.raw=helpers.canonical(self.request)
        self.binding=dict(schema='unified.gateway.read-binding.v1-review2',dataset_id=self.request['dataset_id'],
                          dataset_revision='7',manifest_sha256=helpers.sha(root),schema_sha256=self.domain.DATA_SCHEMA_SHA256,
                          consumer_id=self.request['consumer_context']['consumer_id'],view_id=self.request['consumer_context']['view_id'])
        temp=tempfile.TemporaryDirectory(prefix='canonical-query-component-');self.addCleanup(temp.cleanup)
        self.store=self.store_type.create(Path(temp.name)/'owned',store_id='00000000-0000-4000-8000-000000000020')
        for raw in [root,*objects.values()]:self.store.put(raw)
        self.tls=self.tls_helper.TLSFixture();self.addCleanup(self.tls.close)
        self.assertEqual(self.tls.client.getpeercert(binary_form=True),self.tls.server_der)
        user=self.tls_helper.U
        self.profile=dict(schema='unified.gateway.disposable-identity.v1-review1',realm_id=user,
                          server_certificate_der=self.tls.server_der,clients=[dict(
                              certificate_sha256=hashlib.sha256(self.tls.client_der).hexdigest(),
                              service_id=user,delegated_user_id=user,quota_owner_id='synthetic-query',uri=self.tls_helper.URI,
                              expires_utc=(datetime.now(timezone.utc)+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                              grants=[dict(tool_name='unified.query_market_data',binding=self.binding,owned_store=self.store)])])
        self.audit=self.identity.GatewayAuditSink(max_events=200)
        self.authority=self.identity.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,profile=self.profile,audit_sink=self.audit)
        context=self.authority.authenticate_connection(self.tls.accepted)
        self.cap=self.authority.authorize_read(context,tool_name='unified.query_market_data',request_bytes=self.raw,binding=self.binding,owned_store=self.store)

    def query(self,**changes):
        args=dict(owner_read_capability=self.cap,expected_identity_authority=self.authority,pinned_owned_store=self.store)
        args.update(changes)
        return self.m.read_market_data(self.raw,**args)

    def test_actual_tls_six_read_query_returns_only_requested_row_and_explicit_gap(self):
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            result=self.query();self.assertEqual(reads.call_count,6)
        self.assertEqual(result['status'],'SYNTHETIC_QUERY_RESULT')
        self.assertEqual([r[0] for r in result['rows']],['0'])
        self.assertEqual(result['cells'][1]['disposition'],'GAP')
        self.assertEqual(result['provider_coverage'],'UNKNOWN')
        self.assertEqual(result['request_sha256'],hashlib.sha256(self.raw).hexdigest())
        events=self.audit.drain()
        self.assertEqual(sum(e['decision']=='READ_CURRENT_CHECK' for e in events),7)
        with self.assertRaises(self.identity.GatewayIdentityDenied):self.query()

    def test_missing_capability_denies_before_store_attribute_access(self):
        class Bomb:
            def __getattribute__(self,name):raise AssertionError('supplied store accessed')
        result=self.query(owner_read_capability=None,pinned_owned_store=Bomb())
        self.assertEqual(result['status'],'NOT_EXECUTED');self.assertIsNone(result['rows'])

    def test_legitimate_foreign_issuer_same_store_denies_zero_reads(self):
        foreign=self.identity.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,profile=self.profile,audit_sink=self.audit)
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            with self.assertRaises(self.identity.GatewayIdentityDenied):self.query(expected_identity_authority=foreign)
            self.assertEqual(reads.call_count,0)

    def test_wrong_view_full_query_digest_denies_zero_reads(self):
        altered=copy.deepcopy(self.request);altered['consumer_context']['view_id']='00000000-0000-4000-8000-000000000099'
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            with self.assertRaises(self.identity.GatewayIdentityDenied):
                self.m.read_market_data(helpers.canonical(altered),owner_read_capability=self.cap,expected_identity_authority=self.authority,pinned_owned_store=self.store)
            self.assertEqual(reads.call_count,0)

    def test_real_revocation_after_last_read_blocks_output(self):
        actual=self.store.read;count=0
        def read(key,**kwargs):
            nonlocal count
            raw=actual(key,**kwargs);count+=1
            if count==6:self.authority.revoke_service(self.tls_helper.U)
            return raw
        with patch.object(self.store,'read',side_effect=read):
            with self.assertRaises(self.identity.GatewayIdentityDenied):self.query()
        self.assertEqual(count,6)

    def test_actual_revoked_capability_denies_before_first_read(self):
        self.authority.revoke_service(self.tls_helper.U)
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            with self.assertRaises(self.identity.GatewayIdentityDenied):self.query()
            self.assertEqual(reads.call_count,0)

    def test_other_actual_store_same_uuid_denies_before_read(self):
        with tempfile.TemporaryDirectory(prefix='canonical-query-other-store-') as directory:
            other=self.store_type.create(Path(directory)/'owned',store_id='00000000-0000-4000-8000-000000000020')
            with patch.object(other,'read',wraps=other.read) as reads:
                with self.assertRaises(self.identity.GatewayIdentityDenied):self.query(pinned_owned_store=other)
                self.assertEqual(reads.call_count,0)

    def test_manifest_tool_capability_cannot_authorize_query(self):
        profile=copy.deepcopy({k:v for k,v in self.profile.items() if k!='clients'})
        manifest_binding=dict(self.binding,schema_sha256='a599b399cb8809ad72a2ecdb778a4e7e419f88a6cadcf2da20489cf93d12fd10')
        manifest_raw=helpers.canonical(dict(schema='unified.storage.gateway-manifest-request.v1-review2',
            request_id=self.request['request_id'],dataset_id=self.request['dataset_id'],dataset_revision='7',
            manifest_revision='1',manifest_sha256=self.binding['manifest_sha256'],
            manifest_schema_sha256=manifest_binding['schema_sha256'],consumer_id=self.binding['consumer_id'],view_id=self.binding['view_id']))
        profile['clients']=[dict(self.profile['clients'][0],grants=[dict(tool_name='unified.get_dataset_manifest',binding=manifest_binding,owned_store=self.store)])]
        authority=self.identity.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,profile=profile,audit_sink=self.audit)
        context=authority.authenticate_connection(self.tls.accepted)
        cap=authority.authorize_read(context,tool_name='unified.get_dataset_manifest',request_bytes=manifest_raw,binding=manifest_binding,owned_store=self.store)
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            with self.assertRaises(self.identity.GatewayIdentityDenied):self.query(owner_read_capability=cap,expected_identity_authority=authority)
            self.assertEqual(reads.call_count,0)

    def test_changed_range_and_event_cut_full_digest_denies_before_read(self):
        altered=copy.deepcopy(self.request);altered['range']['end_ms']='180000';altered['event_cut_ms']='180000'
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            with self.assertRaises(self.identity.GatewayIdentityDenied):
                self.m.read_market_data(helpers.canonical(altered),owner_read_capability=self.cap,expected_identity_authority=self.authority,pinned_owned_store=self.store)
            self.assertEqual(reads.call_count,0)

    def test_authorized_missing_dependency_returns_error_no_success_empty_history(self):
        root,objects=helpers.fixture();key=next(iter(objects))
        # Remove only our disposable fixture object; no existing history touched.
        self.store._root.joinpath('objects',key).unlink()
        with self.assertRaisesRegex(ValueError,'OBJECT_UNAVAILABLE'):self.query()

    def test_full_fixture_query_returns_two_rows_and_gap_with_new_actual_permit(self):
        request=copy.deepcopy(self.request);request['range']['end_ms']='180000';request['event_cut_ms']='180000'
        raw=helpers.canonical(request);self.domain.prepare_query(raw)
        context=self.authority.authenticate_connection(self.tls.accepted)
        cap=self.authority.authorize_read(context,tool_name='unified.query_market_data',request_bytes=raw,binding=self.binding,owned_store=self.store)
        result=self.m.read_market_data(raw,owner_read_capability=cap,expected_identity_authority=self.authority,pinned_owned_store=self.store)
        self.assertEqual([r[0] for r in result['rows']],['0','120000'])
        self.assertEqual([c['disposition'] for c in result['cells']],['PRESENT','GAP','PRESENT'])
        self.assertEqual(result['request']['event_cut_ms'],'180000')

    def test_actual_elapsed_registry_expiry_denies_query_zero_reads(self):
        profile=dict(self.profile,clients=[dict(self.profile['clients'][0],
            expires_utc=(datetime.now(timezone.utc)+timedelta(seconds=2)).strftime('%Y-%m-%dT%H:%M:%SZ'))])
        authority=self.identity.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,profile=profile,audit_sink=self.audit)
        context=authority.authenticate_connection(self.tls.accepted)
        cap=authority.authorize_read(context,tool_name='unified.query_market_data',request_bytes=self.raw,binding=self.binding,owned_store=self.store)
        time.sleep(2.05)
        with patch.object(self.store,'read',wraps=self.store.read) as reads:
            with self.assertRaises(self.identity.GatewayIdentityDenied):self.query(owner_read_capability=cap,expected_identity_authority=authority)
            self.assertEqual(reads.call_count,0)

if __name__=='__main__':unittest.main()
