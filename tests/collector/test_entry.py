"""Plan-only entry guards. Execution is added only with the integrated E2E."""
import contextlib,hashlib,io,json,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from unified_system import collector_entry as ce
from test_profile import fixture

class EntryTests(unittest.TestCase):
 def test_explicit_synthetic_mode_routes_bound_profile_to_finite_composition(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();manifest=root/'manifest.json';manifest.write_bytes(b'owned-manifest-fixture')
   value=fixture();value['source_manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
   profile=root/'profile.json';profile.write_text(json.dumps(value),encoding='utf-8')
   async def captured(*args,**kwargs):return {'unit_route_only':True}
   out=io.StringIO()
   with patch('unified_system.collector_offline.collect_synthetic',side_effect=captured) as collect,contextlib.redirect_stdout(out):
    code=ce.main(['--synthetic-offline',str(profile),'--manifest',str(manifest),'--state',str(root/'new-state')])
   self.assertEqual(code,0);collect.assert_called_once()
   self.assertFalse(collect.call_args.kwargs['resume']);self.assertEqual(collect.call_args.kwargs['manifest_bytes'],manifest.read_bytes())
   self.assertEqual(json.loads(out.getvalue()),{'unit_route_only':True});self.assertFalse((root/'new-state').exists())
 def test_unknown_or_execution_arguments_deny_without_files(self):
  for args in ([],['--execute'],['--offline'],['--plan-only','missing'],['--plan-only','a','--manifest','b','--rest']):
   output=io.StringIO()
   with self.subTest(args=args),contextlib.redirect_stdout(output):code=ce.main(args)
   self.assertEqual(code,78);self.assertEqual(output.getvalue().strip(),'BLOCKED_COLLECTOR_ENTRY')
 def test_plan_reads_bound_ordinary_files_without_execution(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();manifest=root/'manifest.json';manifest.write_bytes(b'{"schema":"unified.collector.integration-manifest.v1","assembly_status":"PENDING"}\n')
   doc=fixture();doc['source_manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
   profile=root/'profile.json';profile.write_text(json.dumps(doc),encoding='utf-8')
   before={p.name:p.read_bytes() for p in root.iterdir()};out=io.StringIO()
   with contextlib.redirect_stdout(out):code=ce.main(['--plan-only',str(profile),'--manifest',str(manifest)])
   self.assertEqual(code,0);result=json.loads(out.getvalue())
   self.assertEqual(result['status'],'PLAN_ONLY_NOT_EXECUTION_AUTHORITY');self.assertFalse(result['provider_sends'])
   self.assertEqual({p.name:p.read_bytes() for p in root.iterdir()},before)
 def test_manifest_substitution_and_oversize_profile_deny(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();manifest=root/'manifest.json';manifest.write_bytes(b'changed')
   profile=root/'profile.json';profile.write_text(json.dumps(fixture()),encoding='utf-8')
   for raw in (profile.read_bytes(),b'x'*32769):
    profile.write_bytes(raw);out=io.StringIO()
    with contextlib.redirect_stdout(out):code=ce.main(['--plan-only',str(profile),'--manifest',str(manifest)])
    self.assertEqual(code,78);self.assertNotIn('changed',out.getvalue())
 def test_relative_network_and_parent_paths_rejected(self):
  for path in ('relative.json','//server/share/file','C:/a/../file'):
   with self.subTest(path=path),self.assertRaises(ce.CollectorEntryRejected):ce.read_ordinary_source(path,32768)
 def test_hardlinked_or_oversize_local_source_is_not_admitted(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();source=root/'source.json';source.write_bytes(b'owned-fixture')
   alias=root/'alias.json';alias.hardlink_to(source)
   with self.assertRaises(ce.CollectorEntryRejected):ce.read_ordinary_source(str(source),32768)
   oversized=root/'oversize.json';oversized.write_bytes(b'x'*32769)
   with self.assertRaises(ce.CollectorEntryRejected):ce.read_ordinary_source(str(oversized),32768)

if __name__=='__main__':unittest.main()
