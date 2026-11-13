"""Actual qualifier source-binding controls; no staging/app/import/native effects."""
import copy
import unittest

CONTEXT='unified_system/storage/collector_context.py'
CURRENT='84b52f42298c157a146f4937a06ff3d618e81c4c3e8ef9eab1a6974b38374165'
HISTORICAL='23525973fab305ad290c4120581b22767b1a00f5d344963130cf81fc7bf37aac'
CURRENT_OID='198e77d9efb81e7217170ee8d9fb13e393bc460a'

def make_suite(subject):
    class CurrentSourceTests(unittest.TestCase):
        def files(self):
            return {CONTEXT:dict(bytes=27665,sha256=CURRENT,oid=CURRENT_OID),
                'unified_system/storage/raw_capture.py':dict(bytes=13372,sha256='8af7b96a57f0b84329e8914fe40b41f3804c12722d87f906cb4d25c70e6e2174',oid='dcdde5ab58faabc43892befa4325ef568dc884d9'),
                'unified_system/collector_logging.py':dict(bytes=18309,sha256='0fabda35f20eb9480d2c1565914fcaac041c5d9e91167b55d5d94ccc546f1c71',oid='ab14bc0e657786133319b8c6fc74a4e5ba67eefc')}
        def accepts(self,files):
            try:subject.check_adopted(files)
            except subject.Denied:return False
            return True
        def test_current_root_successor_is_accepted(self):
            self.assertTrue(self.accepts(self.files()))
        def test_historical_supplier_is_not_accepted_as_current_root(self):
            files=self.files();files[CONTEXT]=dict(bytes=20085,sha256=HISTORICAL,oid='c80e32702512949c7224b4c237b437c28c370647')
            self.assertFalse(self.accepts(files))
        def test_historical_owner_pin_and_input_remain_exact(self):
            self.assertEqual(HISTORICAL,subject.PINS[('a4',CONTEXT)])
            self.assertEqual(('602cb6a66cab820947ef6915479c4490ff101358','0d7e2f71384f7a9d14127bd0c74d9f21e073ce04'),subject.INPUTS['a4'])
        def test_current_sha_size_or_oid_drift_denies(self):
            for key,value in (('sha256','0'*64),('bytes',27664),('oid','0'*40),('bytes',True)):
                with self.subTest(key=key,value=value):
                    files=self.files();files[CONTEXT][key]=value;self.assertFalse(self.accepts(files))
        def test_missing_current_source_denies(self):
            files=self.files();del files[CONTEXT];self.assertFalse(self.accepts(files))
        def test_other_historical_adoptions_remain_strict(self):
            for path in ('unified_system/storage/raw_capture.py','unified_system/collector_logging.py'):
                with self.subTest(path=path):
                    files=self.files();files[path]['sha256']='0'*64;self.assertFalse(self.accepts(files))
        def test_current_binding_retains_lossless_separate_provenance(self):
            facts=subject.check_adopted(self.files());self.assertIs(type(facts),list);self.assertEqual(1,len(facts));row=facts[0]
            self.assertEqual(CONTEXT,row['path']);self.assertEqual(CURRENT,row['sha256']);self.assertEqual(27665,row['bytes']);self.assertEqual(CURRENT_OID,row['oid'])
            self.assertEqual('root',row['origin_role']);self.assertEqual('e2e0adf0fd68ef5446913fda6f003c249d335a32',row['source_owner_head'])
            self.assertEqual('1e734fe9b9dfa04c1576a27cadd5837cbf8a1a4b',row['root_adoption_commit'])
            self.assertEqual('a4',row['historical_supplier_role']);self.assertEqual(subject.INPUTS['a4'][0],row['historical_supplier_head']);self.assertEqual(HISTORICAL,row['historical_supplier_sha256'])
            self.assertIs(False,row['replacement_in_stage'])
    CurrentSourceTests.__module__=__name__;CurrentSourceTests.__qualname__=CurrentSourceTests.__name__
    return unittest.defaultTestLoader.loadTestsFromTestCase(CurrentSourceTests)

def load_tests(loader, tests, pattern):
    """Standard discovery executes this SAME current Root qualifier, never CLI."""
    import importlib
    import types
    from pathlib import Path
    root=Path(__file__).absolute().parents[2]
    current=None
    for name,relative,package in (('tools','tools/__init__.py',True),
        ('tools.collector','tools/collector/__init__.py',True),
        ('tools.collector.qualify','tools/collector/qualify.py',False)):
        module=importlib.import_module(name);expected=str(root/relative)
        spec=getattr(module,'__spec__',None)
        if (type(module) is not types.ModuleType or module.__name__!=name or
            getattr(module,'__file__',None)!=expected or spec is None or spec.name!=name or
            spec.origin!=expected or spec.loader is None or
            (package and list(spec.submodule_search_locations or ())!=[str((root/relative).parent)])):
            raise RuntimeError('CURRENT_QUALIFIER_SOURCE_REQUIRED')
        current=module
    return make_suite(current)