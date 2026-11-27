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

    async def test_correct_named_proof_type_never_authorizes_c_dispatch(self):
        # Regression for ROUND16 MASTER: an injected class with the expected
        # name and an exact instance cannot substitute for A/C-bound proof.
        revoker,lane=self.make_revoker()
        class RootProcessExtinction:
            pass
        fake=types.ModuleType("round16.fake_root")
        fake.RootProcessExtinction=RootProcessExtinction
        import unified_system.lab_writer_revoke as root_revoke
        with patch.object(root_revoke, "RootProcessExtinction",
                          RootProcessExtinction, create=True):
            with self.assertRaisesRegex(
                    ResourceFenceBlocked,
                    "LAB_ROOT_BOUND_EXTINCTION_NOT_IMPLEMENTED"):
                await revoker.dispatch_owned_recovery_after_poison(
                    lane,old={"owner":"forged"},streams=(),
                    root_process_evidence=RootProcessExtinction())
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



class ExactRevokeOrderSyntheticTests(unittest.IsolatedAsyncioTestCase):
    """Ordering-only synthetic seam; NEVER native C/PG18/Job evidence."""

    async def _exercise(self, *, valid_receipt=True, stop_raises=False,
                        exact_abi=True, revoke_result=True):
        events=[]
        alive={"value":True}
        locked={"value":False}
        identity=SimpleNamespace(
            owner="root", namespace="isolated", token=17,
            session_id="00000000-0000-0000-0000-000000000001",
            instance_id="00000000-0000-0000-0000-000000000002",
            node_incarnation_id="00000000-0000-0000-0000-000000000003",
            source_sha256="a"*64, schema_sha256="b"*64)
        guard=SimpleNamespace(_identity=identity)
        def block_transfer():
            events.append("TRANSFER_BLOCKED")
            locked["value"]=True
        guard.block_transfer=block_transfer
        def revalidate(pg, *, identity, generation, backend_pid):
            self.assertTrue(locked["value"])
            events.append("LIVE_C_READ")
            if not alive["value"] or not valid_receipt:
                raise ValueError("live original backend unavailable")
            return dict(
                schema="lab-postgres-fence-revalidation.v1",
                scope="ISOLATED_LAB_ONLY",
                resource_id="grid-market-data-primary",
                owner=identity.owner, namespace=identity.namespace,
                generation=generation, token=identity.token,
                backend_pid=backend_pid,
                backend_start="2026-11-26T21:00:00+00:00",
                session_id=identity.session_id,
                instance_id=identity.instance_id,
                node_incarnation_id=identity.node_incarnation_id,
                source_sha256=identity.source_sha256,
                schema_sha256=identity.schema_sha256,
                db_backend_observed=True,
                db_fence_current_at_read=True,
                native_writer_admitted=False, trading_authorized=False)
        def exact_revoke(pg, *, owner, namespace, generation, token,
                         backend_pid, backend_start, timeout=120):
            events.append("C_EXACT_REVOKE")
            self.assertFalse(alive["value"])
            self.assertEqual((owner, namespace, generation, token, backend_pid,
                              backend_start),
                             ("root", "isolated", 9, 17, 4042,
                              "2026-11-26T21:00:00+00:00"))
            return revoke_result
        exact_revoke.__module__="unified_system.lab_pg_fence"
        def legacy_revoke(pg, *, generation, token):
            events.append("LEGACY_SQL_CALLED")
            return True
        legacy_revoke.__module__="unified_system.lab_pg_fence"
        canonical=SimpleNamespace(
            revoke_lab_fence=exact_revoke if exact_abi else legacy_revoke,
            revalidate_lab_fence=revalidate, LabAdmissionRejected=ValueError)
        class Executor:
            poisoned=False
            async def call(self, fn, timeout):
                events.append("OWNER_SQL_EXECUTOR")
                return fn()
        class StopLane:
            async def stop_owned(self, handle, *, timeout):
                events.append("A_STOP_ATTEMPT")
                alive["value"]=False
                if stop_raises:
                    raise OSError("uncertain OS stop")
            async def old_child_extinct(self, handle, *, timeout):
                return RootProcessObservation(
                    "unified.root-process-observation.v1", UNKNOWN,
                    handle, 4042, ["created", "image"], "UNKNOWN")
        revoker=object.__new__(LabWriterRevoker)
        revoker._once=False
        revoker._last=None
        revoker._guard=guard
        revoker._driver=object()
        revoker._handle="owned-op"
        revoker._authority=object()
        revoker._lease=object()
        revoker._pg=object()
        revoker._c=canonical
        revoker._generation=9
        revoker._token=17
        revoker._backend_pid=4042
        revoker._executor=Executor()
        revoker._stop_lane=StopLane()
        outcome=await revoker.revoke(blocking_timeout=2)
        return events,locked,outcome

    async def test_c_live_identity_is_frozen_before_original_os_stop(self):
        events,locked,outcome=await self._exercise()
        self.assertTrue(locked["value"])
        self.assertLess(events.index("TRANSFER_BLOCKED"),
                        events.index("LIVE_C_READ"))
        self.assertLess(events.index("LIVE_C_READ"),
                        events.index("A_STOP_ATTEMPT"))
        self.assertLess(events.index("A_STOP_ATTEMPT"),
                        events.index("C_EXACT_REVOKE"))
        self.assertEqual(events.count("C_EXACT_REVOKE"),1)
        self.assertEqual(outcome.result,"PARTIAL_DENIED")
        self.assertTrue(outcome.sql_fence_revoked)
        self.assertFalse(outcome.consul_released)
        self.assertFalse(outcome.native_admitted)

    async def test_missing_original_live_receipt_never_calls_exact_revoke(self):
        events,locked,outcome=await self._exercise(valid_receipt=False)
        self.assertTrue(locked["value"])
        self.assertIn("A_STOP_ATTEMPT",events)
        self.assertNotIn("C_EXACT_REVOKE",events)
        self.assertEqual(events.count("LIVE_C_READ"),1)
        self.assertFalse(outcome.sql_fence_revoked)
        self.assertEqual(outcome.result,"PARTIAL_DENIED")

    async def test_legacy_short_c_abi_never_uses_sql(self):
        events,locked,outcome=await self._exercise(exact_abi=False)
        self.assertTrue(locked["value"])
        self.assertIn("A_STOP_ATTEMPT",events)
        self.assertNotIn("LEGACY_SQL_CALLED",events)
        self.assertNotIn("LIVE_C_READ",events)
        self.assertFalse(outcome.sql_fence_revoked)

    async def test_uncertain_stop_can_never_prove_transfer(self):
        events,locked,outcome=await self._exercise(stop_raises=True)
        self.assertTrue(locked["value"])
        self.assertIn("C_EXACT_REVOKE",events)
        self.assertFalse(outcome.child_stopped)
        self.assertEqual(outcome.result,"PARTIAL_DENIED")

    async def test_unconfirmed_revoke_never_dispatches_post_revoke_read(self):
        events,locked,outcome=await self._exercise(revoke_result=False)
        self.assertTrue(locked["value"])
        self.assertIn("C_EXACT_REVOKE",events)
        self.assertEqual(events.count("LIVE_C_READ"),1)
        self.assertFalse(outcome.sql_fence_revoked)
        self.assertFalse(outcome.old_backend_rejected)
        self.assertFalse(outcome.consul_released)
        self.assertEqual(outcome.result,"PARTIAL_DENIED")



if __name__=="__main__":
    unittest.main()
