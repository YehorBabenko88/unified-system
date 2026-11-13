"""Pure command/diagnostic contracts; no PowerShell or native/service API call.

Existing test methods run only with inert run_phased/tools/system-directory seams.
This is diagnostic Source coverage, never native behavior acceptance.
"""
import re
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests import native_phase_diagnostics as diag
from tests import test_installation_native_diagnostic as native
from tests import test_installation_service as installation
from unified_system import installation_service as service

OBSERVED_BARE={}

class NativePhaseProbeContractTests(unittest.TestCase):
    def capture(self,kind,fail=False):
        calls=[]
        with tempfile.TemporaryDirectory(prefix='inert-phase-contract-') as temp:
            root=Path(temp);marker=root/'autoload-marker'
            def runner(argv,*,env,timeout=15):
                calls.append((tuple(argv),dict(env),timeout))
                bare=re.sub(r"\[Console\]::Error\.WriteLine\('UNIFIED_PHASE:[A-Z_]+:'\+\[Diagnostics\.Stopwatch\]::GetTimestamp\(\)\);",'',argv[-1]).strip().rstrip(';').strip()
                OBSERVED_BARE.setdefault(kind,set()).add(hashlib.sha256(bare.encode()).hexdigest())
                if fail:raise AssertionError('INERT_FATAL_TIMEOUT')
                if 'CONTROL_LOOKUP_BEGIN' in argv[-1]:marker.write_text('INERT_CONTROL',encoding='ascii')
                return subprocess.CompletedProcess(argv,0,b'INERT_NSSM_BOOTSTRAP_VERIFIED EXIT_FACT_VERIFIED POISON_NOT_FOUND DECLARATIONS_COMPILED UNICODE_AND_OUTPUT_BOUND_VERIFIED',b'')
            cases={'NSSM':(native.NativeDiagnosticTests,'test_new_nssm_bootstrap_seeds_only_application_and_never_adopts_parameters'),'EXIT':(native.NativeDiagnosticTests,'test_real_child_exit_code_without_service_or_acl_operations'),'LOOKUP':(installation.ServiceResourceTests,'test_poisoned_parent_module_path_cannot_autoload_user_module'),'COMPILE':(installation.ServiceResourceTests,'test_real_module_parses_and_native_declarations_compile_without_api_calls')}
            cls,name=cases[kind];case=cls(name);case.root=root
            method=getattr(cls,name)
            # Only bypass the OS decorator for THIS inert command-construction
            # fixture. All actual native tests keep their original decorators.
            method=getattr(method,'__wrapped__',method)
            system=Path('C:/INERT/Windows/System32');ps=str(Path('C:/INERT/powershell.exe'))
            with patch.object(service,'_system_directory',return_value=system),patch.object(service,'_native_tools',return_value={'powershell':{'path':ps}}),patch.object(diag,'run_phased',side_effect=runner),patch.object(native,'run_phased',side_effect=runner):
                method(case)
        return calls
    def names(self,command):return re.findall(r'UNIFIED_PHASE:([A-Z_]+):',command)
    def test_actual_nssm_callsite_separates_members_seed_and_foreign_reject(self):
        command=self.capture('NSSM')[0][0][-1];names=self.names(command)
        for name in ('OTHER_MEMBERS_BEGIN','OTHER_MEMBERS_END','SEED_BEGIN','SEED_END','FOREIGN_REJECT_BEGIN','FOREIGN_REJECT_END'):self.assertIn(name,names)
        self.assertLess(names.index('FIRST_MEMBER_END'),names.index('OTHER_MEMBERS_BEGIN'));self.assertLess(names.index('SEED_END'),names.index('FOREIGN_REJECT_BEGIN'))
    def test_actual_lookup_callsites_separate_lookup_catch_and_write(self):
        control,safe=self.capture('LOOKUP');self.assertIn('CONTROL_LOOKUP_BEGIN',self.names(control[0][-1]));names=self.names(safe[0][-1])
        for name in ('LOOKUP_CALL_BEGIN','LOOKUP_CALL_END','LOOKUP_CATCH_BEGIN','LOOKUP_WRITE_BEGIN','LOOKUP_WRITE_END','LOOKUP_CATCH_END'):self.assertIn(name,names)
        self.assertEqual(control[2],15);self.assertEqual(safe[2],15)
        self.assertNotEqual(control[1]['PSModulePath'],safe[1]['PSModulePath']);self.assertEqual(safe[1]['PSModulePath'],str(Path('C:/INERT/Windows/System32/WindowsPowerShell/v1.0/Modules')))
    def test_actual_exit_callsite_separates_catch_and_exit_fact(self):
        names=self.names(self.capture('EXIT')[0][0][-1])
        for name in ('CHILD_EXCEPTION','EXIT_FACT_BEGIN','EXIT_FACT_END'):self.assertIn(name,names)
    def test_actual_compile_callsite_separates_output_and_child_setup(self):
        command=self.capture('COMPILE')[0][0][-1];names=self.names(command)
        for name in ('COMPILE_OUTPUT_BEGIN','COMPILE_OUTPUT_END','CHILD_SETUP_BEGIN','CHILD_SETUP_END'):self.assertIn(name,names)
        self.assertLess(names.index('COMPILE_END'),names.index('COMPILE_OUTPUT_BEGIN'));self.assertLess(names.index('CHILD_SETUP_END'),names.index('UNICODE_BEGIN'))
    def test_actual_callsites_keep_selectors_bounds_and_closed_phase_budget(self):
        for kind in ('NSSM','EXIT','LOOKUP','COMPILE'):
            for argv,env,timeout in self.capture(kind):
                with self.subTest(kind=kind):
                    self.assertEqual(argv[:4],(str(Path('C:/INERT/powershell.exe')),'-NoProfile','-NonInteractive','-Command'));self.assertEqual(timeout,30 if kind=='COMPILE' else 15)
                    self.assertEqual(env['PSModulePath'],str(Path('C:/INERT/Windows/System32/WindowsPowerShell/v1.0/Modules')) if 'CONTROL_LOOKUP_BEGIN' not in argv[-1] else env['PSModulePath'])
                    names=self.names(argv[-1]);self.assertLessEqual(len(names),16);self.assertTrue(set(names)<=diag.PHASES)
                    self.assertNotIn('Import-Module Microsoft.PowerShell.Utility',argv[-1]);self.assertNotIn('PSModuleAutoLoadingPreference',argv[-1])
    def test_fatal_runner_error_propagates_through_actual_callsites(self):
        for kind in ('NSSM','EXIT','LOOKUP','COMPILE'):
            with self.subTest(kind=kind),self.assertRaisesRegex(AssertionError,'INERT_FATAL_TIMEOUT'):self.capture(kind,fail=True)
    def test_actual_shared_builder_rejects_unknown_kind_missing_or_duplicate_anchor(self):
        build=getattr(diag,'build_ps_probe',None);self.assertTrue(callable(build),'NEW_BUILDER_API_ABSENT')
        for kind,command in [('FOREIGN','x'),('NSSM_BOOTSTRAP','x'),('SAFE_LOOKUP',"try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch{Write-Output 'POISON_NOT_FOUND'}"*2)]:
            with self.subTest(kind=kind),self.assertRaises(ValueError):build(kind,command)
    def test_new_phase_names_are_closed_and_private_text_rejected(self):
        for name in ('LOOKUP_CATCH_BEGIN','LOOKUP_WRITE_BEGIN','COMPILE_OUTPUT_BEGIN','CHILD_SETUP_BEGIN','FOREIGN_REJECT_END'):
            with self.subTest(name=name):self.assertIn(name,diag.PHASES)
        for value in (b'PRIVATE_NATIVE_PATH',b'UNIFIED_PHASE:PRIVATE_ENV:1',b'x'*4097):self.assertEqual(diag.phase_summary(value),'PHASE_DATA_REJECTED')
    def test_actual_run_phased_timeout_keeps_failure_private_and_bound(self):
        error=subprocess.TimeoutExpired(['INERT'],15,output=b'PRIVATE_STDOUT',stderr=b'PRIVATE_STDERR')
        with patch.object(diag.subprocess,'run',side_effect=error) as run:
            with self.assertRaises(AssertionError) as caught:diag.run_phased(['INERT'],env={'INERT':'1'})
        self.assertNotIn('PRIVATE',str(caught.exception));self.assertIn('NATIVE_PHASE_TIMEOUT_15S',str(caught.exception));self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(run.call_args.kwargs['timeout'],15)
    def test_actual_run_phased_nonzero_never_accepts_private_stderr(self):
        result=subprocess.CompletedProcess(['INERT'],1,b'PRIVATE_OUT',b'PRIVATE_ERR')
        with patch.object(diag.subprocess,'run',return_value=result):
            with self.assertRaises(AssertionError) as caught:diag.run_phased(['INERT'],env={})
        self.assertNotIn('PRIVATE',str(caught.exception));self.assertIn('NATIVE_PHASE_EXIT_NONZERO',str(caught.exception))
    def test_actual_run_phased_valid_expanded_frames_stay_bounded(self):
        names=('ENTRY','SAFE_LOOKUP_BEGIN','LOOKUP_CALL_BEGIN','LOOKUP_CATCH_BEGIN','LOOKUP_WRITE_BEGIN','LOOKUP_WRITE_END','LOOKUP_CATCH_END','SAFE_LOOKUP_END','DONE')
        raw='\n'.join('UNIFIED_PHASE:'+n+':1' for n in names).encode();result=subprocess.CompletedProcess(['INERT'],0,b'INERT',raw)
        with patch.object(diag.subprocess,'run',return_value=result):self.assertIs(diag.run_phased(['INERT'],env={}),result)
    def test_unknown_diagnostic_bound_never_reaches_runner(self):
        for timeout in (True,0,16,31):
            with patch.object(diag.subprocess,'run') as run,self.assertRaises(ValueError):diag.run_phased(['INERT'],env={},timeout=timeout)
            run.assert_not_called()
