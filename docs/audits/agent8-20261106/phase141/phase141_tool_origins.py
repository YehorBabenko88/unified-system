import pathlib,json,hashlib,os,stat
r=pathlib.Path.cwd();o=r/'outputs/phase141';b=pathlib.Path('C:/Users/LS-5/.codex/native-e2e-evidence-20261109');m=json.loads((o/'ls5-package-461-b.manifest.json').read_bytes());components=json.loads((b/'ls5-package-components461-b.json').read_bytes());results=[]
for c in components:
 if c['destination_prefix'].startswith('sources/'):continue
 prefix=c['destination_prefix']+'/';src=pathlib.Path(c['source_root']);count=0;total=0
 for name,row in m['files'].items():
  if not name.startswith(prefix):continue
  rel=name[len(prefix):];p=src/rel
  # The tooling-seeds component shares a parent prefix with the other tooling.
  if c['name']=='tooling-seeds' and not p.exists():continue
  s=p.lstat();assert stat.S_ISREG(s.st_mode) and not (getattr(s,'st_file_attributes',0)&1024)
  h=hashlib.sha256()
  with p.open('rb') as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
  assert row==dict(bytes=s.st_size,sha256=h.hexdigest());count+=1;total+=s.st_size
 results.append(dict(component=c['name'],original_source_root=str(src),selected_files=count,selected_bytes=total,all_selected_current_original_bytes_match=True))
receipt=json.loads((o/'ls5-git-export-f6f3418-a.receipt.json').read_bytes());gitfiles={k.removeprefix('tooling/git/'):v for k,v in m['files'].items() if k.startswith('tooling/git/')};assert gitfiles==receipt['files'];assert len(gitfiles)==receipt['file_count']==9593;assert sum(x['bytes'] for x in gitfiles.values())==receipt['total_bytes']==423632674
(o/'tool-origin-verification.json').write_text(json.dumps(dict(current_original_selected_tool_bytes=results,git_export_receipt_file_table_matches_package=True,git_source_hardlink_file_count_reported=receipt['source_hardlink_file_count'],publisher_and_loaded_dll_attestations='NOT_ESTABLISHED',SDK_or_tool_execution=False),indent=2));print(json.dumps(results))
