"""Source rejection controls and injected JUnit validator models, not pytest cases."""
import copy,json,os,pathlib,subprocess,uuid,xml.etree.ElementTree as ET
r=pathlib.Path(__file__).resolve().parents[1];seed=r/'work/review-grid-ci142-7a19';out=r/'outputs/phase58';py=r/'work/a3-ci142-env/Scripts/python.exe';head='7a19ab40c30efef431bb16f0ddc91960608bf597';text=(out/'workflow.original.yml').read_text(encoding='utf-8');base=r/'work'/('a3-ci142-controls-'+uuid.uuid4().hex[:8]);base.mkdir()
def block(name):
 part=text.split('      - name: '+name+'\n',1)[1].split('        run: |\n',1)[1];lines=[]
 for line in part.splitlines():
  if line and not line.startswith('          '):break
  lines.append(line[10:] if line else '')
 return '\n'.join(lines)+'\n'
def git(repo,*a,input=None):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a],input=input)
controls=[]
for kind in ['timestamp_cache','root_shadow','hidden_raw','blob_replace','tree_replace','wrong_head','after_cache','native_overlay','env_prefix','X_prefix','unexpected_pyw']:
 repo=base/kind;subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],capture_output=True,check=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],capture_output=True,check=True);temp=base/(kind+'-output');temp.mkdir();marker=temp/'UNEXPECTED_GUARD_SUCCESS';env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(A3_EXPECTED_HEAD=head,RUNNER_TEMP=str(temp),A3_GUARD_PHASE='after' if kind=='after_cache' else 'before');extra=[];target=repo/'grid/bybit_response_advice.py'
 if kind in ('hidden_raw','blob_replace','tree_replace'):
  raw=target.read_bytes()+b'\n# inert A8 source-change control\n';target.write_bytes(raw)
  if kind=='hidden_raw':git(repo,'update-index','--assume-unchanged','grid/bybit_response_advice.py')
  else:
   bad=git(repo,'hash-object','-w','--stdin',input=raw).decode().strip()
   if kind=='blob_replace':git(repo,'replace',git(repo,'rev-parse',head+':grid/bybit_response_advice.py').decode().strip(),bad)
   else:
    git(repo,'update-index','--cacheinfo','100644,'+bad+',grid/bybit_response_advice.py');new=git(repo,'write-tree').decode().strip();git(repo,'replace',git(repo,'rev-parse',head+'^{tree}').decode().strip(),new)
 elif kind=='timestamp_cache':
  cache=repo/'grid/__pycache__';cache.mkdir();code="import importlib.util,marshal,pathlib,struct; p=pathlib.Path("+repr(str(target))+ ");s=p.stat();raw=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(s.st_mtime),s.st_size)+marshal.dumps(compile('raise AssertionError(\"INERT_CACHE_MARKER\")',str(p),'exec'));(p.parent/'__pycache__'/('bybit_response_advice.'+__import__('sys').implementation.cache_tag+'.pyc')).write_bytes(raw)";subprocess.run([str(py),'-I','-B','-c',code],check=True,capture_output=True)
 elif kind=='root_shadow':(repo/'typing.py').write_text("raise AssertionError('INERT_UNADMITTED_SHADOW')\n",encoding='utf-8')
 elif kind=='unexpected_pyw':(repo/'inert_overlay.pyw').write_text("raise AssertionError('INERT_UNADMITTED_PYW')\n",encoding='utf-8')
 elif kind=='wrong_head':env['A3_EXPECTED_HEAD']='0'*40
 elif kind=='after_cache':(repo/'orphan.pyc').write_bytes(b'INERT_NOT_EXECUTED')
 elif kind=='native_overlay':(repo/'inert.pyd').write_bytes(b'INERT_NOT_EXECUTED')
 elif kind=='env_prefix':env['PYTHONPYCACHEPREFIX']=str(temp/'cache')
 elif kind=='X_prefix':extra=['-X','pycache_prefix='+str(temp/'cache')]
 code=block('Source guard after tests' if kind=='after_cache' else 'Source guard before tests')+'\nPath('+repr(str(marker))+').write_text("unexpected")\n';p=subprocess.run([str(py),'-I','-B',*extra,'-c',code],cwd=repo,env=env,capture_output=True,timeout=30);(out/('negative-'+kind+'.stderr.log')).write_bytes(p.stderr);assert p.returncode!=0 and not marker.exists(),kind;controls.append(dict(case=kind,rejected=True,pytest_cases_executed=0))
models=[]
for step,xmlname,inventory_name in [('Exact codec inventory and zero skips','junit.xml','agent3-checkpoint-v3'),('Exact separate domain/page inventory and zero skips','domain-junit.xml','agent3-market-domain'),('Exact separate response advice inventory and zero skips','response-junit.xml','agent3-bybit-response')]:
 validator=block(step);validator=validator[validator.index('cases=ET.parse'):];original=ET.fromstring((out/xmlname).read_bytes());inventory=json.loads((seed/'tests/fixtures'/inventory_name/'test-inventory.json').read_bytes())
 for mutation in ['valid','missing','duplicate_identity','skip','failure']:
  fixture=base/('junit-'+inventory_name+'-'+mutation);fixture.mkdir();root=copy.deepcopy(original);suite=root.find('testsuite');cases=list(root.iter('testcase'))
  if mutation=='missing':suite.remove(cases[-1])
  elif mutation=='duplicate_identity':cases[-1].attrib=dict(cases[0].attrib)
  elif mutation=='skip':ET.SubElement(cases[0],'skipped')
  elif mutation=='failure':ET.SubElement(cases[0],'failure')
  ET.ElementTree(root).write(fixture/xmlname,encoding='utf-8');accepted=True
  try:exec(compile(validator,'<committed-JUnit-validator-model>','exec'),dict(ET=ET,out=fixture,inventory=inventory,head=head,tree='e7adbc40562e962ae529d157eebeacd550c5b7f6',json=json))
  except AssertionError:accepted=False
  assert accepted==(mutation=='valid');models.append(dict(group=inventory_name,mutation=mutation,accepted=accepted,scope='INJECTED_JUNIT_MODEL_NOT_ACTUAL_PYTEST'))
(out/'independent-controls.json').write_text(json.dumps(dict(source_controls=controls,injected_JUnit_validator_models=models,actual_pytest_cases_in_this_script=0),indent=2),encoding='utf-8');print(json.dumps(dict(source_negatives=len(controls),injected_JUnit_models=len(models),pytest_cases=0)))
