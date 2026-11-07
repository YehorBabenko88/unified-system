from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from unified_system.storage.gateway_disclosure import (
    DisclosureUnavailable, get_dataset_manifest, prepare_manifest_request, TOOL_NAME, MANIFEST_SCHEMA_SHA256,
)
from unified_system.storage.object_store import ObjectStore
from support_owner import load_owner


class ActualTLSDisclosureTests(unittest.TestCase):
    def setUp(self):
        self.owner,self.helper=load_owner()
        self.tls=self.helper.TLSFixture()
        self.addCleanup(self.tls.close)
        self.temp=tempfile.TemporaryDirectory(prefix="gateway-manifest-owned-")
        self.addCleanup(self.temp.cleanup)
        self.store=ObjectStore.create(Path(self.temp.name)/"objects",store_id="00000000-0000-4000-8000-000000000099")
        self.manifest=(Path(__file__).parent/"fixtures/manifest.canonical.json").read_bytes()
        self.ref=self.store.put(self.manifest)
        dataset=json.loads(self.manifest)["lineage"]["dataset_id"]
        self.request=dict(schema="unified.storage.gateway-manifest-request.v1-review2",
            request_id=self.helper.U,dataset_id=dataset,dataset_revision="7",manifest_revision="1",
            manifest_sha256=self.ref.sha256,manifest_schema_sha256=MANIFEST_SCHEMA_SHA256,
            consumer_id=self.helper.U,view_id=self.helper.U)
        self.raw=json.dumps(self.request,sort_keys=True,separators=(",", ":")).encode("ascii")
        self.binding=prepare_manifest_request(self.raw).binding
        self.profile=dict(schema="unified.gateway.disposable-identity.v1-review1",realm_id=self.helper.U,
            server_certificate_der=self.tls.server_der,clients=[dict(
                certificate_sha256=hashlib.sha256(self.tls.client_der).hexdigest(),service_id=self.helper.U,
                delegated_user_id=self.helper.U,quota_owner_id="a4-test-read",uri=self.helper.URI,
                expires_utc=(datetime.now(timezone.utc)+timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                grants=[dict(tool_name=TOOL_NAME,binding=self.binding,owned_store=self.store)])])
        self.audit=self.owner.GatewayAuditSink(max_events=100)
        self.auth=self.owner.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
            profile=self.profile,audit_sink=self.audit)
        self.context=self.auth.authenticate_connection(self.tls.accepted)
        self.cap=self.auth.authorize_read(self.context,tool_name=TOOL_NAME,request_bytes=self.raw,
            binding=self.binding,owned_store=self.store)

    def disclose(self,**changes):
        kwargs=dict(owner_read_capability=self.cap,expected_identity_authority=self.auth,pinned_owned_store=self.store)
        kwargs.update(changes)
        return get_dataset_manifest(self.raw,**kwargs)

    def assert_zero_reads_denied(self,callback):
        reads=[];actual=ObjectStore.read
        def observed(store,*args,**kwargs):
            reads.append(args[0]);return actual(store,*args,**kwargs)
        with patch.object(ObjectStore,"read",observed),self.assertRaises(DisclosureUnavailable):callback()
        self.assertEqual(reads,[])

    def test_actual_tls_capability_reads_exact_manifest_with_only_synthetic_claims(self):
        reads=[];actual=ObjectStore.read
        def observed(store,*args,**kwargs):
            reads.append(args[0]);return actual(store,*args,**kwargs)
        with patch.object(ObjectStore,"read",observed):
            result=self.disclose()
        self.assertIs(type(result),bytes)
        value=json.loads(result)
        self.assertEqual(reads,[self.ref.sha256])
        self.assertLessEqual(len(result),32768)
        self.assertEqual(value["authentication"],"SYNTHETIC_SESSION_AUTHENTICATED_ONLY")
        self.assertFalse(value["native_authenticated"])
        self.assertEqual(value["dataset_revision"],"7")
        self.assertEqual(value["manifest_revision"],"1")
        self.assertEqual(value["manifest"],json.loads(self.manifest))
        self.assertEqual(value["coverage"],"UNKNOWN")
        self.assertEqual(value["gaps"],"UNKNOWN")
        self.assertEqual(value["publication"],"UNPROVEN")
        self.assertEqual(value["registry"],"UNPROVEN")
        self.assertIsNone(value["committed_dataset_revision"])
        self.assertFalse(value["closure_verified"])
        audit=self.audit.drain()
        checks=[x for x in audit if x["decision"]=="READ_CURRENT_CHECK"]
        self.assertEqual(len(checks),2)
        capture=os.environ.get("A4_DISCLOSURE_CAPTURE_DIR")
        if capture:
            directory=Path(capture);directory.mkdir(parents=True,exist_ok=True)
            (directory/"manifest.request.canonical.json").write_bytes(self.raw)
            (directory/"manifest.disclosure.canonical.json").write_bytes(result)
            (directory/"manifest.audit.json").write_text(json.dumps(audit,sort_keys=True,indent=2)+"\n",encoding="utf-8")
            trace=dict(schema="a4.manifest-component-observation.v1",publication_receipt=False,
                actual_object_reads=len(reads),actual_current_checks=len(checks),
                request_sha256=hashlib.sha256(self.raw).hexdigest(),response_sha256=hashlib.sha256(result).hexdigest(),
                server_der_sha256=hashlib.sha256(self.tls.server_der).hexdigest(),
                client_observed_server_der_sha256=hashlib.sha256(self.tls.client.getpeercert(binary_form=True)).hexdigest(),
                actual_tls_version=self.tls.client.version(),whole_http_gateway_route=False,
                native_authenticated=False,production_admission=False)
            (directory/"manifest.component-trace.json").write_text(json.dumps(trace,sort_keys=True,indent=2)+"\n",encoding="utf-8")

    def test_valid_foreign_issuer_same_actual_store_cannot_disclose(self):
        foreign=self.owner.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
            profile=self.profile,audit_sink=self.owner.GatewayAuditSink(max_events=100))
        context=foreign.authenticate_connection(self.tls.accepted)
        cap=foreign.authorize_read(context,tool_name=TOOL_NAME,request_bytes=self.raw,binding=self.binding,owned_store=self.store)
        self.assert_zero_reads_denied(lambda:self.disclose(owner_read_capability=cap))

    def test_reopened_same_root_and_store_id_is_different_commissioned_object(self):
        reopened=ObjectStore.open(Path(self.temp.name)/"objects",store_id=self.store.store_id)
        self.assert_zero_reads_denied(lambda:self.disclose(pinned_owned_store=reopened))

    def test_forged_exact_capability_cannot_use_fake_or_real_issuer_without_inventory(self):
        calls=[]
        class Fake:
            def _check(self,*args,**kwargs):calls.append(True)
        for issuer in (Fake(),self.auth):
            cap=object.__new__(self.owner.GatewayReadCapability);cap._issuer=issuer
            self.assert_zero_reads_denied(lambda:self.disclose(owner_read_capability=cap))
        self.assertEqual(calls,[])

    def test_changed_request_view_resource_or_manifest_revision_refuses_before_read(self):
        for field,value in (("view_id","22222222-2222-4222-8222-222222222222"),
                            ("consumer_id","22222222-2222-4222-8222-222222222222"),
                            ("dataset_id","22222222-2222-4222-8222-222222222222"),
                            ("manifest_schema_sha256","f"*64),("dataset_revision","8"),
                            ("manifest_revision","2"),("request_id","33333333-3333-4333-8333-333333333333")):
            request=dict(self.request);request[field]=value
            raw=json.dumps(request,sort_keys=True,separators=(",", ":")).encode("ascii")
            with self.subTest(field=field):
                self.assert_zero_reads_denied(lambda:get_dataset_manifest(raw,owner_read_capability=self.cap,
                    expected_identity_authority=self.auth,pinned_owned_store=self.store))

    def test_query_tool_capability_does_not_authorize_manifest_tool(self):
        binding=dict(self.binding,schema_sha256="14c9f8e8d5c70584b0ca675c6de676498dafedab442076e71c96d45eb4346a77")
        profile=dict(self.profile,clients=[dict(self.profile["clients"][0],
            grants=[dict(tool_name="unified.query_market_data",binding=binding,owned_store=self.store)])])
        auth=self.owner.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
            profile=profile,audit_sink=self.owner.GatewayAuditSink(max_events=100))
        context=auth.authenticate_connection(self.tls.accepted)
        cap=auth.authorize_read(context,tool_name="unified.query_market_data",request_bytes=self.raw,
            binding=binding,owned_store=self.store)
        self.assert_zero_reads_denied(lambda:self.disclose(owner_read_capability=cap,expected_identity_authority=auth))

    def test_actual_revocation_before_read_blocks_all_object_access(self):
        self.auth.revoke_service(self.helper.U)
        self.assert_zero_reads_denied(self.disclose)

    def test_actual_closed_tls_session_refuses_before_object_access(self):
        self.tls.accepted.close()
        self.assert_zero_reads_denied(self.disclose)

    def test_required_audit_capacity_failure_refuses_before_object_access(self):
        for _ in range(98):self.audit._append(dict(schema="test.audit.capacity"))
        self.assert_zero_reads_denied(self.disclose)

    def test_actual_revocation_during_read_blocks_output_after_real_read(self):
        reads=[];actual=ObjectStore.read
        def revoke(store,*args,**kwargs):
            raw=actual(store,*args,**kwargs);reads.append(args[0]);self.auth.revoke_service(self.helper.U);return raw
        with patch.object(ObjectStore,"read",revoke),self.assertRaises(DisclosureUnavailable):self.disclose()
        self.assertEqual(reads,[self.ref.sha256])

    def test_consumed_capability_replay_has_zero_additional_reads(self):
        self.disclose()
        self.assert_zero_reads_denied(self.disclose)

    def test_actual_expiry_denies_before_object_read(self):
        expiry=(datetime.now(timezone.utc)+timedelta(seconds=3)).replace(microsecond=0)
        profile=dict(self.profile,clients=[dict(self.profile["clients"][0],expires_utc=expiry.strftime("%Y-%m-%dT%H:%M:%SZ"))])
        auth=self.owner.DisposableIdentityAuthority(server_ssl_context=self.tls.server_context,
            profile=profile,audit_sink=self.owner.GatewayAuditSink(max_events=100))
        context=auth.authenticate_connection(self.tls.accepted)
        cap=auth.authorize_read(context,tool_name=TOOL_NAME,request_bytes=self.raw,binding=self.binding,owned_store=self.store)
        time.sleep(max(0,(expiry-datetime.now(timezone.utc)).total_seconds())+0.1)
        self.assert_zero_reads_denied(lambda:self.disclose(owner_read_capability=cap,expected_identity_authority=auth))

    def test_actual_corrupt_owned_object_never_returns_partial_metadata(self):
        (Path(self.temp.name)/"objects"/"objects"/self.ref.sha256).write_bytes(b"corrupt private fixture")
        with self.assertRaises(DisclosureUnavailable):self.disclose()

    def test_authorized_but_inconsistent_content_revision_is_not_disclosed(self):
        value=dict(self.request,manifest_revision="2")
        raw=json.dumps(value,sort_keys=True,separators=(",", ":")).encode("ascii")
        cap=self.auth.authorize_read(self.context,tool_name=TOOL_NAME,request_bytes=raw,
            binding=self.binding,owned_store=self.store)
        with self.assertRaises(DisclosureUnavailable):
            get_dataset_manifest(raw,owner_read_capability=cap,expected_identity_authority=self.auth,pinned_owned_store=self.store)

    def test_fixed_owner_method_ignores_instance_callback_and_source_tampering_denies(self):
        calls=[];self.auth.require_issued_read=lambda *args,**kwargs:calls.append(True)
        self.auth.revoke_service(self.helper.U)
        self.assert_zero_reads_denied(self.disclose)
        self.assertEqual(calls,[])
        with patch.object(self.owner,"__file__",__file__):self.assert_zero_reads_denied(self.disclose)

    def test_complete_output_bound_refuses_without_partial_or_truncated_response(self):
        from unified_system.storage import gateway_disclosure
        with patch.object(gateway_disclosure,"MAX_OUTPUT_BYTES",16),self.assertRaises(DisclosureUnavailable):self.disclose()
