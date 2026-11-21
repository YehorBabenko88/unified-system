"""Three real owned-ObjectStore roles; mandatory hosted, no identity grant.

Ported raw assertions are mapped in docs/migration/canonical-query-role-map.json.
Local Norton-restricted qualification compiles this source only.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unified_system.storage.object_store import ObjectStore
from unified_system.storage.manifest import decode_manifest
from unified_system.storage.contracts import StorageBlocked
from unified_system import market_data_query

HERE=Path(__file__).resolve().parent
FIXTURES=HERE/'query_fixtures'
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def fixture():
    manifest=(FIXTURES/'manifest.canonical.json').read_bytes()
    objects={}
    for name in ('data-schema','rows','segment-index','coverage','dependencies'):
        raw=(FIXTURES/(name+'.canonical.json')).read_bytes();objects[sha(raw)]=raw
    return manifest,objects
def query_request():return json.loads((FIXTURES/'actual-query.request.canonical.json').read_bytes())
def domain_context(claim):
    root=claim.as_dict();lineage=root['lineage']
    context={key:root[key] for key in ('manifest_revision','data_schema_sha256','segments_root_sha256','coverage_root_sha256','dependencies_root_sha256')}
    context.update(manifest_sha256=claim.sha256,dataset_id=lineage['dataset_id'],instrument_id=dict(lineage['instrument_id']),lineage_sha256=claim.lineage_sha256,source_class='SYNTHETIC')
    return context

class QueryOwnedFixtureTests(unittest.TestCase):
    def setUp(self):
        self.store_type=ObjectStore;self.manifest_decoder=decode_manifest
        self.storage_error=StorageBlocked;self.domain=market_data_query.domain

    def test_actual_six_reads_reopen_and_codec_keep_gap_explicit(self):
        manifest,objects=fixture()
        with tempfile.TemporaryDirectory(prefix='canonical-query-store-') as directory:
            path=Path(directory)/'owned'
            store=self.store_type.create(path,store_id='00000000-0000-4000-8000-000000000020')
            for raw in [manifest,*objects.values()]:store.put(raw)
            reopened=self.store_type.open(path,store_id='00000000-0000-4000-8000-000000000020')
            self.assertIsNot(store,reopened)
            root_bytes=reopened.read(sha(manifest),max_bytes=16384)
            claim=self.manifest_decoder(root_bytes)
            self.assertFalse(claim.publication_confirmed);self.assertFalse(claim.closure_verified)
            root=claim.as_dict()
            descriptor=root['data_schema_sha256'];index_key=root['segments_root_sha256']
            resolved={descriptor:reopened.read(descriptor,max_bytes=4096),index_key:reopened.read(index_key,max_bytes=16384)}
            reference=self.domain.decode_query_segment_index(resolved[index_key],context=domain_context(claim))
            resolved[reference.sha256]=reopened.read(reference.sha256,max_bytes=524288)
            coverage_key=root['coverage_root_sha256'];deps_key=root['dependencies_root_sha256']
            resolved[coverage_key]=reopened.read(coverage_key,max_bytes=524288)
            resolved[deps_key]=reopened.read(deps_key,max_bytes=16384)
            # Exact canonical namespace reseal: original fixture3433 -> canonical3468.
            self.assertEqual(sum(map(len,[root_bytes,*resolved.values()])),3468)
            request=query_request();request['range']['end_ms']='180000';request['event_cut_ms']='180000'
            result=self.domain.project_query(self.domain.prepare_query(canonical(request)),context=domain_context(claim),manifest_bytes=root_bytes,objects_by_sha256=resolved)
            self.assertEqual(result['cells'][1]['disposition'],'GAP')
            self.assertEqual(result['provider_coverage'],'UNKNOWN')
            self.assertFalse(result['execution_authority']);self.assertFalse(result['native_authenticated'])
            # Local projection has no capability/current checks: not authenticated query.

    def test_actual_store_missing_object_refuses(self):
        with tempfile.TemporaryDirectory(prefix='canonical-query-store-') as directory:
            store=self.store_type.create(Path(directory)/'owned',store_id='00000000-0000-4000-8000-000000000021')
            with self.assertRaisesRegex(self.storage_error,'OBJECT_UNAVAILABLE'):store.read('f'*64,max_bytes=16384)

    def test_actual_store_modified_owned_object_refuses_hash(self):
        with tempfile.TemporaryDirectory(prefix='canonical-query-store-') as directory:
            path=Path(directory)/'owned'
            store=self.store_type.create(path,store_id='00000000-0000-4000-8000-000000000022')
            raw=b'local-synthetic-only';store.put(raw)
            (path/'objects'/sha(raw)).write_bytes(b'corrupt-owned-disposable-fixture')
            with self.assertRaisesRegex(self.storage_error,'OBJECT_CORRUPT'):store.read(sha(raw),max_bytes=16384)

if __name__=='__main__':unittest.main()
