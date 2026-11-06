"""Real bytes only; these checks never establish replicated authority."""
import hashlib
from dataclasses import replace
import unittest

from unified_system.storage.contracts import SegmentClaim, StorageBlocked
from unified_system.storage.segments import verify_segment_bytes


INSTRUMENT = {"exchange": "bybit", "category": "linear", "symbol": "BTCUSDT", "instrument_version": "1"}
ROW = b'{"event_time_ms":"0","instrument":{"category":"linear","exchange":"bybit","instrument_version":"1","symbol":"BTCUSDT"},"payload":{},"schema_version":"1"}\n'


def claim(raw=ROW, **changes):
    value = dict(schema="unified.storage.segment-claim.stage1", dataset_id="00000000-0000-4000-8000-000000000001",
                 instrument=dict(INSTRUMENT), source_id="fixture.kline", partition_id="fixture-0-60000",
                 data_kind="raw", schema_version="1", encoding="jsonl.stage1", start_ms="0", end_ms="60000",
                 sha256=hashlib.sha256(raw).hexdigest(), byte_length=str(len(raw)), record_count="1")
    value.update(changes)
    return SegmentClaim.from_mapping(value)


class SegmentTests(unittest.TestCase):
    def test_python_equality_objects_cannot_impersonate_typed_fields(self):
        class EqualToAnything:
            def __eq__(self, other):
                return True
        for field in ("schema", "data_kind", "schema_version", "encoding"):
            with self.subTest(field=field), self.assertRaises(StorageBlocked):
                claim(**{field: EqualToAnything()})
            with self.subTest(direct_field=field), self.assertRaises(StorageBlocked):
                replace(claim(), **{field: EqualToAnything()})
        instrument = dict(INSTRUMENT, category=EqualToAnything())
        with self.assertRaises(StorageBlocked):
            claim(instrument=instrument)
        with self.assertRaises(StorageBlocked):
            replace(claim().instrument, category=EqualToAnything())

    def test_matching_bytes_are_not_authoritative_verification(self):
        result = verify_segment_bytes(ROW, claim())
        self.assertEqual(result.status, "BYTES_MATCHED_UNTRUSTED")
        self.assertEqual(result.record_count, 1)
        self.assertFalse(result.authority_verified)

    def test_corruption_and_truncation_cannot_match_original(self):
        for raw in (ROW.replace(b'BTCUSDT', b'ETHUSDT'), ROW[:-1]):
            with self.subTest(raw=raw[-12:]), self.assertRaises(StorageBlocked):
                verify_segment_bytes(raw, claim())

    def test_matching_digest_does_not_waive_framing(self):
        for raw in (ROW[:-1], b'{}\n', ROW + b'\n', b'{"x":NaN}\n', b'{"x":1,"x":2}\n'):
            with self.subTest(raw=raw[-20:]), self.assertRaises(StorageBlocked):
                verify_segment_bytes(raw, claim(raw))

    def test_other_instrument_and_end_boundary_reject(self):
        for raw in (ROW.replace(b'BTCUSDT', b'ETHUSDT'), ROW.replace(b'"event_time_ms":"0"', b'"event_time_ms":"60000"')):
            with self.subTest(raw=raw[:45]), self.assertRaises(StorageBlocked):
                verify_segment_bytes(raw, claim(raw))

    def test_count_and_size_and_input_limit_are_independent(self):
        for changes in ({"record_count": "2"}, {"byte_length": str(len(ROW)+1)}):
            with self.subTest(changes=changes), self.assertRaises(StorageBlocked):
                verify_segment_bytes(ROW, claim(**changes))
        with self.assertRaises(StorageBlocked):
            verify_segment_bytes(ROW, claim(), max_bytes=len(ROW)-1)

    def test_claim_rejects_coercion_unknown_fields_and_invalid_lineage(self):
        for changes in ({"byte_length": True}, {"byte_length": len(ROW)}, {"start_ms": "00"},
                        {"end_ms": "0"}, {"record_count": "9223372036854775808"},
                        {"partition_id": "../escape"}, {"unexpected": "field"}):
            with self.subTest(changes=changes), self.assertRaises(StorageBlocked):
                claim(**changes)

    def test_claim_detaches_mutable_instrument_input(self):
        source = dict(INSTRUMENT)
        value = claim(instrument=source)
        source["symbol"] = "ETHUSDT"
        self.assertEqual(value.instrument.symbol, "BTCUSDT")

    def test_framed_bytes_do_not_claim_source_completeness(self):
        result = verify_segment_bytes(ROW, claim(end_ms="120000"))
        self.assertEqual(result.source_completeness, "UNKNOWN")

    def test_caller_cannot_construct_verified_byte_result(self):
        result = verify_segment_bytes(ROW, claim())
        with self.assertRaises(TypeError):
            type(result)(result.sha256, result.byte_length, result.record_count, authority_verified=True)
