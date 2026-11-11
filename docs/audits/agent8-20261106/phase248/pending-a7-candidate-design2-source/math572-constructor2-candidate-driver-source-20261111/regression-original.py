"""SOURCE ONLY: actual old caller/start/cleanup AST; inert constructor fault."""
import ast,pathlib,hashlib,types,unittest,json
SOURCE=pathlib.Path(__file__).absolute().parent/'math572_compile7_controller_review3.py'
SOURCE_SHA='a05e865da136baec3f7945e795733589fdf4cdd8cc92750aed5046b1c081bca7'
class SetupStageError(RuntimeError):pass
class ConstructorMarker(Exception):pass
class StartMarker(Exception):pass
def require_setup(value,code):
 if not value:raise SetupStageError(code)
def selected_nodes():
 with SOURCE.open('rb') as f:raw=f.read(32769)
 require_setup(len(raw)<=32768 and hashlib.sha256(raw).hexdigest()==SOURCE_SHA,'SOURCE_PIN')
 main=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main'];require_setup(len(main)==1,'MAIN_AST')
 definitions=[n for n in main[0].body if isinstance(n,ast.FunctionDef) and n.name=='start_thread'];require_setup(len(definitions)==1,'START_THREAD_AST')
 owners=[n for n in main[0].body if isinstance(n,ast.Try) and n.finalbody];require_setup(len(owners)==1,'OWNER_TRY_AST')
 caller=[n for n in owners[0].body if isinstance(n,ast.For) and ast.unparse(n.iter)=='read_handles'];require_setup(len(caller)==1,'ACTUAL_CALLER_LOOP_AST')
 cleanup=[n for n in owners[0].finalbody if isinstance(n,ast.For) and ast.unparse(n.iter)=='read_handles'];require_setup(len(cleanup)==1,'ACTUAL_FINALLY_READ_CLOSE_AST')
 nodes=[definitions[0],caller[0],cleanup[0]]
 require_setup(not any(isinstance(n,(ast.Import,ast.ImportFrom)) for node in nodes for n in ast.walk(node)),'NO_SELECTED_IMPORTS')
 return nodes
def execute(nodes,namespace):
 exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<actual-old-constructor-inert-seam>','exec'),namespace)
class ConstructorCallerRegression(unittest.TestCase):
 def setUp(self):self.markers=[];self.closed=[];self.errors=[];self.ns=None
 def tearDown(self):
  print(json.dumps({'schema':'math572.constructor.inert.reached.v1','case':self.id(),'markers':self.markers,'inert_closed_handles':self.closed,'closed_error_labels':self.errors,'compiler_processes':0,'target_Win32_calls':0,'full_main_imported':False},sort_keys=True))
 def namespace(self,constructor):
  def close(handle):
   require_setup(handle==701,'ONLY_INERT_OWN_HANDLE');self.markers.append('INERT_CLOSE_CALLED');self.closed.append(handle)
  self.ns={'threading':types.SimpleNamespace(Thread=constructor),'threads':[],'reader_attempts':set(),'reader_reservations':{},'reader':object(),'read_handles':[(701,'stdout')],'_winapi':types.SimpleNamespace(CloseHandle=close),'error':self.errors.append,'uncertain':False}
  return self.ns
 def run_actual_seam(self,constructor,marker):
  definition,caller,cleanup=selected_nodes();self.markers.append('SOURCE_AND_EXACT_THREE_AST_ADMITTED')
  ns=self.namespace(constructor);execute([definition],ns)
  self.markers.append('ACTUAL_CALLER_LOOP_ENTERED');caught=False
  try:execute([caller],ns)
  except marker:caught=True;self.markers.append('EXPECTED_INJECTED_MARKER_REACHED')
  except BaseException:raise SetupStageError('UNEXPECTED_CALLER_EXCEPTION') from None
  require_setup(caught,'MARKER_NOT_REACHED')
  require_setup(701 in ns['reader_attempts'] or 701 in ns['reader_reservations'],'CALLER_OWNERSHIP_STAGE_NOT_REACHED')
  self.markers.append('ACTUAL_FINALLY_READ_CLOSE_ENTERED');execute([cleanup],ns);self.markers.append('ACTUAL_FINALLY_READ_CLOSE_RETURNED')
  return ns
 def test_actual_constructor_failure_closes_known_unowned_read_handle(self):
  count=[0]
  def constructor(**kwargs):
   count[0]+=1;self.markers.append('INERT_THREAD_CONSTRUCTOR_ENTERED');raise ConstructorMarker('INERT_CONSTRUCTOR_MARKER')
  ns=self.run_actual_seam(constructor,ConstructorMarker)
  require_setup(count==[1],'CONSTRUCTOR_CALL_COUNT')
  require_setup(not any(entry.get('thread') is not None for entry in ns['threads']),'UNEXPECTED_THREAD_OBJECT')
  require_setup('ACTUAL_FINALLY_READ_CLOSE_RETURNED' in self.markers,'CLOSE_STAGE_MISSED')
  # Regression assertion AFTER all fault/setup/reached-stage calibrations.
  self.assertEqual(self.closed,[701],'known read handle must independently close when no Thread.start was attempted')
 def test_actual_unknown_start_preserves_no_close_control(self):
  parent=self;count=[0]
  class InertUnknown:
   @property
   def ident(self):parent.markers.append('INERT_IDENT_OBSERVED');return None
   def is_alive(self):parent.markers.append('INERT_ALIVE_OBSERVED');return False
   def start(self):parent.markers.append('INERT_START_ENTERED');raise StartMarker('INERT_UNKNOWN_START_MARKER')
  def constructor(**kwargs):count[0]+=1;parent.markers.append('INERT_THREAD_CONSTRUCTOR_RETURNED');return InertUnknown()
  ns=self.run_actual_seam(constructor,StartMarker)
  require_setup(count==[1] and len(ns['threads'])==1,'UNKNOWN_CONSTRUCTOR_COUNT')
  require_setup(all(name in self.markers for name in ('INERT_START_ENTERED','INERT_IDENT_OBSERVED','INERT_ALIVE_OBSERVED')),'UNKNOWN_START_CALIBRATION_NOT_REACHED')
  require_setup(ns['threads'][0]['outcome']=='UNKNOWN','UNKNOWN_STATE_NOT_PRESERVED')
  self.assertEqual(self.closed,[],'possibly started reader handle must not be blindly closed')
if __name__=='__main__':unittest.main(verbosity=2)
