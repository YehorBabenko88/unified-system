"""H/R35: original Meta Minute/Footprint consumers against canonical Math API.

This tests ORIGINAL immutable Meta class implementations, NOT reimplementations.
A synthetic test-only import maps their historical market_profile_math import
to the canonical Math module. This proves narrow consumer behavior, NOT source
authenticity, full parity of other families, release, or legacy retirement.
"""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha1
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / ".source" / "meta-h35"
MATH = ROOT / ".source" / "math-h35"
PINS = {
    META: ("b1a4d6a41054f0040a88dc80b585380fb6b4f323", {
        "src/meta_analyse/core.py": "ea9d2acee3fadf94bfce4ea9865d10d8896b6794",
        "src/meta_analyse/footprint.py": "dd7b95ac98550537aa378fba489cece6dd1c9d0a",
    }),
    MATH: ("9e6acbd9e12a91189f57234828e31640983af553", {
        "python/market_math.py": "7d0e45f099b53bd1632d67bd059bc85540105329",
    }),
}


def exact_source(checkout, relative, expected):
    raw = subprocess.check_output(
        ["git", "-C", str(checkout), "show", "HEAD:" + relative])
    actual = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if actual != expected:
        raise AssertionError("H_META_ORIGINAL_BLOB_MISMATCH:" + relative)
    return raw


def verified_sources():
    for root, (expected_head, items) in PINS.items():
        actual = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if actual != expected_head:
            raise AssertionError("H_META_ORIGINAL_HEAD_MISMATCH:" + root.name)
        for relative, blob in items.items():
            exact_source(root, relative, blob)


def execute_original(source, filename, module_name):
    module = types.ModuleType(module_name)
    module.__file__ = str(filename)
    sys.modules[module_name] = module
    exec(compile(source.decode("utf-8"), str(filename), "exec"),
         module.__dict__)
    return module


class OriginalMetaConsumerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verified_sources()
        def original(repo, file, module):
            data = exact_source(repo, file, PINS[repo][1][file])
            return execute_original(data, repo / file, module)
        # Original Meta source imports market_profile_math as an external
        # dependency. Only this isolated test maps it to canonical Math;
        # production Meta and Math imports are not rewritten.
        with patch.dict(sys.modules):
            pure_math = original(MATH, "python/market_math.py",
                                 "h_original_current_math")
            with patch.dict(sys.modules, {"market_profile_math": pure_math}):
                cls.meta_core = original(
                    META, "src/meta_analyse/core.py", "h_meta_original_core")
                cls.meta_footprint = original(
                    META, "src/meta_analyse/footprint.py",
                    "h_meta_original_footprint")
                cls.math = pure_math

    def test_minute_poc_ties_preserve_nearest_close_policy(self):
        d = Decimal
        minute = self.meta_core.Minute(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            d("0.5"), d("101"), d("102"), d("100"), d("101"))
        minute.profile = {d("100"): d("7"), d("102"): d("7")}
        self.assertEqual(minute.poc, d("100"))
        minute.close = d("102")
        self.assertEqual(minute.poc, d("102"))
        self.assertEqual(minute.poc, self.math.volume_profile_poc(
            minute.profile, close=minute.close))

    def test_footprint_poc_ties_preserve_lowest_price_policy(self):
        d = Decimal
        foot = self.meta_footprint.Footprint(
            "BTCUSDT", 0, 60000, d("0.5"))
        self.assertIsNone(foot.poc)
        foot.cells = {
            d("102"): self.meta_footprint.FootprintCell(d("3"), d("4"), 2),
            d("100"): self.meta_footprint.FootprintCell(d("2"), d("5"), 2),
        }
        self.assertEqual(foot.poc, d("100"))
        self.assertEqual(foot.delta, d("-4"))
        self.assertEqual(foot.snapshot()["poc"], "100")
        self.assertEqual(foot.snapshot()["trusted"], True)

    def test_footprint_gap_is_retained_and_never_grants_quality(self):
        from types import SimpleNamespace
        d = Decimal
        foot = self.meta_footprint.Footprint(
            "BTCUSDT", 0, 60000, d("0.5"))
        foot.add(SimpleNamespace(
            symbol="BTCUSDT", timestamp_ms=1000,
            price=d("100.25"), quantity=d("2"), taker_side="Buy"),
            contiguous=True)
        self.assertTrue(foot.trusted)
        foot.add(SimpleNamespace(
            symbol="BTCUSDT", timestamp_ms=1500,
            price=d("100.25"), quantity=d("1"), taker_side="Sell"),
            contiguous=False)
        self.assertFalse(foot.trusted)
        self.assertEqual(foot.snapshot()["trusted"], False)
        self.assertEqual(foot.delta, d("1"))

    def test_original_source_does_not_mutate_math_or_retirement_authority(self):
        d = Decimal
        self.assertEqual(self.math.price_bucket(d("100.25"), d("0.5")),
                         d("100.5"))
        self.assertEqual(self.math.volume_profile_poc(
            {d("100"): d("1"), d("102"): d("1")}), d("100"))
        self.assertNotIn("trading_authorized",
                         vars(self.meta_footprint.Footprint))
        self.assertNotIn("delisting_authorized",
                         vars(self.meta_core.Minute))


if __name__ == "__main__":
    unittest.main()
