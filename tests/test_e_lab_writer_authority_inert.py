"""Round9 E non-actuating LAB authority invariant tests; no native IO."""
import ast
import unittest
from pathlib import Path

from unified_system.lab_writer_authority import LabAuthorityStatus, LabWriterAuthority, LabWriterGrant
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

    def test_async_abi_cannot_be_mistaken_for_boolean_grant(self):
        import asyncio
        from inspect import iscoroutinefunction
        self.assertTrue(iscoroutinefunction(LabWriterAuthority.require_current))
        obj = object.__new__(LabWriterAuthority)
        obj._revoked = True
        with self.assertRaises(ResourceFenceBlocked):
            asyncio.run(obj.require_current())

    def test_untrusted_caller_cannot_construct_lab_writer_grant(self):
        with self.assertRaises(ResourceFenceBlocked):
            LabWriterGrant(object(), object(), {"native_admitted": True})

    def test_revoked_grant_cannot_be_reused(self):
        import asyncio
        permit = object.__new__(LabWriterGrant)
        permit._revoked = True
        with self.assertRaises(ResourceFenceBlocked):
            asyncio.run(permit.require_write_current())

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

    def test_incomplete_authority_revoke_is_fail_closed(self):
        obj = object.__new__(LabWriterAuthority)
        obj._revoked = False
        obj.revoke()
        self.assertTrue(obj._revoked)
        with self.assertRaises(ResourceFenceBlocked):
            import asyncio
            asyncio.run(obj.require_current())

    def test_incomplete_grant_rejection_keeps_original_fence_code(self):
        import asyncio
        obj = object.__new__(LabWriterGrant)
        obj._revoked = True
        with self.assertRaisesRegex(ResourceFenceBlocked,
                                    "LAB_ROOT_GRANT_REVOKED"):
            asyncio.run(obj.require_write_current())
        self.assertTrue(obj._revoked)

    def test_external_uncertainty_latches_transfer_blocked(self):
        obj = object.__new__(LabWriterAuthority)
        obj._revoked = False
        obj._transfer_blocked = False
        obj.block_transfer()
        self.assertTrue(obj._revoked)
        self.assertTrue(obj.transfer_blocked)
        obj.revoke()
        self.assertTrue(obj.transfer_blocked)
        with self.assertRaisesRegex(ResourceFenceBlocked,
                                    "LAB_ROOT_AUTHORITY_REVOKED"):
            import asyncio
            asyncio.run(obj.check())

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
