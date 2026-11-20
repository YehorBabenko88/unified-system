import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ProbeTests(unittest.TestCase):
 def api(self):
  p=ROOT/'tests/preparation_crash_probe.py';self.assertTrue(p.is_file());s=importlib.util.spec_from_file_location('inert_crash_probe',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def test_flags_and_original_crash_hook_are_preserved(self):
  m=self.api();c=m.build_command('python',ROOT,Path('db'),{},Path('phase'),Path('fresh'))
  self.assertEqual(c[1:5],['-I','-S','-B','-X']);self.assertIn('os._exit(23)',c[7]);compile(c[7],'<inert>','exec')
 def test_phase_projection_never_echoes_untrusted_data(self):
  m=self.api()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'phase';self.assertEqual(m.phase_summary(p),'ENTRY_NOT_OBSERVED')
   p.write_text('ENTRY\nIMPORT_BEGIN\n');self.assertEqual(m.phase_summary(p),'ENTRY,IMPORT_BEGIN')
   for text in ('SECRET_SENTINEL', 'ENTRY\n'*1000):
    p.write_text(text);self.assertEqual(m.phase_summary(p),'INVALID_PHASE_RECORD')
if __name__=='__main__':unittest.main()
