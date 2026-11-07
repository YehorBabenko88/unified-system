"""Bounded primary GitHub metadata/log/artifact downloads; never execute payloads."""
import concurrent.futures,hashlib,io,json,pathlib,subprocess,zipfile
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase57';out.mkdir(exist_ok=True);repo='YehorBabenko88/strattester';run=42343442185;head='a56c24a0f25a0c5ea9222fcd953a49536c91dfc9'
def api(path):return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+repo+'/'+path])
def capture(name,path):
 raw=api(path);(out/name).write_bytes(raw);return json.loads(raw)
meta=capture('run.original.json','actions/runs/'+str(run));jobs=capture('jobs.original.json','actions/runs/'+str(run)+'/attempts/1/jobs?per_page=100');art=capture('artifacts.original.json','actions/runs/'+str(run)+'/artifacts?per_page=100')
assert meta['head_sha']==head and meta['run_attempt']==1 and meta['conclusion']=='success' and jobs['total_count']==len(jobs['jobs'])==4 and art['total_count']==len(art['artifacts'])==4
tasks=[('job-'+str(j['id'])+'.log','actions/jobs/'+str(j['id'])+'/logs',None) for j in jobs['jobs']]+[('artifact-'+str(a['id'])+'.zip','actions/artifacts/'+str(a['id'])+'/zip',a['digest']) for a in art['artifacts']]
def fetch(t):
 name,path,expected=t;raw=api(path);actual=hashlib.sha256(raw).hexdigest();assert expected is None or expected=='sha256:'+actual;(out/name).write_bytes(raw)
 row=dict(file=name,bytes=len(raw),sha256=actual)
 if name.endswith('.zip'):
  z=zipfile.ZipFile(io.BytesIO(raw));row['members']=[dict(name=i.filename,bytes=i.file_size,sha256=hashlib.sha256(z.read(i)).hexdigest()) for i in z.infolist()];assert sum(i.file_size for i in z.infolist())<5000000
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,tasks))
(out/'download-index.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results,indent=2))
