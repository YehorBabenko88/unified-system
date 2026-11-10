import pathlib,ast,unittest,sys,subprocess
root=pathlib.Path.cwd();old=sys.argv[1]=='OLD';name='docs/intelligence/identity/run_qualification.py'
raw=subprocess.check_output(['git','--no-replace-objects','cat-file','blob','dd4ef015d9ed20065ccdc2c563e80046015d9193:'+name]) if old else (root/name).read_bytes()
tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('EXPECTED_TEST_NAMES','EXPECTED_STRICT_TEST_ID') for t in n.targets) or isinstance(n,ast.FunctionDef) and n.name=='validate_test_ids'];ns={'unittest':unittest};exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),ns)
prior=['test_gateway_identity.GatewayIdentityTests.'+n for n in ns['EXPECTED_TEST_NAMES']];strict='test_gateway_identity.StrictTLSFixtureTests.test_generated_chain_handshakes_with_explicit_strict_verification';expected=prior+[strict];assert len(prior)==24 and len(set(expected))==25
class IdentityContractTests(unittest.TestCase):
 def suite(self,ids):
  result=[]
  for value in ids:
   item=unittest.FunctionTestCase(lambda:None);item.id=lambda value=value:value;result.append(item)
  return unittest.TestSuite(result)
 def test_exact_25_accepts(self):ns['validate_test_ids'](self.suite(expected))
 def test_original24_without_strict_rejected(self):
  with self.assertRaises(AssertionError):ns['validate_test_ids'](self.suite(prior))
 def test_missing_prior_rejected(self):
  with self.assertRaises(AssertionError):ns['validate_test_ids'](self.suite(expected[1:]))
 def test_duplicate_rejected(self):
  with self.assertRaises(AssertionError):ns['validate_test_ids'](self.suite(expected[:-1]+[expected[0]]))
 def test_extra_rejected(self):
  with self.assertRaises(AssertionError):ns['validate_test_ids'](self.suite(expected+['UNAPPROVED_EXTRA']))
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IdentityContractTests));sys.exit(not r.wasSuccessful())