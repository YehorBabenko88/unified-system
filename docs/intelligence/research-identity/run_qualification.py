"""Exact primary raw sources before/after; actual owned native tests only."""
raise RuntimeError('NATIVE_QUALIFICATION_PREREQUISITES_LOCKED')
import argparse,hashlib,json,os,pathlib,subprocess,sys,types,unittest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expected-head',required=True);parser.add_argument('--grid-source',required=True);args=parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None
    root=pathlib.Path(__file__).absolute().parents[3];grid=pathlib.Path(args.grid_source).absolute()
    def git(path,*argv):return subprocess.check_output(['git','--no-replace-objects','-C',str(path),*argv])
    raw=git(root,'show','f155126a95e80139b1b9679c1870ffd66c29360e:docs/intelligence/identity/run_qualification.py')
    assert hashlib.sha256(raw).hexdigest()=='e3733379da5e0cde84573f3279d265c91e16eceb8c94aeeda8983b51031216fe'
    guard=types.ModuleType('primary_guard');exec(compile(raw,'<pinned-primary-guard>','exec'),guard.__dict__)
    for ancestor in (pathlib.Path(__file__).absolute(),*pathlib.Path(__file__).absolute().parents):guard.ordinary(ancestor)
    assert git(root,'rev-parse','HEAD').decode().strip()==args.expected_head
    assert git(grid,'rev-parse','HEAD').decode().strip()=='40e9c8dc274a2746018bc1aa08d103cd0187cecc'
    before=guard.inventory(root);grid_before=guard.inventory(grid)
    os.environ['A2_RESEARCH_GRID_SOURCE']=str(grid)
    sys.path[:0]=[str(root),str(root/'tests/gateway_research_identity')]
    suite=unittest.defaultTestLoader.discover(str(root/'tests/gateway_research_identity'),pattern='test_*.py')
    def ids(s):
        for test in s:
            if isinstance(test,unittest.TestSuite):yield from ids(test)
            else:yield test.id()
    actual=list(ids(suite))
    expected={
        'test_broker.BrokerBoundaryTests.'+name for name in (
        'test_missing_or_method_shaped_authority_never_authenticates','test_context_and_capture_have_no_public_constructor','test_native_session_syntax_is_distinct_and_never_a_permission')}
    expected.update('test_native_broker.NativeBrokerTests.'+name for name in (
        'test_actual_mtls_native_session_and_sealed_capture','test_actual_native_policy_revocation_and_session_invalidation',
        'test_forward_utc_jump_expires_real_issued_capture','test_shortened_native_policy_expiry_bounds_new_capture',
        'test_acl_default_deny_client_cannot_write_policy','test_close_during_actual_native_create_retires_owned_session',
        'test_read_scope_cannot_be_upgraded_by_request','test_invalidate_latches_and_stale_capture_is_no_permission',
        'test_stale_policy_capture_fails_actual_native_cas','test_real_foreign_native_session_cannot_rebind_issued_context',
        'test_audit_full_invalidation_still_destroys_own_native_session','test_z_real_one_of_three_no_quorum_is_unavailable'))
    assert len(actual)==len(set(actual))==15 and set(actual)==expected
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert guard.inventory(root)==before and guard.inventory(grid)==grid_before
    assert result.wasSuccessful() and result.testsRun==15 and not result.skipped
    print(json.dumps(dict(result='PASS',head=args.expected_head,tree=git(root,'rev-parse','HEAD^{tree}').decode().strip(),grid_head='40e9c8dc274a2746018bc1aa08d103cd0187cecc',raw_files=len(before),grid_raw_files=len(grid_before),tests=15,skips=0,scope='DISPOSABLE_RESEARCH_PRINCIPAL_NOT_JOB_WORKER_OR_PUBLIC_SUBMIT')))
if __name__=='__main__':main()