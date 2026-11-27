"""Offline AST contract tests; synthetic fixtures only, no runtime permission."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import hashlib

SOURCE = Path(__file__).resolve().parents[1] / 'tools/g_mtf_source_compat.py'
spec = importlib.util.spec_from_file_location('g_mtf_source_compat', SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

GRID = '''def project_qualified_rollup(envelope, *, timeframe, limit, now_ms):
    result = {"schema":"test", "source_declared_quality":["GOOD"]}
    return dict(result, dataset_fingerprint=digest(result))
'''
D_BAD = '''_TOP = frozenset({"schema", "dataset_fingerprint"})
def validate_qualified_rollup(envelope, symbol, timeframe, limit):
    delta_binary64 = 0
    return delta_binary64 == row["delta"]
'''
D_GOOD = '''_TOP = frozenset({"schema", "dataset_fingerprint", "source_declared_quality"})
def validate_qualified_rollup(envelope, symbol, timeframe, limit):
    for field, literal in (("source_declared_quality", ["GOOD"]),):
        pass
'''


class CrossOwnerSourceProbeTests(unittest.TestCase):
    def test_current_shape_is_blocked(self):
        result = probe.check_pair(GRID, D_BAD)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(any(x.startswith('DTO_KEYS_MISMATCH:') for x in result['reasons']))
        self.assertIn('LOSSY_DELTA_BINARY64_RECOMPUTATION', result['reasons'])
        self.assertIn('SOURCE_QUALITY_LITERAL_NOT_ENFORCED', result['reasons'])

    def test_old_field_match_is_not_decimal_parity(self):
        result = probe.check_pair(GRID, D_GOOD)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('CANONICAL_MATH_DECIMAL_CONSUMER_UNVERIFIED', result['reasons'])
        self.assertFalse(result['release_authorized'])
        self.assertFalse(result['deletion_authorized'])

    def test_unexpected_field_is_blocked(self):
        result = probe.check_pair(GRID.replace('"schema":"test"','"unreviewed":0,"schema":"test"'),D_GOOD)
        self.assertTrue(any(x.startswith('DTO_KEYS_MISMATCH:') for x in result['reasons']))

    def test_syntax_and_nonliteral_roster_fail_closed(self):
        self.assertEqual(probe.check_pair('def broken(',D_GOOD)['status'],'BLOCKED')
        self.assertEqual(probe.check_pair(GRID,D_GOOD.replace('frozenset({','dynamic({'))['status'],'BLOCKED')

    def test_pin_rejects_changed_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.py';path.write_text(GRID)
            raw=path.read_bytes()
            git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            self.assertEqual(probe._read_pinned(path,git_blob),GRID)
            with self.assertRaises(probe.ContractUnverified):
                probe._read_pinned(path,'0'*40)

    def test_approximate_binary64_producer_is_blocked_even_when_fields_match(self):
        source = GRID.replace('return dict(result, dataset_fingerprint=digest(result))',
                              'buy = volume_total((raw_buy,))\n    return dict(result, dataset_fingerprint=digest(result))')
        self.assertIn('LOSSLESS_SOURCE_DECIMAL_FIELDS_ABSENT',
                      probe.check_pair(source, D_GOOD)['reasons'])

    def test_canonical_exact_decimal_contract_is_still_not_release_authority(self):
        source = GRID.replace('"schema":"test"',
                              '"schema":"test", "buy_volume_decimal":"1.01", '
                              '"sell_volume_decimal":"1", "volume_decimal":"2.01", '
                              '"delta_decimal":"0.01"')
        consumer = D_GOOD.replace('"schema",',
                                  '"schema", "buy_volume_decimal", "sell_volume_decimal", '
                                  '"volume_decimal", "delta_decimal",')
        consumer = consumer.replace('        pass',
                                    '        exact_sum((Decimal("1.01"), Decimal("1")))\n'
                                    '        executed_volume_delta(Decimal("1.01"), Decimal("1"))\n'
                                    '        volume_decimal = envelope["volume_decimal"]')
        result = probe.check_pair(source, consumer)
        self.assertEqual(result['status'], 'SOURCE_CONTRACT_MATCH_ONLY')
        self.assertFalse(result['deletion_authorized'])
        self.assertFalse(result['release_authorized'])
        self.assertEqual(result['native'], 'NOT_RUN')

    def test_no_fake_release_even_when_both_sources_match(self):
        good=probe.check_pair(GRID,D_GOOD)
        self.assertFalse(good['deletion_authorized'])
        self.assertFalse(good['release_authorized'])
        self.assertEqual(good['native'],'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
