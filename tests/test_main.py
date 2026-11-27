import contextlib,io,json,pathlib,runpy,tempfile,unittest
from unittest.mock import patch
from tests.test_runtime_cli import fixture

class MainEntryTests(unittest.TestCase):
 def test_prepare_validates_four_owners_without_constructing_runtime(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp).resolve();config=fixture(root);path=root/'runtime.json';path.write_text(json.dumps(config))
   output=io.StringIO()
   with patch('sys.argv',['unified_system','--config',str(path)]),patch('unified_system.runtime_cli.make_runtime',side_effect=AssertionError('NO RUNTIME')),contextlib.redirect_stdout(output):
    with self.assertRaises(SystemExit) as result:runpy.run_module('unified_system',run_name='__main__')
   self.assertEqual(result.exception.code,0);self.assertIn('modules=4',output.getvalue())
   self.assertFalse((root/'state').exists())
 def test_obsolete_demo_command_is_rejected(self):
  with patch('sys.argv',['unified_system','--demo']),contextlib.redirect_stderr(io.StringIO()),patch('unified_system.runtime_cli.make_runtime',side_effect=AssertionError('NO RUNTIME')):
   with self.assertRaises(SystemExit) as result:runpy.run_module('unified_system',run_name='__main__')
  self.assertEqual(result.exception.code,2)
