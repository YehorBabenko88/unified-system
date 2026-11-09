import sys,unittest,time,json
from unittest.mock import patch
sys.path.insert(0,'.')
import tests.test_lan_transport as t
import unified_system.lan_transport as lan
names=['test_active_control_heartbeats_keep_idle_data_channel_healthy','test_expired_idle_peer_without_activity_still_closes_real_tls']
original=lan.Connection._heartbeat
def delayed(self):
 time.sleep(.6)
 return original(self)
suite=unittest.TestSuite(t.TLSIsolationTests(n) for n in names)
with patch.object(lan.Connection,'_heartbeat',delayed):
 result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==2 and result.wasSuccessful() and not result.skipped
print(json.dumps(dict(unique_cases=2,heartbeat_start_delay_seconds=.6,scope='OWN_LOOPBACK_TLS_CONTROLLED_EXPERIMENT_NOT_HOSTED_RCA')))
