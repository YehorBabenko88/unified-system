import pathlib,subprocess,io,ast,json,hashlib,base64,re
r=pathlib.Path.cwd();p=r/'work/review-resolver80-2ab';o=r/'outputs/phase156';before='47530d81e8b6f297a060a206bea6f783ccd0702e'
def git(*args,data=None):return subprocess.check_output(['git','-C',str(p),*args],input=data)
assert git('show','-s','--format=%T','HEAD').decode().strip()=='cff995cd8e6397c86e51e7cbcfdf896fe80ba689';rows=[]
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
 if row:
  meta,name=row.split(b'\t',1);rows.append((name.decode(),meta.split()[2]))
s=io.BytesIO(git('cat-file','--batch',data=b''.join(oid+b'\n' for _,oid in rows)))
for name,oid in rows:
 actual,kind,size=s.readline().split();raw=s.read(int(size));assert s.read(1)==b'\n' and actual==oid;(p/name).write_bytes(raw)
t=ast.parse((r/'work/phase121_qualify.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='inventory');ns={};exec('import pathlib,subprocess,os,hashlib,json,io',ns);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<inventory>','exec'),ns);inventory=ns['inventory'](p);assert len(inventory)==409
changed=git('diff','--name-only',before,'HEAD').decode().splitlines();assert len(changed)==4;(o/'exact-source-diff.patch').write_bytes(git('diff',before,'HEAD'))
harness=(p/'tests/fresh_render/harness.cjs').read_bytes();previous=git('show',before+':tests/fresh_render/harness.cjs');assert previous.replace(b'MAP * ~NOTFOUND, EXCLUDE localhost',b'MAP * ^NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1')==harness
hashes={}
for file in ['harness.cjs','bootstrap.cjs','diagnostics.cjs','owned_lifecycle.cjs','sync_spawn_guard.cjs']:
 raw=(p/'tests/fresh_render'/file).read_bytes();hashes[file]=hashlib.sha256(raw).hexdigest()
 if file!='harness.cjs':assert raw==git('show',before+':tests/fresh_render/'+file)
manifest=json.loads((p/'tests/fresh_render/CHROMIUM-141-SOURCE.json').read_bytes());primary=[]
for key,row in zip(['mapping','resolver'],manifest['sources']):
 j=json.loads((o/('Chromium141-'+key+'.original.json')).read_bytes());assert j['encoding']=='base64';raw=base64.b64decode(j['content']);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==j['sha']==row['git_blob'];primary.append(dict(path=row['path'],bytes=len(raw),sha256=row['sha256'],git_blob=j['sha'],independently_fetched_primary_matches=True))
a6=pathlib.Path('C:/Users/LS-5/Documents/Codex/2026-11-06/codex-agent-6-distributed-terminan-control/outputs/terminan-sync-v1/loopback-resolver');refs={}
for name in ['RESULTS-2ab52f8.json','loopback-resolver-29-complete.tap','PRIMARY-CHROMIUM-SOURCE.json']:
 raw=(a6/name).read_bytes();(o/name).write_bytes(raw);refs[name]=dict(original=str(a6/name),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
tap=(o/'loopback-resolver-29-complete.tap').read_text();assert len(re.findall(r'^ok \d+ - ',tap,re.M))==29 and '# pass 29' in tap and '# fail 0' in tap and '# skipped 0' in tap
(o/'source-verification.json').write_text(json.dumps(dict(PR=80,head='2ab52f86aca6a38bd63c1fea71e12a80a2c2ddd9',tree='cff995cd8e6397c86e51e7cbcfdf896fe80ba689',changed_paths=changed,primary_raw=inventory,noextras=True,hashes=hashes,runtime_delta='EXACT_ONE_LITERAL_RULE_REPLACEMENT_ONLY',primary_chromium=primary,owner_original_refs=refs,owner29='ORIGINAL_TAP_AUTHENTICATED_NOT_A8_EXECUTION_OR_FULL_RAW_PREPOST_REPLAY',A8_helper_module_fixture_native_Job_SDK_browser_DNSprobe_calls=0,result='SCOPED_F36_RESOLVER_SOURCE_CORRECTION_ACK_NOT_RUNTIME_OR_EGRESS_PROOF'),indent=2));print('409raw/noextras;one runtime literal;two independentprimaryblobs match;owner29notA8')
