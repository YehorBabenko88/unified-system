import unittest,tempfile,hashlib,os,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unified_system.service_bootstrap import ActivationBlocked
from unified_system.service_source_admission import StartupSourceAdmission,MODULES

IDS={'unified_system','market_data','math','terminan'}

class CanonicalManagedSourceTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name).resolve()
        sources={}
        for module in IDS:
            relative='sources/'+module;(root/relative).mkdir(parents=True)
            sources[module]=dict(root=relative,commit='a'*40,tree='b'*40,version='0.1.0')
        files={}
        for relative in ('runtime/python.exe','runtime/git.exe','sources/unified_system/unified_system/service_entry.py','sources/unified_system/unified_system/owned_python.py'):
            p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'pure fixture, never executed')
            files[relative]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        manifest=dict(sources=sources,git='runtime/git.exe',files=files)
        grant=SimpleNamespace(code_root=root,require_current=lambda:True)
        return root,manifest,grant
    def test_four_roots_only_and_retired_sources_rejected(self):
        self.assertEqual(set(MODULES),IDS)
        root,manifest,grant=self.fixture();scope=StartupSourceAdmission(grant,{},manifest)
        self.assertEqual(scope.source_scope('market_data',root/'sources/market_data','a'*40),root/'sources/market_data')
        for old in ('grid','strattester','meta_analyse','unified-system'):
            with self.assertRaises(ActivationBlocked):scope.source_identity(old)
        self.assertFalse(hasattr(scope,'verification_launch'))
    def test_canonical_constructor_scope_does_not_ignore_extra_retired_sources(self):
        root,manifest,grant=self.fixture();manifest['sources']['grid']=manifest['sources']['market_data']
        with self.assertRaises(ActivationBlocked):StartupSourceAdmission(grant,{},manifest)
    def test_live_revocation_still_blocks_every_source_read(self):
        root,manifest,grant=self.fixture();live=[True];grant.require_current=lambda:live[0]
        scope=StartupSourceAdmission(grant,{},manifest);live[0]=False
        with self.assertRaises(ActivationBlocked):scope.source_identity('terminan')
    def test_readonly_serve_never_reads_retired_fleet_credentials(self):
        from unified_system import service_bootstrap as boot,lab_runtime
        root,manifest,grant=self.fixture()
        grant.profile=dict(runtime_config={},offline_context={});grant.computer_name='fixture'
        with patch.object(lab_runtime,'validate_config',return_value={}),patch.object(lab_runtime,'verify_sources'):
            self.assertEqual(boot._runtime_admission(grant,dict(manifest=manifest)),({},{}))

    def test_readonly_serve_still_refuses_source_or_grant_revocation(self):
        from unified_system import service_bootstrap as boot,lab_runtime
        root,manifest,grant=self.fixture()
        grant.profile=dict(runtime_config={},offline_context={});grant.computer_name='fixture'
        for revoked_source in (True,False):
            grant.require_current=lambda: (_ for _ in ()).throw(ActivationBlocked('ACTIVATION_REVOKED'))
            failure=ActivationBlocked('ACTIVATION_CODE_REJECTED') if revoked_source else None
            with self.subTest(source=revoked_source),patch.object(lab_runtime,'validate_config',return_value={}),patch.object(lab_runtime,'verify_sources',side_effect=failure),self.assertRaises(ActivationBlocked):
                boot._runtime_admission(grant,dict(manifest=manifest))

    def test_raw_entry_argument_parser_rejects_retired_modes_without_native_execution(self):
        from unified_system.service_entry import _valid_arguments
        for value in (['--data-first'],['--data-first-worker'],['--verify-module-source','strattester'],['--module-source','grid'],['--module-source','meta_analyse'],['--module-source','math']):
            with self.subTest(args=value):self.assertFalse(_valid_arguments(value))
        for value in ([],['--module-source','market_data'],['--module-source','terminan']):
            self.assertTrue(_valid_arguments(value))
    def test_raw_entry_bootstrap_pin_binds_actual_canonical_bytes(self):
        from unified_system import service_entry,service_bootstrap
        raw=Path(service_bootstrap.__file__).read_bytes()
        self.assertNotIn(b'\r\n',raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),service_entry.BOOTSTRAP_SHA256)
