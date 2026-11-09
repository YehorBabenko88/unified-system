import pathlib,subprocess
r=pathlib.Path.cwd();repo=r/'work/review-map55-c741';o=r/'outputs/phase105'
code='''import pathlib,types,unittest,json,hashlib,sys
root=pathlib.Path.cwd();file=root/'tests/gateway_jobs/test_target_native_mapping_proposal.py';raw=file.read_bytes();source=raw.decode()
guards=["    if native['original_actor_principal_id'] not in profile['principal_registry'].values():raise ValueError('ACTOR_REGISTRY_JOIN')\\n", "    if outer_bytes(q['resource_budget'])!=outer_bytes(load('target-v1-request.source.json')['resource_budget']):raise ValueError('PREFLIGHT_BUDGET_TYPES')\\n"]
for guard in guards:assert source.count(guard)==1;source=source.replace(guard,'')
forbidden=[]
def audit(event,args):
 if event in ['subprocess.Popen','sqlite3.connect','socket.connect','socket.getaddrinfo','os.system']:forbidden.append(event);raise AssertionError('PURE_META_EFFECT_FORBIDDEN')
sys.addaudithook(audit);m=types.ModuleType('_A8_GUARD_DELETION_META_ONLY');m.__file__=str(file);exec(compile(source,'A8_SCRATCH_NOT_PRIMARY_SOURCE','exec'),m.__dict__)
suite=unittest.TestSuite(m.TargetNativeProposal(name) for name in ['test_profile_principal_registry_mismatch_is_refused','test_float_budget_alias_refuses_even_with_rebound_hashes']);result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.testsRun==2 and len(result.failures)==2 and not result.errors and not result.skipped and not forbidden
print(json.dumps({'source_primary_sha256':hashlib.sha256(raw).hexdigest(),'scratch_sha256':hashlib.sha256(source.encode()).hexdigest(),'guards_deleted':guards,'expected_meta_failures':2,'observed_meta_failures':2,'native_calls':0,'scope':'SYNTHETIC_FINAL_SOURCE_GUARD_DELETION_NOT_HISTORICAL_RED_NOT_NATIVE_BUG'},indent=2))
'''
(o/'meta-controls-executed.py').write_text(code);p=subprocess.run([str(r/'work/mux-independent-env/Scripts/python.exe'),'-I','-B','-c',code],cwd=repo,capture_output=True,timeout=30);(o/'meta-controls.stdout.json').write_bytes(p.stdout);(o/'meta-controls.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr;print(p.stdout.decode())
