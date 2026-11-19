import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.stage13_coordination import CohortMoved, manifest, stable_manifest


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.a = "a" * 40
        self.b = "b" * 40
        self.base = "c" * 40
        self.config = {
            "schema": "unified.release-cohort.v1", "owner": "example", "master": 111,
            "sources": {
                "root": {"repo": "unified", "pr": 1, "lane": "C", "depends_on": []},
                "review": {"repo": "unified", "pr": 2, "lane": "F", "depends_on": ["root"]},
            },
        }
        prefix = "repos/example/unified"
        self.first = prefix + "/pulls/1"
        self.second = prefix + "/pulls/2"
        self.endpoints = {
            self.first: self.pull(self.a, "root", self.base, "main"),
            self.second: self.pull(self.b, "review", self.base, "root"),
            self.first + "/files?per_page=100&page=1": [{"filename": "old.py"}],
            self.second + "/files?per_page=100&page=1": [
                {"filename": "new.py", "previous_filename": "old.py"},
            ],
        }
        for head in (self.a, self.b):
            self.endpoints[f"{prefix}/actions/runs?head_sha={head}&per_page=100"] = {
                "total_count": 1,
                "workflow_runs": [{"head_sha": head, "status": "completed", "conclusion": "success"}],
            }

    def pull(self, head, ref, base, base_ref):
        return {
            "head": {"sha": head, "ref": ref, "repo": {"full_name": "example/unified"}},
            "base": {"sha": base, "ref": base_ref},
            "changed_files": 1, "state": "open", "draft": True, "mergeable": True,
        }

    def api(self, endpoint):
        return copy.deepcopy(self.endpoints[endpoint])

    def test_renamed_path_and_stack_drift_are_blocking(self):
        result = manifest(self.config, self.api)
        self.assertEqual(result["conflicts"][0]["paths"], ["old.py"])
        self.assertEqual(result["queue"]["F"]["candidates"]["review"],
                         ["STACK_DRIFT:root", "OVERLAP:root"])
        self.assertEqual(result["executor"], "NOT_CONNECTED")
        self.assertEqual(result["release"], "NO_GO")

    def test_ci_from_a_different_head_is_ignored(self):
        endpoint = f"repos/example/unified/actions/runs?head_sha={self.a}&per_page=100"
        self.endpoints[endpoint]["workflow_runs"][0]["head_sha"] = self.b
        result = manifest(self.config, self.api)
        self.assertIn("CI_REQUIRES_REVIEW", result["queue"]["C"]["candidates"]["root"])

    def test_incomplete_inventory_blocks_observation(self):
        self.endpoints[self.first]["changed_files"] = 2
        with self.assertRaisesRegex(ValueError, "Incomplete file inventory"):
            manifest(self.config, self.api)

    def test_head_change_during_collection_blocks_observation(self):
        first_reads = 0

        def changing_api(endpoint):
            nonlocal first_reads
            value = self.api(endpoint)
            if endpoint == self.first:
                first_reads += 1
                if first_reads == 2:
                    value["head"]["sha"] = self.b
            return value

        with self.assertRaisesRegex(ValueError, "Cohort moved"):
            manifest(self.config, changing_api)

    def test_retry_restarts_collection_and_remains_bounded(self):
        with patch("scripts.stage13_coordination.manifest",
                   side_effect=[CohortMoved("drift"), {"fresh": True}]) as collect:
            self.assertEqual(stable_manifest(self.config, self.api), {"fresh": True})
            self.assertEqual(collect.call_count, 2)
        with patch("scripts.stage13_coordination.manifest",
                   side_effect=CohortMoved("drift")) as collect:
            with self.assertRaises(CohortMoved):
                stable_manifest(self.config, self.api)
            self.assertEqual(collect.call_count, 3)

    def test_workflow_checks_exact_source_and_separates_review_from_publishing(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/stage13-coordination.yml").read_text()
        jobs = workflow.split("\njobs:\n", 1)[1]
        tests, observe = jobs.split("\n  observe:\n", 1)
        observe, publish = observe.split("\n  publish:\n", 1)
        for block in (tests, observe):
            self.assertIn("ref: ${{ env.EXPECTED_HEAD }}", block)
            self.assertIn("git', 'rev-parse', 'HEAD'", block)
            self.assertIn("COORDINATOR_SOURCE_HEAD_MISMATCH", block)
        self.assertIn("pull_request.head.sha || github.sha", workflow)
        self.assertIn("group: stage13-coordination-${{ github.event_name == 'pull_request'", workflow)
        self.assertIn("github.event.pull_request.head.sha || 'publisher'", workflow)
        self.assertIn("github.ref_name == github.event.repository.default_branch", publish)
        self.assertNotIn("issues: write", tests + observe)
