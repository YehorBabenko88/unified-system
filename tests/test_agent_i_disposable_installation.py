"""Agent I disposable inactive staging regression; no SCM/PG/Consul use."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_lab_release import fixture
from unified_system import lab_release
from unified_system.disposable_installation import DisposableInstallation


class DisposableInstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="unified-agent-i-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.capsule = self.root / "capsule"
        self.capsule.mkdir()
        manifest = fixture(self.capsule)
        raw = lab_release.canonical(manifest)
        (self.capsule / "lab-release.json").write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()
        self.install = self.root / "install"
        self.state = self.root / "state"

    def subject(self):
        return DisposableInstallation.from_capsule(
            capsule_root=str(self.capsule), install_root=str(self.install),
            state_root=str(self.state), installation_id="agent-i-lab",
            node_id="node-one", operation_id="op-one", role="WORKER",
            manifest_sha256=self.pin)

    def test_preview_has_zero_effects(self):
        tx = self.subject()
        r = tx.preview()
        self.assertEqual(r["activation"], "BLOCKED")
        self.assertFalse(r["execution_authority"])
        self.assertFalse(r["service_creation"])
        self.assertFalse(r["postgresql_effect"])
        self.assertFalse(r["consul_effect"])
        self.assertFalse(self.install.exists())
        self.assertFalse(self.state.exists())

    def test_approval_required_before_any_mutation(self):
        tx = self.subject()
        with self.assertRaisesRegex(ValueError, "DISPOSABLE_INSTALLATION_REJECTED"):
            tx.stage()
        with self.assertRaises(ValueError):
            tx.execute("STAGE", disposable_approval=1)
        self.assertFalse(self.state.exists())

    def test_stage_and_reopen_are_inactive(self):
        tx = self.subject()
        staged = tx.stage(disposable_approval=True)
        self.assertEqual(staged["status"], "STAGED_INACTIVE")
        self.assertEqual(staged["activation"], "BLOCKED")
        self.assertFalse(staged["execution_authority"])
        self.assertEqual(tx.observe()["transaction_receipt_sha256"],
                         staged["transaction_receipt_sha256"])
        # No service/Pg/Consul is permitted by this wrapper.
        reopened = self.subject()
        self.assertEqual(reopened.stage(disposable_approval=True), staged)

    def test_logical_rollback_retains_every_byte(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        marker = self.state / "user-data"
        marker.write_bytes(b"KEEP")
        before = (self.install / "release" / "lab-release.json").read_bytes()
        done = tx.rollback(disposable_approval=True)
        self.assertEqual(done["status"], "ROLLED_BACK_RETAINED")
        self.assertEqual(marker.read_bytes(), b"KEEP")
        self.assertEqual((self.install / "release" / "lab-release.json").read_bytes(), before)
        with self.assertRaises(ValueError):
            tx.stage(disposable_approval=True)

    def test_uninstall_denied_and_state_retained(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        result = tx.uninstall_preview()
        self.assertEqual(result["status"], "DENIED_NO_OWNED_SERVICE_REMOVAL_RECEIPT")
        self.assertFalse(result["removes_code"])
        self.assertFalse(result["removes_state"])
        self.assertTrue((self.install / "release").is_dir())

    def test_unknown_or_foreign_state_not_adopted(self):
        tx = self.subject()
        self.install.mkdir()
        (self.install / "foreign.txt").write_bytes(b"PRESERVE")
        with self.assertRaises(ValueError):
            tx.stage(disposable_approval=True)
        self.assertEqual((self.install / "foreign.txt").read_bytes(), b"PRESERVE")
        self.assertFalse(self.state.exists())

    def test_corrupt_staged_bytes_fail_closed(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        artifact = self.install / "release" / "lab-release.json"
        artifact.write_bytes(b"CORRUPTED")
        with self.assertRaises(ValueError):
            tx.observe()
        self.assertEqual(artifact.read_bytes(), b"CORRUPTED")

    def test_uncertain_stage_is_not_adopted_or_cleaned(self):
        tx = self.subject()
        from unified_system import installation_transaction
        original = lab_release.stage_capsule
        def interrupted(source, target, digest):
            target.mkdir()
            (target / "unknown.partial").write_bytes(b"RETAIN")
            raise OSError("INTERRUPTED")
        with patch.object(installation_transaction.lab_release, "stage_capsule", side_effect=interrupted):
            with self.assertRaises(OSError):
                tx.stage(disposable_approval=True)
        partial = self.install / "release" / "unknown.partial"
        self.assertTrue(partial.exists())
        with self.assertRaises(ValueError):
            tx.stage(disposable_approval=True)
        self.assertEqual(partial.read_bytes(), b"RETAIN")


    def test_dispose_inactive_removes_only_closed_code_and_preserves_state(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        marker = self.state / "user-data"
        marker.write_bytes(b"KEEP_DATA")
        out = tx.dispose_inactive(disposable_approval=True)
        self.assertEqual(out["status"], "DISPOSED_INACTIVE")
        self.assertEqual(list((self.install / "release").iterdir()), [])
        self.assertEqual(marker.read_bytes(), b"KEEP_DATA")
        self.assertTrue((self.state / "transaction.sqlite").is_file())
        self.assertEqual(tx.observe()["status"], "DISPOSED_INACTIVE")
        self.assertEqual(tx.dispose_inactive(disposable_approval=True), out)
        with self.assertRaises(ValueError):
            tx.rollback(disposable_approval=True)

    def test_dispose_denies_foreign_files_before_any_unlink(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        foreign = self.install / "release" / "foreign.bin"
        foreign.write_bytes(b"DO_NOT_TOUCH")
        legit = self.install / "release" / "runtime.json"
        original = legit.read_bytes()
        with self.assertRaises(ValueError):
            tx.dispose_inactive(disposable_approval=True)
        self.assertEqual(foreign.read_bytes(), b"DO_NOT_TOUCH")
        self.assertEqual(legit.read_bytes(), original)
        with self.assertRaises(ValueError):
            tx.observe()  # a foreign member must also block snapshot certification

    def test_dispose_requires_explicit_boolean_and_temp_workspace(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        with self.assertRaises(ValueError):
            tx.dispose_inactive()
        with self.assertRaises(ValueError):
            tx.dispose_inactive(disposable_approval=1)
        self.assertEqual(tx.observe()["status"], "STAGED_INACTIVE")

    def test_dispose_failpoint_retains_audit_and_requires_manual_review(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        marker = self.state / "userdata.bin"
        marker.write_bytes(b"USER")
        with self.assertRaisesRegex(OSError, "DISPOSABLE_INJECTED_INTERRUPTION"):
            tx.dispose_inactive(disposable_approval=True, fail_after_members=1)
        snapshot = tx.observe()
        self.assertEqual(snapshot["status"], "DISPOSE_INTENT")
        self.assertEqual(snapshot["rollback"], "DISPOSAL_UNCERTAIN_REVIEW_REQUIRED")
        self.assertEqual(marker.read_bytes(), b"USER")
        self.assertTrue((self.state / "transaction.sqlite").exists())
        with self.assertRaises(ValueError):
            tx.dispose_inactive(disposable_approval=True)
        with self.assertRaises(ValueError):
            tx.stage(disposable_approval=True)

    def test_dispose_refuses_modified_manifest_member(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        item = self.install / "release" / "runtime.json"
        item.write_bytes(b"CHANGED")
        with self.assertRaises(ValueError):
            tx.dispose_inactive(disposable_approval=True)
        self.assertEqual(item.read_bytes(), b"CHANGED")

    def test_dispose_refuses_foreign_workspace_name(self):
        tx = self.subject()
        tx.stage(disposable_approval=True)
        with patch("unified_system.installation_transaction.tempfile.gettempdir",
                   return_value=str(self.root.parent / "different-temp")):
            with self.assertRaises(ValueError):
                tx.dispose_inactive(disposable_approval=True)
        self.assertTrue((self.install / "release" / "runtime.json").exists())

    def test_no_runtime_executor_in_wrapper(self):
        import inspect
        import unified_system.disposable_installation as module
        source = inspect.getsource(module)
        for forbidden in ("subprocess.", "os.system(", "shutil.rmtree(", "psycopg", "winreg."):
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()
