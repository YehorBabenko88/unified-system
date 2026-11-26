"""E/A ROUND19 read-only observation contract negatives (non-native).

This file intentionally cannot issue a Root extinction or recovery grant.
"""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.lab_process_extinction import (
    observe_owned_process_extinction, UNKNOWN, EXTINCT,
)
from unified_system.runtime_process import ProcessDriver, _OwnedWindowsChild


class EOwnedJobObservationTests(unittest.TestCase):
    @staticmethod
    def _driver():
        driver=object.__new__(ProcessDriver)
        driver.children={}
        return driver

    def test_foreign_duck_type_is_rejected(self):
        driver=self._driver()
        child=SimpleNamespace(pid=4242, poll=lambda: 0)
        driver.children["original"]=child
        driver._load=lambda _: dict(pid=4242,created=[1,2],state="STOPPED")
        with self.assertRaises(ResourceFenceBlocked):
            observe_owned_process_extinction(driver,"original")

    def test_windows_original_handle_missing_is_rejected(self):
        driver=self._driver()
        child=object.__new__(_OwnedWindowsChild)
        child.pid=4242
        child._handle=None
        child._job=SimpleNamespace(_handle=99,_assigned=True)
        driver.children["original"]=child
        driver._load=lambda _: dict(pid=4242,created=[1,2],state="STOPPED")
        with self.assertRaises(ResourceFenceBlocked):
            observe_owned_process_extinction(driver,"original")

    def test_windows_original_job_assignment_missing_is_rejected(self):
        driver=self._driver()
        child=object.__new__(_OwnedWindowsChild)
        child.pid=4242
        child._handle=88
        child._job=SimpleNamespace(_handle=99,_assigned=False)
        driver.children["original"]=child
        driver._load=lambda _: dict(pid=4242,created=[1,2],state="STOPPED")
        with self.assertRaises(ResourceFenceBlocked):
            observe_owned_process_extinction(driver,"original")

    def test_canonical_a_extinct_stays_non_native_observation(self):
        driver=self._driver()
        child=object.__new__(_OwnedWindowsChild)
        child.pid=4242
        child._handle=88
        child._job=SimpleNamespace(_handle=99,_assigned=True)
        driver.children["original"]=child
        driver._load=lambda _: dict(pid=4242,created=[1,2],state="STOPPED")
        driver.owned_process_state=lambda _: EXTINCT
        result=observe_owned_process_extinction(driver,"original")
        self.assertEqual(result.state,EXTINCT)
        self.assertFalse(result.listener_owner_verified)
        self.assertFalse(result.native_admitted)
        self.assertEqual(result.reason,"A_RETAINED_HANDLE_EXITED_LISTENER_UNVERIFIED")


if __name__=="__main__":
    unittest.main()
