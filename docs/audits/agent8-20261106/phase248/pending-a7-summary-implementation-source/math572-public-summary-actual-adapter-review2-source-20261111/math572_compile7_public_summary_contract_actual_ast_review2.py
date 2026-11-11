"""UNEXECUTED CONTRACT TEST SOURCE; requires approved future helper+print AST adapter.
No projector implementation or target execution is provided here. Binding adapter
must select actual candidate ASTs, validate held pin, run final print into memory,
and return (public_bytes, private_record_after). Missing binding is setup ERROR.
"""
import unittest,json,hashlib,copy,ast,pathlib,types,re
class SetupStageError(RuntimeError):pass
ACTUAL_PROJECT_AND_PRINT=None
ACTUAL_FAULT_AND_PRINT=None
FALLBACK_BYTES=b'{"count_status":"UNAVAILABLE","details_omitted":true,"diagnostic_count":0,"error_count":0,"event_limit":256,"event_overflow":false,"private_evidence_sha256":null,"private_evidence_status":"UNAVAILABLE","result":"DENY","runtime_admission":false,"schema":"math572.compile7.public-summary.v1"}\n'
class PublicSummaryV1Contract(unittest.TestCase):
 def run_actual(self,record,written):
  if ACTUAL_PROJECT_AND_PRINT is None:raise SetupStageError('ACTUAL_APPROVED_AST_BINDING_PENDING')
  original=copy.deepcopy(record)
  output,after=ACTUAL_PROJECT_AND_PRINT(record,written)
  if type(output) is not bytes or after!=original or record!=original:raise SetupStageError('ACTUAL_SERIALIZER_OR_PRIVATE_PRESERVATION')
  self.assertLessEqual(len(output),8192);self.assertTrue(output.endswith(b'\n'));self.assertEqual(output.count(b'\n'),1);self.assertNotIn(b'\r',output)
  def unique(pairs):
   result={}
   for key,value in pairs:
    if key in result:raise AssertionError('DUPLICATE_PUBLIC_KEY')
    result[key]=value
   return result
  def nonfinite(value):raise AssertionError('NONFINITE_PUBLIC_JSON')
  p=json.loads(output.decode('utf-8'),object_pairs_hook=unique,parse_constant=nonfinite)
  self.assertIs(type(p),dict);self.assertEqual(output,(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))
  self.assertEqual(set(p),{'schema','result','runtime_admission','count_status','diagnostic_count','error_count','event_limit','event_overflow','details_omitted','private_evidence_status','private_evidence_sha256'})
  self.assertEqual(p['schema'],'math572.compile7.public-summary.v1');self.assertIs(p['runtime_admission'],False);self.assertIs(type(p['event_limit']),int);self.assertEqual(p['event_limit'],256)
  self.assertIn(p['result'],('DENY','EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS'))
  for key in ('diagnostic_count','error_count'):
   self.assertIs(type(p[key]),int);self.assertGreaterEqual(p[key],0);self.assertLessEqual(p[key],256)
  for key in ('event_overflow','details_omitted','runtime_admission'):self.assertIs(type(p[key]),bool)
  self.assertIn(p['count_status'],('EXACT','CAPPED','UNAVAILABLE'))
  self.assertIn(p['private_evidence_status'],('AVAILABLE','UNAVAILABLE'))
  if p['private_evidence_status']=='AVAILABLE':
   self.assertIs(type(p['private_evidence_sha256']),str);self.assertRegex(p['private_evidence_sha256'],r'^[0-9a-f]{64}$');self.assertIsNotNone(written);self.assertEqual(p['private_evidence_sha256'],hashlib.sha256(written).hexdigest())
  else:self.assertIsNone(p['private_evidence_sha256']);self.assertEqual(p['result'],'DENY')
  if record.get('result')!='EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS' or record.get('errors') or p['event_overflow']:self.assertEqual(p['result'],'DENY')
  return p,output
 def fixture(self,n,errors=()):
  return {'result':'EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS','closed_diagnostics':[{'source':3,'line':1,'column':1,'code':'CS0246','symbol':'OwnedPrivateDesktop'} for _ in range(n)],'errors':list(errors)}
 def test_empty_small_and_original_174_records(self):
  for n in (0,1,174):
   with self.subTest(n=n):
    r=self.fixture(n);written=private_wire(r);p,_=self.run_actual(r,written)
    self.assertEqual(p['diagnostic_count'],n);self.assertEqual(p['error_count'],0);self.assertEqual(p['count_status'],'EXACT');self.assertEqual(p['details_omitted'],bool(n));self.assertIs(p['event_overflow'],False)
    self.assertEqual(p['private_evidence_status'],'AVAILABLE');self.assertEqual(p['private_evidence_sha256'],hashlib.sha256(written).hexdigest())
 def test_arbitrary_paths_errors_and_symbols_stay_private(self):
  secret='PRIVATE_PATH_AND_ERROR_SECRET';r=self.fixture(1,[secret]);r['closed_diagnostics'][0]['symbol']=secret
  p,out=self.run_actual(r,private_wire(r));self.assertNotIn(secret.encode(),out);self.assertEqual(p['error_count'],1);self.assertTrue(p['details_omitted'])
 def test_256_257_event_boundary_honest_capping_and_deny(self):
  for key in ('closed_diagnostics','errors'):
   for n in (256,257):
    with self.subTest(key=key,n=n):
     r=self.fixture(n) if key=='closed_diagnostics' else self.fixture(0,['PRIVATE']*n)
     p,_=self.run_actual(r,private_wire(r));field='diagnostic_count' if key=='closed_diagnostics' else 'error_count'
     self.assertEqual(p[field],min(n,256));self.assertEqual(p['event_overflow'],n>256);self.assertEqual(p['count_status'],'CAPPED' if n>256 else 'EXACT')
     if n>256:self.assertEqual(p['result'],'DENY')
 def test_failed_private_receipt_is_deny_without_fabricated_digest(self):
  p,_=self.run_actual(self.fixture(1),None);self.assertEqual(p['result'],'DENY');self.assertEqual(p['private_evidence_status'],'UNAVAILABLE');self.assertIsNone(p['private_evidence_sha256']);self.assertEqual(p['count_status'],'UNAVAILABLE');self.assertEqual(p['diagnostic_count'],0);self.assertEqual(p['error_count'],0);self.assertIs(p['event_overflow'],False);self.assertIs(p['details_omitted'],True)

 def test_prior_deny_or_unknown_never_promotes(self):
  for status in ('DENY','UNKNOWN'):
   with self.subTest(status=status):
    r=self.fixture(1);r['result']=status;p,_=self.run_actual(r,private_wire(r));self.assertEqual(p['result'],'DENY')
 def test_combined_event_overflow_denies_without_fabricated_category_cap(self):
  r=self.fixture(200,['PRIVATE']*100);p,_=self.run_actual(r,private_wire(r));self.assertEqual(p['diagnostic_count'],200);self.assertEqual(p['error_count'],100);self.assertEqual(p['count_status'],'EXACT');self.assertIs(p['event_overflow'],True);self.assertEqual(p['result'],'DENY')
 def test_actual_projection_serialization_validation_faults_use_exact_fallback(self):
  if ACTUAL_FAULT_AND_PRINT is None:raise SetupStageError('ACTUAL_APPROVED_FAULT_AST_BINDING_PENDING')
  for stage in ('PROJECTOR_EXCEPTION','SERIALIZER_EXCEPTION','VALIDATOR_EXCEPTION','VALIDATOR_REJECT','SERIALIZED_OVERBUDGET'):
   with self.subTest(stage=stage):
    r=self.fixture(174);original=copy.deepcopy(r);written=private_wire(r)
    outcome=ACTUAL_FAULT_AND_PRINT(r,written,stage)
    if outcome['reached']!=[stage] or outcome['final_output_calls']!=1:raise SetupStageError('ACTUAL_FAULT_STAGE_NOT_CALIBRATED')
    self.assertEqual(r,original);self.assertEqual(outcome['private_record_after'],original);self.assertEqual(outcome['original_written_bytes_after'],written)
    self.assertEqual(outcome['public_bytes'],FALLBACK_BYTES);self.assertEqual(outcome['effective_result'],'DENY');self.assertNotEqual(outcome['exit_code'],0)

 def test_private_open_short_write_and_close_failure_exact_unavailable_fallback(self):
  for stage in ('PRIVATE_OPEN_FAILURE','PRIVATE_SHORT_WRITE','PRIVATE_CLOSE_FAILURE'):
   with self.subTest(stage=stage):
    r=self.fixture(1);o=actual_fault_and_print(r,private_wire(r),stage)
    if o['reached']!=[stage]:raise SetupStageError('PRIVATE_FAULT_NOT_REACHED')
    self.assertEqual(o['public_bytes'],FALLBACK_BYTES);self.assertEqual(o['effective_result'],'DENY');self.assertEqual(o['exit_code'],1);self.assertEqual(o['publication']['private_evidence_status'],'UNAVAILABLE');self.assertIsNone(o['publication']['private_evidence_sha256']);p=json.loads(o['public_bytes']);self.assertEqual(p['count_status'],'UNAVAILABLE');self.assertEqual((p['diagnostic_count'],p['error_count']),(0,0));self.assertIs(p['event_overflow'],False);self.assertIs(p['details_omitted'],True)
 def test_stdout_failure_has_one_attempt_nonzero_deny_no_delivery_claim(self):
  for stage in ('OUTPUT_WRITE_FAILURE','OUTPUT_SHORT_WRITE','OUTPUT_FLUSH_FAILURE'):
   with self.subTest(stage=stage):
    r=self.fixture(1);o=actual_fault_and_print(r,private_wire(r),stage)
    if o['reached']!=[stage]:raise SetupStageError('OUTPUT_FAULT_NOT_REACHED')
    self.assertEqual(o['effective_result'],'DENY');self.assertEqual(o['exit_code'],1);self.assertIs(o['publication']['output_delivered'],False);self.assertEqual(o['final_output_calls'],1);self.assertEqual(o['publication']['failure_labels'],['PUBLIC_OUTPUT_WRITE_FAILURE'])
 def test_actual_validator_refuses_promotion_types_digest_duplicate_or_framing(self):
  for stage in ('FORCE_EXPECTED_ON_DENY','BOOL_EVENT_COUNT','INT_EVENT_BOOL','BAD_PRIVATE_DIGEST','BAD_PRIVATE_STATUS','DUPLICATE_PUBLIC_KEY','EXTRA_JSON_OBJECT','EXTRA_LF'):
   with self.subTest(stage=stage):
    r=self.fixture(1);r['result']='DENY';o=actual_fault_and_print(r,private_wire(r),stage)
    if o['reached']!=[stage]:raise SetupStageError('VALIDATION_FAULT_NOT_REACHED')
    self.assertEqual(o['public_bytes'],FALLBACK_BYTES);self.assertEqual(o['exit_code'],1);self.assertEqual(o['publication']['failure_labels'],['PUBLIC_VALIDATOR_FAILURE'])

# New adapter selects actual helper definitions + exact main final publication/return
# AST from held candidate source. No target module/full main imports or Win32 calls.
SOURCE=pathlib.Path(__file__).absolute().parent/'math572_compile7_controller_public_summary_successor_review1.py'
SOURCE_SHA='29f0648889fde452e68745aea9b5848e00ced0bae74259637f7d33954384991a'
def private_wire(record):return (json.dumps(record,indent=2,allow_nan=False)+'\n').encode('utf-8')
def actual_environment():
 with SOURCE.open('rb') as f:raw=f.read(32769)
 if len(raw)>32768 or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise SetupStageError('HELD_SOURCE_PIN')
 tree=ast.parse(raw);names={'project_public_summary','serialize_public_summary','validate_public_summary','publish_public_summary'}
 funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 constants=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PUBLIC_SUMMARY_FALLBACK' for t in n.targets)]
 mains=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main']
 if len(funcs)!=4 or len(constants)!=1 or len(mains)!=1:raise SetupStageError('ACTUAL_HELPER_AST_SET')
 tail=mains[0].body[-2:]
 if len(tail)!=2 or not isinstance(tail[0],ast.Assign) or not isinstance(tail[0].value,ast.Call) or not isinstance(tail[0].value.func,ast.Name) or tail[0].value.func.id!='publish_public_summary' or not isinstance(tail[1],ast.Return):raise SetupStageError('ACTUAL_MAIN_FINAL_PUBLICATION_AST')
 selected=constants+funcs
 if any(isinstance(n,(ast.Import,ast.ImportFrom)) for node in selected+tail for n in ast.walk(node)):raise SetupStageError('SELECTED_IMPORT')
 wrapper=ast.FunctionDef(name='actual_main_tail',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=tail,decorator_list=[])
 env={'json':json,'hashlib':hashlib,'re':re}
 exec(compile(ast.fix_missing_locations(ast.Module(body=selected+[wrapper],type_ignores=[])),'<actual-held-publication-helpers-and-main-tail>','exec'),env)
 if env['PUBLIC_SUMMARY_FALLBACK']!=FALLBACK_BYTES:raise SetupStageError('EXACT_FALLBACK_PIN')
 return env

def execute_actual(record,expected_written,stage=None):
 env=actual_environment();reached=[];private_chunks=[];private_success=[];outputs=[];calls=[0];publication=[];closed=[False]
 original=copy.deepcopy(record);setup_errors=[];seams=[]
 def setup_error(code):setup_errors.append(code);raise SetupStageError(code)
 def reach(name):reached.append(name)
 class HeldPrivate:
  def __enter__(self):return self
  def write(self,data):
   seams.append('PRIVATE_WRITE')
   if type(data) is not bytes:setup_error('PRIVATE_WRITE_BYTES')
   private_chunks.append(data)
   if stage=='PRIVATE_SHORT_WRITE':reach(stage);return len(data)-1
   return len(data)
  def __exit__(self,*args):
   seams.append('PRIVATE_CLOSE')
   if stage=='PRIVATE_CLOSE_FAILURE':reach(stage);raise OSError('INERT_PRIVATE_CLOSE')
   if args[0] is None:private_success.append(b''.join(private_chunks));closed[0]=True
 class ReceiptPath:
  def open(self,mode):
   seams.append('PRIVATE_OPEN')
   if mode!='xb':setup_error('EXCLUSIVE_PRIVATE_WRITE_MODE')
   if expected_written is None or stage=='PRIVATE_OPEN_FAILURE':
    if stage:reach(stage)
    raise OSError('INERT_PRIVATE_OPEN')
   return HeldPrivate()
 class OutRoot:
  def __truediv__(self,name):
   if name!='receipt.json':setup_error('ACTUAL_RECEIPT_PATH')
   return ReceiptPath()
 class Output:
  def write(self,data):
   calls[0]+=1
   if type(data) is not bytes:setup_error('FINAL_OUTPUT_BYTES')
   if stage=='OUTPUT_WRITE_FAILURE':reach(stage);raise OSError('INERT_STDOUT_WRITE')
   outputs.append(data)
   if stage=='OUTPUT_SHORT_WRITE':reach(stage);return len(data)-1
   return len(data)
  def flush(self):
   if stage=='OUTPUT_FLUSH_FAILURE':reach(stage);raise OSError('INERT_STDOUT_FLUSH')
 projector=env['project_public_summary'];serializer=env['serialize_public_summary'];validator=env['validate_public_summary'];publisher=env['publish_public_summary']
 def project(r,w):
  seams.append('PROJECTOR_CALL')
  if not closed[0] or private_success!=[w] or w!=expected_written:setup_error('ACTUAL_SUCCESSFUL_WRITE_BYTES_CUSTODY')
  if stage=='PROJECTOR_EXCEPTION':reach(stage);raise RuntimeError('INERT_PROJECTOR')
  result=projector(r,w)
  changes={'FORCE_EXPECTED_ON_DENY':('result','EXPECTED_COMPILE_DIAGNOSTIC_OBSERVED_NOT_RUNTIME_PASS'),'BOOL_EVENT_COUNT':('diagnostic_count',True),'INT_EVENT_BOOL':('event_overflow',0),'BAD_PRIVATE_DIGEST':('private_evidence_sha256','0'*64),'BAD_PRIVATE_STATUS':('private_evidence_status','UNAVAILABLE')}
  if stage in changes:reach(stage);key,value=changes[stage];result[key]=value
  return result
 def serialize(p):
  seams.append('SERIALIZER_CALL')
  if stage=='SERIALIZER_EXCEPTION':reach(stage);raise RuntimeError('INERT_SERIALIZER')
  result=serializer(p)
  if stage in ('SERIALIZED_OVERBUDGET','DUPLICATE_PUBLIC_KEY','EXTRA_JSON_OBJECT','EXTRA_LF'):
   reach(stage)
   if stage=='SERIALIZED_OVERBUDGET':return result+b' '*8192
   if stage=='DUPLICATE_PUBLIC_KEY':return b'{"result":"DENY",'+result[1:]
   if stage=='EXTRA_JSON_OBJECT':return result[:-1]+b'{}\n'
   return result+b'\n'
  return result
 def validate(raw,r,w):
  seams.append('VALIDATOR_CALL')
  if stage=='VALIDATOR_EXCEPTION':reach(stage);raise RuntimeError('INERT_VALIDATOR')
  if stage=='VALIDATOR_REJECT':reach(stage);return False
  return validator(raw,r,w)
 def publish(r,path,output):
  result=publisher(r,path,output,projector=project,serializer=serialize,validator=validate);publication.append(result);return result
 env.update(record=record,OUT=OutRoot(),sys=types.SimpleNamespace(stdout=types.SimpleNamespace(buffer=Output())),publish_public_summary=publish)
 exit_code=env['actual_main_tail']()
 if setup_errors:raise SetupStageError(setup_errors[0])
 if len(publication)!=1 or calls!=[1] or record!=original:setup_error('ACTUAL_MAIN_PUBLICATION_OR_PRESERVATION')
 if expected_written is not None and stage not in ('PRIVATE_OPEN_FAILURE','PRIVATE_SHORT_WRITE','PRIVATE_CLOSE_FAILURE') and private_success!=[expected_written]:setup_error('WRITTEN_ORIGINAL_BYTE_CUSTODY')
 result=publication[0]
 print(json.dumps({'schema':'math572.public-summary.contract.actual-ast.v1','stage':stage,'reached':reached,'seams':seams,'final_output_calls':calls[0],'private_write_success':bool(private_success),'private_sha256':hashlib.sha256(private_success[0]).hexdigest() if private_success else None,'public_bytes':len(outputs[0]) if outputs else 0,'output_delivered':result['output_delivered'],'exit_code':exit_code,'compiler_processes':0,'target_Win32_calls':0,'full_main_imported':False},sort_keys=True))
 return {'public_bytes':outputs[0] if outputs else b'','private_record_after':record,'original_written_bytes_after':private_success[0] if private_success else None,'reached':reached,'final_output_calls':calls[0],'effective_result':result['effective_result'],'exit_code':exit_code,'publication':result}
def actual_project_and_print(record,written):
 result=execute_actual(record,written)
 return result['public_bytes'],result['private_record_after']
def actual_fault_and_print(record,written,stage):return execute_actual(record,written,stage)
ACTUAL_PROJECT_AND_PRINT=actual_project_and_print
ACTUAL_FAULT_AND_PRINT=actual_fault_and_print
