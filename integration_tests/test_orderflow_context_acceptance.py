"""Independent installed-SDK regression for the release-blocking stream defect."""
from decimal import Decimal, Inexact, Rounded, localcontext
import unittest


class StreamContextAcceptance(unittest.TestCase):
    @staticmethod
    def events():
        pattern = (("100.00001", "buy"), ("0.00002", "buy"),
                   ("0.00004", "sell"), ("0.00003", "unknown"))
        for index in range(100_000):
            volume, side = pattern[index % 4]
            yield (100_000 - index, Decimal("1.009"), Decimal(volume), side)

    def test_100k_exact_distribution_across_precision_and_traps(self):
        from market_profile_math import aggregate_orderflow_stream

        baseline = None
        for precision, traps in ((28, False), (3, False), (5, True), (28, True)):
            with self.subTest(precision=precision, traps=traps), localcontext() as context:
                context.prec = precision
                context.traps[Inexact] = traps
                context.traps[Rounded] = traps
                result = aggregate_orderflow_stream(
                    self.events(), mode="price", tick_size=Decimal("0.001"),
                    initial_delta=Decimal("0.00007"),
                )
                self.assertEqual(len(result), 1)
                key, metrics = result[0]
                self.assertEqual(key, Decimal("1.009"))
                for name, expected in (
                    ("buy_volume", "2500000.75000"), ("sell_volume", "1.00000"),
                    ("unknown_volume", "0.75000"), ("delta", "2499999.75000"),
                    ("cumulative_delta", "2499999.75007"),
                ):
                    self.assertEqual(metrics[name], Decimal(expected), name)
                self.assertEqual(metrics["trade_count"], 100_000)
                self.assertTrue(metrics["imbalance"].is_finite())
                if baseline is None:
                    baseline = result
                self.assertEqual(result, baseline)

    def test_nonterminating_ratio_and_late_price_buckets_are_deterministic(self):
        from market_profile_math import aggregate_orderflow_stream

        baseline = None
        for precision in (28, 3, 5):
            with self.subTest(precision=precision), localcontext() as context:
                context.prec = precision
                context.traps[Inexact] = True
                context.traps[Rounded] = True
                result = aggregate_orderflow_stream(iter([
                    (200, Decimal("2.009"), Decimal("2"), "buy"),
                    (0, Decimal("1.009"), Decimal("1"), "buy"),
                    (100, Decimal("1.009"), Decimal("2"), "sell"),
                ]), mode="price", tick_size=Decimal("0.001"))
                self.assertEqual([key for key, _ in result], [Decimal("1.009"), Decimal("2.009")])
                self.assertEqual(result[0][1]["delta"], Decimal("-1"))
                self.assertEqual(result[1][1]["cumulative_delta"], Decimal("1"))
                if baseline is None:
                    baseline = result
                self.assertEqual(result, baseline)


if __name__ == "__main__":
    unittest.main()
