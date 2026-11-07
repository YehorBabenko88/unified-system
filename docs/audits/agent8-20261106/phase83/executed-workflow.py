import hashlib,io,json,os,pathlib,subprocess,sys

def main():
    root=pathlib.Path.cwd()
    git=pathlib.Path('C:/Program Files/Git/cmd/git.exe' if sys.platform=='win32' else '/usr/bin/git')
    def g(*args,input=None):
        return subprocess.check_output([str(git),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=root,input=input)
    assert sys.version_info[:3]==(3,12,10)
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix is None
    assert g('rev-parse','HEAD').decode().strip()==os.environ['EXPECTED_HEAD']
    def inventory():
        entries=[];dirs={''}
        for row in g('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
            if not row: continue
            meta,name=row.split(b'\t',1);mode,kind,oid=meta.split()
            assert mode in (b'100644',b'100755') and kind==b'blob'
            name=name.decode();entries.append((name,oid.decode()))
            dirs.update(p.as_posix() for p in pathlib.PurePosixPath(name).parents if p.as_posix()!='.')
        raw=g('cat-file','--batch',input=''.join(oid+'\n' for _,oid in entries).encode())
        stream=io.BytesIO(raw);result={}
        for name,oid in entries:
            actual,kind,size=stream.readline().split();data=stream.read(int(size))
            assert actual.decode()==oid and kind==b'blob' and stream.read(1)==b'\n'
            path=root/name
            assert path.is_file() and not path.is_symlink() and path.read_bytes()==data,name
            result[name]=hashlib.sha256(data).hexdigest()
        assert not stream.read()
        for path in root.rglob('*'):
            rel=path.relative_to(root)
            if rel.parts[0]=='.git': continue
            assert not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&1024),str(rel)
            if path.is_file(): assert rel.as_posix() in result and path.suffix not in ('.pyc','.pyo'),str(rel)
            elif path.is_dir(): assert rel.as_posix() in dirs,str(rel)
            else: raise AssertionError(str(rel))
        return result
    before=inventory()
    required=['test_front.FrontTests.test_actual_tls_catalog_not_identity_or_registered_tools', 'test_front.FrontTests.test_duplicate_headers_transfer_encoding_and_wrong_host_refused', 'test_front.FrontTests.test_head_errors_never_emit_response_body', 'test_front.FrontTests.test_head_no_body_unknown_path_and_body_on_catalog', 'test_front.FrontTests.test_invalid_path_query_and_unbounded_headers_refused', 'test_front.FrontTests.test_owned_shutdown_has_no_remaining_workers_or_restart', 'test_front.FrontTests.test_protected_route_ignores_forged_role_and_does_not_read_body', 'test_front.FrontTests.test_tls_peer_without_certificate_cannot_read_catalog', 'test_front.FrontTests.test_unverified_context_rejected_before_bind', 'test_intelligence_gateway.GatewayTests.test_book_request_not_silently_upgraded_to_available_history', 'test_intelligence_gateway.GatewayTests.test_catalog_closed_and_independent_copies', 'test_intelligence_gateway.GatewayTests.test_costs_exact_decimal_no_double_cost_assumption', 'test_intelligence_gateway.GatewayTests.test_depth_array_and_node_limits', 'test_intelligence_gateway.GatewayTests.test_duplicate_keys_nonfinite_and_oversized_input', 'test_intelligence_gateway.GatewayTests.test_every_runtime_tool_denied_even_claimed_admin', 'test_intelligence_gateway.GatewayTests.test_lookahead_overlapping_and_outside_periods_refused', 'test_intelligence_gateway.GatewayTests.test_query_budget_no_boolean_or_unbounded_page', 'test_intelligence_gateway.GatewayTests.test_query_canonical_digest_and_no_claim_of_data', 'test_intelligence_gateway.GatewayTests.test_query_rejects_unknown_versions_and_credentials', 'test_intelligence_gateway.GatewayTests.test_query_time_range_identity_and_units_strict', 'test_intelligence_gateway.GatewayTests.test_research_plan_is_deterministic_not_job_or_registry', 'test_intelligence_gateway.GatewayTests.test_research_production_and_forged_approval_refused', 'test_intelligence_gateway.GatewayTests.test_research_resource_exhaustion_refused', 'test_intelligence_gateway.GatewayTests.test_retrieved_prompt_text_is_data_not_permission', 'test_intelligence_gateway.GatewayTests.test_shell_orders_unknown_and_callable_never_executed']
    child="""import json,pathlib,sys,unittest
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix is None
root=pathlib.Path(sys.argv[1]);sys.path.insert(0,str(root))
suite=unittest.TestSuite()
for folder,name in (('tests','test_intelligence_gateway.py'),('tests/gateway_runtime','test_front.py')):
    suite.addTests(unittest.defaultTestLoader.discover(str(root/folder),pattern=name))
def collect(s):
    result=[]
    for item in s:
        result.extend(collect(item) if isinstance(item,unittest.TestSuite) else [item.id()])
    return result
ids=collect(suite);required=json.loads(sys.argv[2])
assert len(ids)==len(set(ids)) and set(ids)==set(required),(ids,required)
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun==len(required) and not result.skipped
"""
    result=None;after=None
    output=pathlib.Path(os.environ['RUNNER_TEMP'])/'gateway-runtime-front-evidence.json'
    try:
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',child,str(root),json.dumps(required)],cwd=root,timeout=180)
        assert result.returncode==0,result.returncode
    finally:
        try:
            after=inventory()
            assert before==after
        finally:
            output.write_text(json.dumps(dict(head=os.environ['EXPECTED_HEAD'],python=sys.version,tests=required,returncode=None if result is None else result.returncode,source_before=before,source_after=after,qualification='DISPOSABLE_TLS_FRONT_ONLY_NO_AUTHENTICATED_RESOURCE_ROUTES',native_authority=False,grants_node_operations=False),indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    main()
