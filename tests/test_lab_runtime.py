"""Canonical four-owner lab policy tests; no listeners or child processes.

Replaces retired Grid control/worker launcher assertions. Historical native
heartbeat/source-launch evidence remains in parent Git history, not qualification
of market_data/Terminan entrypoints. Their managed startup/revocation still needs
separately qualified source admission and native acceptance.
"""
import copy
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unified_system import lab_runtime as lab
from unified_system.module_catalog import MODULE_IDS


class CanonicalLabRuntimePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'capsule'
        self.state=Path(self.tmp.name)/'state'
        self.credential=Path(self.tmp.name)/'credentials'
        repos={'unified_system':'unified-system','market_data':'strattester','math':'math','terminan':'Terminan'}
        sources={n:dict(root='sources/'+n,repository='YehorBabenko88/'+repos[n],version='1.0.0',commit='a'*40,tree='b'*40,dependencies={}) for n in MODULE_IDS}
        bootstrap='sources/unified_system/unified_system/owned_python.py'
        files={'tools/python.exe':{'sha256':'c'*64,'bytes':1},'tools/git.exe':{'sha256':'d'*64,'bytes':1},bootstrap:{'sha256':'e'*64,'bytes':1}}
        for n in MODULE_IDS:files['sources/'+n+'/inert.txt']={'sha256':'f'*64,'bytes':1}
        self.m=dict(sources=sources,files=files,release_id='fixture',git='tools/git.exe',runtime_config='runtime.json')
        programs={}
        for n in ('market_data','math','terminan'):
            argv=[str(self.root/'tools/python.exe'),str(self.root/'sources/math/src/math-engine-server.mjs')]
            env={}
            if n!='math':
                module='market_data.cli' if n=='market_data' else 'terminan.server'
                tail=['serve'] if n=='market_data' else ['--host','127.0.0.1','--port','19000']
                argv=[str(self.root/'tools/python.exe'),'-I','-S','-B',str(self.root/bootstrap),'--source-root',str(self.root/'sources'/n),'--dependency-root',str(self.root/'dependencies/site-packages'),'--module',module,'--',*tail]
            if n=='market_data':env['MARKET_DATA_PORT']='19000'
            programs[n]=dict(argv=argv,cwd=str(self.root/'sources'/n),health_url='http://127.0.0.1:19000/health',executable_sha256='c'*64,file_pins={'inert.txt':'f'*64},env=env)
        self.c=dict(schema='unified.runtime.config.v2',node_id='LS5',release_id='fixture',release_sha256='b'*64,state_root=str(self.state),snapshot_path=str(self.state/'public/runtime.json'),http_port=19001,tick_seconds=.1,specs=[dict(module_id=n,version='1.0.0',api_major=1,dependencies=[],start_timeout=5) for n in MODULE_IDS],programs=programs)

    def validate(self,c=None,**kwargs):
        return lab.validate_config(self.c if c is None else c,self.m,self.root,hostname='LS5',**kwargs)

    def test_canonical_entrypoints_are_closed_source_profiles(self):
        original=copy.deepcopy(self.c)
        admitted=self.validate()
        self.assertEqual(set(admitted['programs']),{'market_data','math','terminan'})
        self.assertEqual(self.c,original,'validation must not mutate untrusted config')
        for name,program in admitted['programs'].items():
            self.assertEqual(Path(program['env']['PROGRAMDATA']),(self.state/name/'data').resolve())
        for name,old in [('market_data','grid.owned_worker_service'),('market_data','uvicorn'),('terminan','meta_analyse.headless_service'),('terminan','terminan.unified_runner')]:
            c=copy.deepcopy(self.c);p=c['programs'][name];p['argv'][p['argv'].index('--module')+1]=old
            with self.subTest(old=old),self.assertRaises(ValueError):self.validate(c)

    def test_managed_market_data_cannot_capture_backfill_or_select_remote_host(self):
        for tail in (['capture'],['backfill'],['serve','--host','0.0.0.0'],['serve','--execute']):
            c=copy.deepcopy(self.c);p=c['programs']['market_data'];i=p['argv'].index('--');p['argv']=p['argv'][:i+1]+tail
            with self.subTest(tail=tail),self.assertRaises(ValueError):self.validate(c)
        for port in ('18766','0','19000;bad'):
            c=copy.deepcopy(self.c);c['programs']['market_data']['env']['MARKET_DATA_PORT']=port
            with self.subTest(port=port),self.assertRaises(ValueError):self.validate(c)
        c=copy.deepcopy(self.c);p=c['programs']['terminan'];p['argv'][p['argv'].index('--host')+1]='0.0.0.0'
        with self.assertRaises(ValueError):self.validate(c)

    def test_managed_python_health_url_is_exact_loopback_contract(self):
        for name in ('market_data','terminan'):
            for url in ('http://127.0.0.1:19000/ready','https://127.0.0.1:19000/health','http://localhost:19000/health','http://127.0.0.1:19000/health/'):
                c=copy.deepcopy(self.c);c['programs'][name]['health_url']=url
                with self.subTest(name=name,url=url),self.assertRaises(ValueError):self.validate(c)

    def test_source_versions_paths_pins_and_state_namespaces_are_bound(self):
        for fault in ('version','dependency','cwd','executable','bootstrap','source','pin','state','snapshot','legacy_source'):
            c=copy.deepcopy(self.c);m=copy.deepcopy(self.m);p=c['programs']['market_data']
            if fault=='version':c['specs'][0]['version']='9.0.0'
            if fault=='dependency':c['specs'][0]['dependencies']=['math']
            if fault=='cwd':p['cwd']=str(self.state)
            if fault=='executable':p['argv'][0]=str(self.root.parent/'outside.exe')
            if fault=='bootstrap':p['argv'][4]=str(self.root/'sources/other/owned_python.py')
            if fault=='source':p['argv'][p['argv'].index('--source-root')+1]=str(self.root/'sources/terminan')
            if fault=='pin':p['file_pins']['inert.txt']='0'*64
            if fault=='state':c['state_root']=str(self.root/'mutable')
            if fault=='snapshot':c['snapshot_path']=str(self.root.parent/'outside.json')
            if fault=='legacy_source':m['sources']['grid']=m['sources'].pop('market_data')
            with self.subTest(fault=fault),self.assertRaises(ValueError):lab.validate_config(c,m,self.root,hostname='LS5')

    def test_environment_cannot_smuggle_credentials_native_roles_or_startup_code(self):
        for key,value in [('GRID_SHARED_TOKEN','a'*64),('NODE_CREDENTIAL','a'*64),('PGPASSWORD','bad'),('POSTGRES_DSN','postgresql://bad'),('MARKET_DATA_INGEST_DSN','postgresql://bad'),('GRID_LAB_AUTH_PATH',str(self.credential/'old.json')),('ROLE','coordinator'),('NODE_ROLE','CONTROL'),('NODE_OPTIONS','--import bad'),('PYTHONPATH','bad'),('UNIFIED_INSTANCE_TOKEN','a'*64),('BYBIT_API_KEY','bad')]:
            c=copy.deepcopy(self.c);c['programs']['market_data']['env'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(c)
        c=copy.deepcopy(self.c);c['programs']['market_data']['env']['market_data_port']='19000'
        with self.assertRaises(ValueError):self.validate(c)
        c=copy.deepcopy(self.c);c['programs']['market_data']['env']['PATH']=str(self.root.parent)
        with self.assertRaises(ValueError):self.validate(c)

    def test_password_free_isolated_read_dsn_is_market_data_control_only(self):
        valid='postgresql://unified_lab_read@127.0.0.1:55449/unified_lab_history'
        for key in ('MARKET_DATA_DSN','market_data_dsn','Market_Data_Dsn'):
            c=copy.deepcopy(self.c);c['programs']['market_data']['env'][key]=valid
            self.assertEqual(self.validate(c)['programs']['market_data']['env'][key],valid)
        for value in ('postgresql://unified_lab_read:secret@127.0.0.1:55449/unified_lab_history','postgresql://unified_lab_read@remote.invalid:55449/unified_lab_history','postgresql://postgres@127.0.0.1:55449/unified_lab_history',valid+'?sslmode=disable'):
            c=copy.deepcopy(self.c);c['programs']['market_data']['env']['MARKET_DATA_DSN']=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.validate(c)
        c=copy.deepcopy(self.c);c['programs']['math']['env']['MARKET_DATA_DSN']=valid
        with self.assertRaises(ValueError):self.validate(c)
        c=copy.deepcopy(self.c);c['node_id']='PC1';c['programs']['market_data']['env']['MARKET_DATA_DSN']=valid
        with self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='Easy')

    def test_offline_context_never_grants_execution_or_unscoped_paths(self):
        c=copy.deepcopy(self.c);c['node_id']='fixture_node'
        context=dict(scope='OFFLINE_VALIDATION_ONLY',role='SINGLE_PC',node_id=c['node_id'],computer_name='fixture_host',credential_root=str(self.credential))
        self.assertEqual(lab.validate_config(c,self.m,self.root,hostname='fixture_host',offline_context=context)['node_id'],'fixture_node')
        with self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='fixture_host')
        for change in ({'scope':'APPROVED'},{'node_id':'other'},{'credential_root':str(self.state)}):
            with self.subTest(change=change),self.assertRaises(ValueError):lab.validate_config(c,self.m,self.root,hostname='fixture_host',offline_context={**context,**change})
        for node,host in [('PC1','Easy'),('PC2','Leitstelle1'),('PC3','LS03e'),('PC4','LS4'),('LS7','LS-07')]:
            candidate=copy.deepcopy(self.c);candidate['node_id']=node
            self.assertEqual(lab.validate_config(candidate,self.m,self.root,hostname=host)['node_id'],node)
            with self.assertRaises(ValueError):lab.validate_config(candidate,self.m,self.root,hostname='ADMINIT')

    def test_child_environment_does_not_inherit_secrets_or_startup_injection(self):
        env=lab.child_environment({'SYSTEMROOT':'C:/Windows','BYBIT_API_KEY':'bad','GRID_SHARED_TOKEN':'bad','UNIFIED_INSTANCE_TOKEN':'bad','PYTHONPATH':'bad','NODE_OPTIONS':'--import bad'})
        for key in ('BYBIT_API_KEY','GRID_SHARED_TOKEN','UNIFIED_INSTANCE_TOKEN','PYTHONPATH','NODE_OPTIONS'):self.assertNotIn(key,env)
        self.assertEqual(env['UNIFIED_TRADING_AUTHORIZED'],'false')

    def test_execute_is_denied_before_prepare_runtime_privileges_or_processes(self):
        with patch.object(lab,'prepare') as prepare,patch.object(lab,'make_runtime') as make,patch.object(lab,'run_runtime') as run,patch('subprocess.Popen') as child,patch('sys.stdout',io.StringIO()):
            self.assertEqual(lab.main(['--mode','LAB_SIMULATION','--root',str(self.root),'--manifest-sha256','a'*64,'--execute']),1)
            prepare.assert_not_called();make.assert_not_called();run.assert_not_called();child.assert_not_called()

    def test_prepare_mode_remains_inert_and_trusted_mode_has_no_unsigned_fallback(self):
        with patch.object(lab,'prepare',return_value=(self.c,{'manifest':self.m})) as prepare,patch.object(lab,'make_runtime') as make,patch('subprocess.Popen') as child,patch('sys.stdout',io.StringIO()):
            self.assertEqual(lab.main(['--mode','LAB_SIMULATION','--root',str(self.root),'--manifest-sha256','a'*64]),0)
            self.assertEqual(prepare.call_count,1);make.assert_not_called();child.assert_not_called()
            self.assertEqual(lab.main(['--mode','TRUSTED_RELEASE','--root',str(self.root),'--manifest-sha256','a'*64]),1)
            self.assertEqual(prepare.call_count,1)

    def test_configuration_digest_binds_the_parsed_read(self):
        raw=b'{"fixture":"canonical"}';m=copy.deepcopy(self.m);m['files']['runtime.json']={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        with patch.object(lab.socket,'gethostname',return_value='LS5'),patch.object(lab.lab_release,'verify_capsule',return_value={'manifest':m}),patch.object(lab,'read_config',return_value=(self.c,raw)),patch.object(lab,'verify_sources'):
            self.assertEqual(lab.prepare(self.root,'a'*64)[0]['release_sha256'],'a'*64)
        with patch.object(lab.socket,'gethostname',return_value='LS5'),patch.object(lab.lab_release,'verify_capsule',return_value={'manifest':m}),patch.object(lab,'read_config',return_value=(self.c,raw+b' ')),patch.object(lab,'verify_sources'):
            with self.assertRaises(ValueError):lab.prepare(self.root,'a'*64)

    def test_all_four_source_checks_and_revocation_remain_required(self):
        from integration import source_guard
        root=self.root.resolve();m=self.m;seen=[]
        class Fence:
            def __init__(self,source,commit,**kwargs):
                self.name=Path(source).name
                self.commit=commit
                seen.append(self.name)
            def check(self):
                return {'tree':'b'*40,'runtime_files':{'owned.py':{'comparison':'RAW_IDENTICAL'}}}
            def git(self,*args):
                return ('https://github.com/'+m['sources'][self.name]['repository']).encode()
        with patch.object(source_guard,'SourceFence',Fence):
            checked=lab.verify_sources(root,m)
            self.assertEqual(set(checked),MODULE_IDS)
            self.assertEqual(set(seen),MODULE_IDS)
        with patch.object(source_guard,'SourceFence',Fence),patch.object(Fence,'check',side_effect=ValueError('source revoked')):
            with self.assertRaises(ValueError):lab.verify_sources(root,m)
        with patch.object(source_guard,'SourceFence',Fence),patch.object(Fence,'check',return_value={'tree':'0'*40,'runtime_files':{}}):
            with self.assertRaises(ValueError):lab.verify_sources(root,m)

    def test_historical_auth_reader_retains_hash_and_worker_secret_refusals(self):
        import json
        self.credential.mkdir()
        record=dict(schema='unified.lab.grid-auth.v3',node_id='PC1',role='WORKER',release_id='fixture',source_commit='a'*40,grid_shared_token=None,node_credential='w'*64,postgres_password=None)
        target=self.credential/'historical.json'
        def write():
            raw=lab.lab_release.canonical(record);target.write_bytes(raw);return hashlib.sha256(raw).hexdigest()
        pin=write()
        self.assertEqual(lab.read_grid_auth(target,pin,node_id='PC1',release_id='fixture',source_commit='a'*40),{'NODE_CREDENTIAL':'w'*64})
        with self.assertRaises(ValueError):lab.read_grid_auth(target,'0'*64,node_id='PC1',release_id='fixture',source_commit='a'*40)
        for changes in ({'schema':'unified.lab.grid-auth.v2'},{'grid_shared_token':'a'*64},{'postgres_password':'b'*64},{'node_id':'PC2'}):
            baseline=copy.deepcopy(record);record.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):lab.read_grid_auth(target,write(),node_id='PC1',release_id='fixture',source_commit='a'*40)
            record.clear();record.update(baseline)

if __name__=='__main__':unittest.main()
