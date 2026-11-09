"""Counter metadata is DATA; zero delta is never a physical-time guarantee."""
import hashlib
import json
import unittest
from clock_source_prerequisites import observe_clock_source_v1, counter_span_v1

INC='11111111-1111-4111-8111-111111111111'
OTHER='22222222-2222-4222-8222-222222222222'
def source(**changes):
    value=dict(runtime_source_binding_sha256='0'*64,observation_incarnation_id=INC,clock_name='monotonic')
    value.update(changes);return value

class ClockSourcePrerequisites(unittest.TestCase):
    def test_zero_delta_never_means_instant_query_or_physical_age(self):
        value=counter_span_v1(100,100,start_source=source(),end_source=source())
        self.assertEqual(value.state,'COUNTER_DELTA_ONLY_NOT_PHYSICAL_TIME')
        self.assertEqual(value.counter_delta_ns,0)
        self.assertIsNone(value.physical_elapsed_upper_bound_ns)
        self.assertIsNone(value.measurement_age_upper_bound_ns)
        self.assertIsNone(value.operational_max_age_ns)
        self.assertFalse(value.admission_supported)
    def test_cross_runtime_incarnation_or_clock_is_refused(self):
        for end in (source(runtime_source_binding_sha256='1'*64),source(observation_incarnation_id=OTHER),source(clock_name='perf_counter')):
            self.assertEqual(counter_span_v1(0,1,start_source=source(),end_source=end).state,'FOREIGN_CLOCK_SOURCE')
    def test_invalid_or_rollback_endpoints_and_scope_are_refused(self):
        for start,end in ((True,1),(0,1.0),(-1,0),(2,1)):
            self.assertNotEqual(counter_span_v1(start,end,start_source=source(),end_source=source()).state,'COUNTER_DELTA_ONLY_NOT_PHYSICAL_TIME')
        for malformed in (source(clock_name='utc'),source(observation_incarnation_id='host'),source(extra=True)):
            self.assertEqual(counter_span_v1(0,1,start_source=malformed,end_source=malformed).state,'UNSUPPORTED')
    def test_metadata_binding_is_canonical_observed_data_not_permission(self):
        value=observe_clock_source_v1()
        canonical=json.dumps(dict(runtime=value['runtime'],clocks=value['clocks']),sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        self.assertEqual(value['runtime_source_binding_sha256'],hashlib.sha256(canonical).hexdigest())
        self.assertEqual(value['admitted_fields'],[])
        self.assertIsNone(value['quantization_uncertainty_ns'])
        self.assertFalse(value['admission_supported'])
        self.assertEqual(value['runtime']['binding_status'],'OBSERVED_FILES_NOT_LOADED_IMAGE_CUSTODY')
