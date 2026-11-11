"""UNEXECUTED SOURCE: selected actual Python AST with inert API/file doubles only."""
import ast,pathlib,hashlib,types,threading,re,unittest,sys
BASE=pathlib.Path(__file__).absolute().parent
PROFILES={
 'old':(BASE/'math572-compile7-before-a8-source-fix-20261111/controller.py','dff93058aa9c97e776c7febb3d354cbf5502da4995e92340aa383fdc65b40494'),
 'candidate':(BASE/'math572-compile7-a8-source-correction-20261111/controller-after.py','444c32b8456fa1c42e1504a96e5a2882b29c3a832368671aba813b4f2d3477d2')}
PROFILE='candidate'
if __name__=='__main__' and sys.argv[1:]:
 if len(sys.argv)!=3 or sys.argv[1]!='--profile' or sys.argv[2] not in PROFILES:raise ValueError('EXACT_PROFILE_ONLY')
 PROFILE=sys.argv[2];sys.argv=sys.argv[:1]

def selected_source():
 path,pin=PROFILES[PROFILE]
 with path.open('rb') as f:raw=f.read(32769)
 if len(raw)>32768 or hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('SOURCE_PIN')
 tree=ast.parse(raw);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 return main
def contains_assignment(node,name):
 return any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets) for n in ast.walk(node))
def record_key(node,key):
 return isinstance(node,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='record' and isinstance(t.slice,ast.Constant) and t.slice.value==key for t in node.targets)
def definition(name,namespace):
 node=next(n for n in selected_source().body if isinstance(n,ast.FunctionDef) and n.name==name)
 if any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(node)):raise ValueError('IMPORT_IN_SELECTED_FUNCTION')
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<selected-actual-inert-function>','exec'),namespace)
 return namespace[name]
def final_body():
 # Actual main try contains creation_intent and its unconditional finalbody.
 matches=[n for n in selected_source().body if isinstance(n,ast.Try) and n.finalbody and any(record_key(c,'creation_intent') for c in ast.walk(n))]
 if len(matches)!=1:raise ValueError('EXACT_MAIN_FINALLY')
 return matches[0].finalbody
def policy(namespace):
 body=final_body();start=next(i for i,n in enumerate(body) if contains_assignment(n,'text'));end=next(i for i,n in enumerate(body) if record_key(n,'whole_wallclock_claim'))
 nodes=body[start:end]
 if any(isinstance(n,(ast.Import,ast.ImportFrom)) for node in nodes for n in ast.walk(node)):raise ValueError('IMPORT_IN_POLICY')
 exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<selected-actual-inert-policy>','exec'),namespace)
 return namespace['record']
class Event:
 def __init__(self):self.value=False
 def set(self):self.value=True
 def is_set(self):return self.value
GOOD=b"S03.cs(52,5): error CS0246: The type 'OwnedPrivateDesktop' could not be found\n"
def namespace(stdout=GOOD,stderr=b''):
 record={'errors':[],'logs':{'stdout':{},'stderr':{}},'job_assigned_before_resume':True,'result':'DENY'}
 state={name:{'started':True,'eof':True,'read_failed':False,'close_ok':True,'close_failed':False,'retired':True,'log_written':True} for name in ('stdout','stderr')}
 return {'record':record,'reader_state':state,'captured':{'stdout':stdout,'stderr':stderr},'buffers':{'stdout':bytearray(stdout),'stderr':bytearray(stderr)},'error':record['errors'].append,'uncertain':False,'overflow':Event(),'lock':threading.Lock(),'re':re,'exit_code':1}
class Pipe:
 def __init__(self,blocks,close_fails=False):self.blocks=list(blocks);self.close_fails=close_fails
 def read(self,size):
  value=self.blocks.pop(0) if self.blocks else b''
  if isinstance(value,BaseException):raise value
  return value
 def close(self):
  if self.close_fails:raise OSError('INERT_CLOSE')
class Win:
 def __init__(self,polls,terminate_fails=False):self.polls=list(polls);self.terminate_fails=terminate_fails;self.kills=0;self.waits=0
 def WaitForSingleObject(self,handle,timeout):
  self.waits+=1;value=self.polls.pop(0)
  if isinstance(value,BaseException):raise value
  return value
 def TerminateProcess(self,handle,code):
  self.kills+=1
  if self.terminate_fails:raise OSError('INERT_KILL')
 def GetExitCodeProcess(self,handle):return 1
class Kernel:
 def __init__(self,fail=False):self.fail=fail;self.kills=0
 def TerminateJobObject(self,job,code):self.kills+=1;return not self.fail

class TerminationControls(unittest.TestCase):
 def test_unknown_poll_unassigned_child_still_direct_termination(self):
  ns=namespace();win=Win([OSError('INERT_POLL')]);ns.update(hp='OWN',job=None,_winapi=win,k=Kernel())
  definition('terminate_owned',ns)();self.assertEqual(win.kills,1);self.assertIn('PROCESS_POLL_FAILURE',ns['record']['errors'])
 def test_poll_and_kill_failure_still_reaches_actual_independent_wait(self):
  ns=namespace();win=Win([OSError('CLEANUP_POLL'),OSError('DIRECT_POLL'),0],True)
  ns.update(hp='OWN',job=None,_winapi=win,k=Kernel(),deadline=5,time=types.SimpleNamespace(monotonic=lambda:0));ns['record']['child']={'retired':False}
  definition('terminate_owned',ns)
  blocks=[n for n in final_body() if isinstance(n,ast.If) and ast.unparse(n.test)=='hp is not None' and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='GetExitCodeProcess' for x in ast.walk(n))]
  if len(blocks)!=1:raise ValueError('EXACT_RETIREMENT_BLOCK')
  exec(compile(ast.fix_missing_locations(ast.Module(body=blocks,type_ignores=[])),'<selected-actual-inert-retirement>','exec'),ns)
  self.assertEqual(win.kills,1);self.assertEqual(win.waits,3);self.assertTrue(ns['record']['child']['retired']);self.assertIn('PROCESS_TERMINATE_FAILURE',ns['record']['errors'])
 def test_retired_child_control_avoids_direct_termination(self):
  ns=namespace();win=Win([0]);ns.update(hp='OWN',job=None,_winapi=win,k=Kernel());definition('terminate_owned',ns)();self.assertEqual(win.kills,0)

class CompilerPolicyControls(unittest.TestCase):
 def test_expected_only_control_is_diagnostic_not_runtime_pass(self):
  result=policy(namespace());self.assertTrue(result['result'].startswith('EXPECTED_COMPILE_'));self.assertTrue(result['original_logs_complete'])
 def test_expected_plus_unrelated_error_is_unknown(self):
  result=policy(namespace(GOOD+b"error CS0006: unrelated missing reference\n"));self.assertEqual(result['result'],'DENY');self.assertEqual(result['startup_class'],'UNKNOWN_MIXED_OR_UNADMITTED_COMPILER_OUTPUT')
 def test_unknown_symbol_and_warning_are_denied(self):
  for extra in (b"S03.cs(2,1): error CS0246: type 'Unrelated' missing\n",b"S03.cs(2,1): warning CS0168: unused variable\n"):
   with self.subTest(extra=extra[:32]):self.assertEqual(policy(namespace(GOOD+extra))['result'],'DENY')
 def test_native_startup_cannot_be_missing_type_result(self):
  ns=namespace();ns['exit_code']=0xC0000142;result=policy(ns);self.assertEqual(result['result'],'DENY');self.assertEqual(result['startup_class'],'NATIVE_STARTUP_FAILURE_UNKNOWN_CAUSE')

class LogCompletenessControls(unittest.TestCase):
 def run_actual_reader(self,pipe):
  ns=namespace();ns['buffers']={'stdout':bytearray(),'stderr':bytearray()};ns.update(os=types.SimpleNamespace(fdopen=lambda *a,**k:pipe,O_RDONLY=0,O_BINARY=0),msvcrt=types.SimpleNamespace(open_osfhandle=lambda *a:7),_winapi=types.SimpleNamespace(CloseHandle=lambda h:None),CAP=8192,total=[0])
  ns['reader_state']['stdout'].update(started=False,eof=False,read_failed=False,close_ok=False,close_failed=False)
  definition('reader',ns)(7,'stdout');ns['captured']={name:bytes(raw) for name,raw in ns['buffers'].items()}
  return ns
 def test_actual_reader_failure_never_claims_complete_logs(self):
  ns=self.run_actual_reader(Pipe([GOOD,OSError('INERT_READ')]))
  result=policy(ns);self.assertFalse(result['original_logs_complete']);self.assertEqual(result['result'],'DENY');self.assertTrue(ns['reader_state']['stdout']['read_failed'])
 def test_actual_reader_close_failure_never_claims_complete_logs(self):
  ns=self.run_actual_reader(Pipe([GOOD,b''],True));result=policy(ns);self.assertFalse(result['original_logs_complete']);self.assertEqual(result['result'],'DENY');self.assertTrue(ns['reader_state']['stdout']['close_failed'])
 def test_missing_eof_retirement_or_log_write_never_complete(self):
  for field in ('eof','retired','log_written'):
   with self.subTest(field=field):
    ns=namespace();ns['reader_state']['stdout'][field]=False;result=policy(ns);self.assertFalse(result['original_logs_complete']);self.assertEqual(result['result'],'DENY')
 def test_missing_evidence_member_never_complete(self):
  ns=namespace();ns['record']['logs'].pop('stderr');result=policy(ns);self.assertFalse(result['original_logs_complete']);self.assertEqual(result['result'],'DENY')

if __name__=='__main__':unittest.main(verbosity=2)
