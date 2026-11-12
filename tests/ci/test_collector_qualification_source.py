"""Inert qualification guards only; never launch Collector/process fixtures."""
import ast
import importlib.util
from pathlib import Path
import unittest
import sys
import types
import tempfile
import os
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('collector_qualification_guards',ROOT/'tools/collector/qualify.py')
Q=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(Q)


class CollectorQualificationSourceTests(unittest.TestCase):
    def test_five_explicit_source_roles_and_new_grid_pin(self):
        self.assertEqual(set(Q.INPUTS),{'grid','a5','a4','logger'})
        self.assertEqual(Q.INPUTS['grid'][0],'3bfddc3811e5f88a2b24b5026025f772814f3eb4')
        self.assertEqual(Q.INPUTS['a5'][0],'dec4ac619239f9c84982850be2bb6a7cb896e370')
        self.assertEqual(Q.INPUTS['logger'][0],'07eb13bef9099da750d50943120ac5fdc98db9c6')

    def test_actual_ast_inventory_does_not_hardcode_live_counts(self):
        raw=b'import unittest\nclass T(unittest.TestCase):\n def test_one(self): pass\n def helper(self): pass\n def test_two(self): pass\n'
        self.assertEqual(Q.ast_ids(raw,'selected'),['selected.T.test_one','selected.T.test_two'])

    def test_duplicate_and_empty_ast_inventory_denied(self):
        for raw in (b'import unittest\nclass T(unittest.TestCase):\n def test_x(self):pass\n def test_x(self):pass\n',b'x=1\n'):
            with self.assertRaises(Q.Denied):Q.ast_ids(raw,'selected')

    def test_exact_run_ids_no_skip_no_extra(self):
        expected=['module.T.test_one']
        Q.check_cases(expected,[{'id':expected[0],'outcome':'PASS'}],1,0,0,0,0,0)
        for records in ([],[{'id':expected[0],'outcome':'SKIP'}],[{'id':'foreign.T.test_x','outcome':'PASS'}],
                        [{'id':expected[0],'outcome':'PASS'}]*2):
            with self.assertRaises(Q.Denied):Q.check_cases(expected,records,len(records),0,0,0,0,0)

    def test_failure_expectedfailure_and_skip_never_pass(self):
        for index in range(5):
            counts=[0]*5;counts[index]=1
            with self.assertRaises(Q.Denied):Q.check_cases(['m.T.test_x'],[{'id':'m.T.test_x','outcome':'PASS'}],1,*counts)

    def test_zero_cases_cannot_report_qualification_success(self):
        with self.assertRaises(Q.Denied):Q.check_cases([],[],0,0,0,0,0,0)

    def test_actual_recovery_driver_preserves_phase_identity_from_component_data(self):
        def module(name,**values):
            item=types.ModuleType(name);item.__dict__.update(values);return item
        component={'schema':'unified.collector.offline-result.v1','scope':'SYNTHETIC_OFFLINE',
                   'phase':'STOPPED','child_pid':999,'status':'component-status','raw_observations_stored':3,
                   'native_outcome':'UNKNOWN','publication_confirmed':False,'provider_sends':0,
                   'service_running':False,'physical_accepted':False,'postgresql':'NOT_RUN','writer_closed':True}
        async def capture(*args,**kwargs):return dict(component)
        package=module('unified_system');package.__path__=[]
        storage=module('unified_system.storage');storage.__path__=[]
        modules={'unified_system':package,'unified_system.storage':storage,
          'test_profile':module('test_profile',fixture=lambda:{'context_id':'1'*32,'store_id':'synthetic'}),
          'unified_system.collector_profile':module('unified_system.collector_profile',validate_collector_profile=lambda *a,**k:object()),
          'unified_system.collector_offline':module('unified_system.collector_offline',collect_synthetic=capture,synthetic_frames=lambda:()),
          'unified_system.storage.collector_context':module('unified_system.storage.collector_context',CollectorContext=None,
             CollectorContextProfile=lambda **kwargs:object(),CollectorBlocked=RuntimeError),
          'unified_system.storage.raw_capture':module('unified_system.storage.raw_capture',RawCaptureProfile=lambda **kwargs:object()),
          'unified_system.storage.object_store':module('unified_system.storage.object_store',ObjectStore=None),
          'unified_system.journal':module('unified_system.journal',Journal=None),
          'sqlite3':module('sqlite3',connect=lambda *args,**kwargs:types.SimpleNamespace(
              execute=lambda sql:types.SimpleNamespace(fetchone=lambda:('ok',)),close=lambda:None))}
        result={'schema':'collector.phase-result.v1','phase':'FIRST','child_pid':123,'status':'FAILURE_OR_UNKNOWN'}
        fake=types.SimpleNamespace(raw_file=lambda *args:b'fixture')
        with patch.dict(sys.modules,modules):Q.recovery_phase(fake,'FIRST',ROOT,ROOT,ROOT/'inert.json',result)
        self.assertEqual(result['phase'],'FIRST')
        self.assertEqual(result['child_pid'],123)
        self.assertEqual(result['schema'],'collector.phase-result.v1')
        self.assertEqual(result['collector_result'],component)
        component['provider_sends']=1
        with patch.dict(sys.modules,modules),self.assertRaises(Q.Denied):
            Q.recovery_phase(fake,'FIRST',ROOT,ROOT,ROOT/'inert.json',dict(result))

    def test_manifest_permissions_are_exact_false_not_zero(self):
        doc={'schema':'unified.collector.integration-manifest.v1','execution_scope':'SYNTHETIC_OFFLINE',
             'permissions':{key:False for key in Q.PERMISSIONS},'new_components':[
                 {'owner':'A3','head':Q.INPUTS['grid'][0],'tree':Q.INPUTS['grid'][1]},
                 {'owner':'A5','head':Q.INPUTS['a5'][0],'tree':Q.INPUTS['a5'][1]}]}
        Q.check_manifest(doc)
        for bad in (True,0,None):
            doc['permissions']['real_provider_sends']=bad
            with self.assertRaises(Q.Denied):Q.check_manifest(doc)

    def test_old_grid_or_duplicate_owner_not_selected(self):
        doc={'schema':'unified.collector.integration-manifest.v1','execution_scope':'SYNTHETIC_OFFLINE',
             'permissions':{key:False for key in Q.PERMISSIONS},'new_components':[
                 {'owner':'A3','head':'53b842df817d37b006809d73f9b6195348d32cc2','tree':Q.INPUTS['grid'][1]},
                 {'owner':'A5','head':Q.INPUTS['a5'][0],'tree':Q.INPUTS['a5'][1]}]}
        with self.assertRaises(Q.Denied):Q.check_manifest(doc)
        doc['new_components'][0]['head']=Q.INPUTS['grid'][0]
        doc['new_components'].append(dict(doc['new_components'][0]))
        with self.assertRaises(Q.Denied):Q.check_manifest(doc)

    def test_overlay_is_one_explicit_file_not_whole_a5_merge(self):
        self.assertEqual(Q.A5_OVERLAY,'grid/owned_worker_service.py')
        self.assertEqual(Q.PINS[('a5',Q.A5_OVERLAY)],'81e3637799f7e43ead0e0c637d2ac96a3a0fd443f469277cbc8a77c8db109a12')
        self.assertNotIn(('a5','grid/worker.py'),Q.PINS)

    def test_adopted_root_bytes_must_match_reviewed_owner_pin(self):
        files={name:{'sha256':digest} for name,digest in Q.ADOPTED.items()}
        Q.check_adopted(files)
        files['unified_system/collector_logging.py']['sha256']='0'*64
        with self.assertRaises(Q.Denied):Q.check_adopted(files)

    def test_budget_clock_rollback_nonfinite_and_output_exhaustion_deny(self):
        self.assertEqual(Q.remaining_budget(1.0,2.0,0),(239.0,262144))
        for now,used in ((0.0,0),(float('nan'),0),(float('inf'),0),(2.0,262145)):
            with self.assertRaises(Q.Denied):Q.remaining_budget(1.0,now,used)

    def test_output_or_checkout_overlap_is_denied_before_any_directory_creation(self):
        paths={name:ROOT.parent/name for name in ('root','grid','a5','a4','logger','out')}
        args=['--parent']
        for name,path in paths.items():args.extend(['--'+name,str(path)])
        Q.cli(args)
        for target in (paths['root'],paths['root']/'bad-output',paths['root'].parent):
            altered=list(args);altered[altered.index('--out')+1]=str(target)
            with self.assertRaises(Q.Denied):Q.cli(altered)

    def test_success_exit_with_cleanup_unknown_never_passes(self):
        record={'returncode':0,'reason':None,'retired':True,'errors':[]}
        Q.check_capture('UNITS',record)
        for patch in ({'reason':'RETIREMENT_UNKNOWN'},{'retired':False},{'errors':['WAIT']},{'returncode':77}):
            with self.assertRaises(Q.Denied):Q.check_capture('UNITS',{**record,**patch})
        Q.check_capture('CRASH',{**record,'returncode':77})

    def test_stock_data_map_includes_top_level_runtime_dll_not_only_python_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'Lib').mkdir();(root/'vcruntime140.dll').write_bytes(b'INERT-DATA-NOT-A-DLL')
            fake=types.SimpleNamespace(ordinary=lambda path,*args,**kwargs:path)
            with patch.object(Q.sys,'base_prefix',str(root)),patch.object(Q.sysconfig,'get_path',return_value=str(root/'Lib')):
                value=Q.runtime_data(fake)
            self.assertIn('runtime/vcruntime140.dll',value['files'])

    def test_retained_hardlink_negative_fixture_is_data_not_source_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'one').write_bytes(b'OWN-INERT-FIXTURE');os.link(root/'one',root/'two')
            q=Q.bootstrap_helpers(ROOT)
            value=None;caught=None
            try:value=Q.evidence_index(q,root)
            except BaseException as exc:caught=type(exc).__name__
            self.assertIsNone(caught)
            self.assertEqual(set(value['files']),{'one','two'})
            self.assertEqual(value['files']['one']['sha256'],value['files']['two']['sha256'])
            self.assertEqual(value['files']['one']['link_count'],2)

    def test_no_old_raw_capture_58_configuration_changed(self):
        raw=(ROOT/'tools/raw_capture/qualify.py').read_bytes()
        import hashlib
        self.assertEqual(hashlib.sha256(raw).hexdigest(),Q.HELPER_SHA256)

    def test_workflow_is_readonly_five_checkout_pinned_and_no_dispatch(self):
        text=(ROOT/'.github/workflows/collector-offline-qualified.yml').read_text()
        self.assertIn('contents: read',text);self.assertIn('fail-fast: false',text)
        self.assertNotIn('workflow_dispatch:',text)
        self.assertEqual(text.count('persist-credentials: false'),5)
        for head,_ in Q.INPUTS.values():self.assertIn(head,text)
        for pin in ('11d5960a326750d5838078e36cf38b85af677262','a26af69be951a213d495a4c3e4e4022e16d87065','ea165f8d65b6e75b540449e92b4886f43607fa02'):self.assertIn(pin,text)
        self.assertIn('/evidence',text)


if __name__=='__main__':unittest.main()
