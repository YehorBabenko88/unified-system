"""Single actual six-profile runtime proof; isolated cloud, synthetic data only.

No production enrollment, publisher admission, market authenticity, training,
live feed, paper execution, physical acceptance or trading authority is proved.
Inputs pin exact committed sources and installed fixture runtimes independently.
"""
import argparse
import asyncio
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback

NAMES={'unified-system','grid','math','meta_analyse','strattester','terminan'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(1048576),b''):h.update(data)
    return h.hexdigest()


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def dependency_digest(root):
    files={}
    for path in sorted(root.rglob('*')):
        if path.suffix not in ('.py','.so','.pyd','.dll') or '__pycache__' in path.parts:continue
        if path.is_symlink() or not path.is_file():raise ValueError('linked dependency')
        files[str(path.relative_to(root))]=sha(path)
    if not 1<=len(files)<=20000:raise ValueError('dependency inventory bound')
    return hashlib.sha256(encoded(files)).hexdigest(),len(files)


def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def request(number,method,path,*,token=None,body=None):
    c=http.client.HTTPConnection('127.0.0.1',number,timeout=2)
    headers={}
    if token is not None:headers['Authorization']='Bearer '+token
    if body is not None:headers['Content-Type']='application/json';body=encoded(body)
    try:
        c.request(method,path,body=body,headers=headers);r=c.getresponse();raw=r.read(1048577)
        if len(raw)>1048576:raise ValueError('response bound')
        return r.status,raw
    finally:c.close()


async def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pins',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--execute-isolated-cloud-test',action='store_true');args=p.parse_args()
    # Guard before filesystem/database/process effects. No configurable office exemption.
    if (not args.execute_isolated_cloud_test or socket.gethostname().split('.')[0].upper() in ('ADMINIT','LS5','PC4')
        or not sys.platform.startswith('linux') or not Path('/etc/codex/network-policy.json').is_file()):
        p.error('managed cloud execution only; physical targets forbidden')
    pins=json.loads(args.pins.read_bytes());assert set(pins['sources'])==NAMES
    output=args.output.absolute();assert output.is_relative_to(Path('/workspace/.onboarding/mission4'))
    assert not output.exists();output.mkdir(mode=0o700)
    report=dict(schema='unified.six.actual-runtime.v1',result='BLOCKED',physical='NOT_RUN',production='NO_GO',
        source_authenticity='NOT_EVALUATED',market_data='SYNTHETIC_OFFLINE_ONLY',training_authorized=False,
        trading_authorized=False,physical_deployment_allowed=False,live_feed='NOT_RUN',paper_execution='NOT_RUN',
        owner_release_admission='NOT_EVALUATED',native_installation='NOT_RUN',all_six_functional=False,
        script_sha256=sha(__file__),sources={})
    def save(name,value):
        (output/name).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')
    def write_report():save('report.json',report)
    write_report();stage='EXTERNAL_PINS';runtime=driver=thread=None;stop=threading.Event();fences={};admin=None;dbname=None
    execution_errors=[];capsules=output/'capsules';capsules.mkdir()
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,
        GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    gitexe=Path(pins['git']['path']);python=Path(pins['python']['path']);node=Path(pins['node']['path'])
    def git(root,*a):
        return subprocess.check_output([str(gitexe),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath='+os.devnull,'-C',str(root),*a],env=env,stderr=subprocess.PIPE,timeout=30)
    def imports_checked():
        owners={'unified_system':'unified-system','integration':'unified-system','grid':'grid','meta_analyse':'meta_analyse','strattester':'strattester','terminan':'terminan'}
        for name,module in tuple(sys.modules.items()):
            owner=owners.get(name.split('.')[0])
            if owner and getattr(module,'__file__',None):fences[owner].module(module)
    try:
        for kind in ('git','python','node'):
            exe=Path(pins[kind]['path']);assert exe.is_absolute() and not exe.is_symlink() and sha(exe)==pins[kind]['sha256']
        assert Path(sys.executable).resolve()==python and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
        dependencies=Path(pins['dependencies']['path']);assert dependencies.is_absolute() and not dependencies.is_symlink()
        dep_digest,dep_count=dependency_digest(dependencies);assert dep_digest==pins['dependencies']['sha256']
        report['dependencies']={'files':dep_count,'sha256':dep_digest,'authenticity':'INSTALLED_CLOUD_FIXTURE_NOT_PUBLISHER_QUALIFIED','site_pth_execution':False}
        stage='EXACT_SOURCE_CAPSULES'
        for name,source in pins['sources'].items():
            assert re.fullmatch('[a-f0-9]{40}',source['commit'])
            origin=Path(source['path']);assert origin.is_absolute() and origin.parent==Path('/workspace')
            git(origin,'cat-file','-e',source['commit']+'^{commit}')
            target=capsules/name
            subprocess.run([str(gitexe),'-c','core.hooksPath='+os.devnull,'clone','--local','--no-hardlinks','--no-checkout',str(origin),str(target)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=True)
            git(target,'config','core.autocrlf','false');git(target,'config','core.fsmonitor','false')
            git(target,'checkout','--detach',source['commit'])
            assert not git(target,'status','--porcelain','--untracked-files=all').strip()
        root=capsules/'unified-system'
        assert (root/'integration/source_guard.py').read_bytes()==git(root,'show',pins['sources']['unified-system']['commit']+':integration/source_guard.py')
        cache=output/'import-cache';cache.mkdir();sys.pycache_prefix=str(cache);sys.dont_write_bytecode=True
        sys.path[:0]=[str(root),str(capsules/'grid'),str(capsules/'strattester'),str(capsules/'meta_analyse/src'),str(dependencies)]
        from integration.source_guard import SourceFence
        for name in NAMES:
            fences[name]=SourceFence(capsules/name,pins['sources'][name]['commit'],isolated_cache=cache,
                git_executable=str(gitexe),git_sha256=pins['git']['sha256'])
        before={name:f.check() for name,f in fences.items()}
        for name,value in before.items():
            assert all(v['comparison']=='RAW_IDENTICAL' for v in value['runtime_files'].values())
            report['sources'][name]={'commit':value['head'],'tree':value['tree'],'raw_files':len(value['runtime_files'])}
        imports_checked();stage='OWNED_POSTGRES18_DATABASE'
        import asyncpg
        # Fixed previously authorized disposable cloud fixture, never arbitrary DSN.
        dsn='postgresql://grid_test:grid_test@127.0.0.1:55438/grid_test'
        admin=await asyncpg.connect(dsn,timeout=5)
        assert int(await admin.fetchval('SHOW server_version_num'))//10000==18
        assert await admin.fetchval('SELECT current_database()')=='grid_test'
        import secrets
        dbname='six_cloud_'+secrets.token_hex(10)
        await admin.execute('CREATE DATABASE "'+dbname+'"')
        own_dsn=dsn.rsplit('/',1)[0]+'/'+dbname
        report['postgres']={'major':18,'database':'RANDOM_OWNED_DISPOSABLE','coordination':'LEGACY_SINGLE_PRIMARY_NOT_HA'}
        stage='REAL_SYNTHETIC_FIXTURES'
        def fixture(name,file):
            fences[name].file(capsules/name/file,python=True)
            spec=importlib.util.spec_from_file_location('_six_fixture_'+name.replace('-','_'),capsules/name/file)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);fences[name].module(module);return module
        grid_fixture=fixture('grid','tests/test_history_export.py')
        from grid.history_export_v11 import export_records_v11
        records,query,trust=grid_fixture.fixture(3);payload=export_records_v11(records,query,trust)
        assert payload['evidence_class']=='SYNTHETIC';save('synthetic-grid-history.json',payload)
        strat_fixture=fixture('strattester','tests/research/test_owned_receipt_compatibility.py')
        fixtures=output/'fixtures';fixtures.mkdir()
        generator=strat_fixture.sources.__wrapped__(fixtures)
        source_tuple=next(generator)
        try:record=strat_fixture.produce(source_tuple)
        finally:
            try:next(generator)
            except StopIteration:pass
        result_db=fixtures/'results.db';initial_db_sha=sha(result_db)
        assert record['execution_authority'] is False and record['metrics']=={'sum':4}
        save('synthetic-owned-research-record.json',record)
        local_trust={'sources':[[record['producer_identity'],record['source_revision'],record['dataset']['source_identity']]],
            'receipts':[[record['producer_identity'],record['source_revision'],record['run_id'],record['completion_receipt']]]}
        report['results_admission']='LOCAL_SYNTHETIC_FIXTURE_ONLY_NOT_PRODUCTION_OWNER_TRUST'
        from unified_system.runtime_cli import make_runtime,run_runtime,validate_config
        from unified_system.module_catalog import MODULE_IDS
        ports={name:port() for name in NAMES};assert len(set(ports.values()))==6
        snapshot=output/'public/runtime.json';release='cloud-six-synthetic-'+secrets.token_hex(6)
        release_digest=hashlib.sha256(encoded(report['sources'])).hexdigest()
        bootstrap=root/'unified_system/owned_python.py'
        common_env={'PATH':str(gitexe.parent),'UNIFIED_GIT_EXECUTABLE':str(gitexe),'UNIFIED_GIT_SHA256':pins['git']['sha256'],
            'UNIFIED_SOURCE_ROOT':str(root),'UNIFIED_ROOT_SOURCE_COMMIT':pins['sources']['unified-system']['commit'],
            'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'GIT_CONFIG_SYSTEM':os.devnull,'GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1',
            'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
        programs={}
        def python_program(name,module,arguments,dependency_roots=()):
            target=capsules/name
            argv=[str(python),'-I','-S','-B',str(bootstrap),'--source-root',str(target)]
            for dep in dependency_roots:argv+=['--dependency-root',str(dep)]
            argv+=['--module',module,'--',*arguments]
            programs[name]=dict(argv=argv,cwd=str(target),executable_sha256=pins['python']['sha256'],
                file_pins={n:v['raw_sha256'] for n,v in before[name]['runtime_files'].items()},
                external_file_pins={str(bootstrap):sha(bootstrap),str(gitexe):pins['git']['sha256']},
                health_url=f'http://127.0.0.1:{ports[name]}/internal/v2/module/health',
                env={**common_env,'UNIFIED_SOURCE_COMMIT':pins['sources'][name]['commit']})
        python_program('meta_analyse','meta_analyse.headless_service',['--execute','--port',str(ports['meta_analyse'])])
        python_program('strattester','strattester.owned_results_service',['--serve','--store',str(result_db),'--port',str(ports['strattester'])],[root])
        programs['strattester']['env']['STRATTESTER_RESULTS_TRUST_JSON']=json.dumps(local_trust)
        python_program('terminan','terminan.unified_runner',['--expected-sha',pins['sources']['terminan']['commit'],'--port',str(ports['terminan'])])
        programs['terminan']['env']['TERMINAN_RUNTIME_V2_SNAPSHOT']=str(snapshot)
        # owned_python also supports a dependency package as its explicit source
        # root. No site initialization or editable .pth finder executes.
        python_program('grid','uvicorn',['grid.coordinator:app','--host','127.0.0.1','--port',str(ports['grid']),'--no-access-log'],[capsules/'grid'])
        programs['grid']['argv'][6]=str(dependencies)
        grid_state=output/'grid-state'
        programs['grid']['env'].update(POSTGRES_DSN=own_dsn,GRID_COORDINATION_MODE='legacy',GRID_HA_REQUIRED='false',
            ProgramData=str(grid_state),ProgramFiles=str(grid_state/'program-files'),ML_ARTIFACT_ROOT=str(grid_state/'artifacts'),
            ARCHIVE_ROOT=str(grid_state/'archive'),STRATEGY_CACHE_DIR=str(grid_state/'strategies'),
            BYBIT_REST_URL='http://127.0.0.1:9',BYBIT_WS_URL='ws://127.0.0.1:9',BYBIT_ARCHIVE_BASE_URL='http://127.0.0.1:9',
            TELEGRAM_BOT_TOKEN='',GRID_SHARED_TOKEN=secrets.token_hex(32),LOG_LEVEL='WARNING',RETENTION_ENABLED='false')
        programs['math']=dict(argv=[str(node),str(capsules/'math/src/math-engine-server.mjs')],cwd=str(capsules/'math'),
            executable_sha256=pins['node']['sha256'],file_pins={n:v['raw_sha256'] for n,v in before['math']['runtime_files'].items()},
            external_file_pins={str(gitexe):pins['git']['sha256']},health_url=f'http://127.0.0.1:{ports["math"]}/internal/v2/module/health',
            env={**common_env,'UNIFIED_SOURCE_COMMIT':pins['sources']['math']['commit'],'MATH_ENGINE_PORT':str(ports['math'])})
        dependencies_map={'unified-system':[],'grid':['unified-system'],'math':['unified-system'],
            'meta_analyse':['grid','math'],'strattester':['grid','math'],'terminan':['meta_analyse','strattester']}
        config=dict(schema='unified.runtime.config.v2',node_id='isolated-six-cloud',release_id=release,release_sha256=release_digest,
            state_root=str(output/'state'),snapshot_path=str(snapshot),http_port=ports['unified-system'],tick_seconds=.1,
            specs=[dict(module_id=n,version='1.0.0',api_major=1,dependencies=dependencies_map[n],start_timeout=40) for n in sorted(NAMES)],programs=programs)
        validate_config(config);imports_checked()
        runtime=make_runtime(config,lambda action,module:action=='start' and module in NAMES);driver=runtime.driver.delegate
        runtime.max_restarts=0
        save('before.json',runtime.snapshot());stage='SINGLE_SUPERVISOR_DEPENDENT_STARTUP'
        def run():
            try:run_runtime(config,runtime,stop_event=stop)
            except BaseException as e:execution_errors.append(type(e).__name__)
        thread=threading.Thread(target=run,name='single-actual-runtime-loop');thread.start()
        deadline=time.monotonic()+65;seen=[]
        while time.monotonic()<deadline:
            view=runtime.snapshot()
            current={n:m['state'] for n,m in view['modules'].items()}
            if not seen or seen[-1]!=current:seen.append(current)
            if view['ready']:break
            if execution_errors or any(m['state'] in ('FAILED','BACKOFF') for m in view['modules'].values()):break
            await asyncio.sleep(.1)
        save('startup-states.json',seen);save('ready-or-blocked.json',view)
        assert not execution_errors and view['ready'] and len(driver.children)==5
        assert runtime.health_release(release)['ready'] is True
        for states in seen:
            for name in ('meta_analyse','strattester','terminan'):
                if states[name] in ('STARTING','READY'):
                    assert all(states[d]=='READY' for d in dependencies_map[name])
        stage='REAL_PRIVATE_AUTH_AND_PUBLIC_TERM_SNAPSHOT'
        tokens={}
        for operation in driver.children:
            private=driver._load(operation);tokens[private['module_id']]=private['token']
        assert set(tokens)==NAMES-{'unified-system'}
        for name,token in tokens.items():
            code,raw=request(ports[name],'GET','/internal/v2/module/health',token=token);body=json.loads(raw)
            assert code==200 and body==dict(module_id=name,version='1.0.0',release_id=release,instance_token=token,ready=True)
            assert request(ports[name],'GET','/internal/v2/module/health')[0] in (401,403)
            assert request(ports[name],'GET','/internal/v2/module/health',token='0'*64)[0] in (401,403)
        code,raw=request(ports['terminan'],'GET','/api/runtime-v2');term_view=json.loads(raw)
        assert code==200 and term_view['ready'] and term_view['release_id']==release
        save('terminan-actual-runtime.json',term_view)
        code,raw=request(ports['terminan'],'GET','/workspace/runtime');assert code==200 and b'Node-local runtime' in raw
        assert request(ports['unified-system'],'POST','/internal/v2/runtime')[0]==405
        assert request(ports['unified-system'],'GET','/internal/v2/runtime?tick=1')[0]==404
        stage='ACTUAL_NUMERICAL_HISTORY_AND_RESULT_APIS'
        code,raw=request(ports['math'],'POST','/v1/evaluate',body=dict(schema='math.evaluate.v1',mode='HISTORICAL_RESEARCH',execution_authority=False,closes=[100]*500));numerical=json.loads(raw)
        assert code==200 and numerical['windows'][0]['test']['rmse']==0
        assert all(numerical[k] is False for k in ('execution_authority','trading_authorized','training_authorized'))
        save('math-evaluation.json',numerical)
        graph=dict(schema='math.scientific.graph.v2',mode='HISTORICAL_RESEARCH',execution_authority=False,asOf=3,
            nodes=[dict(id='s',kind='source',type='series',unit='dimensionless',values=[1,2,3],timestamps=[1,2,3],availableAt=[1,2,3],provenance=dict(sourceId='synthetic-six-offline-proof',version='proof-v1',sha256='a'*64)),dict(id='f',kind='formula',expression='x*2',outputUnit='dimensionless')],
            edges=[{'from':{'node':'s','port':'value'},'to':{'node':'f','port':'x'}}],outputs=[{'node':'f','port':'value'}])
        code,raw=request(ports['math'],'POST','/v2/graph/execute',body=graph);graph_result=json.loads(raw)
        assert code==200 and graph_result['outputs'][0]['values']==[2,4,6]
        assert all(graph_result[k] is False for k in ('execution_authority','trading_authorized','training_authorized'))
        save('math-scientific-graph.json',graph_result)
        from meta_analyse.grid_history_adapter import analyze_grid_history
        for decision,count in ((59999,0),(120000,2),(180000,3)):
            code,raw=request(ports['meta_analyse'],'POST','/internal/v1/history/analyze',token=tokens['meta_analyse'],body={'payload':payload,'decision_ms':decision});analysis=json.loads(raw)
            assert code==200 and analysis==analyze_grid_history(payload,decision_ms=decision) and len(analysis['candles'])==count
            assert analysis['source_authenticity']=='NOT_EVALUATED' and all(analysis[k] is False for k in ('execution_authority','trading_authorized','training_authorized'))
            save('meta-history-'+str(decision)+'.json',analysis)
        code,raw=request(ports['strattester'],'GET','/internal/v1/runs',token=tokens['strattester']);runs=json.loads(raw)
        assert code==200 and runs['runs']==[record] and runs['execution_authority'] is False
        save('strat-synthetic-runs.json',runs);assert sha(result_db)==initial_db_sha
        conn=await asyncpg.connect(own_dsn,timeout=5)
        try:
            gate=await conn.fetchval('SELECT state FROM grid_runtime_state WHERE singleton=true')
            tables=await conn.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            assert gate=='INFRA_ONLY' and tables>10
            report['grid_database']={'runtime_gate':gate,'public_tables':tables,'market_capture':'NOT_STARTED'}
        finally:await conn.close()
        report.update(result='PASS_CLOUD_FUNCTIONAL_ONLY',all_six_functional=True,owned_processes=5,builtin_profiles=1,
            authorization='PRIVATE_PER_PROCESS_NONCE',dependency_order_verified=True,terminan_display='ACTUAL_SUPERVISOR_SNAPSHOT',
            numerical='REAL_OFFLINE_ENDPOINT',meta_history='ACTUAL_GRID_SYNTHETIC_EXPORT_CAUSAL_0_2_3_ROWS',results='ACTUAL_SYNTHETIC_RESEARCHRUNNER_RECEIPT_READONLY_API')
    except BaseException as exc:
        report.update(result='BLOCKED',failure_stage=stage,error_class=type(exc).__name__,failure_line=traceback.extract_tb(exc.__traceback__)[-1].lineno)
        # Closed public failure; preserve states and sources, not nonce/DSN or raw traceback.
    finally:
        stop.set()
        if thread is not None:thread.join(20)
        if runtime is not None:
            try:
                runtime.stop(administrative=True);stopped=runtime.snapshot();save('stopped.json',stopped)
                assert not stopped['ready'] and all(m['state']=='STOPPED' and m['administrative_stop'] for m in stopped['modules'].values())
                assert thread is None or not thread.is_alive()
                assert all(not driver.alive(op) for op in driver.children)
                report['owned_stop_confirmed']=True
            except BaseException as exc:report.update(result='BLOCKED',cleanup='OWNED_STOP_NOT_PROVED',cleanup_error=type(exc).__name__)
        if admin is not None:
            try:
                if dbname is not None:await admin.execute('DROP DATABASE "'+dbname+'" WITH (FORCE)');report['owned_database_removed']=True
                await admin.close()
            except Exception:report.update(result='BLOCKED',database_cleanup='REQUIRES_REVIEW')
        if fences:
            try:
                imports_checked()
                for fence in fences.values():fence.finish()
                report['source_tree_unchanged']=True
                assert dependency_digest(Path(pins['dependencies']['path']))[0]==pins['dependencies']['sha256']
                report['dependency_bytes_unchanged']=True
            except BaseException as exc:report.update(result='BLOCKED',postcheck_error=type(exc).__name__)
        if report.get('owned_stop_confirmed'):
            shutil.rmtree(output/'state/private-processes',ignore_errors=True)
            report['private_nonce_records_removed']=True
        write_report();print(json.dumps(report,sort_keys=True),flush=True)
    return 0 if report['result']=='PASS_CLOUD_FUNCTIONAL_ONLY' else 1


if __name__=='__main__':raise SystemExit(asyncio.run(main()))
