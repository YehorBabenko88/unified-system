import pathlib,subprocess,json,hashlib,textwrap
r=pathlib.Path.cwd();repo=r/'work/unified-audit';o=r/'outputs/phase68';head='8bfa00d779438dc204b1e9ee82f496efce9e6154';prefix='release/evidence/lan-mux-composition-20261107/'
def raw(h,p):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),'show',h+':'+p])
idx=raw(head,prefix+'evidence-index.json');(o/'owner-evidence-index.original.json').write_bytes(idx)
for row in json.loads(idx)['files']:
 b=raw(head,prefix+row['path']);assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];(o/('owner-'+row['path'])).write_bytes(b)
driver=raw(head,prefix+'executed-integrated-source.py');assert driver==(o/'executed-workflow.py').read_bytes()
owner=json.loads(raw(head,prefix+'owner-lan-mux-root492-additive-handoff-v2.json'));(o/'owner-handoff-keys.json').write_text(json.dumps(owner,indent=2),encoding='utf-8');print(json.dumps(owner,indent=2)[:5500])
