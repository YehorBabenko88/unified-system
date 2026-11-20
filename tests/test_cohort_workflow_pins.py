"""Actual workflow source SHAs must equal their active qualification cohort."""
import json,pathlib,re,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def checkout_pins(text):
 result={};blocks=re.split(r'(?m)^      - ',text)
 for block in blocks:
  if not block.startswith('uses: actions/checkout@'):continue
  repo=re.search(r'(?m)^          repository: ([A-Za-z0-9_/-]+)$',block)
  ref=re.search(r'(?m)^          ref: ([a-f0-9]{40})$',block)
  if repo and ref:
   if repo[1] in result:raise ValueError('duplicate source checkout')
   result[repo[1]]=ref[1]
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
  with self.assertRaises(ValueError):checkout_pins(workflow+chr(10)+block)
if __name__=='__main__':unittest.main()
