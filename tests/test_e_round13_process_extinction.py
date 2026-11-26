"""E ROUND13 tri-state OS observation negative unit coverage.

A real subprocess is launched only by separate authorized hosted LAB tests.
This file tests observer refusal against synthetic retained Popen fixtures.
Tests authored here; no claim of execution without actual run logs.
"""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from unified_system.lab_process_extinction import (
    observe_owned_process_extinction, RootProcessObservation,
    UNKNOWN, EXTINCT, STILL_ALIVE,
)
from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.runtime_process import ProcessDriver


class TriStateProcessTests(unittest.TestCase):
    def test_missing_owned_driver_rejected(self):
        with self.assertRaises(ResourceFenceBlocked):
            observe_owned_process_extinction(SimpleNamespace(children={}), "x")

    def test_states_are_exact_and_never_boolean(self):
        self.assertEqual({EXTINCT, STILL_ALIVE, UNKNOWN},
                         {"EXTINCT", "STILL_ALIVE", "UNKNOWN"})
        with self.assertRaises(ResourceFenceBlocked):
            RootProcessObservation("unified.root-process-observation.v1",
                "False", "op", 1234, ["stamp","image"],"BAD")

    def test_retained_process_exit_does_not_attest_listener(self):
        obj=RootProcessObservation("unified.root-process-observation.v1",
                                  EXTINCT,"op",1234,
                                  ["stamp","image"],"RETAINED_HANDLE_EXITED",
                                  listener_owner_verified=False)
        self.assertEqual(obj.state,EXTINCT)
        self.assertFalse(obj.listener_owner_verified)
        self.assertFalse(obj.native_admitted)

    def test_access_denied_cannot_be_mapped_to_extinct(self):
        # Type of Popen and actual OS handle are required by observer.
        fake=SimpleNamespace(pid=1234,poll=lambda:None)
        driver=object.__new__(ProcessDriver)
        driver.children={"x":fake}
        with patch.object(ProcessDriver,"_load",
                          return_value={"pid":1234,"created":["stamp","image"]}):
            with self.assertRaises(ResourceFenceBlocked):
                observe_owned_process_extinction(driver,"x")


if __name__=="__main__":
    unittest.main()
