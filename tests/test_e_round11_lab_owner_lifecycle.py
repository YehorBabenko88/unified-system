"""Round11 E isolated unit tests: owner executor, ordered revoke, OS witness.

All database/Consul/ProcessDriver behavior below is stubbed. They are not
native PostgreSQL, Windows, Consul or end-to-end admission acceptance.
"""
import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.lab_owner_executor import LabOwnerExecutor
from unified_system.lab_writer_revoke import LabWriterRevoker
from unified_system.lab_root_child_witness import RootGridChildWitness
from unified_system.lab_root_stop_lane import LabRootStopLane
from unified_system.lab_process_extinction import RootProcessObservation, EXTINCT

class SimulatedCStaleFence(Exception):
    """Test-only stand-in for C's exported LabAdmissionRejected type."""



class SerialOwnerExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_is_off_reactor_thread(self):
        executor = LabOwnerExecutor()
        try:
            caller = threading.get_ident()
            worker = await executor.call(threading.get_ident, timeout=1)
            self.assertNotEqual(caller, worker)
            self.assertFalse(executor.poisoned)
        finally:
            executor.close()

    async def test_timeout_poison_prevents_second_sql(self):
        executor = LabOwnerExecutor()
        entered = threading.Event()
        release = threading.Event()
        touched = []
        def stuck():
            entered.set()
            release.wait(2)
            return "late commit outcome"
        try:
            task = asyncio.create_task(executor.call(stuck, timeout=.3))
            self.assertTrue(await asyncio.to_thread(entered.wait, .2))
            with self.assertRaises(asyncio.TimeoutError):
                await task
            self.assertTrue(executor.poisoned)
            with self.assertRaises(ResourceFenceBlocked):
                await executor.call(lambda: touched.append(1), timeout=1)
            self.assertEqual(touched, [])
        finally:
            release.set()
            executor.close()

    async def test_cancel_poison_prevents_retry(self):
        executor = LabOwnerExecutor()
        entered = threading.Event()
        release = threading.Event()
        def blocked():
            entered.set()
            release.wait(2)
        try:
            task = asyncio.create_task(executor.call(blocked, timeout=1))
            await asyncio.to_thread(entered.wait, .5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(executor.poisoned)
            with self.assertRaises(ResourceFenceBlocked):
                await executor.call(lambda: None)
        finally:
            release.set()
            executor.close()


class RevocationStateTests(unittest.IsolatedAsyncioTestCase):
    def make_revoker(self, *, sql_ok=True, sql_fault=False, stale_code=True):
        owner = object.__new__(LabWriterRevoker)
        events = []
        executor = LabOwnerExecutor()
        class Guard:
            _identity = SimpleNamespace(instance_id="test")
            def revoke(self):
                events.append("local")
        class Driver:
            def stop(self, handle):
                events.append("stop")
            def alive(self, handle):
                events.append("alive")
                return False
        class SQL:
            LabAdmissionRejected = SimulatedCStaleFence
            def revoke_lab_fence(self, pg, *, generation, token):
                events.append("sql")
                if sql_fault:
                    raise RuntimeError("database unavailable")
                return sql_ok
            def revalidate_lab_fence(self, pg, *, identity, generation, backend_pid):
                events.append("revalidate")
                if stale_code:
                    raise SimulatedCStaleFence("LAB_FENCE_REVALIDATION_DENIED")
                return {"db_fence_current_at_read": True}
        class Consul:
            async def release(self, lease):
                events.append("release")
            async def validate(self, lease):
                events.append("validate")
                return False
        owner._guard = Guard()
        owner._driver = Driver()
        owner._handle = "dummy"
        owner._authority = Consul()
        owner._lease = object()
        owner._pg = object()
        owner._c = SQL()
        owner._generation = 10
        owner._token = 100
        owner._backend_pid = 120
        owner._once = False
        owner._last = None
        owner._executor = executor
        class StopLane:
            async def stop_owned(self, handle, *, timeout):
                owner._driver.stop(handle)
            async def old_child_extinct(self, handle, *, timeout):
                owner._driver.alive(handle)
                return RootProcessObservation(
                    "unified.root-process-observation.v1", EXTINCT,
                    handle, 12345, ["creation", "exe"],
                    "TEST_LOCAL_EXIT_LISTENER_UNVERIFIED")
        owner._stop_lane = StopLane()
        return owner, events, executor

    async def test_local_revocations_cannot_forge_listener_extinction(self):
        owner, events, executor = self.make_revoker()
        try:
            result = await owner.revoke(blocking_timeout=1)
            self.assertEqual(result.result, "PARTIAL_DENIED")
            self.assertFalse(result.child_extinct)
            self.assertEqual(events,
                             ["local", "stop", "sql", "release",
                              "validate", "alive", "revalidate"])
            self.assertFalse(result.native_admitted)
            self.assertFalse(result.trading_authorized)
            self.assertIs(await owner.revoke(), result)
        finally:
            executor.close()

    async def test_sql_failure_preserves_partial_and_still_releases_consul(self):
        owner, events, executor = self.make_revoker(sql_fault=True)
        try:
            result = await owner.revoke(blocking_timeout=1)
            self.assertEqual(result.result, "PARTIAL_DENIED")
            self.assertFalse(result.sql_fence_revoked)
            self.assertFalse(result.old_backend_rejected)
            self.assertIn("release", events)
            self.assertIn("alive", events)
        finally:
            executor.close()

    async def test_poisoned_sql_lane_does_not_block_independent_os_stop(self):
        owner, events, executor = self.make_revoker()
        try:
            # No SQL is allowed after an ambiguous previous COMMIT.
            with executor._lock:
                executor._poisoned = True
            result = await owner.revoke(blocking_timeout=1)
            self.assertEqual(result.result, "PARTIAL_DENIED")
            self.assertTrue(result.child_stopped)
            self.assertFalse(result.child_extinct)
            self.assertFalse(result.sql_fence_revoked)
            self.assertIn("stop", events)
            self.assertIn("alive", events)
            self.assertNotIn("sql", events)
        finally:
            executor.close()

    async def test_c_false_return_cannot_claim_revoke(self):
        owner, _, executor = self.make_revoker(sql_ok=False)
        try:
            result = await owner.revoke(blocking_timeout=1)
            self.assertEqual(result.result, "PARTIAL_DENIED")
            self.assertFalse(result.sql_fence_revoked)
        finally:
            executor.close()

    async def test_ambiguous_c_error_is_not_old_backend_proof(self):
        owner, _, executor = self.make_revoker(stale_code=False)
        try:
            result = await owner.revoke(blocking_timeout=1)
            self.assertEqual(result.result, "PARTIAL_DENIED")
            self.assertFalse(result.old_backend_rejected)
        finally:
            executor.close()


class RootWitnessStructuralTests(unittest.TestCase):
    def test_caller_supplied_object_not_process_driver(self):
        with self.assertRaises(ResourceFenceBlocked):
            RootGridChildWitness(object(), "not-owned", release_id="x",
                                 source_commit="a" * 40)

    def test_actual_driver_process_identity_is_required(self):
        # No OS process started; reject a fake driver even with plausible
        # pid and source values rather than accepting caller booleans.
        fake = SimpleNamespace(children={"x": object()})
        with self.assertRaises(ResourceFenceBlocked):
            RootGridChildWitness(fake, "x", release_id="lab",
                                 source_commit="a" * 40)


if __name__ == "__main__":
    unittest.main()
