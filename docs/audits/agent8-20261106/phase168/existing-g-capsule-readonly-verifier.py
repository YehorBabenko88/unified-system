import pathlib,json,hashlib,os,stat,time
base=pathlib.Path('C:/Users/LS-5/.codex/native-e2e-evidence-20261109');root=base/'ls5-package-1d923f6-g';raw=(base/'ls5-package-1d9-g.manifest.json').read_bytes();pin=hashlib.sha256(raw).hexdigest();assert pin=='3e05c5251d0bd84e073dc0545c95c903424654690942bd77313175ae493b0a5a';manifest=json.loads(raw);expected=manifest['files'];start=time.monotonic();seen=set();total=0
for parent in (root,*root.parents):assert not (getattr(parent.lstat(),'st_file_attributes',0)&1024)
stack=[root]
while stack:
 directory=stack.pop()
 with os.scandir(directory) as entries:
  for entry in entries:
   info=pathlib.Path(entry.path).lstat();assert not (getattr(info,'st_file_attributes',0)&1024),'REPARSE_REJECTED'
   path=pathlib.Path(entry.path)
   if stat.S_ISDIR(info.st_mode):stack.append(path);continue
   assert stat.S_ISREG(info.st_mode) and info.st_nlink==1,'NONORDINARY_MEMBER';name=path.relative_to(root).as_posix();assert name in expected,'UNEXPECTED_MEMBER';record=expected[name];assert info.st_size==record['bytes'];h=hashlib.sha256()
   with path.open('rb') as stream:
    for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    end=os.fstat(stream.fileno())
   assert (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==(end.st_dev,end.st_ino,end.st_size,end.st_mtime_ns),'CHANGED_MEMBER';assert h.hexdigest()==record['sha256'],'DIGEST_MISMATCH';seen.add(name);total+=info.st_size
assert seen==set(expected) and len(seen)==manifest['file_count']==19300 and total==manifest['total_bytes']==1008702257
result={'schema':'unified.local-capsule-readonly-integrity.v1','manifest_sha256':pin,'members_verified':len(seen),'bytes_verified':total,'ordinary_single_link_no_reparse':True,'all_member_digests_match':True,'elapsed_seconds':round(time.monotonic()-start,3),'scope':'EXISTING_LS5_G_CAPSULE_LOCAL_BYTES_ONLY','pc4_staged':False,'pc4_execution':False,'new_runtime_admission':False,'source_provenance_promoted':False,'changes_performed':False};out=(json.dumps(result,indent=2)+'\n').encode();pathlib.Path('C:/Users/LS-5/.codex/ci-boundary-evidence-20261110/existing-g-capsule-integrity-readonly.json').write_bytes(out);print(out.decode());print('evidence_sha256='+hashlib.sha256(out).hexdigest())