"""Round29: original stopped-service owner + APP_ONLY removal, fake Windows only.

No real Windows SCM, elevation, PostgreSQL, network, activation or execution.
This test composes existing canonical lifecycle classes; no second installer.
"""
from pathlib import Path
import unittest

from tests import test_installation_service as service_fixtures
from tests.test_installation_uninstall import FakeRemoval
from unified_system.installation_service import ServiceResource
from unified_system.installation_uninstall import Uninstaller


class AgentIScopedServiceLifecycle(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        # Scoped FakeWindows runs are disposable tests only. Never grants
        # actual WindowsRemovalBoundary or caller-driven runtime uninstall.
        sandbox_gate = patch('unified_system.installation_uninstall._exclusive_code_removal_proven', return_value=True)
        sandbox_gate.start()
        self.addCleanup(sandbox_gate.stop)
        self.fixture = service_fixtures.ServiceResourceTests(
            "test_registered_command_uses_only_reviewed_protected_entry")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.plan = self.fixture.plan()
        self.backend = self.fixture.backend
        self.guard = self.fixture.guard

    def test_stopped_service_to_owned_app_only_uninstall_preserves_state(self):
        resource = ServiceResource.create(self.plan, self.backend, self.guard)
        observed = resource.inspect(self.guard)
        self.assertEqual(observed["status"], "STOPPED_RESOURCE_RECORDED")
        self.assertEqual(observed["activation"], "BLOCKED")
        self.assertFalse(observed["execution_authority"])
        marker = Path(self.plan["state"]) / "UNTOUCHED_USER_STATE"
        marker.write_bytes(b"PRESERVE")
        original_receipt = (Path(self.plan["root"]) / "ownership/service.sqlite").read_bytes()
        removal = FakeRemoval(self.backend)
        result = Uninstaller(resource, removal).run(guard=self.guard)
        self.assertEqual(result["status"], "APP_ONLY_REMOVED")
        self.assertFalse(Path(self.plan["code"]).exists())
        self.assertEqual(marker.read_bytes(), b"PRESERVE")
        self.assertEqual((Path(self.plan["root"]) / "ownership/service.sqlite").read_bytes(), original_receipt)
        self.assertTrue((Path(self.plan["root"]) / "ownership/uninstall.sqlite").is_file())
        self.assertEqual(self.backend.service, None)
        self.assertNotIn("START", self.backend.calls)
        self.assertNotIn("STOP", self.backend.calls)

    def test_foreign_owned_code_refuses_service_uninstall(self):
        resource = ServiceResource.create(self.plan, self.backend, self.guard)
        outsider = Path(self.plan["code"]) / "foreign-file.txt"
        outsider.write_bytes(b"FOREIGN_PRESERVE")
        removal = FakeRemoval(self.backend)
        with self.assertRaises(ValueError):
            Uninstaller(resource, removal).run(guard=self.guard)
        self.assertEqual(outsider.read_bytes(), b"FOREIGN_PRESERVE")
        self.assertNotIn("REMOVE_SERVICE", removal.calls)
        self.assertIsNotNone(self.backend.service)

    def test_failed_native_register_never_adopts_partial_install(self):
        self.backend.fault = "REGISTER"
        with self.assertRaisesRegex(OSError, "INJECTED_PRIVATE_FAULT"):
            ServiceResource.create(self.plan, self.backend, self.guard)
        self.assertTrue(Path(self.plan["root"]).exists())
        self.assertTrue(Path(self.plan["code"]).is_dir())
        self.assertIsNone(self.backend.service)
        self.backend.fault = None
        with self.assertRaises(ValueError):
            ServiceResource.create(self.plan, self.backend, self.guard)
        self.assertTrue(Path(self.plan["root"]).exists())

    def test_wrong_host_blocks_service_creation_without_effect(self):
        self.backend.host = "UNEXPECTED-HOST"
        with self.assertRaises(ValueError):
            ServiceResource.create(self.plan, self.backend, self.guard)
        self.assertEqual(self.backend.calls, [])
        self.assertFalse(Path(self.plan["root"]).exists())


if __name__ == "__main__":
    unittest.main()
