"""J ROUND28: source-closed, import-only and model-only integration regression.

No PostgreSQL, Consul, Bybit, service process, networking or file deletion.
This test NEVER attests a native Root/writer grant or production release.
"""
import ast
import importlib
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "unified_system"
START = ("lab_pg_recovery", "lab_pg_checkpoint", "lab_writer_revoke")
OBSERVED = "4a91bb79-c488-1086-0664-30ccbc028eda"


class JRound28SourceClosure(unittest.TestCase):
    def test_original_c_e_runtime_relative_import_closure(self):
        pending = list(START)
        checked = set()
        while pending:
            module = pending.pop()
            if module in checked:
                continue
            self.assertRegex(module, r"\A[a-z][a-z0-9_]*\Z")
            path = PACKAGE / (module + ".py")
            self.assertTrue(path.is_file() and not path.is_symlink(),
                            "missing or redirected first-party module: " + module)
            source = path.read_bytes()
            self.assertLess(len(source), 1000000)
            parsed = ast.parse(source, filename=str(path))
            checked.add(module)
            for node in ast.walk(parsed):
                if isinstance(node, ast.ImportFrom) and node.level == 1:
                    if node.module:
                        pending.append(node.module)
                    else:
                        for alias in node.names:
                            if (PACKAGE / (alias.name + ".py")).is_file():
                                pending.append(alias.name)
        self.assertTrue({"lab_pg_recovery", "lab_pg_checkpoint", "lab_pg_fence",
                         "lab_postgres", "lab_writer_revoke", "lab_writer_authority",
                         "lab_root_stop_lane", "lab_root_child_witness",
                         "lab_process_extinction", "lab_pg_recovery_lane",
                         "lab_owner_executor", "consul_authority",
                         "grid_writer_fence_model"}.issubset(checked))

    def test_first_party_runtime_modules_are_importable_without_activation(self):
        # Importing is a syntax/namespace contract, not a process launch.
        for name in START:
            with self.subTest(module=name):
                mod = importlib.import_module("unified_system." + name)
                self.assertTrue(mod.__file__)
        from unified_system.lab_pg_recovery import recover_exclusive_lab_cluster
        from unified_system.lab_pg_checkpoint import read_lab_pending, read_lab_checkpoint
        from unified_system.lab_writer_revoke import LabWriterRevoker
        self.assertTrue(callable(recover_exclusive_lab_cluster))
        self.assertTrue(callable(read_lab_pending))
        self.assertTrue(callable(read_lab_checkpoint))
        self.assertTrue(callable(LabWriterRevoker))

    def test_c_and_e_sql_session_subset_agree_without_lease_claim(self):
        from unified_system.lab_pg_fence import _id
        from unified_system.grid_writer_fence_model import _sql_consul_session_id
        from unified_system.lab_simulation_admission import LabAdmissionRejected
        good = (OBSERVED, str(uuid.uuid4()), str(uuid.uuid5(uuid.NAMESPACE_DNS, "lab")))
        for value in good:
            with self.subTest(value=value):
                self.assertTrue(_sql_consul_session_id(value))
                self.assertEqual(_id(value, consul_session=True), value)
        bad = ("opaque-id", "", OBSERVED.upper(), "{" + OBSERVED + "}",
               OBSERVED + " ", OBSERVED.replace("-", ""), None, True)
        for value in bad:
            with self.subTest(value=repr(value)):
                self.assertFalse(_sql_consul_session_id(value))
                with self.assertRaises(LabAdmissionRejected):
                    _id(value, consul_session=True)

    def test_consul_session_does_not_relax_instance_node_uuid4(self):
        from unified_system.lab_pg_fence import _id
        from unified_system.grid_writer_fence_model import _uuid4
        from unified_system.lab_simulation_admission import LabAdmissionRejected
        self.assertFalse(_uuid4(OBSERVED))
        with self.assertRaises(LabAdmissionRejected):
            _id(OBSERVED)
        accepted = str(uuid.uuid4())
        self.assertTrue(_uuid4(accepted))
        self.assertEqual(_id(accepted), accepted)

    def test_model_always_refuses_native_writer_admission(self):
        from unified_system.grid_writer_fence_model import (
            native_writer_admission, ResourceFenceBlocked,
        )
        with self.assertRaisesRegex(ResourceFenceBlocked, "NATIVE_DB_FENCE_NOT_ADMITTED"):
            native_writer_admission()


if __name__ == "__main__":
    unittest.main()
