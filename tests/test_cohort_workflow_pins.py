"""Actual workflow source SHAs must equal their active qualification cohort."""
import json,pathlib,re,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def checkout_pins(text):
 result={};blocks=re.split(r'(?m)^      - ',text)
 for block in blocks:
  first=block.splitlines()[0] if block.splitlines() else ''
  rows=re.findall(r'(?m)^          repository: (.+)$',block)
  if not rows:continue # Root checkout has no repository override.
  if not re.fullmatch(r"uses: ['\"]?actions/checkout@[A-Za-z0-9_.-]+['\"]?",first):raise ValueError('unrecognized source checkout action')
  if len(rows)!=1 or not re.fullmatch(r'YehorBabenko88/(?:strattester|math|Terminan)',rows[0]):raise ValueError('closed canonical SDK repository required')
  refs=re.findall(r'(?m)^          ref: (.+)$',block)
  if len(refs)!=1 or not re.fullmatch(r'[a-f0-9]{40}',refs[0]):raise ValueError('literal committed SDK source required')
  if rows[0] in result:raise ValueError('duplicate source checkout')
  result[rows[0]]=refs[0]
 return result
class CohortWorkflowPinsTests(unittest.TestCase):
 def check(self,workflow,cohort):
  expected={v['repository']:v['commit'] for k,v in cohort['sources'].items() if k!='unified_system'}
  self.assertEqual(checkout_pins(workflow),expected)
 def test_actual_causal_workflow_matches_its_active_cohort(self):
  self.check((ROOT/'.github/workflows/paper-causal.yml').read_text(),json.loads((ROOT/'docs/qualification/offline-causal-20261120/cohort.json').read_bytes()))
 def test_actual_common_workflow_matches_its_active_cohort(self):
  self.check((ROOT/'.github/workflows/four-source-integration.yml').read_text(),json.loads((ROOT/'integration/four_owner/cohort.json').read_bytes()))
 def test_stale_and_duplicate_source_checkouts_are_not_silently_accepted(self):
  workflow=(ROOT/'.github/workflows/paper-causal.yml').read_text();cohort=json.loads((ROOT/'docs/qualification/offline-causal-20261120/cohort.json').read_bytes())
  pin=cohort['sources']['math']['commit']
  with self.assertRaises(AssertionError):self.check(workflow.replace(pin,'0'*40),cohort)
  block="      - uses: actions/checkout@fixed\n        with:\n          repository: YehorBabenko88/math\n          ref: "+pin+chr(10)
  for duplicate in (block,block.replace(pin,'${{ github.sha }}'),block.replace('ref: '+pin,'ref: main'),block.replace('ref: '+pin,'ref: '+pin+chr(10)+'          ref: '+pin)):
   with self.assertRaises(ValueError):checkout_pins(workflow+chr(10)+duplicate)
if __name__=='__main__':unittest.main()
