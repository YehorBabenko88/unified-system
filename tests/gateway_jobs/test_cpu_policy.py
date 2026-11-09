"""Pure integer policy regressions, never resource enforcement qualification."""
import dataclasses
import unittest
from unified_system.gateway_worker import cpu_hard_cap_policy_v1

def policy(m=1000,**changes):
    args=dict(processor_groups=1,active_processor_count=16,process_affinity_mask=65535,
              system_affinity_mask=65535,already_reserved_millicores=0,
              parent_cpu_control='NONE',dfss_state='DISABLED')
    args.update(changes)
    return cpu_hard_cap_policy_v1(m,**args)

class CpuPolicy(unittest.TestCase):
    def test_floor_bound_and_quantum_across_single_group_sizes(self):
        for n in (1,2,3,8,16,32,64):
            for m in (1,7,100,999,1000,n*1000):
                with self.subTest(n=n,m=m):
                    result=policy(m,active_processor_count=n,process_affinity_mask=(1<<n)-1,system_affinity_mask=(1<<n)-1)
                    rate=10*m//n
                    if rate==0:self.assertEqual(result.reason,'BELOW_NATIVE_QUANTUM');continue
                    self.assertEqual(result.state,'CONVERTIBLE_NOT_ADMITTED')
                    self.assertEqual(result.cpu_rate,rate)
                    self.assertEqual(result.control_flags,5)
                    self.assertEqual(result.nominal_millicores_numerator,rate*n)
                    self.assertEqual(result.nominal_millicores_denominator,10)
                    self.assertLessEqual(rate*n,m*10)
                    self.assertLess(m*10-rate*n,n)
                    self.assertFalse(result.admission_supported)
                    self.assertFalse(result.behaviorally_qualified)
    def test_no_oversubscription_or_implicit_clamp(self):
        for m,reserved in ((16001,0),(1000,15001),(1,16000)):
            self.assertEqual(policy(m,already_reserved_millicores=reserved).reason,'CPU_CAPACITY_EXHAUSTED')
        self.assertEqual(policy(1000,already_reserved_millicores=15000).cpu_rate,625)
    def test_unsupported_topology_ancestry_and_dfss(self):
        cases=[dict(processor_groups=2),dict(process_affinity_mask=255),dict(system_affinity_mask=0),
               dict(active_processor_count=15),dict(process_affinity_mask=1<<64),
               dict(parent_cpu_control='UNKNOWN'),dict(parent_cpu_control='RATE_CONTROLLED'),
               dict(dfss_state='UNKNOWN'),dict(dfss_state='ENABLED')]
        for changes in cases:
            with self.subTest(changes=changes):
                result=policy(**changes)
                self.assertEqual(result.state,'UNSUPPORTED')
                self.assertIsNone(result.cpu_rate)
                self.assertFalse(result.admission_supported)
    def test_invalid_numeric_inputs_never_coerce(self):
        for m in (True,1.0,'1000',0,-1,None):
            self.assertEqual(policy(m).state,'UNSUPPORTED')
        for field in ('processor_groups','active_processor_count','process_affinity_mask','system_affinity_mask','already_reserved_millicores'):
            for value in (True,1.0,'1',-1,None):
                with self.subTest(field=field,value=value):self.assertEqual(policy(**{field:value}).state,'UNSUPPORTED')
    def test_frozen_result_is_not_a_dispatch_capability(self):
        result=policy()
        with self.assertRaises(dataclasses.FrozenInstanceError):result.admission_supported=True
        self.assertEqual(result.policy_version,'windows-hard-cap-logical-mcpu.v1')
