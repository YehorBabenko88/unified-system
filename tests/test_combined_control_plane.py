"""Cross-stream disposable integration: fleet + lifecycle + source boundary.

This verifies shared API behavior, not trust in votes, production identity,
physical nodes, or authorization to execute any module.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path

from unified_system.fleet_control import FleetControl
from unified_system.lifecycle import Lifecycle
from unified_system.release_boundary import HistoricalBoundary, ReleasePin


class CombinedControlPlaneTests(unittest.TestCase):
    def test_six_node_fleet_visible_to_lifecycle_without_execution_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fleet = FleetControl(root / "fleet.sqlite", ["voter-a", "voter-b", "voter-c"])
            for i in range(1, 7):
                name = f"PC{i}"
                fleet.approve_node(name, 1, f"zone-{i % 2}", f"synthetic-owner-plan-{i}")
                fleet.heartbeat(name, 1, 1, 100, {"cpu": 8.0, "memory": 32.0, "disk": 100.0})
            # These are simulated caller votes, not distributed consensus.
            fleet.elect(1, "voter-a", ["voter-a", "voter-b"], 100, 60)
            fleet.submit("historical-job", {"cpu": 1.0, "memory": 2.0, "disk": 5.0})
            lease = fleet.place("historical-job", 101, 1)
            self.assertIs(lease["execution_authorized"], False)
            lifecycle = Lifecycle(
                root / "lifecycle.sqlite",
                ["unified-system", "terminan", "strattester", "grid", "math"],
                fleet_provider=lambda: fleet.status_snapshot(101000),
            )
            view = lifecycle.initialize()
            self.assertEqual(len(view["fleet"]["nodes"]), 6)
            self.assertEqual(view["fleet"]["mode"], "PLAN_ONLY")
            self.assertIs(view["execution_authorized"], False)
            self.assertIs(view["trading_authorized"], False)
            self.assertEqual(view["physical_acceptance"], "NOT_RUN")

    def test_missing_modules_and_missing_source_authority_remain_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fleet = FleetControl(root / "fleet.sqlite", ["voter-a"])
            lifecycle = Lifecycle(
                root / "lifecycle.sqlite",
                [],
                fleet_provider=lambda: fleet.status_snapshot(100000),
            )
            view = lifecycle.initialize()
            self.assertEqual(view["fleet"]["nodes"], [])
            self.assertEqual(view["available_modules"], [])
            self.assertIs(view["execution_authorized"], False)

            fake_bytes = b"synthetic artifact"
            release = ReleasePin(
                producer="strattester",
                revision="a" * 40,
                tree="b" * 40,
                artifact_sha256=hashlib.sha256(fake_bytes).hexdigest(),
            )
            verifier = HistoricalBoundary(release, [])
            result = verifier.verify(
                {},
                observed_revision=release.revision,
                observed_tree=release.tree,
                artifact_bytes=fake_bytes,
            )
            self.assertEqual(result["verdict"], "UNAVAILABLE")
            self.assertIs(result["execution_authorized"], False)
            self.assertIs(result["trading_authorized"], False)


if __name__ == "__main__":
    unittest.main()
