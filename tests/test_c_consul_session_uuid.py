"""Consul session syntax is not permission: native IDs must round-trip exactly."""
import unittest
import uuid

from unified_system.lab_pg_fence import _id
from unified_system.lab_simulation_admission import LabAdmissionRejected


class ConsulSessionUuidTests(unittest.TestCase):
    def test_actual_consul_210_server_session_id_is_preserved(self):
        # Genuine Consul 2.1.0 session ID observed in ROUND24 native receipt.
        actual = "4a91bb79-c488-1086-0664-30ccbc028eda"
        self.assertEqual(_id(actual, consul_session=True), actual)
        legacy_v5 = "80be6eac-1604-59c1-b4bf-eea940b0f62e"
        self.assertEqual(_id(legacy_v5, consul_session=True), legacy_v5)
        version4 = str(uuid.uuid4())
        self.assertEqual(_id(version4, consul_session=True), version4)

    def test_consul_session_is_canonical_uuid_syntax_not_uuid4_or_5_gate(self):
        for value in ("4a91bb79-c488-1086-0664-30ccbc028eda",
                      str(uuid.uuid1()), str(uuid.uuid3(uuid.NAMESPACE_DNS, "x")),
                      "00000000-0000-0000-0000-000000000000"):
            with self.subTest(value=value):
                self.assertEqual(_id(value, consul_session=True), value)

    def test_instance_and_node_identifiers_remain_uuid4_only(self):
        for value in ("4a91bb79-c488-1086-0664-30ccbc028eda",
                      "80be6eac-1604-59c1-b4bf-eea940b0f62e",
                      str(uuid.uuid1()), "00000000-0000-0000-0000-000000000000"):
            with self.subTest(value=value):
                with self.assertRaises(LabAdmissionRejected):
                    _id(value)
        good = str(uuid.uuid4())
        self.assertEqual(_id(good), good)

    def test_noncanonical_or_non_uuid_session_strings_fail_closed(self):
        for bad in (None, "", "opaque-not-a-uuid", "a" * 200,
                    "4A91BB79-C488-1086-0664-30CCBC028EDA",
                    "{4a91bb79-c488-1086-0664-30ccbc028eda}",
                    "4a91bb79-c488-1086-0664-30ccbc028eda ",
                    "4a91bb79c4881086066430ccbc028eda"):
            with self.subTest(value=bad):
                with self.assertRaises(LabAdmissionRejected):
                    _id(bad, consul_session=True)
