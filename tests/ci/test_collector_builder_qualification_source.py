"""Pure source/guard tests; no qualified child, fixture I/O or native service."""
import ast
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


class BuilderQualificationSourceTests(unittest.TestCase):
    def subject(self):
        path=ROOT/'tools/collector/qualify_builder.py'
        self.assertTrue(path.is_file(),'FEATURE_NOT_IMPLEMENTED: dedicated builder lane absent')
        spec=importlib.util.spec_from_file_location('builder_lane_source_subject',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_fixed_case_ids_and_limits(self):
        module=self.subject()
        self.assertEqual(len(module.EXPECTED_IDS),15)
        self.assertEqual(len(set(module.EXPECTED_IDS)),15)
        self.assertEqual((module.CHILD_SECONDS,module.OUTPUT_CAP),(120,262144))
        self.assertEqual(module.HELPER_SHA,'b4fdd6cc2dea47a4fe8da0ce400004a20e36d4f401fb9bb37d20c0a597857df5')

    def test_hardlink_is_only_the_single_declared_fixture_pair(self):
        module=self.subject()
        root=Path(ROOT.anchor)/'owned-builder-source-test'
        source=root/'test_rejects_hardlinked_input/input/sources/grid/module.txt'
        target=root/'test_rejects_hardlinked_input/alias.txt'
        self.assertTrue(module.hardlink_scope(root,source,target,-1,-1))
        self.assertFalse(module.hardlink_scope(root,source,root/'other.txt',-1,-1))
        self.assertFalse(module.hardlink_scope(root,ROOT/'tools/collector/build_package.py',target,-1,-1))
        self.assertFalse(module.hardlink_scope(root,source,target,0,-1))
        self.assertFalse(module.hardlink_scope(root,'relative',target,-1,-1))

    def test_case_outcomes_cannot_hide_skips_or_duplicate_ids(self):
        module=self.subject()
        records=[{'id':name,'outcome':'PASS'} for name in module.EXPECTED_IDS]
        module.require_results(records,15,0,0,0,0,0)
        with self.assertRaises(ValueError):module.require_results(records,15,0,0,1,0,0)
        with self.assertRaises(ValueError):module.require_results(records[:-1]+[records[0]],15,0,0,0,0,0)

    def test_unknown_hardlink_is_rejected_before_delegate(self):
        module=self.subject();calls=[];blocked=[]
        root=Path(ROOT.anchor)/'owned-builder-source-test'
        class Q:
            @staticmethod
            def owned_effect_guard(*args):return lambda *args:calls.append(args)
        guard=module.make_guard(Q,root,root/'result.json',blocked)
        with self.assertRaises(ValueError):guard('os.link',(str(root/'other'),str(root/'alias'),-1,-1))
        self.assertEqual(calls,[])
        self.assertEqual(blocked,['os.link'])

    def test_uses_existing_helpers_not_a_new_verifier_or_installer(self):
        self.subject()
        raw=(ROOT/'tools/collector/qualify_builder.py').read_text()
        tree=ast.parse(raw)
        self.assertFalse(any(isinstance(node,ast.ClassDef) and node.name.endswith(('SourceGate','Broker')) for node in ast.walk(tree)))
        for token in ('q.primary(', 'q.capture(', 'q.owned_effect_guard(', 'c.runtime_data(', 'c.project_origins(', 'c.check_cases('):
            self.assertIn(token,raw)
        self.assertNotIn('stage_capsule(',raw)

    def test_workflow_is_pr_only_pinned_and_explicit(self):
        path=ROOT/'.github/workflows/collector-builder-qualified.yml'
        self.assertTrue(path.is_file(),'FEATURE_NOT_IMPLEMENTED: workflow absent')
        raw=path.read_text()
        self.assertIn('pull_request:',raw)
        self.assertNotIn('workflow_dispatch:',raw)
        self.assertNotIn('\n  push:',raw)
        self.assertIn('contents: read',raw)
        self.assertIn('windows-latest',raw)
        self.assertIn('ubuntu-24.04',raw)
        self.assertIn("python-version: '3.12.10'",raw)
        self.assertIn('qualify_builder.py',raw)
        self.assertIn('ref: ${{ github.event.pull_request.head.sha }}',raw)
        for action in ('actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
                       'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
                       'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'):
            self.assertIn(action,raw)
