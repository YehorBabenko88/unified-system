import pathlib,subprocess,json,hashlib,io,zipfile
r=pathlib.Path.cwd();o=r/'outputs/phase151';o.mkdir(exist_ok=True);records=[]
def api(path):return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/YehorBabenko88/unified-system/'+path])
for run in [42716081580,42716071876]:
 meta=json.loads(api('actions/runs/'+str(run)));jobs=json.loads(api('actions/runs/'+str(run)+'/jobs'));arts=json.loads(api('actions/runs/'+str(run)+'/artifacts'));assert meta['head_sha']=='e203c0bbeaa176a843a7d80b2eadfefe8fce7385' and meta['run_attempt']==1 and meta['conclusion']=='success';assert len(jobs['jobs'])==2 and all(j['conclusion']=='success' for j in jobs['jobs']);assert len(arts['artifacts'])==2
 (o/(str(run)+'.metadata.json')).write_text(json.dumps(dict(run=meta,jobs=jobs,artifacts=arts),indent=2))
 for art in arts['artifacts']:
  raw=api('actions/artifacts/'+str(art['id'])+'/zip');digest=hashlib.sha256(raw).hexdigest();assert art['digest']=='sha256:'+digest and len(raw)==art['size_in_bytes'];(o/(str(art['id'])+'.original.zip')).write_bytes(raw);z=zipfile.ZipFile(io.BytesIO(raw));files={}
  for name in z.namelist():
   if name.endswith('/'):continue
   b=z.read(name);files[name]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());target=o/str(art['id'])/name;assert '..' not in pathlib.PurePosixPath(name).parts and not pathlib.PurePosixPath(name).is_absolute();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  records.append(dict(run=run,artifact_id=art['id'],name=art['name'],zip_bytes=len(raw),zip_sha256=digest,files=files))
(o/'original-ci-verification.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
