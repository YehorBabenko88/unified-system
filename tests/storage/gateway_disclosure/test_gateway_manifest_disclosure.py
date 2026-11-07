import hashlib
import json
import unittest

from unified_system.storage.gateway_disclosure import (
    DisclosureInvalid, DisclosureUnavailable, ManifestReadRequest, prepare_manifest_request, get_dataset_manifest,
)


SCHEMA_SHA = "a599b399cb8809ad72a2ecdb778a4e7e419f88a6cadcf2da20489cf93d12fd10"
UUID = "00000000-0000-4000-8000-000000000001"


def request():
    return dict(schema="unified.storage.gateway-manifest-request.v1-review2",
        request_id=UUID, dataset_id=UUID, dataset_revision="7", manifest_revision="1",
        manifest_sha256="a"*64, manifest_schema_sha256=SCHEMA_SHA, consumer_id=UUID, view_id=UUID)


def raw(value):
    return json.dumps(value,sort_keys=True,separators=(",", ":")).encode("ascii")


class NoTouch:
    def __getattribute__(self,name):
        raise AssertionError("UNAUTHORIZED_OBJECT_ACCESS")


class DisclosureBoundaryTests(unittest.TestCase):
    def test_missing_capability_rejects_before_store_or_request_access(self):
        with self.assertRaises(DisclosureUnavailable):
            get_dataset_manifest(NoTouch(),owner_read_capability=None,expected_identity_authority=NoTouch(),pinned_owned_store=NoTouch())

    def test_json_bool_label_callable_and_foreign_handle_never_authorize(self):
        for cap in (None,True,{},"SYNTHETIC_SESSION_AUTHENTICATED_ONLY",lambda:None,NoTouch()):
            with self.subTest(cap=type(cap).__name__),self.assertRaises(DisclosureUnavailable):
                get_dataset_manifest(raw(request()),owner_read_capability=cap,expected_identity_authority=NoTouch(),pinned_owned_store=NoTouch())

    def test_method_shape_none_return_is_not_owner_proof(self):
        calls=[]
        class Fake:
            def check_current(self,**kwargs):calls.append(kwargs)
        with self.assertRaises(DisclosureUnavailable):
            get_dataset_manifest(raw(request()),owner_read_capability=Fake(),expected_identity_authority=NoTouch(),pinned_owned_store=NoTouch())
        self.assertEqual(calls,[])

    def test_request_binding_keeps_resource_and_manifest_revisions_separate(self):
        value=prepare_manifest_request(raw(request()))
        self.assertEqual(value.binding["dataset_revision"],"7")
        self.assertEqual(value.as_dict()["manifest_revision"],"1")
        self.assertEqual(value.binding["schema_sha256"],SCHEMA_SHA)
        self.assertFalse(value.disclosure_authorized)

    def test_exact_bytes_and_detached_binding_cannot_mutate_request(self):
        source=raw(request());value=prepare_manifest_request(source)
        self.assertEqual(value.request_sha256,hashlib.sha256(source).hexdigest())
        binding=value.binding;binding["dataset_revision"]="8"
        decoded=value.as_dict();decoded["view_id"]="foreign"
        self.assertEqual(value.binding["dataset_revision"],"7")
        self.assertEqual(value.as_dict()["view_id"],UUID)
        with self.assertRaises(DisclosureInvalid):ManifestReadRequest(bytearray(source))

    def test_all_string_fields_reject_terminal_lf(self):
        for key in request():
            value=request();value[key]+="\n"
            with self.subTest(key=key),self.assertRaises(DisclosureInvalid):prepare_manifest_request(raw(value))

    def test_revision_counters_reject_numbers_bool_zero_and_overflow(self):
        for field in ("dataset_revision","manifest_revision"):
            for bad in (True,1,"0","01","9223372036854775808"):
                value=request();value[field]=bad
                with self.subTest(field=field,bad=bad),self.assertRaises(DisclosureInvalid):prepare_manifest_request(raw(value))

    def test_unknown_profile_schema_and_paths_do_not_select_alternate_backend(self):
        for key,bad in (("schema","legacy"),("manifest_schema_sha256","f"*64),
                        ("manifest_sha256","../private"),("consumer_id","principal"),("view_id","*")):
            value=request();value[key]=bad
            with self.subTest(key=key),self.assertRaises(DisclosureInvalid):prepare_manifest_request(raw(value))
        for extra in ("path","url","authority","native_authenticated","tool_name"):
            value=request();value[extra]="private-value"
            with self.subTest(extra=extra),self.assertRaises(DisclosureInvalid):prepare_manifest_request(raw(value))

    def test_noncanonical_duplicate_oversized_missing_and_nonascii_requests_reject(self):
        missing=request();del missing["view_id"]
        for value in (b"",b" "*16385,raw(request())+b"\n",b'{"schema":"x","schema":"x"}',
                      raw(missing),b'{"private":"\\u00e9"}'):
            with self.subTest(value=value[:40]),self.assertRaises(DisclosureInvalid):prepare_manifest_request(value)

    def test_closed_errors_never_reflect_private_input(self):
        marker="private-secret-path-cert"
        value=request();value[marker]=marker
        with self.assertRaises(DisclosureInvalid) as error:prepare_manifest_request(raw(value))
        self.assertNotIn(marker,str(error.exception))
        with self.assertRaises(DisclosureUnavailable) as error:
            get_dataset_manifest(marker,owner_read_capability={marker:marker},expected_identity_authority=NoTouch(),pinned_owned_store=NoTouch())
        self.assertNotIn(marker,str(error.exception))

    def test_expected_issuer_is_required_not_derived_from_capability(self):
        with self.assertRaises(TypeError):
            get_dataset_manifest(raw(request()),owner_read_capability=NoTouch(),pinned_owned_store=NoTouch())
        with self.assertRaises(DisclosureUnavailable):
            get_dataset_manifest(raw(request()),owner_read_capability=NoTouch(),expected_identity_authority=None,pinned_owned_store=NoTouch())


if __name__=="__main__":
    unittest.main(verbosity=2)
