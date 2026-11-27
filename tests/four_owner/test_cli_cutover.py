"""No effects before canonical CLI admission; no retired CLI aliases."""
import contextlib,importlib.util,io,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
ENTRIES=('verify_owner_boundary.py','verify_market_analysis_chain.py','verify_result_handoff.py','verify_result_provenance.py')
def load(name):
 spec=importlib.util.spec_from_file_location('canonical_'+name[:-3],ROOT/'scripts'/name);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class CanonicalCliTests(unittest.TestCase):
 def test_retired_positional_cli_is_refused_before_any_output(self):
  for name in ENTRIES:
   with self.subTest(name=name),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as refused:load(name).main(['upstream'])
   self.assertEqual(refused.exception.code,2)
 def test_valid_local_cli_cannot_impersonate_hosted_qualification(self):
  import os
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{},clear=True):
   out=pathlib.Path(tmp)/'not-created'
   for name in ENTRIES:
    with self.subTest(name=name),self.assertRaisesRegex(ValueError,'HOSTED_SOURCE_QUALIFICATION_ONLY'):
     load(name).main(['--root-head','a'*40,'--market-data',tmp,'--math',tmp,'--terminan',tmp,'--out',str(out)])
    self.assertFalse(out.exists())
 def test_no_old_entrypoint_remains_and_every_consumer_uses_canonical_suite(self):
  for name in ('verify_five_boundary.py','verify_three_module_chain.py','verify_handoff_roundtrip.py','verify_provenance_handoff.py'):self.assertFalse((ROOT/'scripts'/name).exists())
  for file,suite in (('market-analysis-chain.yml','chain'),('result-handoff.yml','handoff'),('result-provenance.yml','provenance')):
   text=(ROOT/'.github/workflows'/file).read_text();self.assertIn('uses: ./.github/workflows/owner-source-suite.yml',text);self.assertIn('suite: '+suite,text);self.assertNotIn('upstream',text)
  self.assertIn('verify_owner_boundary.py',(ROOT/'.github/workflows/owner-boundary.yml').read_text())
if __name__=='__main__':unittest.main()
