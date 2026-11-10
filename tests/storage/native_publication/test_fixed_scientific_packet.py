"""Pure exact-byte acceptance; no stores, authority doubles or scientific execution."""
import dataclasses
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from unified_system.storage import publication_records as records
from unified_system.storage.contracts import StorageBlocked


FIXTURES = Path(__file__).with_name('btc_v1')


class FixedScientificPacketTests(unittest.TestCase):
    def setUp(self):
        self.raw = tuple((FIXTURES / name).read_bytes() for name in
                         ('request.json', 'descriptor.json', 'meta-result.json'))

    def decode(self, values=None):
        return records.decode_fixed_btc_v1(*(self.raw if values is None else values))

    def test_exact_packet_retains_bytes_and_no_authority(self):
        packet = self.decode()
        self.assertEqual((packet.request_bytes, packet.descriptor_bytes, packet.artifact_bytes), self.raw)
        self.assertEqual(packet.classification, 'LOCAL_UNATTESTED')
        self.assertIsNone(packet.committed_revision)
        self.assertIsNone(packet.receipt)
        for name in ('publication_confirmed', 'authority_verified', 'current_read_authorized',
                     'replica_verified', 'scientific_correctness_verified'):
            self.assertIs(getattr(packet, name), False)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            packet.artifact_bytes = b'changed'

    def test_changed_same_length_bytes_rejected_before_decode(self):
        for index, raw in enumerate(self.raw):
            changed = list(self.raw)
            changed[index] = bytes([raw[0] ^ 1]) + raw[1:]
            with self.subTest(index=index), patch.object(json, 'loads', side_effect=AssertionError('decoded')):
                with self.assertRaisesRegex(StorageBlocked, 'FIXED_PACKET_HASH'):
                    self.decode(changed)

    def test_type_size_and_reencoding_rejected_before_decode(self):
        class BytesSubclass(bytes):
            pass
        for index in range(3):
            for bad in (b'', b'x' * 32769, bytearray(self.raw[index]),
                        BytesSubclass(self.raw[index]), self.raw[index] + b'\n',
                        json.dumps(json.loads(self.raw[index]), indent=2).encode()):
                changed = list(self.raw)
                changed[index] = bad
                with self.subTest(index=index, kind=type(bad).__name__), patch.object(
                        json, 'loads', side_effect=AssertionError('decoded')):
                    with self.assertRaises(StorageBlocked):
                        self.decode(changed)

    def test_reviewed_digest_units_and_historical_claims(self):
        packet = self.decode()
        request, descriptor, artifact = map(json.loads, self.raw)
        meta = json.dumps({'payload': request['payload'], 'decision_ms': request['decision_ms']},
                          sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        self.assertEqual(hashlib.sha256(meta).hexdigest(), artifact['request_digest'])
        self.assertEqual(packet.meta_request_digest, artifact['request_digest'])
        self.assertEqual(packet.dataset_id, descriptor['provenance']['dataset_id'])
        self.assertEqual(packet.payload_sha256, '33d5bf0f918884c8908795b384e0964a48a1351c808800964b8cacf3f83e28b6')
        self.assertEqual(artifact['units'], {'price': 'USDT/BTC', 'volume': 'BTC'})
        self.assertEqual(artifact['source']['source_revision'], '6360a75a428c0cb1538085820381324bc4dd9d6f')
        self.assertEqual(descriptor['provenance']['dataset_revision'], 'UNAVAILABLE_A4_BINDING_PENDING')

    def test_numeric_alias_and_authority_escalation_cannot_enter_profile(self):
        for index, key, value in ((0, 'decision_ms', True), (0, 'decision_ms', 300000.0),
                                  (2, 'execution_authority', True), (2, 'coverage_status', 'VERIFIED')):
            obj = json.loads(self.raw[index]); obj[key] = value
            changed = list(self.raw)
            changed[index] = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
            with self.subTest(key=key, value=value), self.assertRaises(StorageBlocked):
                self.decode(changed)


if __name__ == '__main__':
    unittest.main()
