"""Isolated local codec tests; no native wire/admission result."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from unified_system.storage.manifest import ManifestClaim, decode_manifest, read_manifest_object, validate_manifest_successor
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def fixture():
    return dict(schema="unified.storage.instrument-manifest.v1-review1",
        lineage=dict(schema="unified.storage.manifest-lineage.v1-review1",
            cluster_id="00000000-0000-4000-8000-000000000001",
            dataset_id="00000000-0000-4000-8000-000000000002",
            source_id="bybit.public.linear.kline.1m.v1", partition_id="2026-11",
            instrument_id=dict(exchange="bybit", category="linear", symbol="BTCUSDT", instrument_version="1"),
            data_kind="raw"), manifest_revision="1", previous_manifest_sha256=None,
        segments_root_sha256="a"*64, coverage_root_sha256="b"*64,
        dependencies_root_sha256="c"*64, data_schema_sha256="d"*64)


class ManifestCodecProposal(unittest.TestCase):
    def test_exact_canonical_bytes_and_lineage_digest_remain_untrusted(self):
        value=fixture();raw=canonical(value);claim=decode_manifest(raw)
        self.assertEqual(claim.sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(claim.lineage_sha256, hashlib.sha256(canonical(value["lineage"])).hexdigest())
        self.assertFalse(claim.publication_confirmed)
        with self.assertRaises(StorageBlocked):
            claim.require_publication_authority()

    def test_genesis_successor_and_wrong_predecessor_or_lineage(self):
        first=decode_manifest(canonical(fixture()));validate_manifest_successor(first, None)
        value=fixture();value.update(manifest_revision="2", previous_manifest_sha256=first.sha256)
        second=decode_manifest(canonical(value));validate_manifest_successor(second, first)
        for change in ({"manifest_revision":"3"}, {"previous_manifest_sha256":"f"*64}):
            bad=dict(value, **change)
            with self.subTest(change=change),self.assertRaises(StorageBlocked):
                validate_manifest_successor(decode_manifest(canonical(bad)),first)
        value["lineage"]["instrument_id"]["instrument_version"]="2"
        with self.assertRaises(StorageBlocked):
            validate_manifest_successor(decode_manifest(canonical(value)),first)

    def test_counter_and_unknown_noncanonical_duplicate_fields_rejected(self):
        for bad in (True, 1, "01", "9223372036854775808", "1\n"):
            value=fixture();value["manifest_revision"]=bad
            with self.subTest(bad=bad),self.assertRaises(StorageBlocked):
                decode_manifest(canonical(value))
        raw=canonical(fixture())
        for bad in (raw+b"\n", b'{"schema":"x","schema":"x"}', canonical(dict(fixture(),unknown=None))):
            with self.subTest(bad=bad[:30]),self.assertRaises(StorageBlocked):
                decode_manifest(bad)

    def test_actual_manifest_object_readback_and_corruption_rejection(self):
        with tempfile.TemporaryDirectory(prefix="manifest-owned-fixture-") as temp:
            root=Path(temp)/"objects"
            store=ObjectStore.create(root,store_id="00000000-0000-4000-8000-000000000088")
            ref=store.put(canonical(fixture()))
            self.assertEqual(read_manifest_object(store,ref.sha256).sha256,ref.sha256)
            (root/"objects"/ref.sha256).write_bytes(b'corrupt fixture')
            with self.assertRaises(StorageBlocked):
                read_manifest_object(store,ref.sha256)

    def test_all_string_leaves_reject_terminal_lf(self):
        def leaves(value, path=()):
            for key, child in value.items():
                if type(child) is dict:
                    yield from leaves(child,path+(key,))
                elif type(child) is str:
                    yield path+(key,),child
        source=fixture()
        for path,text in leaves(source):
            changed=deepcopy(source);parent=changed
            for key in path[:-1]:parent=parent[key]
            parent[path[-1]]=text+"\n"
            with self.subTest(path=path),self.assertRaises(StorageBlocked):
                decode_manifest(canonical(changed))

    def test_instrument_counter_profile_and_lineage_are_not_coerced(self):
        for bad in (True,1,"0","01","9223372036854775808"):
            value=fixture();value["lineage"]["instrument_id"]["instrument_version"]=bad
            with self.subTest(bad=bad),self.assertRaises(StorageBlocked):decode_manifest(canonical(value))
        for key,bad in (("schema","legacy"),("data_kind","RAW"),("cluster_id","host"),("source_id","source/path")):
            value=fixture();value["lineage"][key]=bad
            with self.subTest(key=key),self.assertRaises(StorageBlocked):decode_manifest(canonical(value))
        for key in ("job_id","cluster_generation"):
            value=fixture();value["lineage"][key]="foreign"
            with self.subTest(key=key),self.assertRaises(StorageBlocked):decode_manifest(canonical(value))

    def test_genesis_semantics_and_overflow_never_reset_revision(self):
        for revision,previous in (("1","a"*64),("2",None),("0",None)):
            value=fixture();value.update(manifest_revision=revision,previous_manifest_sha256=previous)
            with self.subTest(revision=revision),self.assertRaises(StorageBlocked):decode_manifest(canonical(value))
        value=fixture();value.update(manifest_revision="9223372036854775807",previous_manifest_sha256="a"*64)
        last=decode_manifest(canonical(value))
        with self.assertRaises(StorageBlocked):validate_manifest_successor(decode_manifest(canonical(fixture())),last)
        with self.assertRaises(StorageBlocked):validate_manifest_successor(last,None)

    def test_changed_kind_partition_or_instrument_cannot_succeed_same_lineage(self):
        first=decode_manifest(canonical(fixture()))
        for key,changed in (("data_kind","derived"),("partition_id","2026-12"),("source_id","other-source")):
            value=fixture();value.update(manifest_revision="2",previous_manifest_sha256=first.sha256)
            value["lineage"][key]=changed
            with self.subTest(key=key),self.assertRaises(StorageBlocked):
                validate_manifest_successor(decode_manifest(canonical(value)),first)

    def test_constructor_and_decoded_copy_cannot_rewrite_claim(self):
        raw=canonical(fixture());claim=ManifestClaim(raw)
        copy=claim.as_dict();copy["lineage"]["instrument_id"]["symbol"]="OTHER"
        self.assertEqual(claim.raw_bytes,raw)
        self.assertEqual(claim.as_dict()["lineage"]["instrument_id"]["symbol"],"BTCUSDT")
        with self.assertRaises(StorageBlocked):ManifestClaim(bytearray(raw))
        with self.assertRaises(StorageBlocked):ManifestClaim(b'{}')
        with self.assertRaises(StorageBlocked):decode_manifest(b' '*16385)

    def test_hashes_missing_objects_and_unsupported_claims_never_verify_closure(self):
        claim=decode_manifest(canonical(fixture()))
        self.assertFalse(claim.closure_verified)
        for bad in ("A"*64,"a"*63,"../foreign"):
            value=fixture();value["coverage_root_sha256"]=bad
            with self.subTest(bad=bad),self.assertRaises(StorageBlocked):decode_manifest(canonical(value))
        with self.assertRaises(StorageBlocked):validate_manifest_successor(True,None)


if __name__=="__main__":
    unittest.main(verbosity=2)
