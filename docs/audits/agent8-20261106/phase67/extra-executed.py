import sys,pathlib,importlib.util,types,subprocess,tempfile,zipfile,json
root=pathlib.Path.cwd();sys.path.insert(0,str(root));path=root/'scripts/prepare_lab_capsule.py'
def module(raw,name):
 m=types.ModuleType(name);m.__file__=str(path);exec(compile(raw,str(path),'exec'),m.__dict__);return m
fixed=module(path.read_bytes(),'a8_current');old=module(subprocess.check_output(['git','--no-replace-objects','show','HEAD^:scripts/prepare_lab_capsule.py']),'a8_old')
cases=[['tools/Lib/a','tools/lib/b'],['tools/A/B/a','tools/A/b/c'],['tools/Lib','tools/Lib/a'],['tools/Lib/a','tools/Lib'],['tools/Lib/','tools/lib/a']]
rows=[]
for names in cases:
 with tempfile.TemporaryDirectory() as d:
  root=pathlib.Path(d);z=root/'x.zip';target=root/'new'
  with zipfile.ZipFile(z,'w') as f:
   for n in names:f.writestr(n,b'' if n.endswith('/') else b'inert')
  try:fixed.extract(z,target,'tools/');raise AssertionError('accepted conflict')
  except ValueError as e:assert str(e) in ['ARCHIVE_ALIAS','ARCHIVE_NAMESPACE_CONFLICT']
  assert not target.exists();rows.append(dict(names=names,current_refused_before_creation=True))
# Independent witness: original accepts implicit-parent alias on Windows.
with tempfile.TemporaryDirectory() as d:
 root=pathlib.Path(d);z=root/'x.zip'
 with zipfile.ZipFile(z,'w') as f:
  f.writestr('tools/Lib/a',b'a');f.writestr('tools/lib/b',b'b')
 old.extract(z,root/'old','tools/');assert (root/'old/Lib/a').read_bytes()==b'a' and (root/'old/Lib/b').read_bytes()==b'b'
print(json.dumps(dict(cases=rows,primary_parent_alias_reproduced=True,scope='INERT_ARCHIVE_ONLY'),indent=2))
