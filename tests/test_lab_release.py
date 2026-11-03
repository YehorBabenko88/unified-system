import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from unified_system.module_catalog import MODULE_IDS
from unified_system import lab_release as lab


def fixture(root):
    files={}
    def put(name,raw):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    put('runtime.json',b'{}\n');put('deps/requirements.lock',b'example==1.0\n')
    put('tools/git.exe',b'inert fixture, never executed')
    sources={}
    repos={'grid':'bybit-cluster-grid','terminan':'Terminan'}
    for name in MODULE_IDS:
        put('sources/'+name+'/inert.txt',b'fixture')
        put('sources/'+name+'/empty.txt',b'')
        sources[name]=dict(repository='YehorBabenko88/'+repos.get(name,name),
            root='sources/'+name,commit='a'*40,tree='b'*40,version='1.0.0',dependencies={})
    m=dict(schema='unified.lab-release.v1',mode='LAB_SIMULATION',release_id='lab-1',sequence=1,
        market_access='PUBLIC_READ_ONLY',execution='PAPER_ONLY',credentials='FORBIDDEN',
        trading_authorized=False,sources=sources,files=files,
        directories=sorted({p.as_posix() for name in files for p in Path(name).parents if str(p)!='.'}),
        dependencies=[dict(name='python',version='3.12.10',lock_path='deps/requirements.lock')],
        runtime_config='runtime.json',git='tools/git.exe',
        instruments=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT','BNBUSDT','ADAUSDT','AVAXUSDT','DOTUSDT','LINKUSDT'])
    return m


class LabReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.m=fixture(self.root)

    def publish(self,m=None):
        raw=lab.canonical(self.m if m is None else m)
        (self.root/'lab-release.json').write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_unsigned_lab_requires_external_manifest_hash_and_exact_file_closure(self):
        pin=self.publish()
        result=lab.verify_capsule(self.root,pin)
        self.assertEqual(result['mode'],'LAB_SIMULATION')
        self.assertEqual(result['publisher_trust'],'NOT_REQUIRED_FOR_LAB')
        self.assertIs(result['trading_authorized'],False)
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,'0'*64)
        (self.root/'extra.txt').write_text('unadmitted')
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,pin)

    def test_changed_missing_or_hardlinked_files_fail_closed(self):
        import os
        pin=self.publish();p=self.root/'runtime.json'
        p.write_bytes(b'changed')
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,pin)
        p.unlink()
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,pin)
        p.write_bytes(b'{}\n');os.link(p,self.root/'alias')
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,pin)

    def test_explicit_empty_directories_are_bound_and_extra_namespaces_reject(self):
        (self.root/'empty').mkdir();self.m['directories']=sorted(self.m['directories']+['empty'])
        pin=self.publish();lab.verify_capsule(self.root,pin)
        (self.root/'unlisted-empty').mkdir()
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,pin)

    def test_lab_cannot_claim_trusted_release_or_enable_trading(self):
        for key,value in [('mode','TRUSTED_RELEASE'),('execution','LIVE'),('credentials','ALLOWED'),
                          ('market_access','PRIVATE_API'),('trading_authorized',True),('sequence',True),
                          ('publisher_sha256','0'*64)]:
            m=copy.deepcopy(self.m);m[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):lab.verify_capsule(self.root,self.publish(m))

    def test_missing_source_dependency_cycle_wrong_origin_and_unsafe_paths_reject(self):
        mutations=[lambda m:m['sources'].pop('math'),
            lambda m:m['sources']['math'].update(repository='other/math'),
            lambda m:m['sources']['math'].update(root='../outside'),
            lambda m:m['dependencies'][0].update(version='latest'),
            lambda m:m['dependencies'][0].update(lock_path='missing.lock'),
            lambda m:m['sources']['math']['dependencies'].update(math='1.0.0')]
        for mutate in mutations:
            m=copy.deepcopy(self.m);mutate(m)
            with self.assertRaises(ValueError):lab.verify_capsule(self.root,self.publish(m))

    def test_duplicate_json_and_noncanonical_encoding_reject(self):
        raw=lab.canonical(self.m)
        for altered in (raw+b' ',raw.replace(b'{',b'{"mode":"LAB_SIMULATION",',1)):
            (self.root/'lab-release.json').write_bytes(altered)
            with self.assertRaises(ValueError):lab.verify_capsule(self.root,hashlib.sha256(altered).hexdigest())

    def test_even_hash_admitted_active_dotenv_cannot_bypass_lab_settings(self):
        raw=b'BYBIT_API_KEY=INERT_TEST_SECRET\n';name='sources/grid/.env'
        (self.root/name).write_bytes(raw)
        self.m['files'][name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        with self.assertRaises(ValueError):lab.verify_capsule(self.root,self.publish())

    def test_scoped_dependency_and_cpp_names_remain_inside_pinned_closure(self):
        name='deps/@scope/pkg/c++.js';raw=b'inert dependency fixture'
        path=self.root/name;path.parent.mkdir(parents=True);path.write_bytes(raw)
        self.m['files'][name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        self.m['directories']=sorted(set(self.m['directories'])|{p.as_posix() for p in Path(name).parents if str(p)!='.'})
        pin=self.publish();self.assertEqual(lab.verify_capsule(self.root,pin)['manifest_sha256'],pin)

    def test_stage_copies_verified_bytes_to_new_directory_only(self):
        pin=self.publish()
        target=self.root.parent/(self.root.name+'-staged')
        self.addCleanup(lambda:__import__('shutil').rmtree(target) if target.exists() else None)
        lab.stage_capsule(self.root,target,pin)
        self.assertEqual(lab.verify_capsule(target,pin)['manifest_sha256'],pin)
        with self.assertRaises(ValueError):lab.stage_capsule(self.root,target,pin)


if __name__=='__main__':unittest.main()
