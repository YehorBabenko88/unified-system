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
    def test_unported_operational_auth_fails_before_old_credential_reader(self):
        from unified_system import service_bootstrap as boot,lab_runtime
        root,manifest,grant=self.fixture()
        grant.profile=dict(runtime_config={},offline_context={});grant.computer_name='fixture'
        with patch.object(lab_runtime,'validate_config',return_value={}),patch.object(lab_runtime,'verify_sources'),patch.object(lab_runtime,'read_grid_auth',side_effect=AssertionError('retired authorization cannot be adopted')):
            with self.assertRaises(ActivationBlocked) as caught:boot._runtime_admission(grant,dict(manifest=manifest))
        self.assertEqual(caught.exception.code,'ACTIVATION_MARKET_DATA_AUTH_UNPORTED')

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
