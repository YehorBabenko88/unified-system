"""Bounded static four-path triage. Never print/export private key bytes."""
import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1];repo=root/'work/review7-meta_analyse';out=root/'outputs/phase16';out.mkdir(exist_ok=True)
head='88b45c328bfdc8131ff0c6d139fddd8b27a4050c';prefix='docs/commissioning_evidence_v3/tls-loopback/'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==head
def blob(path):return git('show',head+':'+path)
evidence=json.loads(blob('docs/commissioning_evidence_v3/EVIDENCE_HASHES.json'));indexed={i['path']:i['sha256'] for i in evidence['files']}
keys=[]
for name in ('ca','good','self','wrong'):
 path=prefix+name+'.key';data=blob(path);local=(repo/path).read_bytes();assert data==local
 # Only irreversible identifiers and classification leave memory; no PEM excerpts.
 sha=hashlib.sha256(data).hexdigest();keys.append({'path':path,'git_blob':git('rev-parse',head+':'+path).decode().strip(),'sha256':sha,'historical_hash_matches_git_bytes':indexed['tls-loopback/'+name+'.key']==sha,'historical_evidence_reference_present':True})
paths=git('ls-tree','-r','--name-only',head).decode().splitlines()
runtime=[p for p in paths if p.startswith(('src/','commissioning/','scripts/')) and p.endswith(('.py','.json','.toml','.ps1'))]
tokens=['tls-loopback','TLS audit CA','ca.pem','good.pem','self.pem','wrong.pem'];refs={}
for path in runtime:
 text=blob(path).decode(errors='replace');found=[t for t in tokens if t in text]
 if found:refs[path]=found
assert set(refs)<= {'scripts/s1_source_reference.json'}
audit=blob(prefix+'audit.py').decode();assert "asyncio.start_server(peer,'127.0.0.1',0,ssl=ctx)" in audit
assert "ssl.create_default_context(cafile=str(OUT/'ca.pem'))" in audit and "verify.check_hostname" in audit
notice=blob('docs/commissioning_evidence_v3/TLS_FIXTURES.txt').decode();assert 'Never install this test CA in an OS trust store' in notice
config=blob('pyproject.toml').decode();assert '[tool.setuptools.packages.find]\nwhere = ["src"]' in config
report={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'scope':'STATIC_FOUR_NAMED_FIXTURES_ONLY_NO_KEY_EXPORT_NO_RUNTIME_EXECUTION','keys':keys,'purpose':'PUBLICLY_COMMITTED_DISPOSABLE_LOOPBACK_TLS_TEST_FIXTURES','source_notice':'docs/commissioning_evidence_v3/TLS_FIXTURES.txt','fixture_generator':'audit.py generates2day localhost/wrong.invalid/selfsigned fixtures,loopback listener,explicit context trust','runtime_reference_files':refs,'system_trust_installation_in_fixture_script':'NO_CALL_IDENTIFIED_STATIC_ONLY','production_secret_or_deployment_usage':'NOT_ESTABLISHED','package_scope':{'Git_source_snapshot':'INCLUDES_FOUR_TRACKED_FIXTURES','setuptools_discovery':'src_ONLY_STATIC_CONFIG','built_wheel_installer_release_payload':'NOT_INSPECTED_NOT_QUALIFIED','primary_CI_artifact_paths':'public-platform/public-evidence/public-benchmark projections; four historical fixture paths not explicitly selected in main CI'},'required_release_rule':'Exclude exact historical TLS fixture prefix from deployable payload; reject these fixture credentials/testCA as operational trust material, verify final artifact inventory; preserve original evidence/sourceproof hashes and repository history. Source/audit archives may retain clearly labeled fixtures outside runtime installation.','severity':'INFORMATIONAL_HYGIENE_RECOMMENDATION_NO_CONFIRMED_PRODUCTION_SECRET_INCIDENT','key_material_exported':False,'keys_regenerated':False,'trust_or_network_changes':False,'overall':'NO_GO_EXISTING_GATES_UNCHANGED'}
(out/'tls-fixture-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
