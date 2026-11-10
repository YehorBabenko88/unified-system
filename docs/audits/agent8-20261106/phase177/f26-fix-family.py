import os,pathlib,subprocess,time,json,hashlib,shutil
root=pathlib.Path(__file__).resolve().parent.parent
source=root/'work/f26-fix-qualification-source'
output=root/'outputs/f26-fix-qualification-20261110'
output.mkdir(exist_ok=False)
python='C:/Users/LS-5/AppData/Local/Python/pythoncore-3.12-64/python.exe'
start=time.monotonic();results=[]
for case in ('P','M','N'):
    remaining=88-(time.monotonic()-start)
    if remaining<5:raise RuntimeError('FAMILY_BUDGET')
    env=dict(os.environ,RUNNER_TEMP=str(output),EXPECTED_HEAD='ab9362706cd8cd75b2fc0f5177481a96a5f73ac4',QUAL_CASE=case,CASE_SAFETY_SECONDS=str(min(84,remaining-2)))
    with (output/(case+'-process.log')).open('wb') as log:
        p=subprocess.run([python,'-I','-S','-B',str(root/'work/f26-fix-qualification.py')],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=remaining)
    receipt=json.loads((output/('f26-fix-'+case)/'receipt.json').read_text(encoding='utf8'))
    events=json.loads((output/('f26-fix-'+case)/'per-call-phases.json').read_text(encoding='utf8'))['events']
    outcome=receipt['outcomes'][0]
    text=(output/('f26-fix-'+case)/(case+'-tests.log')).read_text(encoding='utf8')
    clean=receipt['source_unchanged'] and not receipt['harness_error'] and not receipt['scope_violation'] and receipt['lane']=='RETIRED' and p.returncode==0
    if case=='M':
        causal=receipt['mutant_invocations']>0 and 'renewed.get(timeout=3),True' in text and 'False is not True' in text and not any(e['phase']=='APP_CALL' and e['completed'] for e in events)
        classification='ORACLE_CAUSAL_REJECTION' if clean and causal and outcome['failures']==1 and outcome['errors']==0 else 'ORACLE_INCONCLUSIVE'
    else:classification='PASS' if clean and outcome['tests']==1 and outcome['failures']==0 and outcome['errors']==0 and outcome['skips']==0 else 'FAIL'
    results.append(dict(case=case,classification=classification,outcome=outcome,mutant_invocations=receipt['mutant_invocations'],returncode=p.returncode))
    print(json.dumps(results[-1]),flush=True)
    if not clean:break
summary=dict(head='ab9362706cd8cd75b2fc0f5177481a96a5f73ac4',tree='cfa80d600603d947e79304e075d48787c116a8a1',results=results,family_seconds=round(time.monotonic()-start,3),lane='RETIRED',push=False,historical_cause='NOT_ESTABLISHED')
(output/'summary.json').write_text(json.dumps(summary,sort_keys=True),encoding='utf8')
for name in ('f26-fix-family.py','f26-fix-qualification.py','f26-fix-source-guard.py'):shutil.copyfile(root/'work'/name,output/name)
manifest={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
(output/'SHA256.json').write_text(json.dumps(manifest,sort_keys=True),encoding='utf8')
print(json.dumps(summary),flush=True)
