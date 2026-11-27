"""Identity syntax only: a UUID is never independent lease authority."""
import unittest
import uuid
from unified_system.lab_pg_fence import _id
from unified_system.lab_simulation_admission import LabAdmissionRejected


class ConsulSessionUuidTests(unittest.TestCase):
    def test_actual_consul_210_server_session_uuid5_is_preserved(self):
        observed = "80be6eac-1604-59c1-b4bf-eea940b0f62e"
        self.assertEqual(_id(observed, consul_session=True), observed)
        version4 = str(uuid.uuid4())
        self.assertEqual(_id(version4, consul_session=True), version4)

    def test_instance_and_node_identifiers_remain_uuid4_only(self):
        with self.assertRaises(LabAdmissionRejected):
            _id("80be6eac-1604-59c1-b4bf-eea940b0f62e")

    def test_session_noncanonical_versions_and_variants_are_denied(self):
        for bad in (None, "", str(uuid.uuid1()), str(uuid.uuid3(uuid.NAMESPACE_DNS, "x")),
                    "00000000-0000-0000-0000-000000000000",
                    "80be6eac-1604-59c1-74bf-eea940b0f62e",
                    "80be6eac-1604-59c1-f4bf-eea940b0f62e",
                    "80BE6EAC-1604-59C1-B4BF-EEA940B0F62E"):
            with self.subTest(value=bad):
                with self.assertRaises(LabAdmissionRejected):
                    _id(bad, consul_session=True)
