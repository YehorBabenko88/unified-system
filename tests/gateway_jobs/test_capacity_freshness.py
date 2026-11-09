"""Local timestamp-span arithmetic; never remote capacity/admission proof."""
import dataclasses
import unittest
from unittest.mock import patch
from unified_system import gateway_worker as worker

INC='11111111-1111-4111-8111-111111111111'
OTHER='22222222-2222-4222-8222-222222222222'
def freshness(**changes):
    args=dict(observed_start_ns=100,observed_end_ns=150,now_ns=199,
              observation_incarnation_id=INC,expected_incarnation_id=INC,max_age_ns=100)
    args.update(changes);return worker.capacity_freshness_v1(**args)

class CapacityFreshness(unittest.TestCase):
    def test_query_duration_counts_and_exact_boundary_is_stale(self):
        result=freshness();self.assertEqual(result.state,'FRESH_LOCAL_DATA_NOT_ADMISSION')
        self.assertEqual(result.age_ns,99)
        self.assertEqual(freshness(now_ns=200).state,'STALE')
        self.assertEqual(freshness(observed_start_ns=0,observed_end_ns=199,now_ns=200).state,'STALE')
    def test_no_operational_limit_is_invented(self):
        for limit in (None,0,-1,True,100.0,'100'):
            with self.subTest(limit=limit):self.assertEqual(freshness(max_age_ns=limit).state,'UNSUPPORTED')
    def test_foreign_restart_scope_and_clock_rollback_are_unusable(self):
        self.assertEqual(freshness(observation_incarnation_id=OTHER).state,'FOREIGN_CLOCK_SCOPE')
        for changes in (dict(observed_start_ns=151),dict(now_ns=149),dict(observed_start_ns=-1),
                        dict(now_ns=True),dict(observed_end_ns=150.0),dict(expected_incarnation_id='host-name')):
            with self.subTest(changes=changes):self.assertNotEqual(freshness(**changes).state,'FRESH_LOCAL_DATA_NOT_ADMISSION')
    def test_result_cannot_be_promoted_to_admission_or_reservation(self):
        result=freshness();self.assertFalse(result.admission_supported);self.assertFalse(result.resources_reserved)
        with self.assertRaises(dataclasses.FrozenInstanceError):result.admission_supported=True
    def test_host_query_records_conservative_actual_call_span(self):
        class Kernel:
            def K32GetPerformanceInfo(self,pointer,size):
                info=pointer._obj;info.page_size=4096;info.commit_total=1;info.commit_limit=4;info.physical_available=2
                return True
        with patch.object(worker.time,'monotonic_ns',side_effect=[100,200]):
            value=worker._attempt_host(Kernel())
        self.assertEqual(value['observation_started_monotonic_ns'],'100')
        self.assertEqual(value['observation_completed_monotonic_ns'],'200')
        self.assertEqual(value['query_duration_ns'],'100')
        self.assertEqual(value['observation_incarnation_id'],worker._PROCESS_INCARNATION)
        self.assertEqual(value['monotonic_ns'],'200')
        self.assertEqual(value['monotonic_ns_semantics'],'QUERY_COMPLETION_DIAGNOSTIC_ONLY_NOT_FRESHNESS')
        self.assertFalse(value['qualified_for_native_admission'])
