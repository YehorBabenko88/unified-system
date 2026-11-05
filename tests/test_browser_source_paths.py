"""CLI-relative source paths must reach the same strict source fence on Windows."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class BrowserSourcePathTests(unittest.TestCase):
    def test_relative_source_arguments_do_not_bypass_or_break_qualification(self):
        script=Path(__file__).resolve().parents[1]/'integration/verify_chromium.py'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'source').mkdir();(root/'evidence').mkdir()
            evidence=root/'evidence/evidence.json'
            evidence.write_text(json.dumps({'qualification':'NOT_RUN'}))
            command=[sys.executable,'-B',str(script),'--output','evidence']
            for name in ('terminan','math','grid','strattester'):command+=['--'+name,'source']
            result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('BROWSER_UNQUALIFIED:SOURCE_RUN_UNQUALIFIED',result.stderr)
            self.assertEqual(json.loads(evidence.read_text())['browser'],{'qualification':'UNQUALIFIED','reason':'SOURCE_RUN_UNQUALIFIED'})


if __name__=='__main__':unittest.main()
