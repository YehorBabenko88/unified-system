import unittest

from unified_system.storage.contracts import StorageBlocked, decode_untrusted_claim, require_publication_authority


class ClaimTests(unittest.TestCase):
    def test_parse_is_untrusted_and_cannot_promote(self):
        parsed = decode_untrusted_claim(b'{"commit_status":"COMMITTED"}')
        self.assertEqual(parsed.value["commit_status"], "COMMITTED")
        self.assertFalse(parsed.authority_verified)
        with self.assertRaisesRegex(StorageBlocked, "PROOF_ADAPTER_UNAVAILABLE"):
            require_publication_authority(parsed)

    def test_parser_rejects_duplicate_numbers_nonascii_and_noncanonical_bytes(self):
        for raw in (b'{"a":null,"a":null}', b'{"n":1}', b'{"n":NaN}',
                    b'{"s":"\\u00e9"}', b'{ "a":null}', b'{"z":null,"a":null}', b'{}\n'):
            with self.subTest(raw=raw), self.assertRaises(StorageBlocked):
                decode_untrusted_claim(raw)

    def test_parser_bounds_and_counterfeit_primitive_types(self):
        for raw in (b'['*20 + b']'*20, b'"not-object"', b'null', b'{}'*20000):
            with self.subTest(length=len(raw)), self.assertRaises(StorageBlocked):
                decode_untrusted_claim(raw)

    def test_decoded_copy_cannot_rewrite_original_claim(self):
        parsed = decode_untrusted_claim(b'{"status":"UNTRUSTED"}')
        parsed.value["status"] = "VERIFIED"
        self.assertEqual(parsed.value["status"], "UNTRUSTED")
