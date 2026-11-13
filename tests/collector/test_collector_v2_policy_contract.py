"""Independent V2 pure policy contracts; no filesystem/native/resource effects."""
import copy
import ctypes
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[2]
sys.path.insert(0,str(ROOT))
from unified_system import collector_service_plan_v2 as policy
from unified_system import collector_service_plan as frozen_v1


class CollectorV2StopPolicyTests(unittest.TestCase):
 def setUp(self):
  native=patch.object(ctypes,'WinDLL',side_effect=AssertionError('NO_NATIVE_API'),create=True)
  native.start();self.addCleanup(native.stop)
  # Arithmetic fixture values only, not measured shutdown/resource qualification.
  self.value=dict(transport='NSSM_CONSOLE_CTRL_C_V1',console=0,skip_methods=6,
   kill_process_tree=0,console_grace_ms=1000,owner_retire_seconds=5,
   actuation_timeout_seconds=10)

 def test_closed_numeric_policy_returns_independent_copy(self):
  result=policy.validate_collector_stop_policy(self.value)
  self.assertEqual(result,self.value);self.assertIsNot(result,self.value)
  result['console']=1;self.assertEqual(self.value['console'],0)

 def test_fixed_transport_and_console_shutdown_settings_are_not_widened(self):
  for field,value in [('transport','stdin'),('console',1),('skip_methods',14),
                      ('kill_process_tree',1),('owner_retire_seconds',6)]:
   changed=copy.deepcopy(self.value);changed[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):policy.validate_collector_stop_policy(changed)

 def test_bool_float_string_and_subclass_numeric_aliases_reject(self):
  class IntSubclass(int):pass
  class TextSubclass(str):pass
  for field,original in self.value.items():
   aliases=[TextSubclass(original)] if type(original) is str else [bool(original),float(original),str(original),IntSubclass(original)]
   for alias in aliases:
    changed=copy.deepcopy(self.value);changed[field]=alias
    with self.subTest(field=field,type=type(alias).__name__),self.assertRaises(ValueError):policy.validate_collector_stop_policy(changed)

 def test_timeout_poll_bound_and_retirement_margin_are_strict(self):
  for grace,timeout in [(0,10),(-1,10),(1000,0),(1000,61),(5000,10),(6000,10)]:
   changed=copy.deepcopy(self.value);changed.update(console_grace_ms=grace,actuation_timeout_seconds=timeout)
   with self.subTest(grace=grace,timeout=timeout),self.assertRaises(ValueError):policy.validate_collector_stop_policy(changed)
  changed=copy.deepcopy(self.value);changed.update(console_grace_ms=4999,actuation_timeout_seconds=10)
  self.assertEqual(policy.validate_collector_stop_policy(changed),changed)

 def test_missing_extra_and_nonbuiltin_keys_reject_before_equality(self):
  touched=[]
  class Key(str):
   def __eq__(self,other):touched.append('equality');return super().__eq__(other)
   __hash__=str.__hash__
  values=[]
  for key in self.value:
   changed=copy.deepcopy(self.value);changed.pop(key);values.append(changed)
  changed=copy.deepcopy(self.value);changed['extra']=0;values.append(changed)
  changed=copy.deepcopy(self.value);changed[Key('console')]=changed.pop('console');values.append(changed);touched.clear()
  for changed in values:
   with self.subTest(keys=list(changed)),self.assertRaises(ValueError):policy.validate_collector_stop_policy(changed)
  self.assertEqual(touched,[])

 def test_v1_compiled_source_cohort_constants_remain_frozen(self):
  self.assertEqual(policy.SCHEMA,'unified.owned-collector-stopped-service.v2')
  self.assertEqual(frozen_v1.SCHEMA,'unified.owned-collector-stopped-service.v1')
  self.assertEqual(frozen_v1.ENTRY_PIN,'3645dddef0ac6479edcc22ac61203db14fe802aa37641fa50ef2c1535f46f3cb')
  self.assertEqual(frozen_v1.BOOTSTRAP_PIN,'6d3be096e0df7d7633b14b55ec9d049e25b537bb530ba17f995c10a357b85005')
  self.assertEqual(frozen_v1.EXECUTOR_PIN,'ee0ec4d73e92a234396a37622e8080967105c497cf538f66e703021cbc3978bf')


if __name__=='__main__':unittest.main()
