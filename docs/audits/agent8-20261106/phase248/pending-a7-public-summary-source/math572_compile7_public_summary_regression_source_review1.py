"""UNEXECUTED SOURCE: actual a05e policy and final serialization, inert data only."""
import ast,pathlib,hashlib,types,contextlib,json,re,unittest
SOURCE=pathlib.Path(__file__).absolute().parent/'math572_compile7_controller_review3.py'
SOURCE_SHA='a05e865da136baec3f7945e795733589fdf4cdd8cc92750aed5046b1c081bca7'
CAP=8192
LINE=b'S03.cs(1,1): error CS0246: OwnedPrivateDesktop\n'
class SetupStageError(RuntimeError):pass
def require_setup(value,code):
 if not value:raise SetupStageError(code)
def record_key(node,key):
 return isinstance(node,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='record' and isinstance(t.slice,ast.Constant) and t.slice.value==key for t in node.targets)
def assigns_text(node):
 return any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='text' for t in n.targets) for n in ast.walk(node))
def actual_nodes():
 with SOURCE.open('rb') as f:raw=f.read(32769)
 require_setup(len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==SOURCE_SHA,'SOURCE_PIN')
 mains=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main'];require_setup(len(mains)==1,'MAIN_AST')
 owners=[n for n in mains[0].body if isinstance(n,ast.Try) and n.finalbody];require_setup(len(owners)==1,'OWNER_FINALLY_AST')
 body=owners[0].finalbody;start=[i for i,n in enumerate(body) if assigns_text(n)];end=[i for i,n in enumerate(body) if record_key(n,'whole_wallclock_claim')]
 require_setup(len(start)==len(end)==1 and start[0]<end[0],'ACTUAL_DIAGNOSTIC_POLICY_SLICE')
 summary=[n for n in mains[0].body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='print' and n.value.args and isinstance(n.value.args[0],ast.Call) and isinstance(n.value.args[0].func,ast.Attribute) and isinstance(n.value.args[0].func.value,ast.Name) and n.value.args[0].func.value.id=='json' and n.value.args[0].func.attr=='dumps']
 require_setup(len(summary)==1,'ACTUAL_FINAL_SUMMARY_SERIALIZATION')
 nodes=body[start[0]:end[0]]+[summary[0]]
 require_setup(not any(isinstance(n,(ast.Import,ast.ImportFrom)) for node in nodes for n in ast.walk(node)),'NO_SELECTED_IMPORTS')
 return nodes
class PublicSummaryBoundaryRegression(unittest.TestCase):
 def setUp(self):self.facts={'policy_reached':False,'serialization_calls':0,'target_Win32_calls':0,'compiler_processes':0,'full_main_imported':False}
 def tearDown(self):print(json.dumps({'schema':'math572.public-summary.inert.reached.v1','case':self.id(),**self.facts},sort_keys=True))
 def actual_serialization(self,raw,records):
  require_setup(len(raw)<=CAP and len(raw.splitlines())==records and records>0,'BOUNDED_RAW_FIXTURE_CALIBRATION')
  captured={'stdout':raw,'stderr':b''};original=dict(captured);printed=[]
  state={name:{'started':True,'eof':True,'read_failed':False,'close_ok':True,'close_failed':False,'retired':True,'log_written':True} for name in captured}
  record={'errors':[],'logs':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in captured.items()},'result':'DENY','job_assigned_before_resume':True}
  def capture_print(*args,**kwargs):
   require_setup(len(args)==1 and type(args[0]) is str and not kwargs,'ACTUAL_PRINT_FORM')
   printed.append((args[0]+'\n').encode('utf-8'))
  namespace={'captured':captured,'reader_state':state,'record':record,'uncertain':False,'overflow':types.SimpleNamespace(is_set=lambda:False),'lock':contextlib.nullcontext(),'re':re,'json':json,'error':record['errors'].append,'exit_code':1,'print':capture_print}
  nodes=actual_nodes();execute=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]))
  exec(compile(execute,'<actual-policy-and-public-summary-inert-data>','exec'),namespace)
  require_setup(record['diagnostic_set_admitted'] and record['original_logs_complete'] and record['result'].startswith('EXPECTED_COMPILE_'),'ACTUAL_EXPECTED_POLICY_NOT_REACHED')
  require_setup(len(record['closed_diagnostics'])==records and len(printed)==1,'ACTUAL_SERIALIZATION_COUNT')
  parsed=json.loads(printed[0]);require_setup(len(parsed['closed_diagnostics'])==records and parsed['result']==record['result'],'ACTUAL_JSON_ROUNDTRIP')
  require_setup(captured==original and not record['errors'],'RAW_FIXTURE_OR_COMPLETENESS_CHANGED')
  self.facts.update(policy_reached=True,serialization_calls=len(printed),raw_bytes=len(raw),raw_records=records,public_serialized_bytes=len(printed[0]),closed_diagnostic_records=len(record['closed_diagnostics']),raw_fixture_unchanged=True)
  return printed[0]
 def test_actual_small_serialized_summary_bounded_positive_control(self):
  public=self.actual_serialization(LINE,1)
  self.assertLessEqual(len(public),CAP)
 def test_actual_final_summary_expansion_must_obey_public_byte_cap(self):
  count=CAP//len(LINE);raw=LINE*count
  require_setup(count>1 and len(raw)<=CAP,'OVERBUDGET_INPUT_REACHABILITY')
  public=self.actual_serialization(raw,count)
  # Regression assertion after all source/policy/serializer/reached calibrations.
  # This test introduces NO limiter and never silently truncates original data.
  self.assertLessEqual(len(public),CAP,'actual serialized public summary must independently respect8192byte cap')
if __name__=='__main__':unittest.main(verbosity=2)
