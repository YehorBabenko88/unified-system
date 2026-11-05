"""Adversarial checks for the mandatory synthetic causal CI gate."""
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CausalGateTests(unittest.TestCase):
    def module(self):
        path=ROOT/'scripts/ci_paper_causal.py'
        self.assertTrue(path.is_file(), 'mandatory causal CI gate is missing')
        spec=importlib.util.spec_from_file_location('_paper_ci_gate',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_closed_inventory_has_exact_sixteen_unique_cases(self):
        m=self.module();self.assertEqual(len(m.EXPECTED_IDS),16)
        self.assertEqual(len(set(m.EXPECTED_IDS)),16)
        with self.assertRaises(m.GateRejected):m.require_inventory(list(m.EXPECTED_IDS)[:-1])
        with self.assertRaises(m.GateRejected):m.require_inventory(list(m.EXPECTED_IDS)+[m.EXPECTED_IDS[0]])
        m.require_inventory(list(reversed(m.EXPECTED_IDS)))

    def test_any_skip_or_missing_started_case_rejects_success(self):
        m=self.module()
        class Case(unittest.TestCase):
            def runTest(self):self.skipTest('mandatory dependency absent')
        result=m.CausalResult();Case().run(result)
        with self.assertRaises(m.GateRejected):m.require_success(result,('test_ci_paper_causal.CausalGateTests',))
        result=m.CausalResult();result.testsRun=16
        with self.assertRaises(m.GateRejected):m.require_success(result,m.EXPECTED_IDS)

    def test_actual_failure_cannot_be_reported_as_pass(self):
        m=self.module()
        class Case(unittest.TestCase):
            def runTest(self):self.fail('actual negative assertion')
        result=m.CausalResult();case=Case();case.run(result)
        with self.assertRaises(m.GateRejected):m.require_success(result,(case.id(),))

    def test_source_snapshot_proves_origin_head_cleanliness_and_raw_bytes(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'candidate';root.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
            git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
            git('remote','add','origin','https://github.com/YehorBabenko88/Terminan.git')
            (root/'tracked.py').write_bytes(b'first\n');git('add','tracked.py');git('commit','-m','synthetic')
            head=git('rev-parse','HEAD');one=m.source_snapshot(root,'Terminan',head)
            self.assertEqual(one['head'],head);self.assertEqual(len(one['tracked_raw_sha256']),64)
            with self.assertRaises(m.GateRejected):m.source_snapshot(root,'Terminan','a'*40)
            with self.assertRaises(m.GateRejected):m.source_snapshot(root,'strattester',head)
            (root/'tracked.py').write_bytes(b'changed\n')
            with self.assertRaises(m.GateRejected):m.source_snapshot(root,'Terminan',head)
            git('checkout','--','tracked.py');(root/'injected.py').write_text('x=1')
            with self.assertRaises(m.GateRejected):m.source_snapshot(root,'Terminan',head)

    def test_output_must_be_outside_every_source_checkout(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'repo';root.mkdir()
            with self.assertRaises(m.GateRejected):m.require_external_output(root/'report.json',[root])
            with self.assertRaises(m.GateRejected):m.require_external_output(root,[root])
            m.require_external_output(Path(temporary)/'evidence/report.json',[root])

    def test_source_change_after_tests_rejects_qualification(self):
        m=self.module();before={'grid':{'head':'a'*40,'tracked_raw_sha256':'b'*64}}
        m.require_unchanged(before,before.copy())
        with self.assertRaises(m.GateRejected):m.require_unchanged(before,{'grid':{'head':'a'*40,'tracked_raw_sha256':'c'*64}})

    def test_isolated_test_dependencies_reject_missing_version_or_pth_preload(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with self.assertRaises(m.GateRejected):m.dependencies_snapshot(root)
            for name,version in m.TEST_DEPENDENCIES.items():
                info=root/(name+'-'+version+'.dist-info');info.mkdir()
                (info/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n')
            one=m.dependencies_snapshot(root);self.assertEqual(one['versions'],m.TEST_DEPENDENCIES)
            (root/'preload.pth').write_text('import unexpected')
            with self.assertRaises(m.GateRejected):m.dependencies_snapshot(root)

if __name__=='__main__':unittest.main()
