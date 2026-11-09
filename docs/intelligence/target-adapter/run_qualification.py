"""Exact-source local target qualification; no scheduler/native admission."""
import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path

def main():
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.version_info[:3]==(3,12,10)
    root=Path(__file__).absolute().parents[3]
    helper=root/'docs/intelligence/identity/run_qualification.py'
    raw=helper.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='e3733379da5e0cde84573f3279d265c91e16eceb8c94aeeda8983b51031216fe'
    guard={'__name__':'owned_inventory','__file__':str(helper)}
    exec(compile(raw,str(helper),'exec'),guard)
    git=guard['git'];inventory=guard['inventory']
    assert git(root,'rev-parse','HEAD').decode().strip()==os.environ['EXPECTED_HEAD']
    stratt=Path(os.environ['TARGET_STRATT_ROOT']);meta=Path(os.environ['TARGET_META_ROOT'])
    assert git(stratt,'rev-parse','HEAD').decode().strip()=='aed8a7c8a952f96803c207d5e90b133969a47f04'
    assert git(meta,'rev-parse','HEAD').decode().strip()=='f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1'
    roots={'unified':root,'strattester':stratt,'meta_analyse':meta}
    before={name:inventory(path) for name,path in roots.items()}
    sys.path.insert(0,str(root))
    suite=unittest.TestLoader().discover(str(root/'tests/gateway_target_adapter'),pattern='test_direct.py')
    def ids(suite):
        result=[]
        for item in suite:result.extend(ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])
        return result
    actual=ids(suite)
    assert sorted(actual)==REQUIRED and len(actual)==len(set(actual))==22
    result=None;after=None
    out=Path(os.environ['RUNNER_TEMP'])/'target-adapter-evidence';out.mkdir(exist_ok=True)
    try:
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        assert result.wasSuccessful() and result.testsRun==22 and not result.skipped
        from unified_system.gateway_target_adapter import DisposableTargetStand,prepare_target,template_request
        request=json.dumps(template_request(),sort_keys=True,separators=(',',':')).encode()
        with tempfile.TemporaryDirectory(prefix='qualified-direct-target-') as stand_root:
            stand=DisposableTargetStand(stand_root,stratt_source_root=str(stratt),meta_source_root=str(meta))
            try:
                value=stand.execute(prepare_target(request),context=stand.local_test_context())
                assert value['status']=='DIRECT_TARGET_PASS' and stand.invocations==1
                assert stand.execute(prepare_target(request),context=stand.local_test_context())==value and stand.invocations==1
                result_raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
                artifact=json.dumps(value['result'],sort_keys=True,separators=(',',':')).encode()
                assert hashlib.sha256(artifact).hexdigest()=='f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940'
                (out/'prepared-request.json').write_bytes(request)
                (out/'direct-result.json').write_bytes(result_raw)
                (out/'actual-meta-result.json').write_bytes(artifact)
                (out/'local-journal.json').write_text(json.dumps(stand._journal.read(),indent=2)+'\n',encoding='utf-8')
            finally:stand.close()
    finally:
        after={name:inventory(path) for name,path in roots.items()}
        assert before==after
        receipt={'head':os.environ['EXPECTED_HEAD'],'python':sys.version,'tests':actual,
            'tests_run':None if result is None else result.testsRun,'skips':None if result is None else len(result.skipped),
            'source_before':before,'source_after':after,'scope':'DIRECT_DISPOSABLE_ONLY_NOT_SCHEDULER_AUTHENTICATED_OR_PHYSICAL',
            'actual_existing_target':'A7_EXECUTE_SYNTHETIC_RESEARCH_TO_META_ANALYZE_OHLCV_RESEARCH',
            'public_submit':'DENY','scheduler':'BLOCKED','publication':'LOCAL_UNATTESTED','native_admission':False}
        receipt['files']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.is_file() and p.name!='qualification.json'}
        (out/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')

REQUIRED = ['test_direct.DirectTests.test_actual_existing_target_and_reproducible_levels', 'test_direct.DirectTests.test_actual_owned_process_crash_before_and_after_calculation_stays_unknown', 'test_direct.DirectTests.test_actual_target_no_python_network_and_only_owned_sqlite', 'test_direct.DirectTests.test_cancel_after_actual_calculation_discards_result', 'test_direct.DirectTests.test_cancel_before_execution_has_no_invocation', 'test_direct.DirectTests.test_canonical_or_windows_drive_alias_sqlite_calibration', 'test_direct.DirectTests.test_claimed_native_authority_is_rejected_not_simulated', 'test_direct.DirectTests.test_concurrent_local_writer_refused', 'test_direct.DirectTests.test_duplicate_and_restart_returns_same_without_second_invocation', 'test_direct.DirectTests.test_fixed_profile_output_tampering_after_actual_target_refused', 'test_direct.DirectTests.test_idempotency_collision_refuses_without_target', 'test_direct.DirectTests.test_invalid_financial_units_after_actual_target_refused', 'test_direct.DirectTests.test_missing_or_foreign_local_context_denied', 'test_direct.DirectTests.test_oversized_output_after_actual_target_refused', 'test_direct.DirectTests.test_partial_journal_cannot_return_or_reexecute', 'test_direct.DirectTests.test_partial_or_wrong_units_after_actual_calculation_refused', 'test_direct.DirectTests.test_prompt_shell_order_parameters_and_duplicate_json_rejected', 'test_direct.DirectTests.test_registry_reports_unavailable_targets_truthfully', 'test_direct.DirectTests.test_scope_expiry_and_revocation_deny', 'test_direct.DirectTests.test_source_mismatch_fails_without_claimed_result_and_never_retries', 'test_direct.DirectTests.test_unknown_after_actual_calculation_is_retained_without_retry', 'test_direct.DirectTests.test_wrong_target_dataset_principal_scope_budget_schema_units']
if __name__=='__main__':main()
