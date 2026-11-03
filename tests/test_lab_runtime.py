import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unified_system import lab_runtime as lab
from unified_system import runtime_cli
from tests.test_lab_release import fixture
from tests.test_runtime_cli import fixture as runtime_fixture


class LabRuntimePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.m=fixture(self.root)
        self.c=runtime_fixture(self.root)
        self.c['schema']='unified.runtime.config.v2';self.c['programs'].pop('unified-system')
        self.c['http_port']=19001;self.c['node_id']='LS5'
        self.c['release_id']=self.m['release_id']
        self.c['state_root']=str(self.root.parent/(self.root.name+'-state'))
        self.c['snapshot_path']=str(Path(self.c['state_root'])/'public/runtime.json')
        exe=self.root/'tools/git.exe'
        bootstrap='sources/unified-system/unified_system/owned_python.py'
        self.m['files'][bootstrap]={'sha256':'a'*64,'bytes':1}
        for n,p in self.c['programs'].items():
            argv=[str(exe),str(self.root/'sources/math/src/math-engine-server.mjs')]
            if n!='math':
                modules={'grid':'uvicorn','meta_analyse':'meta_analyse.headless_service','strattester':'strattester.owned_results_service','terminan':'terminan.unified_runner'}
                tails={'grid':['grid.coordinator:app','--host','127.0.0.1','--port','19000','--no-access-log'],
                       'meta_analyse':['--execute','--port','19000'],
                       'strattester':['--serve','--store',str(Path(self.c['state_root'])/'results.sqlite'),'--port','19000'],
                       'terminan':['--expected-sha','a'*40,'--port','19000']}
                argv=[str(exe),'-I','-S','-B',str(self.root/bootstrap),'--source-root',str(self.root/'sources'/n),'--module',modules[n],'--',*tails[n]]
            p.update(argv=argv,cwd=str(self.root/'sources'/n),
                     executable_sha256=self.m['files']['tools/git.exe']['sha256'],
                     file_pins={'inert.txt':self.m['files']['sources/'+n+'/inert.txt']['sha256']})
        self.c['programs']['grid']['env']={'POSTGRES_DSN':'postgresql://unified_lab_test@127.0.0.1:55449/unified_lab_test'}

    def test_explicit_lab_config_allows_office_node_without_weakening_ci_guard(self):
        with self.assertRaises(ValueError):runtime_cli.validate_config(self.c)
        result=lab.validate_config(self.c,self.m,self.root,hostname='LS5')
        self.assertEqual(result['node_id'],'LS5')
        self.assertTrue(all(Path(p['env']['PROGRAMDATA']).resolve().is_relative_to(Path(self.c['state_root']).resolve()) for p in result['programs'].values()))
        with self.assertRaises(ValueError):runtime_cli.assert_ephemeral(self.c,self.root/'runtime.json',hostname='LS5')

    def test_worker_nodes_cannot_launch_another_coordinator(self):
        c=copy.deepcopy(self.c);c['node_id']='PC1'
        with self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='PC1')
        p=c['programs']['grid'];index=p['argv'].index('--module')
        p['argv']=p['argv'][:index]+['--module','grid.owned_worker_service','--','--execute','--port','19000']
        p['env'].pop('POSTGRES_DSN')
        result=lab.validate_config(c,self.m,self.root,hostname='PC1')
        self.assertEqual(result['programs']['grid']['env']['ROLE'],'worker')

    def test_private_grid_auth_is_hash_bound_and_only_contains_lab_identity(self):
        import json
        state=Path(self.c['state_root']);state.mkdir()
        self.addCleanup(lambda:__import__('shutil').rmtree(state))
        record=dict(schema='unified.lab.grid-auth.v1',node_id='LS5',role='CONTROL',release_id=self.m['release_id'],
                    source_commit=self.m['sources']['grid']['commit'],grid_shared_token='c'*64,node_credential=None)
        raw=lab.lab_release.canonical(record);path=state/'grid-auth.json';path.write_bytes(raw)
        pin=hashlib.sha256(raw).hexdigest()
        env=lab.read_grid_auth(path,pin,node_id='LS5',release_id=self.m['release_id'],source_commit='a'*40)
        self.assertEqual(env,{'GRID_SHARED_TOKEN':'c'*64})
        with self.assertRaises(ValueError):lab.read_grid_auth(path,'0'*64,node_id='LS5',release_id=self.m['release_id'],source_commit='a'*40)
        with self.assertRaises(ValueError):lab.read_grid_auth(path,pin,node_id='PC1',release_id=self.m['release_id'],source_commit='a'*40)

    def test_office_node_ids_bind_to_the_observed_windows_hostnames(self):
        for node,hostname in [('PC1','Easy'),('PC2','Leitstelle1'),('PC3','LS03e'),('PC4','LS4'),('LS7','LS-07')]:
            c=copy.deepcopy(self.c);c['node_id']=node
            p=c['programs']['grid'];index=p['argv'].index('--module')
            p['argv']=p['argv'][:index]+['--module','grid.owned_worker_service','--','--execute','--port','19000']
            p['env'].pop('POSTGRES_DSN')
            with self.subTest(node=node):
                self.assertEqual(lab.validate_config(c,self.m,self.root,hostname=hostname)['node_id'],node)
                with self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='LS5')
                with self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='ADMINIT')

    def test_source_versions_files_state_and_node_are_bound_to_capsule(self):
        for fault in ('node','version','cwd','executable','script','pin','state','snapshot'):
            c=copy.deepcopy(self.c);p=c['programs']['math']
            if fault=='node':c['node_id']='PC4'
            if fault=='version':c['specs'][0]['version']='9.0.0'
            if fault=='cwd':p['cwd']=str(self.root.parent)
            if fault=='executable':p['argv'][0]=str(self.root.parent/'outside.exe')
            if fault=='script':p['argv'][1]=str(self.root.parent/'outside.py')
            if fault=='pin':p['file_pins']['inert.txt']='0'*64
            if fault=='state':c['state_root']=str(self.root/'mutable')
            if fault=='snapshot':c['snapshot_path']=str(self.root.parent/'outside.json')
            with self.subTest(fault=fault),self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='LS5')
        for name in ('ADMINIT','ADMINIT-JQ1IQSV','outside-node'):
            c=copy.deepcopy(self.c);c['node_id']=name
            with self.subTest(host=name),self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname=name)

    def test_exchange_credentials_and_unsafe_startup_settings_rejected(self):
        for key,value in [('BYBIT_API_KEY','private'),('BYBIT_API_SECRET','private'),
                          ('NODE_OPTIONS','--import external.mjs'),('PYTHONPATH','outside'),
                          ('NODE_TLS_REJECT_UNAUTHORIZED','0'),('BYBIT_WS_URL','wss://stream.bybit.com/v5/private'),
                          ('BYBIT_REST_URL','http://api.bybit.com'),('PATH',str(Path(self.c['state_root'])/'outside-bin')),
                          ('UNIFIED_SOURCE_ROOT',str(self.root.parent/'outside-source')),
                          ('ML_ARTIFACT_ROOT',str(self.root/'sources/math')),('GRID_COORDINATION_MODE','production')]:
            c=copy.deepcopy(self.c);c['programs']['grid']['env'].update({key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='LS5')

    def test_minimal_environment_never_inherits_exchange_or_startup_secrets(self):
        result=lab.child_environment({'SystemRoot':'C:/Windows','PATH':'untrusted',
            'BYBIT_API_KEY':'PRIVATE','AWS_SECRET_ACCESS_KEY':'PRIVATE','PYTHONPATH':'untrusted','NODE_OPTIONS':'untrusted'})
        self.assertEqual(result['SystemRoot'],'C:/Windows')
        self.assertNotIn('BYBIT_API_KEY',result);self.assertNotIn('NODE_OPTIONS',result)
        self.assertNotIn('PRIVATE',str(result));self.assertNotIn('PATH',result)
        self.assertEqual(result['UNIFIED_DEPLOYMENT_MODE'],'LAB_SIMULATION')
        self.assertEqual(result['UNIFIED_ORDER_MODE'],'PAPER_ONLY')

    def test_configuration_hash_binds_the_parsed_read_not_a_second_read(self):
        report={'manifest':self.m}
        with patch.object(lab.lab_release,'verify_capsule',return_value=report),\
             patch.object(lab,'read_config',return_value=(self.c,b'changed parsed bytes')),\
             patch.object(lab,'verify_sources',side_effect=AssertionError('MUST_NOT_REACH_SOURCE_OR_LAUNCH')):
            with self.assertRaises(ValueError):lab.prepare(self.root,'a'*64)

    def test_actual_git_source_fence_checks_all_six_and_rejects_changed_bytes(self):
        import shutil,subprocess
        git=Path(shutil.which('git')).resolve()
        # Component-level test uses the real installed Git runtime. The complete
        # capsule gate separately requires this executable inside its file closure.
        m=copy.deepcopy(self.m);m['git']=str(git)
        m['files'][str(git)]={'sha256':hashlib.sha256(git.read_bytes()).hexdigest(),'bytes':git.stat().st_size}
        for name,s in m['sources'].items():
            source=self.root/s['root']
            def command(*args):return subprocess.check_output([str(git),'-C',str(source),*args],stderr=subprocess.PIPE,text=True).strip()
            command('init','-q');command('config','core.autocrlf','false')
            command('remote','add','origin','https://github.com/'+s['repository']+'.git')
            command('add','.');command('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','inert source fixture')
            s['commit']=command('rev-parse','HEAD');s['tree']=command('rev-parse','HEAD^{tree}')
        self.assertEqual(set(lab.verify_sources(self.root,m)),set(m['sources']))
        (self.root/'sources/math/inert.txt').write_text('changed source bytes')
        with self.assertRaises(ValueError):lab.verify_sources(self.root,m)

    def test_actual_native_child_receives_only_lab_environment(self):
        import json,sys,time
        from unified_system.runtime_process import ProcessDriver
        from unified_system.runtime import ModuleSpec
        helper=self.root/'env_probe.py';output=self.root/'environment.json'
        helper.write_text('import json,os,sys\njson.dump({k:os.environ.get(k) for k in ("BYBIT_API_KEY","NODE_OPTIONS","UNIFIED_ORDER_MODE","UNIFIED_DEPLOYMENT_MODE")},open(sys.argv[1],"w"))\n')
        sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
        executable=Path(sys.executable).resolve()
        programs={'math':dict(argv=[str(executable),'-I','-S','-B',str(helper),str(output)],
            cwd=str(self.root),health_url='http://127.0.0.1:19000/ready',
            executable_sha256=sha(executable),file_pins={'env_probe.py':sha(helper)})}
        driver=ProcessDriver(self.root/'private',programs,authorize=lambda *_:True,child_environment=lambda module:lab.child_environment())
        with patch.dict(os.environ,{'BYBIT_API_KEY':'INERT_TEST_SECRET','NODE_OPTIONS':'INERT_TEST_STARTUP'}):
            handle=driver.start(ModuleSpec('math','1.0.0'),'lab-test','a'*32)
        try:
            until=time.monotonic()+5
            while not output.exists() and time.monotonic()<until:time.sleep(.02)
            returncode=driver.children[handle].wait(timeout=5)
            self.assertEqual(returncode,0)
            result=json.loads(output.read_text())
            self.assertIsNone(result['BYBIT_API_KEY']);self.assertIsNone(result['NODE_OPTIONS'])
            self.assertEqual(result['UNIFIED_ORDER_MODE'],'PAPER_ONLY')
            self.assertEqual(result['UNIFIED_DEPLOYMENT_MODE'],'LAB_SIMULATION')
        finally:driver.stop(handle)
        self.assertTrue(driver.children[handle].stdin.closed)


if __name__=='__main__':unittest.main()
