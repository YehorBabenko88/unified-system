import pathlib,subprocess,os,textwrap,json,uuid,hashlib
r=pathlib.Path.cwd();seed=r/'work/review-gatewayb126';out=r/'outputs/phase80';head='b1261c560922ac6fc255d79809759d7d06035f0a';code=(out/'executed-workflow.py').read_text(encoding='utf-8');guard=code.split('    before=inventory()')[0]+'    inventory()\nif __name__=="__main__": main()\n';assert 'result=subprocess.run' not in guard;rows=[]
for name in ['cache','shadow','tracked','replace']:
 repo=r/'work'/('gateway-a8-negative-'+name+'-'+uuid.uuid4().hex[:6]);subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],capture_output=True,check=True);subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',head],capture_output=True,check=True);target=repo/'unified_system/intelligence_gateway.py'
 if name=='cache':(repo/'orphan.pyc').write_bytes(b'INERT_NOT_EXECUTED')
 elif name=='shadow':(repo/'json.py').write_text("raise AssertionError('INERT_SHADOW')\n",encoding='utf-8')
 else:
  target.write_bytes(target.read_bytes()+b'\n# inert raw source mismatch\n')
  if name=='replace':
   old=subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'rev-parse',head+':unified_system/intelligence_gateway.py']).decode().strip();new=subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--no-filters',str(target)]).decode().strip();subprocess.run(['git','-C',str(repo),'replace',old,new],capture_output=True,check=True)
 env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')};env.update(EXPECTED_HEAD=head,RUNNER_TEMP=str(r/'work/gatewayb126-a8-temp'));p=subprocess.run([str(r/'work/audit-venv/Scripts/python.exe'),'-I','-S','-B','-c',guard],cwd=repo,env=env,capture_output=True,timeout=40);(out/('guard-'+name+'.stderr.log')).write_bytes(p.stderr);assert p.returncode!=0;rows.append(dict(case=name,rejected=True,tests_executed=0,stderr_sha256=hashlib.sha256(p.stderr).hexdigest()))
(out/'guard-controls.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('4 own guard negatives refused before0tests')
