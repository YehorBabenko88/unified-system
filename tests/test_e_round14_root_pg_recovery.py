"""E ROUND14: protected isolated PG recovery and canonical A OS ABI tests.

No PostgreSQL process is started, no user database is accessed, and these
source-authored tests are NOT evidence of actual PG18/WAL native recovery.
"""
import asyncio
import unittest
import sys
import types
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.lab_pg_recovery_lane import (
    LabPgRecoveryLane, LabPgRecoveryObservation,
)
from unified_system.lab_writer_revoke import LabWriterRevoker
from unified_system.lab_process_extinction import (
    RootProcessObservation, UNKNOWN, EXTINCT, STILL_ALIVE,
)


class RootRecoveryContractTests(unittest.TestCase):
    def test_stopped_pg_cluster_is_not_old_backend_proof(self):
        result=LabPgRecoveryObservation(
            "unified.root-pg-recovery-dispatch.v2",
            "UNKNOWN",worker_done=False)
        self.assertEqual(result.state,"UNKNOWN")
        self.assertFalse(result.worker_done)
        self.assertFalse(result.native_admitted)

    def test_bogus_backend_receipt_rejected(self):
        with self.assertRaises(ResourceFenceBlocked):
            LabPgRecoveryObservation(
                "unified.root-pg-recovery-dispatch.v2",
                "UNKNOWN",worker_done="yes")

    def test_cannot_forge_full_sql_backend_recovery(self):
        with self.assertRaises(ResourceFenceBlocked):
            LabPgRecoveryObservation(
                "unified.root-pg-recovery-dispatch.v2",
                "EXTINCT",worker_done=True)

    def test_cannot_forge_tcp_listener_proof(self):
        with self.assertRaises(ResourceFenceBlocked):
            RootProcessObservation(
                "unified.root-process-observation.v1",
                EXTINCT,"op",4321,["stamp","image"],
                "FORGED",listener_owner_verified=True)

    def test_fabricated_pid_only_stop_is_not_owner(self):
        with self.assertRaises((ResourceFenceBlocked,ImportError,ModuleNotFoundError)):
            LabPgRecoveryLane(SimpleNamespace(
                major=18,port=55432,started=True,
                stop=lambda:None))

    def test_one_C_owner_never_gets_second_dispatcher_after_close(self):
        # C module is deliberately absent from standalone E branch. Inject
        # a synthetic owner CLASS to exercise only the E one-owner registry.
        class FakeCPostgres:
            major=18
            port=55432
            def _verify_owned(self):
                return None
        fake=types.ModuleType("unified_system.lab_postgres")
        fake.LabPostgres=FakeCPostgres
        with patch.dict(sys.modules, {"unified_system.lab_postgres": fake}):
            owner=FakeCPostgres()
            lane=LabPgRecoveryLane(owner)
            try:
                with self.assertRaises(ResourceFenceBlocked):
                    LabPgRecoveryLane(owner)
                lane.close()
                with self.assertRaises(ResourceFenceBlocked):
                    LabPgRecoveryLane(owner)
            finally:
                lane.close()

    def test_os_extinct_not_tcp_extinct(self):
        p=RootProcessObservation(
            "unified.root-process-observation.v1",EXTINCT,"op",4321,
            ["stamp","image"],"A_RETAINED_HANDLE_EXITED",
            listener_owner_verified=False)
        self.assertFalse(p.listener_owner_verified)
        self.assertFalse(p.native_admitted)

    def test_uncertain_os_not_extinct(self):
        for state in (UNKNOWN,STILL_ALIVE):
            p=RootProcessObservation(
                "unified.root-process-observation.v1",
                state,"op",4321,["stamp","image"],"OBSERVED")
            self.assertNotEqual(p.state,EXTINCT)


class PoisonedOwnerContainmentTests(unittest.IsolatedAsyncioTestCase):
    def make_revoker(self, *, poisoned=True, stopped=True):
        revoker=object.__new__(LabWriterRevoker)
        revoker._once=True
        revoker._last=SimpleNamespace(
            result="PARTIAL_DENIED", child_stopped=stopped)
        revoker._executor=SimpleNamespace(poisoned=poisoned)
        revoker._pg=object()
        lane=object.__new__(LabPgRecoveryLane)
        lane._pg=revoker._pg
        return revoker,lane

    async def test_missing_sealed_root_receipt_blocks_C_dispatch(self):
        revoker,lane=self.make_revoker()
        with self.assertRaises((ResourceFenceBlocked, ImportError)):
            await revoker.dispatch_owned_recovery_after_poison(
                lane,old={},streams=(),root_process_evidence=None)
        self.assertEqual(lane._pg,revoker._pg)

    async def test_nonpoisoned_or_foreign_owner_cannot_dispatch_recovery(self):
        revoker,lane=self.make_revoker(poisoned=False)
        with self.assertRaises(ResourceFenceBlocked):
            await revoker.dispatch_owned_recovery_after_poison(
                lane,old={},root_process_evidence=None)
        revoker,lane=self.make_revoker()
        lane._pg=object()
        with self.assertRaises(ResourceFenceBlocked):
            await revoker.dispatch_owned_recovery_after_poison(
                lane,old={},root_process_evidence=None)


if __name__=="__main__":
    unittest.main()
