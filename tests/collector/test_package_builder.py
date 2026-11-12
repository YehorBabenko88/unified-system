"""Inert file-copy tests; no runtime binary, service or capsule code executes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from unified_system import lab_release


def pin(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def source_pin(raw):return dict(pin(raw),blob_oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())


class PackageBuilderTests(unittest.TestCase):
    scratch_parent=None

    def setUp(self):
        self.assertIsNotNone(self.scratch_parent,'explicit retained scratch parent required')
        self.root=Path(self.scratch_parent)/self._testMethodName
        self.root.mkdir(exist_ok=False)
        self.inputs=self.root/'input';self.inputs.mkdir()
        self.counter=0
        self.make_fixture()
        path=REPO/'tools/collector/build_package.py'
        if not path.exists():self.fail('FEATURE_NOT_IMPLEMENTED: required package builder absent')
        spec=importlib.util.spec_from_file_location('collector_package_builder_test_subject',path)
        self.builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.builder)

    def make_fixture(self):
        m=dict(schema='unified.lab-release.collector.v1',mode='SYNTHETIC_OFFLINE',
            release_id='inert-copy-fixture',sequence=1,
            permissions={key:False for key in lab_release.COLLECTOR_PERMISSIONS},sources={},files={},
            directories=[],dependencies=[],collector_profile='collector.json',source_manifest='source-manifest.json',
            git='tools/git.exe',runtime={},overlays=[])
        payloads={
            'sources/unified-system/module.txt':b'inert unified source\n',
            'sources/grid/module.txt':b'inert grid source\n',
            'runtime/python/python.exe':b'INERT_NOT_EXECUTABLE_PYTHON\n',
            'tools/git.exe':b'INERT_NOT_EXECUTABLE_GIT\n',
            'dependencies/requirements.lock':b'python==3.12.10\n',
            'source-manifest.json':lab_release.canonical({'inert':True})}
        for name,repo in (('unified-system','unified-system'),('grid','bybit-cluster-grid')):
            path='sources/'+name+'/module.txt'
            m['sources'][name]=dict(repository='YehorBabenko88/'+repo,root='sources/'+name,
                commit='a'*40,tree='b'*40,version='1.0.0',dependencies={},file_pins={'module.txt':source_pin(payloads[path])})
        profile=dict(schema='unified.data-only-collector.profile.v1',mode='SYNTHETIC_OFFLINE',
            grid_launch_profile='grid.data-only-collector.v1',instrument_identity='synthetic-btcusdt-v1',
            source_manifest_sha256=pin(payloads['source-manifest.json'])['sha256'],
            network=dict(rest=False,websocket=False),
            features={key:False for key in ('trading','training','math','public_submit','authority_mutation')})
        payloads['collector.json']=lab_release.canonical(profile)
        m['files']={path:pin(raw) for path,raw in payloads.items()}
        m['directories']=sorted({parent.as_posix() for path in payloads for parent in Path(path).parents if str(parent)!='.'})
        lock=m['files']['dependencies/requirements.lock']['sha256']
        m['dependencies']=[dict(name='python',version='3.12.10',lock_path='dependencies/requirements.lock',lock_sha256=lock)]
        m['runtime']=dict(python=dict(path='runtime/python/python.exe',version='3.12.10',sha256=m['files']['runtime/python/python.exe']['sha256']),
                          lock=dict(path='dependencies/requirements.lock',sha256=lock))
        roles={'sources/unified-system/module.txt':'APPLICATION_SOURCE','sources/grid/module.txt':'APPLICATION_SOURCE',
               'runtime/python/python.exe':'PYTHON_RUNTIME','tools/git.exe':'GIT_TOOL',
               'dependencies/requirements.lock':'LOCK','source-manifest.json':'SOURCE_MANIFEST','collector.json':'COLLECTOR_PROFILE'}
        for path,raw in payloads.items():
            target=self.inputs/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        self.ledger=self.root/'runtime-ledger.json'
        self.ledger.write_bytes(lab_release.canonical(dict(files={'external-native/python.exe':m['files']['runtime/python/python.exe']},
            interpretation='INERT_UNIT_FIXTURE_NOT_RUNNABLE')))
        self.supplier=self.root/'native-source-root-data.json'
        self.supplier.write_bytes(lab_release.canonical({'supplier':'EXTERNAL_INERT_FIXTURE_NOT_ATTESTED'}))
        self.recipe=dict(schema='unified.collector.source-recipe.v1',manifest=m,
            input_roots={'input':dict(path=str(self.inputs),files=m['files'],directories=m['directories'])},
            members={path:dict(root='input',relative=path,role=roles[path],
                **({'ledger_path':'external-native/python.exe'} if roles[path]=='PYTHON_RUNTIME' else {})) for path in payloads},
            runtime_byte_ledger=dict(path=str(self.ledger),sha256=pin(self.ledger.read_bytes())['sha256']),
            native_source_root_data=dict(path=str(self.supplier),sha256=pin(self.supplier.read_bytes())['sha256']),
            limits=dict(unified_source_bytes=56*1024*1024,grid_source_bytes=3670016,
                        total_bytes=512*1024*1024,max_files=100000))

    def build(self):
        self.counter+=1
        recipe=self.root/('recipe-'+str(self.counter)+'.json')
        raw=lab_release.canonical(self.recipe);recipe.write_bytes(raw)
        return self.builder.build_package(recipe,recipe_sha256=pin(raw)['sha256'],
            work_root=self.root/('work-'+str(self.counter)),output_root=self.root/('output-'+str(self.counter)))

    def test_actual_copy_inventory_manifest_and_non_admission_receipt(self):
        result=self.build()
        capsule=Path(result['capsule_root'])
        checked=lab_release.verify_capsule(capsule,result['manifest_sha256'])
        self.assertEqual(checked['files_verified'],7)
        self.assertFalse(result['execution_authority'])
        self.assertFalse(result['service_admission'])
        self.assertEqual(result['native_supplier_provenance'],'EXTERNAL_NOT_ATTESTED')
        self.assertEqual((capsule/'runtime/python/python.exe').read_bytes(),b'INERT_NOT_EXECUTABLE_PYTHON\n')
        for name in ('source-recipe.json','file-inventory.json','build-receipt.json'):
            self.assertTrue((capsule.parent/name).is_file())

    def test_rejects_unknown_input_file_before_output(self):
        (self.inputs/'unknown.bin').write_bytes(b'x')
        with self.assertRaises(ValueError):self.build()
        self.assertFalse((self.root/'output-1').exists())

    def test_rejects_input_hash_drift(self):
        (self.inputs/'sources/grid/module.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.build()

    def test_rejects_role_scope_confusion(self):
        self.recipe['members']['sources/grid/module.txt']['role']='PYTHON_RUNTIME'
        self.recipe['members']['sources/grid/module.txt']['ledger_path']='external-native/python.exe'
        with self.assertRaises(ValueError):self.build()

    def test_rejects_runtime_ledger_mismatch(self):
        self.recipe['members']['runtime/python/python.exe']['ledger_path']='missing'
        with self.assertRaises(ValueError):self.build()

    def test_designated_python_cannot_bypass_runtime_ledger(self):
        self.recipe['manifest']['runtime']['python']['path']='tools/git.exe'
        self.recipe['manifest']['runtime']['python']['sha256']=self.recipe['manifest']['files']['tools/git.exe']['sha256']
        with self.assertRaises(ValueError):self.build()

    def test_total_input_count_includes_explicit_unused_members(self):
        extra=b'unused but explicitly inventoried\n'
        (self.inputs/'unused.bin').write_bytes(extra)
        self.recipe['input_roots']['input']['files']=dict(self.recipe['manifest']['files'],**{'unused.bin':pin(extra)})
        self.recipe['limits']['max_files']=7
        with self.assertRaises(ValueError):self.build()
        self.assertFalse((self.root/'output-1').exists())

    def test_total_byte_budget_covers_retained_work_and_output_and_metadata(self):
        self.recipe['limits']['total_bytes']=sum(v['bytes'] for v in self.recipe['manifest']['files'].values())+1
        with self.assertRaises(ValueError):self.build()
        self.assertFalse((self.root/'output-1').exists())

    def test_rejects_budget_overflow_before_output(self):
        self.recipe['limits']['grid_source_bytes']=1
        with self.assertRaises(ValueError):self.build()
        self.assertFalse((self.root/'output-1').exists())

    def test_rejects_hardlinked_input(self):
        import os
        os.link(self.inputs/'sources/grid/module.txt',self.root/'alias.txt')
        with self.assertRaises(ValueError):self.build()

    def test_reparse_stat_is_rejected_without_native_link_creation(self):
        target=self.inputs/'sources/grid/module.txt'
        actual=Path.lstat
        def facts(path,*args,**kwargs):
            if path==target:return SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=1024)
            return actual(path,*args,**kwargs)
        with patch.object(Path,'lstat',facts):
            with self.assertRaises(ValueError):self.build()
        self.assertFalse((self.root/'output-1').exists())

    def test_response_loss_after_stage_preserves_inactive_output_without_receipt_or_retry(self):
        actual=lab_release.stage_capsule;calls=[]
        def lose_response(*args,**kwargs):
            calls.append(args)
            actual(*args,**kwargs)
            raise OSError('synthetic response loss after real staging')
        with patch.object(lab_release,'stage_capsule',lose_response):
            with self.assertRaises(OSError):self.build()
        self.assertEqual(len(calls),1)
        self.assertTrue((self.root/'work-1/capsule/lab-release.json').is_file())
        self.assertTrue((self.root/'output-1/capsule/lab-release.json').is_file())
        self.assertFalse((self.root/'output-1/build-receipt.json').exists())

    def test_rejects_source_work_output_overlap(self):
        raw=lab_release.canonical(self.recipe);recipe=self.root/'overlap-recipe.json';recipe.write_bytes(raw)
        with self.assertRaises(ValueError):
            self.builder.build_package(recipe,recipe_sha256=pin(raw)['sha256'],
                work_root=self.inputs/'work',output_root=self.root/'out')

    def test_rejects_reusing_completed_output(self):
        result=self.build()
        recipe=self.root/'recipe-1.json';raw=recipe.read_bytes()
        with self.assertRaises(ValueError):
            self.builder.build_package(recipe,recipe_sha256=pin(raw)['sha256'],
                work_root=self.root/'unused-work',output_root=Path(result['capsule_root']).parent)

    def test_ordered_overlay_bytes_must_match_existing_manifest_verifier(self):
        new=b'actual final overlay bytes\n'
        target=self.inputs/'overlay/module.txt';target.parent.mkdir();target.write_bytes(new)
        self.recipe['input_roots']['input']['files']=dict(self.recipe['manifest']['files'],**{'overlay/module.txt':pin(new)})
        self.recipe['input_roots']['input']['directories']=sorted(self.recipe['manifest']['directories']+['overlay'])
        self.recipe['manifest']['overlays']=[dict(source='grid',commit='c'*40,tree='d'*40,files={'module.txt':source_pin(new)})]
        self.recipe['manifest']['files']['sources/grid/module.txt']=pin(new)
        self.recipe['members']['sources/grid/module.txt']['relative']='overlay/module.txt'
        result=self.build()
        self.assertEqual((Path(result['capsule_root'])/'sources/grid/module.txt').read_bytes(),new)
