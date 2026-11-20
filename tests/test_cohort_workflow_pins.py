"""Actual workflow source SHAs must equal their active qualification cohort."""
import json,pathlib,re,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def checkout_pins(text):
 result={}
 for section in re.split(r'(?m)^  [A-Za-z0-9_-]+:[ \t]*$',text):
  root_checkouts=0;saw_checkout=False;blocks=re.split(r'(?m)^      - ',section)
  for block in blocks:
   first=block.splitlines()[0] if block.splitlines() else ''
   if first.startswith(('*','&','!','{','[')) or re.search(r'(?m)^\s*<<\s*:',block):raise ValueError('checkout metadata aliases/merges unsupported')
   uses=re.findall(r"(?m)^(?:uses: |        uses: )(.+)$",block)
   if re.search(r"(?m)^\s*['\"]?uses['\"]?\s*:",block) and len(uses)!=1:raise ValueError('unsupported step action declaration')
   if len(uses)>1 or any(not re.fullmatch(r"['\"]?[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[A-Za-z0-9_.-]+['\"]?",value) for value in uses):raise ValueError('one explicit literal step action required')
   matches=[value.strip("'\"") for value in uses if 'actions/checkout@' in value]
   if not matches:
    if 'actions/checkout@' in block:raise ValueError('unsupported checkout step declaration')
    continue
   if len(matches)!=1:raise ValueError('one checkout action required')
   saw_checkout=True
   rows=re.findall(r'(?m)^          repository: (.+)$',block)
   declared_repository=bool(re.search(r'\brepository\b',block))
   if not declared_repository:
    root_checkouts+=1
    if root_checkouts!=1 or re.search(r'(?m)^\s*path\s*:',block):raise ValueError('one default-root checkout required')
    refs=re.findall(r'(?m)^          ref: (.+)$',block)
    if refs!=['\x24{{ github.event.pull_request.head.sha || github.sha }}']:raise ValueError('event HEAD Root checkout required')
    continue
   if len(rows)!=1 or not re.fullmatch(r'YehorBabenko88/(?:strattester|math|Terminan)',rows[0]):raise ValueError('one literal canonical SDK repository required')
   refs=re.findall(r'(?m)^          ref: (.+)$',block)
   if len(refs)!=1 or not re.fullmatch(r'[a-f0-9]{40}',refs[0]):raise ValueError('literal committed SDK source required')
   if rows[0] in result:raise ValueError('duplicate source checkout')
   paths=re.findall(r'(?m)^          path: (.+)$',block)
   expected={ 'YehorBabenko88/strattester':'.source/market_data','YehorBabenko88/math':'.source/math','YehorBabenko88/Terminan':'.source/terminan'}
   if paths!=[expected[rows[0]]]:raise ValueError('canonical SDK checkout destination required')
   result[rows[0]]=refs[0]
  if saw_checkout and root_checkouts!=1:raise ValueError('one Root checkout per job required')
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
  for duplicate in (block,block.replace(pin,'${{ github.sha }}'),block.replace('ref: '+pin,'ref: main'),block.replace('ref: '+pin,'ref: '+pin+chr(10)+'          ref: '+pin),block.replace('repository: YehorBabenko88/math','repository:'),block.replace('repository: YehorBabenko88/math'+chr(10),'')):
   with self.assertRaises(ValueError):checkout_pins(workflow+chr(10)+duplicate)
 def test_named_extra_sdk_and_root_checkouts_are_refused(self):
  workflow=(ROOT/'.github/workflows/paper-causal.yml').read_text()
  for block in ("      - name: Additional checkout\n        uses: actions/checkout@fixed\n        with:\n          repository: YehorBabenko88/math\n          ref: ${{ github.sha }}\n          path: .source/math\n","      - name: Additional checkout\n        uses: actions/checkout@fixed\n        with:\n          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n          path: .source/math\n"):
   with self.assertRaises(ValueError):checkout_pins(workflow+chr(10)+block)
if __name__=='__main__':unittest.main()
