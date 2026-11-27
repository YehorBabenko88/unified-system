"""Identity syntax negatives; no lease or native admission is fabricated."""
import unittest
import uuid
from dataclasses import replace
from unified_system.grid_writer_fence_model import WriterLeaseIdentity, ResourceFenceBlocked


class ConsulSessionIdentityTests(unittest.TestCase):
    def test_original_consul_210_session_uuid5_is_preserved(self):
        observed = "80be6eac-1604-59c1-b4bf-eea940b0f62e"
        identity = WriterLeaseIdentity("unified-system", "codex-round24/isolated",
            observed, 11, str(uuid.uuid4()), str(uuid.uuid4()), "a" * 64, "b" * 64)
        self.assertEqual(identity.session_id, observed)

    def test_uuid5_never_becomes_instance_or_node_identity(self):
        identity = WriterLeaseIdentity("unified-system", "codex-round24/isolated",
            str(uuid.uuid4()), 11, str(uuid.uuid4()), str(uuid.uuid4()), "a" * 64, "b" * 64)
        for field in ("instance_id", "node_incarnation_id"):
            with self.subTest(field=field):
                with self.assertRaises(ResourceFenceBlocked):
                    replace(identity, **{field: "80be6eac-1604-59c1-b4bf-eea940b0f62e"})
        for invalid in (None, "", str(uuid.uuid1()), str(uuid.uuid3(uuid.NAMESPACE_DNS, "x")),
                        "80be6eac-1604-59c1-74bf-eea940b0f62e",
                        "80be6eac-1604-59c1-f4bf-eea940b0f62e",
                        "80BE6EAC-1604-59C1-B4BF-EEA940B0F62E"):
            with self.subTest(value=invalid):
                with self.assertRaises(ResourceFenceBlocked):
                    replace(identity, session_id=invalid)
