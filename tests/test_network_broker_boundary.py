"""Closed broker policy tests with inert SCM; not native denial qualification."""
import unittest
from unified_system import service_actuator as actuator
from unified_system.contracts import seal
from tests import test_service_actuator as _fixtures

class NetworkBrokerBoundaryTests(unittest.TestCase):
 def setUp(self):
  # Compose the existing owned capsule/receipt fixture and fake SCM backend.
  self.fixture=_fixtures.ActuatorTests('test_missing_or_denied_phase_has_no_native_effect')
  self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
 def test_network_and_third_party_services_cannot_be_targeted_even_with_rehashed_plan(self):
  f=self.fixture
  for name in ('Tailscale','Dhcp','Dnscache','NlaSvc','WlanSvc','MpsSvc','ekrn','Reolink'):
   plan=f.plan();plan['service_name']=name
   plan['plan_sha256']=seal({key:value for key,value in plan.items()if key!='plan_sha256'})
   with self.subTest(service=name),self.assertRaises(actuator.ActuationBlocked):f.run_plan(plan)
  self.assertEqual(f.native.opens,0);self.assertEqual(f.native.handle.calls,[])
 def test_network_configuration_and_reset_are_not_broker_actions(self):
  f=self.fixture
  for action in ('SET_DNS','SET_DHCP','SET_GATEWAY','ADD_ROUTE','RESET_FIREWALL',
                 'TAILSCALE_UP','RESTART_ETHERNET','RESTART_WLAN','RESTART_NETWORK'):
   with self.subTest(action=action),self.assertRaises(actuator.ActuationBlocked):f.plan(action)
  self.assertEqual(f.native.opens,0);self.assertEqual(f.native.handle.calls,[])

if __name__=='__main__':unittest.main()
