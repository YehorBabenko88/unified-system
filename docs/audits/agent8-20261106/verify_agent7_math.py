"""Independent raw-Git source-preservation and compile-only red/green review."""
import hashlib,io,json,os,pathlib,re,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];repo=ROOT/'work/review7-math';out=ROOT/'outputs/phase4';base='5721987a15d20c3f9984d52eac4446704566d4b9';head='5f93cf91acc04c6561da2e940cad87f9ac41baf2'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(sha,path):return git('show',sha+':'+path)
def batch(sha,paths):
    paths=list(paths);data=subprocess.check_output(['git','-C',str(repo),'cat-file','--batch'],input=''.join(sha+':'+p+'\n' for p in paths).encode());stream=io.BytesIO(data);values={}
    for path in paths:
        oid,kind,size=stream.readline().split();assert kind==b'blob';values[path]=stream.read(int(size));assert stream.read(1)==b'\n'
    return values
old=json.loads(blob(base,'scripts/platform-source-proof.json'));new=json.loads(blob(head,'scripts/platform-source-proof.json'))
assert len(old['testFiles'])==len(new['testFiles'])==188
for field in old:
    if field!='addedFiles':assert old[field]==new[field],field
assert new['addedFiles']==old['addedFiles']+['tests/agent7-replay-research.test.mjs']
current=batch(head,new['destinations'])
for path,expected in new['destinations'].items():assert hashlib.sha256(current[path]).hexdigest()==expected,path
for original in new['testFiles']:
    reconstructed=b''.join(current[p['path']][p['start']:p['end']] for p in new['recipes'][original['path']])
    assert len(reconstructed)==original['bytes'] and hashlib.sha256(reconstructed).hexdigest()==original['sha256']
    assert hashlib.sha1(b'blob '+str(len(reconstructed)).encode()+b'\0'+reconstructed).hexdigest()==original['blob']
before=json.loads(blob(base,'scripts/platform-test-inventory.json'));after=json.loads(blob(head,'scripts/platform-test-inventory.json'))
assert after['tests'][:len(before['tests'])]==before['tests'] and len(after['tests'])==len(before['tests'])+8
extra=after['tests'][len(before['tests']):];assert all(r['platform']=='cross' and r['destination']=='tests/agent7-replay-research.test.mjs' for r in extra)
filename='tests/adminit-loader-facts.windows.mjs';old_text=blob(base,filename).decode();new_text=blob(head,filename).decode()
expected=old_text.replace("'tests/fixtures/adminit-containment/HostedLoaderEvents.cs');", "'tests/fixtures/adminit-containment/HostedLoaderEvents.cs','tests/fixtures/adminit-containment/HostedPrivateDesktop.cs');")
expected=expected.replace("$sources[0]+[Environment]::NewLine+$sources[3])", "$sources[0]+[Environment]::NewLine+$sources[3]+[Environment]::NewLine+$sources[7])")
assert expected==new_text,'CHANGE_BEYOND_TWO_COMPILE_INPUT_EDITS'
compile_results={}
temp=ROOT/'work/agent7-compile-scratch';temp.mkdir(exist_ok=True)
for label,text in [('baseline',old_text),('fixed',new_text)]:
    recipe=json.loads(re.search(r'const script=("(?:\\.|[^"\\])*");',text).group(1))
    assert ';$method=' in recipe
    compile_only=recipe.split(';$method=',1)[0]
    # Sources other than the recipe are unchanged by this PR; both variants read
    # the same exact-source clone, isolating only the two compile-input edits.
    env=os.environ.copy();env.update(LOADER_TEST_ROOT=str(repo),TEMP=str(temp),TMP=str(temp))
    p=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',compile_only],capture_output=True,timeout=30,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (out/('math-compile-'+label+'.stdout.log')).write_bytes(p.stdout);(out/('math-compile-'+label+'.stderr.log')).write_bytes(p.stderr)
    compile_results[label]={'exit_code':p.returncode,'recipe_sha256':hashlib.sha256(compile_only.encode()).hexdigest(),'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()}
assert compile_results['baseline']['exit_code']!=0 and compile_results['fixed']['exit_code']==0,compile_results
canonical=hashlib.sha256(json.dumps(old,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
assert canonical=='0696dd46d5386a532060220af8d491b6888e53d7a51082f9defca30684fc857e'
result={'head':head,'base':base,'tree':git('rev-parse',head+'^{tree}').decode().strip(),'original_files_reconstructed':188,'baseline_canonical_proof_sha256':canonical,'original_inventory_cases':len(before['tests']),'added_inventory_cases':8,'all_original_identities_preserved':True,'only_two_compile_inputs_changed':True,'compile_only_red_green':compile_results,'native_launch':'NOT_RUN','reported_0xC0000142':'NOT_RESOLVED_BY_COMPILE_ONLY_RESULT','scope':'RAW_GIT_PRESERVATION_AND_LOCAL_COMPILE_ONLY'}
(out/'math-source-and-compile-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
