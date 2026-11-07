import pathlib,subprocess,json,hashlib
r=pathlib.Path.cwd();o=r/'outputs/phase67';head='49290143a49b4a58c6f9f98e1c9722bc6e526575';prefix='release/evidence/installer-archive-namespace-20261107/'
def raw(p):return subprocess.check_output(['git','--no-replace-objects','-C',str(r/'work/unified-audit'),'show',head+':'+prefix+p])
idx=raw('evidence-index.json');(o/'owner-evidence-index.original.json').write_bytes(idx)
for row in json.loads(idx)['files']:
 b=raw(row['path']);assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];(o/('owner-'+row['path'])).write_bytes(b)
ci=json.loads((o/'ci.original.json').read_text());print(json.dumps(dict(index_members=6,CI=[{k:d.get(k) for k in ['id','head_sha','status','conclusion','run_attempt']} for d in ci['workflow_runs']])))
