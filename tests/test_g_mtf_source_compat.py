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


    def test_versioned_v2_exact_roster_is_only_source_match(self):
        grid, consumer = self._v2_source_fixture()
        receipt = probe.check_pair(grid, consumer)
        self.assertEqual(receipt['status'], 'SOURCE_CONTRACT_MATCH_ONLY', receipt)
        self.assertEqual(receipt['reasons'], [])
        self.assertFalse(receipt['deletion_authorized'])
        self.assertFalse(receipt['release_authorized'])

    def test_v2_missing_exact_field_is_denied(self):
        grid, consumer = self._v2_source_fixture()
        altered = grid.replace('"delta_decimal": raw_delta}', '}')
        receipt = probe.check_pair(altered, consumer)
        self.assertEqual(receipt['status'], 'BLOCKED')
        self.assertIn('PRODUCER_EXACT_FIELDS_UNVERIFIED', receipt['reasons'])

    def test_v2_missing_math_check_is_denied(self):
        grid, consumer = self._v2_source_fixture()
        altered = consumer.replace('executed_volume_delta(buy, sell) == delta', 'True')
        receipt = probe.check_pair(grid, altered)
        self.assertEqual(receipt['status'], 'BLOCKED')
        self.assertIn('CONSUMER_MATH_OR_INTEGRITY_UNVERIFIED', receipt['reasons'])

    def test_v2_unexpected_top_field_is_denied(self):
        grid, consumer = self._v2_source_fixture()
        altered = grid.replace("'schema': None,", "'schema': None, 'unexpected': True,")
        receipt = probe.check_pair(altered, consumer)
        self.assertEqual(receipt['status'], 'BLOCKED')
        self.assertIn('EXACT_TOP_KEYS_MISMATCH', receipt['reasons'])

    @staticmethod
    def _v2_source_fixture():
        import ast
        # These are intentionally synthetic: we validate AST behavior, not
        # assert original B307/D132 runtime was loaded into this test.
        base_top = (
            'schema api_version producer symbol timeframe limit status reason '
            'source_timeframe source_minutes parent_dataset_fingerprint '
            'source_revision producer_epoch coverage record_integrity '
            'source_authenticity exchange_completeness quality_attestation '
            'storage_immutability immutable read_only execution_authority '
            'trading_authorized paper_admitted rows dataset_fingerprint'
        ).split()
        v1_top = base_top + ['source_declared_quality']
        row = ('start_ms end_ms open high low close buy_volume sell_volume '
               'delta trade_count source_minute_fingerprints').split()
        extra = 'buy_volume_decimal sell_volume_decimal volume_decimal delta_decimal'.split()
        literal = lambda keys, value: ', '.join(f'{key!r}: {value}' for key in keys)
        # Use a real result dict (with .v2 metadata amended after creation)
        # to match the original B307 AST shape.
        producer = f'''def project_qualified_rollup(envelope, *, timeframe, limit, now_ms, exact=False):
    raw_buy = Decimal('1.01')
    raw_sell = Decimal('1')
    raw_volume = exact_sum((raw_buy, raw_sell))
    raw_delta = executed_volume_delta(raw_buy, raw_sell)
    candle = {{{literal(row, '0')}}}
    exact_values = {{"buy_volume_decimal": raw_buy, "sell_volume_decimal": raw_sell,
                    "volume_decimal": raw_volume, "delta_decimal": raw_delta}}
    for key, value in exact_values.items():
        candle[key] = format(value, 'f')
    result = {{{literal([k for k in base_top if k != 'dataset_fingerprint'], 'None')}}}
    if exact:
        result['decimal_contract'] = 'CANONICAL_MATH_EXACT_STORED_1M'
    return dict(result, dataset_fingerprint=digest(result))
'''
        top = ', '.join(map(repr, v1_top))
        rowkeys = ', '.join(map(repr, row))
        consumer = f'''_TOP = frozenset({{{top}}})
_ROW = frozenset({{{rowkeys}}})
_EXACT_TOP = frozenset({{"decimal_contract", "numeric_presentation", "source_numeric_precision"}})
_EXACT_ROW = frozenset({{"buy_volume_decimal", "sell_volume_decimal", "volume_decimal", "delta_decimal"}})
_HISTORICAL_ONLY = frozenset({{"freshness_mode", "as_of_ms", "live_freshness", "historical_source_trust"}})
def validate_qualified_rollup(envelope, symbol, timeframe, limit, exact=False):
    buy, sell, volume, delta = (Decimal('1.01'), Decimal('1'), Decimal('2.01'), Decimal('0.01'))
    _need(exact_sum((buy, sell)) == volume)
    _need(executed_volume_delta(buy, sell) == delta)
    _need(envelope['dataset_fingerprint'])
'''
        ast.parse(producer)
        ast.parse(consumer)
        return producer, consumer



if __name__ == '__main__':
    unittest.main()
