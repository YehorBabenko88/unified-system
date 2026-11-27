"""Artifact-path calibration only; never execute Consul or source runners."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MuxArtifactAllowlistTests(unittest.TestCase):
 def test_only_three_reviewed_json_reports_are_uploaded(self):
  raw=(ROOT/'.github/workflows/agent2-control-mux-runtime.yml').read_text()
  section=raw[raw.index('      - uses: actions/upload-artifact@'):]
  lines=section.splitlines();start=next(i for i,line in enumerate(lines) if line.strip()=='path: |')
  paths=[]
  for line in lines[start+1:]:
   if line.strip() and len(line)-len(line.lstrip())<=10:break
   if line.strip():paths.append(line.strip())
  self.assertEqual(paths,['.lab-evidence/source-bound.json','.lab-evidence/source-guard-controls.json','.lab-evidence/reconciliation-review2-models.json'])
  self.assertIn('include-hidden-files: true',section)
  self.assertIn('if-no-files-found: error',section)
  self.assertNotIn('*',''.join(paths));self.assertNotIn('.log',''.join(paths))
 def test_existing_worker_roles_and_source_pins_are_unchanged(self):
  raw=(ROOT/'tests/control_mux/source_runner.py').read_text()
  self.assertIn("assert result.wasSuccessful() and not result.skipped and set(executed)==UNITS",raw)
  self.assertIn("assert real['events']==EVENTS and real['result']=='PASS' and real['owned_processes_stopped'] is True",raw)
  self.assertIn("grid,'58cfe0f51bc05bb0ee2ed09368a9b64679358c63'",raw)
  self.assertIn("production='NO_GO'",raw)
if __name__=='__main__':unittest.main()
