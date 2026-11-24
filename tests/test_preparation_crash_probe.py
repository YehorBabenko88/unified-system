import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ProbeTests(unittest.TestCase):
 def api(self):
  p=ROOT/'tests/preparation_crash_probe.py';self.assertTrue(p.is_file());s=importlib.util.spec_from_file_location('inert_crash_probe',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def test_flags_and_original_crash_hook_are_preserved(self):
  m=self.api();c=m.build_command('python',ROOT,Path('db'),{},Path('phase'),Path('fresh'))
  self.assertEqual(c[1:5],['-I','-S','-B','-X']);self.assertIn('os._exit(23)',c[7]);compile(c[7],'<inert>','exec')
 def test_phase_projection_never_echoes_untrusted_data(self):
  m=self.api()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'phase';self.assertEqual(m.phase_summary(p),'ENTRY_NOT_OBSERVED')
   p.write_text('ENTRY\nIMPORT_BEGIN\n');self.assertEqual(m.phase_summary(p),'ENTRY,IMPORT_BEGIN')
   for text in ('SECRET_SENTINEL', 'ENTRY\n'*1000):
    p.write_text(text);self.assertEqual(m.phase_summary(p),'INVALID_PHASE_RECORD')

 def test_earliest_stdout_marker_precedes_every_probe_import(self):
  import ast
  m=self.api();tree=ast.parse(m.CRASH_CODE)
  first=tree.body[0]
  self.assertIsInstance(first,ast.Expr)
  self.assertIsInstance(first.value,ast.Call)
  self.assertEqual('print',first.value.func.id)
  self.assertEqual('PREPARATION_PYTHON_ENTERED',ast.literal_eval(first.value.args[0]))
  self.assertEqual({'flush':True},{k.arg:ast.literal_eval(k.value) for k in first.value.keywords})
  self.assertIsInstance(tree.body[1],ast.Import)
  self.assertNotIn('PREPARATION_PYTHON_ENTERED',m.PHASES)
 def test_timeout_output_empty_bytes_str_and_none_are_distinct(self):
  m=self.api();self.assertTrue(hasattr(m,'timeout_output'),'bounded timeout projection missing')
  for value,kind in ((None,'none'),(b'','bytes'),('','str')):
   self.assertEqual(dict(kind=kind,size=0,truncated=False,entry_marker=False,exceptions=[],redacted=False),m.timeout_output(value))
 def test_timeout_output_retains_only_closed_diagnostic_tokens(self):
  m=self.api();self.assertTrue(hasattr(m,'timeout_output'),'bounded timeout projection missing')
  text='PREPARATION_PYTHON_ENTERED\nModuleNotFoundError: private credential\n'
  for value,kind in ((text,'str'),(text.encode(),'bytes')):
   result=m.timeout_output(value)
   self.assertEqual(kind,result['kind']);self.assertEqual(len(value),result['size'])
   self.assertTrue(result['entry_marker']);self.assertEqual(['ModuleNotFoundError'],result['exceptions'])
   self.assertTrue(result['redacted']);self.assertFalse(result['truncated'])
   self.assertNotIn('private',str(result));self.assertNotIn('credential',str(result))
 def test_timeout_output_invalid_utf_controls_and_commands_never_echo(self):
  m=self.api();self.assertTrue(hasattr(m,'timeout_output'),'bounded timeout projection missing')
  for value in (b'\xff\xfe\x00\x1b[31mSECRET\r\n', '\ud800\x00\u202eSECRET\n', 'python -c SECRET\nTOKEN=SECRET\nValueError: SECRET'):
   result=m.timeout_output(value)
   self.assertFalse(result['entry_marker']);self.assertTrue(result['redacted'])
   self.assertNotIn('SECRET',str(result));self.assertNotIn('python',str(result))
   self.assertTrue(str(result).isascii())
  self.assertFalse(m.timeout_output('PREPARATION_PYTHON_ENTERED extra')['entry_marker'])
 def test_timeout_output_is_bounded_and_does_not_coerce_unknown_objects(self):
  m=self.api();self.assertTrue(hasattr(m,'timeout_output'),'bounded timeout projection missing')
  for value in ('x'*1000000,b'x'*1000000):
   result=m.timeout_output(value+'\nPREPARATION_PYTHON_ENTERED' if type(value) is str else value+b'\nPREPARATION_PYTHON_ENTERED')
   self.assertTrue(result['truncated']);self.assertFalse(result['entry_marker'])
   self.assertLess(len(str(result)),256)
  class Refuse:
   def __str__(self):raise AssertionError('coercion')
   def __bool__(self):raise AssertionError('truthiness')
  self.assertEqual(dict(kind='unsupported',size=None,truncated=False,entry_marker=False,exceptions=[],redacted=True),m.timeout_output(Refuse()))
 def test_timeout_failure_uses_projected_streams_without_command_text(self):
  import ast
  m=self.api();self.assertTrue(hasattr(m,'timeout_evidence'),'timeout evidence missing');summary=m.timeout_evidence(b'PREPARATION_PYTHON_ENTERED\n',b'ValueError: SECRET')
  self.assertIn('PREPARATION_PYTHON_ENTERED',m.CRASH_CODE)
  self.assertIn('entry_marker',summary);self.assertNotIn('SECRET',summary)
  self.assertLess(len(summary),1024)
  tree=ast.parse((ROOT/'tests/test_agent5_scheduler_components.py').read_text())
  method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='test_process_crash_before_event_commit_recovers_without_partial_hold')
  call=next(n for n in ast.walk(method) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='run')
  self.assertEqual(20,next(ast.literal_eval(k.value) for k in call.keywords if k.arg=='timeout'))
  handler=next(n for n in ast.walk(method) if isinstance(n,ast.ExceptHandler))
  projection=next(n for n in ast.walk(handler) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='timeout_evidence')
  self.assertEqual(['stdout','stderr'],[n.attr for n in projection.args])
  self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='cmd' for n in ast.walk(handler)))

if __name__=='__main__':unittest.main()
