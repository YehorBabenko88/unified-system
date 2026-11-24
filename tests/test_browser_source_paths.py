"""Relative canonical proof paths cannot turn an unqualified source into a grant."""
import contextlib,importlib.util,io,json,os
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
class BrowserSourcePathTests(unittest.TestCase):
 def test_relative_source_arguments_do_not_bypass_or_break_qualification(self):
  root=Path(__file__).resolve().parents[1];script=root/'integration/verify_chromium.py'
  spec=importlib.util.spec_from_file_location('canonical_browser_gate',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as temporary:
   base=Path(temporary);(base/'evidence').mkdir();(base/'evidence/source.json').write_text(json.dumps({'qualification':'NOT_RUN'}))
   error=io.StringIO()
   with patch('os.getcwd',return_value=str(base)),contextlib.redirect_stderr(error):code=module.main(['--source-proof','evidence/source.json','--output','result'])
   self.assertNotEqual(code,0);self.assertIn('BROWSER_UNQUALIFIED:SOURCE_RUN_UNQUALIFIED',error.getvalue())
   report=json.loads((base/'result/evidence.json').read_bytes());self.assertEqual(report['status'],'BLOCKED');self.assertFalse(report['passed']);self.assertEqual(report['missing_proofs'][0],'SOURCE_RUN_UNQUALIFIED');self.assertEqual(report['release_status'],'NO_GO')
if __name__=='__main__':unittest.main()
