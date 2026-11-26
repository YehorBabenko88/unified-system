"""E ROUND14: protected isolated PG recovery and canonical A OS ABI tests.

No PostgreSQL process is started, no user database is accessed, and these
source-authored tests are NOT evidence of actual PG18/WAL native recovery.
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.lab_pg_recovery_lane import (
    LabPgRecoveryLane, LabPgRecoveryObservation,
)
from unified_system.lab_process_extinction import (
    RootProcessObservation, UNKNOWN, EXTINCT, STILL_ALIVE,
)


class RootRecoveryContractTests(unittest.TestCase):
    def test_stopped_pg_cluster_is_not_old_backend_proof(self):
        result=LabPgRecoveryObservation(
            "unified.root-lab-pg-recovery-observation.v1",
            "UNKNOWN",14321,isolated_cluster_stopped=True)
        self.assertEqual(result.state,"UNKNOWN")
        self.assertFalse(result.old_backend_extinct)
        self.assertFalse(result.durable_fence_verified)
        self.assertFalse(result.wal_reconciled)
        self.assertFalse(result.native_admitted)

    def test_bogus_backend_receipt_rejected(self):
        with self.assertRaises(ResourceFenceBlocked):
            LabPgRecoveryObservation(
                "unified.root-lab-pg-recovery-observation.v1",
                "UNKNOWN","14321",isolated_cluster_stopped=True)

    def test_fabricated_pid_only_stop_is_not_owner(self):
        with self.assertRaises((ResourceFenceBlocked,ImportError,ModuleNotFoundError)):
            LabPgRecoveryLane(SimpleNamespace(
                major=18,port=55432,started=True,
                stop=lambda:None))

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


if __name__=="__main__":
    unittest.main()
