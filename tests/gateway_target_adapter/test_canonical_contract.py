import json,os,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
from unified_system import gateway_target_adapter as adapter
class CanonicalContractTests(unittest.TestCase):
 def test_current_target_is_only_canonical_terminan_and_v2(self):
  q=adapter.template_request();self.assertEqual(q['schema'],'unified.gateway.target-request.v2');self.assertEqual(q['target_kind'],'terminan');self.assertEqual(q['target_capability'],'terminan.ohlcv.untouched_levels.v1');self.assertEqual(q['target_version'],'742d9681b9b57e0252182e3edf4c1dd90ba19c53');self.assertEqual(adapter.MATH_HEAD,'0dcb85e76214453e2e1ff2abdfb8734cde5922b5');self.assertEqual(q['result_schema'],'unified.gateway.direct-target-result.v2')
 def test_old_v1_meta_request_has_no_active_alias(self):
  q=adapter.template_request();q.update(schema='unified.gateway.target-request.v1',target_kind='MetaAnalyse',target_capability='meta.ohlcv.untouched_levels.v1')
  with self.assertRaises(adapter.TargetRejected):adapter.prepare_target(adapter._canonical(q))
  for old_version in ('b99913690ce29ce60e73414cc4d626ca989916ce','75a906d36574bfdc19acd966e79a6c168dc71ad4','042b075dda0fc8cf6bb829d758632cfa989e8e55','221a2562f70558e7753a92499fee1c3f2e706bfb','fc0bed4937ab5dbb039320aae48e49b01b31bb43'):
   q=adapter.template_request();q['target_version']=old_version
   with self.subTest(old_version=old_version),self.assertRaises(adapter.TargetRejected):adapter.prepare_target(adapter._canonical(q))
 def test_registry_contains_no_old_active_owner_or_entrypoint(self):
  raw=json.dumps(adapter.capability_registry());self.assertIn('market_math.untouched_decimal_levels',raw);self.assertNotIn('market_math.untouched_levels',raw);self.assertNotIn('strattester',raw);self.assertNotIn('meta_analyse',raw);self.assertNotIn('MetaAnalyse',raw);self.assertNotIn('UNRESOLVED',raw)
 def kwargs(self):return dict(terminan_source_root=os.environ['TARGET_TERMINAN_ROOT'],math_source_root=os.environ['TARGET_MATH_ROOT'],git_executable=os.environ['TARGET_GIT'],git_sha256=os.environ['TARGET_GIT_SHA256'],runtime_sha256=os.environ['TARGET_RUNTIME_SHA256'])
 def test_old_marker_directory_refuses_without_adoption(self):
  with tempfile.TemporaryDirectory() as root:
   marker=Path(root)/'stand.marker';marker.write_bytes(b'unified.direct-target.owned-disposable.v1\n');before=list(Path(root).iterdir())
   with self.assertRaises(adapter.TargetRejected):adapter.DisposableTargetStand(root,**self.kwargs())
   self.assertEqual(list(Path(root).iterdir()),before);self.assertEqual(marker.read_bytes(),b'unified.direct-target.owned-disposable.v1\n')
 def test_unqualified_cache_and_runtime_refuse_before_app_import(self):
  for field in ('cache','runtime'):
   with tempfile.TemporaryDirectory() as root:
    kwargs=self.kwargs()
    if field=='runtime':kwargs['runtime_sha256']='0'*64
    with patch.object(sys,'pycache_prefix',None if field=='cache' else sys.pycache_prefix),patch.dict(sys.modules,{},clear=False),self.assertRaises(adapter.TargetRejected):adapter.DisposableTargetStand(root,**kwargs)
    self.assertEqual(list(Path(root).iterdir()),[])

class CanonicalCustodyAndJournalTests(unittest.TestCase):
 kwargs=CanonicalContractTests.kwargs
 def stand(self,root):return adapter.DisposableTargetStand(root,**self.kwargs())
 def test_qualified_py_origin_without_qualified_cached_bytecode_is_not_custody(self):
  import types,importlib.util
  path=Path(os.environ['TARGET_TERMINAN_ROOT'])/'terminan/__init__.py'
  fake=types.ModuleType('terminan');fake.__file__=str(path);fake.__spec__=importlib.util.spec_from_file_location('terminan',path);fake.__cached__=str(Path(tempfile.gettempdir())/'unqualified.pyc')
  with tempfile.TemporaryDirectory() as root:
   stand=self.stand(root)
   try:
    with patch.dict(sys.modules,{'terminan':fake}),patch.object(adapter.importlib,'import_module',side_effect=AssertionError('APP_IMPORT_BEFORE_CUSTODY')) as imported:
     value=stand.execute(adapter.prepare_target(adapter._canonical(adapter.template_request())),context=stand.local_test_context())
    self.assertEqual(value['status'],'FAILED');self.assertEqual(stand.invocations,0);imported.assert_not_called()
   finally:stand.close()
 def test_nonempty_isolated_cache_refuses_before_any_stand_files(self):
  with tempfile.TemporaryDirectory() as root,tempfile.TemporaryDirectory() as cache:
   (Path(cache)/'unqualified.pyc').write_bytes(b'untrusted')
   with patch.object(sys,'pycache_prefix',cache),self.assertRaises(adapter.TargetRejected):self.stand(root)
   self.assertEqual(list(Path(root).iterdir()),[])
 def test_v2_journal_requires_started_before_finished_and_exact_envelope_binding(self):
  for mode in ('finished-first','wrong-binding'):
   with tempfile.TemporaryDirectory() as root:
    stand=self.stand(root);raw=adapter._canonical(adapter.template_request());q=adapter._decode(raw)
    try:
     if mode=='wrong-binding':stand._append(raw,'STARTED')
     result=stand._envelope(q,raw,'FAILED',error='TARGET_RESULT_UNAVAILABLE')
     if mode=='wrong-binding':result['request_id']='22222222-2222-4222-8222-222222222222'
     stand._append(raw,'FINISHED',result)
     with self.assertRaises(adapter.TargetRejected):stand._records()
     self.assertEqual(stand.invocations,0)
    finally:stand.close()
 def test_pure_fault_after_durable_intent_never_reexecutes_on_reopen(self):
  class Fault(BaseException):pass
  with tempfile.TemporaryDirectory() as root:
   stand=self.stand(root);raw=adapter._canonical(adapter.template_request())
   try:
    with patch.object(stand,'_invoke',side_effect=Fault):
     with self.assertRaises(Fault):stand.execute(adapter.prepare_target(raw),context=stand.local_test_context())
   finally:stand.close()
   other=self.stand(root)
   try:
    result=other.execute(adapter.prepare_target(raw),context=other.local_test_context());self.assertEqual(result['status'],'UNKNOWN');self.assertEqual(result['error'],'ORIGINAL_INTENT_OUTCOME_UNKNOWN_NO_REEXECUTION');self.assertEqual(other.invocations,0)
   finally:other.close()
 def test_revoke_after_calculation_keeps_intent_unknown_without_finished_commit(self):
  with tempfile.TemporaryDirectory() as root:
   stand=self.stand(root);context=stand.local_test_context();raw=adapter._canonical(adapter.template_request());original=stand._invoke
   def revoke(check):
    result=original(check);stand.revoke(context);return result
   try:
    with patch.object(stand,'_invoke',revoke),self.assertRaises(adapter.TargetRejected):stand.execute(adapter.prepare_target(raw),context=context)
    self.assertEqual([r['receipt']['phase'] for r in stand._records()],['STARTED']);self.assertEqual(stand.invocations,1)
    fresh=stand.local_test_context();result=stand.execute(adapter.prepare_target(raw),context=fresh);self.assertEqual(result['status'],'UNKNOWN');self.assertEqual(stand.invocations,1)
   finally:stand.close()

 def test_foreign_marker_size_and_linked_lock_refuse_before_content_open(self):
  for kind in ('marker','lock'):
   with tempfile.TemporaryDirectory() as root,tempfile.TemporaryDirectory() as other:
    location=Path(root);marker=location/'canonical-target.v2.marker';marker.write_bytes(b'x'*5000000 if kind=='marker' else adapter._MARKER)
    if kind=='lock':
     outside=Path(other)/'outside';outside.write_bytes(b'');os.link(outside,location/'canonical-target.v2.lock')
    calls=[];original_read=Path.read_bytes;original_open=Path.open
    def read(path,*a,**kw):
     if path==marker:calls.append('read-marker')
     return original_read(path,*a,**kw)
    def opened(path,*a,**kw):
     if path==location/'canonical-target.v2.lock':calls.append('open-lock')
     return original_open(path,*a,**kw)
    with patch.object(Path,'read_bytes',read),patch.object(Path,'open',opened),self.assertRaises(adapter.TargetRejected):self.stand(root)
    self.assertEqual(calls,[])
 def test_foreign_directory_inventory_is_cut_before_unbounded_iteration(self):
  with tempfile.TemporaryDirectory() as root:
   location=Path(root);original=Path.iterdir;seen=[]
   def entries(path):
    if path!=location:return original(path)
    def hostile():
     for index in range(1000000):seen.append(index);yield location/str(index)
    return hostile()
   with patch.object(Path,'iterdir',entries),self.assertRaises(adapter.TargetRejected):self.stand(root)
   self.assertLessEqual(len(seen),4)
