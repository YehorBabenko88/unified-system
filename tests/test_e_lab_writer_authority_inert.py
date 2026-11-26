"""Round9 E non-actuating LAB authority invariant tests; no native IO."""
import ast
import unittest
from pathlib import Path

from unified_system.lab_writer_authority import LabAuthorityStatus, LabWriterAuthority
from unified_system.grid_writer_fence_model import (
    ResourceFenceBlocked, native_writer_admission,
)


class LabAuthorityInvariants(unittest.TestCase):
    def test_status_has_no_native_or_trade_authority(self):
        status = LabAuthorityStatus(
            "unified.lab-root-writer-authority.v1", "ISOLATED_LAB_ONLY",
            "a" * 64, 1, "READ_ONLY_REVALIDATED_NOT_NATIVE")
        self.assertFalse(status.native_admitted)
        self.assertFalse(status.trading_authorized)

    def test_constructor_rejects_forged_flag_objects(self):
        class Fake:
            isolated_lab = True
            def require_current(self): return True
            def confirmed_quiescent(self): return True
        with self.assertRaises(ResourceFenceBlocked):
            LabWriterAuthority(
                authority=Fake(), lease=Fake(), source=Fake(),
                identity=Fake(), generation=1, pg=Fake(), c_module=Fake(),
                quiescence=Fake(), backend_pid=123, process=Fake())

    def test_legacy_native_gate_unconditionally_denied(self):
        with self.assertRaisesRegex(ResourceFenceBlocked,
                                    "NATIVE_DB_FENCE_NOT_ADMITTED"):
            native_writer_admission(True, {"trusted_root_authority": True})

    def test_no_dynamic_admission_or_write_calls(self):
        source = Path(__file__).parents[1] / "unified_system" / "lab_writer_authority.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        invocations = [node.func.attr for node in ast.walk(tree)
                       if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
        for forbidden in ("claim_lab_fence", "fenced_lab_witness",
                          "lab_fenced_insert", "Popen", "start", "write"):
            self.assertNotIn(forbidden, invocations)

    def test_revocation_is_irreversible(self):
        obj = object.__new__(LabWriterAuthority)
        obj._revoked = False
        obj.revoke()
        self.assertTrue(obj._revoked)
        with self.assertRaises(ResourceFenceBlocked):
            import asyncio
            asyncio.run(obj.check())


if __name__ == "__main__":
    unittest.main()
