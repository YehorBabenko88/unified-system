"""UNEXECUTED CONTRACT TEST SOURCE; requires approved future helper+print AST adapter.
No projector implementation or target execution is provided here. Binding adapter
must select actual candidate ASTs, validate held pin, run final print into memory,
and return (public_bytes, private_record_after). Missing binding is setup ERROR.
"""
import unittest,json,hashlib,copy
class SetupStageError(RuntimeError):pass
ACTUAL_PROJECT_AND_PRINT=None
class PublicSummaryV1Contract(unittest.TestCase):
 def run_actual(self,record,written):
  if ACTUAL_PROJECT_AND_PRINT is None:raise SetupStageError('ACTUAL_APPROVED_AST_BINDING_PENDING')
  original=copy.deepcopy(record)
  output,after=ACTUAL_PROJECT_AND_PRINT(record,written)
  if type(output) is not bytes or after!=original or record!=original:raise SetupStageError('ACTUAL_SERIALIZER_OR_PRIVATE_PRESERVATION')
  self.assertLessEqual(len(output),8192);self.assertTrue(output.endswith(b'\n'))
  p=json.loads(output)
  self.assertEqual(set(p),{'schema','result','runtime_admission','diagnostic_count','error_count','event_limit','event_overflow','details_omitted','private_evidence_status','private_evidence_sha256'})
  self.assertEqual(p['schema'],'math572.compile7.public-summary.v1');self.assertIs(p['runtime_admission'],False);self.assertEqual(p['event_limit'],256)
  self.assertIn(p['result'],('DENY','EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS'))
  for key in ('diagnostic_count','error_count'):
   self.assertIs(type(p[key]),int);self.assertGreaterEqual(p[key],0);self.assertLessEqual(p[key],256)
  return p,output
 def fixture(self,n,errors=()):
  return {'result':'EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS','closed_diagnostics':[{'source':3,'line':1,'column':1,'code':'CS0246','symbol':'OwnedPrivateDesktop'} for _ in range(n)],'errors':list(errors)}
 def test_empty_small_and_original_174_records(self):
  for n in (0,1,174):
   with self.subTest(n=n):
    r=self.fixture(n);written=(json.dumps(r,sort_keys=True)+'\n').encode();p,_=self.run_actual(r,written)
    self.assertEqual(p['diagnostic_count'],n);self.assertEqual(p['error_count'],0);self.assertEqual(p['details_omitted'],bool(n));self.assertIs(p['event_overflow'],False)
    self.assertEqual(p['private_evidence_status'],'AVAILABLE');self.assertEqual(p['private_evidence_sha256'],hashlib.sha256(written).hexdigest())
 def test_arbitrary_paths_errors_and_symbols_stay_private(self):
  secret='PRIVATE_PATH_AND_ERROR_SECRET';r=self.fixture(1,[secret]);r['closed_diagnostics'][0]['symbol']=secret
  p,out=self.run_actual(r,json.dumps(r).encode());self.assertNotIn(secret.encode(),out);self.assertEqual(p['error_count'],1);self.assertTrue(p['details_omitted'])
 def test_256_257_event_boundary_honest_capping_and_deny(self):
  for key in ('closed_diagnostics','errors'):
   for n in (256,257):
    with self.subTest(key=key,n=n):
     r=self.fixture(n) if key=='closed_diagnostics' else self.fixture(0,['PRIVATE']*n)
     p,_=self.run_actual(r,json.dumps(r).encode());field='diagnostic_count' if key=='closed_diagnostics' else 'error_count'
     self.assertEqual(p[field],min(n,256));self.assertEqual(p['event_overflow'],n>256)
     if n>256:self.assertEqual(p['result'],'DENY')
 def test_failed_private_receipt_is_deny_without_fabricated_digest(self):
  p,_=self.run_actual(self.fixture(1),None);self.assertEqual(p['result'],'DENY');self.assertEqual(p['private_evidence_status'],'UNAVAILABLE');self.assertIsNone(p['private_evidence_sha256'])
