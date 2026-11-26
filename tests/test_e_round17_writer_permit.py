"""ROUND17 E: bounded Root-owned operation permit contract.

These are local synthetic negative/serialization tests, NOT native PostgreSQL,
Windows or real Root admission. The real B/C integration stays denied.
"""
import asyncio
import threading
import unittest
from types import SimpleNamespace
from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.lab_owner_executor import LabOwnerExecutor
from unified_system.lab_writer_authority import (
    LabWriterAuthority, LabWriterGrant, LabWriterOperationPermit,
    _ISSUANCE_SEAL,
)


class OperationPermitTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_original_owner_thread_is_retained(self):
        executor=LabOwnerExecutor()
        try:
            observed=await executor.call(threading.get_ident)
            self.assertEqual(observed,executor.owner_thread_id)
            later=await executor.call(threading.get_ident)
            self.assertEqual(later,observed)
            self.assertNotEqual(observed,threading.get_ident())
        finally:
            executor.close()

    async def test_permit_can_only_be_issued_from_root_grant(self):
        with self.assertRaises(ResourceFenceBlocked):
            LabWriterOperationPermit(object(),None,None,"a"*32,"b"*64,
                                     "c"*64,"grid.canonical_lab_fenced_writer",
                                     "2026-11-26T01:00:00+00:00")

    async def test_forged_executor_rejected_before_any_grant(self):
        authority=object.__new__(LabWriterAuthority)
        original=LabOwnerExecutor()
        foreign=LabOwnerExecutor()
        authority._executor=original
        try:
            with self.assertRaises(ResourceFenceBlocked):
                await authority.issue_operation_permit(
                    executor=foreign,operation_id="a"*32,content_id="b"*64,
                    package_identity="c"*64,
                    entrypoint="grid.canonical_lab_fenced_writer")
        finally:
            original.close()
            foreign.close()

    async def test_invalid_operation_id_and_package_rejected(self):
        authority=object.__new__(LabWriterAuthority)
        executor=LabOwnerExecutor()
        authority._executor=executor
        try:
            for operation,package in (("forged","a"*64),("a"*32,"bad")):
                with self.assertRaises(ResourceFenceBlocked):
                    await authority.issue_operation_permit(
                        executor=executor,operation_id=operation,
                        content_id="b"*64,package_identity=package,
                        entrypoint="grid.canonical_lab_fenced_writer")
        finally:
            executor.close()


if __name__=="__main__":
    unittest.main()
