"""Offline bounded acceptance oracle for the future B/D qualified MTF slice.

Contract-only tests. The original canonical producer, numerical SDK and UI
are not imported. A PASS here does NOT certify a B/D integration or provider.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "functional-coverage" / "mtf-v1-contract.json"
PIN_REPOS = {"Grid", "Math", "Terminan"}
EXACT_FAILURES = {
    "interior_missing_minute", "duplicate_minute", "wrong_symbol",
    "mixed_epoch", "mixed_revision", "unavailable", "stale",
    "unclosed_bucket", "non_aligned_start", "invalid_numeric",
    "too_many_minutes", "future_event", "unsupported_interval",
    "false_ready", "false_trading_permission",
}


def _load_contract():
    data = CONTRACT.read_bytes()
    if len(data) > 65536:
        raise ValueError("MTF contract budget exceeded")
    return json.loads(data)


def check_source_minutes(starts, *, interval_minutes, first_start, cutoff_ms):
    """Pure acceptance oracle for minute COVERAGE only, not exchange truth.

    Fail closed. Does not calculate OHLCV and never fills missing candles.
    """
    if type(interval_minutes) is not int or interval_minutes not in (5, 15):
        raise ValueError("UNSUPPORTED_INTERVAL")
    if type(first_start) is not int or first_start < 0:
        raise ValueError("START")
    if type(cutoff_ms) is not int or cutoff_ms < 0:
        raise ValueError("CUTOFF")
    cadence_ms = interval_minutes * 60000
    if first_start % cadence_ms:
        raise ValueError("UNALIGNED_START")
    if type(starts) not in (tuple, list) or not 1 <= len(starts) <= 75:
        raise ValueError("SOURCE_PAGE_BOUND")
    if len(starts) % interval_minutes:
        raise ValueError("UNCLOSED_BUCKET")
    if len(starts) // interval_minutes > 5:
        raise ValueError("OUTPUT_BAR_BOUND")
    if any(type(start) is not int or start < 0 or start % 60000
           for start in starts):
        raise ValueError("MINUTE_CLOCK")
    if len(starts) != len(set(starts)):
        raise ValueError("DUPLICATE_MINUTE")
    ordered = sorted(starts)
    if ordered[0] != first_start:
        raise ValueError("START_NOT_BOUND")
    for index, start in enumerate(ordered):
        if start != first_start + index * 60000:
            raise ValueError("MISSING_MINUTE")
    if ordered[-1] + 60000 > cutoff_ms:
        raise ValueError("NOT_CLOSED_AS_OF")
    if (ordered[-1] + 60000) % cadence_ms:
        raise ValueError("UNCLOSED_BUCKET")
    return len(ordered) // interval_minutes


class HMultiTimeframeAcceptanceTests(unittest.TestCase):
    def test_exact_source_pins_and_owner_contract(self):
        spec = _load_contract()
        self.assertEqual(spec["schema"], "unified.h.mtf-acceptance.v1")
        self.assertEqual(set(spec["pins"]), PIN_REPOS)
        for sha in spec["pins"].values():
            self.assertEqual(len(sha), 40)
            self.assertTrue(all(char in "0123456789abcdef" for char in sha))
        self.assertEqual(spec["producer_owner"], "Grid")
        self.assertEqual(spec["consumer_owner"], "Terminan")
        self.assertEqual(spec["numerical_owner"], "Math")

    def test_source_only_status_not_release(self):
        spec = _load_contract()
        self.assertEqual(spec["status"], "CANDIDATE_NOT_RELEASE")
        self.assertEqual(spec["supported_intervals"], ["5m", "15m"])
        self.assertEqual(spec["proposed_response"], "market_data.qualified-mtf-envelope.v2")
        self.assertEqual(spec["max_source_rows"],75)
        self.assertEqual(spec["max_output_bars"],5)
        self.assertEqual(spec["rejection"]["non_partial_source"],"HTTP_503_NO_ROWS")
        self.assertNotIn("READY", spec["status_only"])
        self.assertEqual(set(spec["negative_cases"]), EXACT_FAILURES)
        self.assertIn("paper_admitted false", spec["output_policy"])
        self.assertIn("exchange_completeness NOT_ATTESTED", spec["output_policy"])

    def test_positive_closed_5m_and_15m(self):
        for n in (5, 15):
            with self.subTest(minutes=n):
                starts = [n * 60000 + i * 60000 for i in range(n * 2)]
                self.assertEqual(check_source_minutes(
                    starts, interval_minutes=n, first_start=n * 60000,
                    cutoff_ms=(n * 3) * 60000), 2)

    def test_rejects_interior_gap_and_duplicate(self):
        starts = [i * 60000 for i in range(5)]
        with self.assertRaisesRegex(ValueError, "MISSING_MINUTE"):
            check_source_minutes([*starts[:2], starts[3], starts[4], starts[4] + 60000],
                                 interval_minutes=5, first_start=0, cutoff_ms=360000)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_MINUTE"):
            check_source_minutes([0, 60000, 60000, 180000, 240000],
                                 interval_minutes=5, first_start=0, cutoff_ms=300000)

    def test_rejects_partial_or_future_bucket(self):
        with self.assertRaisesRegex(ValueError, "UNCLOSED_BUCKET"):
            check_source_minutes([0, 60000, 120000, 180000],
                                 interval_minutes=5, first_start=0, cutoff_ms=300000)
        with self.assertRaisesRegex(ValueError, "NOT_CLOSED_AS_OF"):
            check_source_minutes([i * 60000 for i in range(5)],
                                 interval_minutes=5, first_start=0, cutoff_ms=299999)

    def test_rejects_invalid_intervals_and_limits(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_INTERVAL"):
            check_source_minutes([i*60000 for i in range(5)],
                                 interval_minutes=3, first_start=0, cutoff_ms=300000)
        with self.assertRaisesRegex(ValueError, "SOURCE_PAGE_BOUND"):
            check_source_minutes([i*60000 for i in range(80)],
                                 interval_minutes=5, first_start=0, cutoff_ms=60300000)
        with self.assertRaisesRegex(ValueError, "OUTPUT_BAR_BOUND"):
            check_source_minutes([i*60000 for i in range(30)],
                                 interval_minutes=5, first_start=0, cutoff_ms=1800000)
        with self.assertRaisesRegex(ValueError, "UNALIGNED_START"):
            check_source_minutes([60000+i*60000 for i in range(5)],
                                 interval_minutes=5, first_start=60000, cutoff_ms=360000)

    def test_round29_original_math_and_historical_boundaries(self):
        spec = _load_contract()
        self.assertEqual(spec["pins"], {
            "Grid": "4287c5ca8e7fd4f88376cc3e9fa0f578db6a9a4f",
            "Math": "9e6acbd9e12a91189f57234828e31640983af553",
            "Terminan": "bcdf3287a47e60f6c50022adce7651bcb51e587f",
        })
        history = spec["historical_asof"]
        self.assertEqual(history["status"], "PARTIAL")
        self.assertEqual(history["schema"], "market_data.historical-as-of-mtf-envelope.v2")
        self.assertEqual(history["route"], "/internal/v2/candles/historical-as-of-exact")
        self.assertEqual(history["freshness_mode"], "HISTORICAL_AS_OF")
        self.assertEqual(history["historical_source_trust"],
                         "NOT_INDEPENDENTLY_ATTESTED")
        self.assertEqual(history["consumer"].split(";")[0],
                         "Terminan PR132 historical read-only backend IMPLEMENTED")
        self.assertEqual(spec["rejection"]["historical_asof"],
                         "SOURCE_ONLY_CANDIDATE_UNATTESTED")
        self.assertIn("preserves exact Decimal strings", spec["numeric_policy"])

    def test_float_presentation_cancellation_is_not_source_delta(self):
        from decimal import Decimal
        buy = Decimal("10000000000000004.01")
        sell = Decimal("10000000000000004")
        # Decimal oracle only: does not import or replace the original Math SDK.
        self.assertEqual(buy - sell, Decimal("0.01"))
        self.assertEqual(float(buy), float(sell))
        self.assertEqual(float(buy) - float(sell), 0.0)
        self.assertEqual(float(buy - sell), 0.01)



    def test_round32_pair_is_source_matched_not_installed_release(self):
        gate = _load_contract()["round32_gate"]
        self.assertEqual(gate["status"], "SOURCE_PAIR_MATCHED_NOT_RELEASE")
        self.assertEqual(gate["grid_producer_sha"], "4287c5ca8e7fd4f88376cc3e9fa0f578db6a9a4f")
        self.assertEqual(gate["terminan_consumer_sha"], "bcdf3287a47e60f6c50022adce7651bcb51e587f")
        self.assertEqual(gate["canonical_math_sha"], "9e6acbd9e12a91189f57234828e31640983af553")
        self.assertEqual(gate["api_version"], {"major": 2, "minor": 1})
        self.assertEqual(gate["source_schema_keys"], {"top": 29, "row": 15})
        self.assertEqual(set(gate["decimal_fields"]), {
            "buy_volume_decimal", "sell_volume_decimal",
            "volume_decimal", "delta_decimal"})
        self.assertEqual(gate["source_precision"],
                         "STORED_1M_JSON_NUMBERS_NOT_PROVIDER_RAW")
        for field in ("original_cross_repo_runtime_pass",
                      "native_e2e_pass", "deduplicated_68_lines_equivalence_pass",
                      "production_release_admitted", "trading_authority_allowed"):
            self.assertIs(gate[field], False)
        self.assertTrue(gate["historical_source_only"])
        self.assertTrue(gate["live_5m_15m_ui_implemented"])
        self.assertTrue(gate["historical_backend_implemented"])
        self.assertTrue(gate["historical_ui_implemented"])
        self.assertTrue(gate["exact_live_cursor_alignment_implemented"])
        self.assertTrue(gate["historical_full_period_cursor_alignment_implemented"])
        self.assertFalse(gate["historical_ui_e2e_pass"])

    def test_round30_exact_volume_loss_is_a_real_blocker(self):
        from decimal import Decimal
        buy = Decimal("10000000000000004.01")
        sell = Decimal("10000000000000004")
        exact_total = buy + sell
        exact_delta = buy - sell
        # Independent acceptance counterexample only; canonical Math SDK owns
        # all production sums and deltas. Binary64 is presentation, not proof.
        self.assertEqual(str(exact_total), "20000000000000008.01")
        self.assertEqual(str(exact_delta), "0.01")
        self.assertEqual(float(buy), float(sell))
        self.assertNotEqual(Decimal(str(float(buy))) + Decimal(str(float(sell))),
                            exact_total)


    def test_round31_lossless_stored_source_decimal_receipt(self):
        from decimal import Decimal
        buy = Decimal("10000000000000004.01")
        sell = Decimal("10000000000000004")
        total = Decimal("20000000000000008.01")
        delta = Decimal("0.01")
        # This only checks the independent H oracle; production invokes Math.
        self.assertEqual(buy + sell, total)
        self.assertEqual(buy - sell, delta)
        for value in (buy, sell, total, delta):
            rendered = format(value, "f")
            self.assertNotIn("E", rendered.upper())
            self.assertEqual(Decimal(rendered), value)
        self.assertNotEqual(Decimal(str(float(buy))) + Decimal(str(float(sell))), total)

    def test_round32_historical_ui_is_source_only_not_native_proven(self):
        spec = _load_contract()
        gate = spec["round32_gate"]
        self.assertEqual(gate["historical_schema"],
                         "market_data.historical-as-of-mtf-envelope.v2")
        self.assertEqual(gate["live_schema"],
                         "market_data.qualified-mtf-envelope.v2")
        self.assertIn("IMPLEMENTED", spec["historical_asof"]["consumer"])
        self.assertIs(gate["historical_ui_implemented"], True)
        self.assertIs(gate["historical_ui_e2e_pass"], False)
        self.assertIs(gate["native_e2e_pass"], False)


    def test_round32_new_cursor_gate_never_confers_release(self):
        gate = _load_contract()["round32_gate"]
        self.assertTrue(gate["exact_live_cursor_alignment_implemented"])
        self.assertTrue(gate["historical_full_period_cursor_alignment_implemented"])
        self.assertTrue(gate["historical_ui_implemented"])
        self.assertIs(gate["original_cross_repo_runtime_pass"], False)
        self.assertIs(gate["native_e2e_pass"], False)
        self.assertIs(gate["deduplicated_68_lines_equivalence_pass"], False)
        self.assertIs(gate["trading_authority_allowed"], False)



    def test_round33_original_four_cell_http_is_scoped_not_release(self):
        g = _load_contract()["round33_gate"]
        self.assertEqual(g["status"],
                         "ORIGINAL_FOUR_CELL_HTTP_PASS_BROWSER_FAIL_NOT_RELEASE")
        self.assertIs(g["original_cross_repo_runtime_pass"], True)
        ev = g["original_cross_repo_http_tests"]
        self.assertEqual(ev["workflow_run_id"], 45991815725)
        self.assertEqual(ev["passed"], 72)
        self.assertEqual((ev["failed"], ev["errors"], ev["skipped"]), (0, 0, 0))
        self.assertEqual((ev["ubuntu_python311"], ev["ubuntu_python312"],
                          ev["windows_python311"], ev["windows_python312"]),
                         (18, 18, 18, 18))
        self.assertEqual(ev["producer_sha"], g["grid_producer_sha"])
        self.assertEqual(ev["canonical_math_sha"], g["canonical_math_sha"])
        self.assertFalse(g["browser_full_e2e_pass"])
        self.assertFalse(g["native_pg18_consul_windows_installer_pass"])
        self.assertFalse(g["deduplicated_68_lines_equivalence_pass"])
        self.assertFalse(g["production_release_admitted"])

    def test_round33_browser_failure_is_not_promoted_to_pass(self):
        g = _load_contract()["round33_gate"]
        e = g["browser_test_failure"]
        self.assertEqual(e["workflow_run_id"], 45991815731)
        self.assertEqual(e["job_id"], 140481243214)
        self.assertEqual(e["failing_line"], 87)
        self.assertEqual((e["passed"], e["failed"], e["errors"], e["skipped"]),
                         (0, 1, 0, 0))
        self.assertFalse(g["browser_full_e2e_pass"])
        self.assertFalse(g["historical_ui_e2e_pass"])

    def test_round33_strattester_guard_pass_not_full_grid_migration(self):
        g = _load_contract()["round33_gate"]
        e = g["strattester_guard_ci"]
        self.assertEqual(e["head_sha"],
                         "c95ced815575ab3fe25f619f97e9bf040d58f3da")
        self.assertEqual(e["run_id"], 45995842410)
        self.assertEqual(e["windows311_pass"] + e["windows313_pass"]
                         + e["ubuntu311_pass"] + e["ubuntu313_pass"], 2154)
        self.assertEqual(e["ubuntu311_skip"] + e["ubuntu313_skip"], 2)
        self.assertFalse(e["release_admitted"])
        self.assertFalse(e["managed_root_capability_verified"])
        self.assertFalse(g["full_strattester_unique_function_migration_pass"])


    def test_round33_generic_mtf_legacy_browser_expectation_is_unsafe(self):
        gate = _load_contract()["round33_gate"]
        failure = gate["browser_test_failure"]
        self.assertIn("generic /api/candles?timeframe=5m",
                      failure["fail_closed_behavior_expected"])
        self.assertIn("chart MUST remain empty",
                      failure["fail_closed_behavior_expected"])
        self.assertIn("Do NOT let generic 2-candle",
                      failure["required_owner_fix"])
        self.assertFalse(gate["source_browser_test_not_release"] is False)
        self.assertFalse(gate["production_release_admitted"])


if __name__ == "__main__":
    unittest.main()
