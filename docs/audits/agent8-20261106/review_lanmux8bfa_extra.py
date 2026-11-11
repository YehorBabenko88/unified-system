import pathlib,subprocess,os
r=pathlib.Path.cwd();repo=r/'work/review-lanmux-8bfa';out=r/'outputs/phase68'
s='''import sys,pathlib,unittest
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests')]
from test_lan_transport import TLSIsolationTests
from unified_system.lan_transport import LanTransport,PeerRegistry,TransportError
from unified_system.lan_mux_channel import LanMuxChannel,MuxError
from unittest.mock import patch
class Additional(unittest.TestCase):
 def test_native_factories_closed_before_side_effects(self):
  with patch('socket.socket') as opened:
   with self.assertRaisesRegex(TransportError,'NATIVE_RUNTIME_ADMISSION_REQUIRED'):LanTransport.runtime()
   with self.assertRaisesRegex(MuxError,'NATIVE_MUX_ADMISSION_REQUIRED'):LanMuxChannel.runtime()
   opened.assert_not_called()
 def test_self_connect_refused_before_socket(self):
  TLSIsolationTests.setUpClass()
  fixture=TLSIsolationTests('test_isolation_rejects_nonloopback_even_if_registry_admits_it');fixture.setUp()
  try:
   transport=fixture.transport('PC1',PeerRegistry.from_document(fixture.document()))
   with patch('socket.socket') as opened:
    with self.assertRaisesRegex(TransportError,'CONNECTING'):transport.connect('PC1')
    opened.assert_not_called()
   self.assertEqual(transport.connections,{});self.assertEqual(transport.connecting,set());self.assertEqual(transport.memory.used,0)
  finally:fixture.tearDown();TLSIsolationTests.doClassCleanups()
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Additional));assert result.wasSuccessful() and result.testsRun==2 and not result.skipped
'''
(out/'extra-executed.py').write_text(s,encoding='utf-8');p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-B','-c',s],cwd=repo,capture_output=True,timeout=60);(out/'extra.stdout.log').write_bytes(p.stdout);(out/'extra.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace');print('2 independent native/self-connect probes PASS')
