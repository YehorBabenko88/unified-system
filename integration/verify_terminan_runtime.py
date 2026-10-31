"""Exact-source owned Terminan process proof; never physical or six-module admission."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def isolated_host(execute):
    if execute is not True:
        raise ValueError('explicit isolated cloud execution flag required')
    if socket.gethostname().split('.')[0].upper() in ('ADMINIT', 'LS5', 'PC4'):
        raise ValueError('office execution prohibited')
    hosted = (os.environ.get('GITHUB_ACTIONS') == 'true'
              and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted')
    if os.name == 'nt':
        if not hosted or os.environ.get('RUNNER_OS') != 'Windows' or not os.environ.get('RUNNER_TEMP'):
            raise ValueError('disposable hosted Windows runner required')
        return Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    if not sys.platform.startswith('linux'):
        raise ValueError('unsupported isolated execution host')
    if not (hosted and os.environ.get('RUNNER_OS') == 'Linux'
            or Path('/etc/codex/network-policy.json').is_file()):
        raise ValueError('managed cloud or disposable hosted Linux fixture required')
    return Path(os.environ['RUNNER_TEMP']).resolve(strict=True) if hosted else Path(tempfile.gettempdir()).resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--execute-isolated-cloud-test', action='store_true')
    args = parser.parse_args()
    try:
        parent = isolated_host(args.execute_isolated_cloud_test)
    except ValueError as exc:
        parser.error(str(exc))
    term = args.terminan.resolve(strict=True)
    output = args.output.absolute()
    if any(output.resolve().is_relative_to(source) for source in (ROOT, term)):
        parser.error('evidence must be outside both source trees')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema='unified.terminan.actual-process.v1', result='FAIL',
                  qualification='UNQUALIFIED', physical='NOT_RUN', production='NO_GO',
                  trading_authorized=False, authentication_required=False,
                  owned_stop_confirmed=False, other_five_modules='STOPPED_NOT_QUALIFIED',
                  all_six_ready=False)

    def save():
        (output/'evidence.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n', encoding='utf-8')

    save()
    workspace = None
    runtime = driver = None
    fences = None
    stage = 'EXECUTION_SCOPE'
    failed = True

    def attest_imports():
        for name, module in tuple(sys.modules.items()):
            if name.split('.')[0] in ('integration', 'unified_system'):
                if name == 'integration' and getattr(module, '__file__', None) is None:
                    continue
                fences['unified-system'].module(module)

    try:
        workspace = Path(tempfile.mkdtemp(prefix='mission4-real-terminan-', dir=parent))
        cache = workspace/'bytecode'
        cache.mkdir()
        # No Root executable imports before switching to a fresh bytecode namespace.
        sys.pycache_prefix = str(cache)
        sys.path.insert(0, str(ROOT))
        from integration.source_guard import SourceFence
        pins = json.loads((ROOT/'integration/source-pins.json').read_text(encoding='utf-8'))
        stage = 'SOURCE_PRECHECK'
        fences = {'unified-system': SourceFence(ROOT, isolated_cache=cache),
                  'terminan': SourceFence(term, pins['terminan'], isolated_cache=cache)}
        before = {name: fence.check() for name, fence in fences.items()}
        fences['unified-system'].file(__file__, python=True)
        from unified_system.runtime import RuntimeSupervisor, ModuleSpec
        from unified_system.runtime_process import ProcessDriver
        from unified_system.runtime_cli import write_snapshot
        from unified_system.module_catalog import MODULE_IDS

        attest_imports()
        # Each executable pin is bound to bytes already checked against immutable
        # tracked Git blobs, including the explicitly declared Windows EOL policy.
        files = before['terminan']['runtime_files']
        file_pins = {name: record['raw_sha256'] for name, record in files.items()}
        binding = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        executable = Path(sys.executable).resolve(strict=True)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        snapshot = workspace/'public/runtime.json'
        program = dict(argv=[str(executable), '-B', '-m', 'terminan.unified_runner',
                             '--expected-sha', before['terminan']['head'], '--port', str(port)],
                       cwd=str(term), executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                       file_pins=file_pins, health_url=f'http://127.0.0.1:{port}/internal/v2/module/health',
                       env={'TERMINAN_RUNTIME_V2_SNAPSHOT': str(snapshot), 'PYTHONPATH': str(term),
                            'PYTHONPYCACHEPREFIX': str(workspace/'child-bytecode'),
                            'PYTHONDONTWRITEBYTECODE': '1'})
        driver = ProcessDriver(workspace/'private', {'terminan': program},
                               authorize=lambda action, module: action == 'start' and module == 'terminan')
        release = 'cloud-terminan-source-regression'
        identity = {name: {'head': value['head'], 'tree': value['tree']} for name, value in before.items()}
        release_digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        runtime = RuntimeSupervisor(workspace/'runtime.db', driver,
                                    [ModuleSpec(name, '1.0.0') for name in sorted(MODULE_IDS)],
                                    release_id=release, release_sha256=release_digest,
                                    node_id='isolated-terminan-test', max_restarts=0)
        stage = 'OWNED_START_AND_AUTHENTICATED_READINESS'
        write_snapshot(snapshot, runtime.snapshot())
        runtime.start_module('terminan')
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            runtime.tick()
            view = runtime.snapshot()
            write_snapshot(snapshot, view)
            if view['modules']['terminan']['ready']:
                break
            time.sleep(.05)
        if not view['modules']['terminan']['ready']:
            raise AssertionError('Terminan did not become ready')
        if view['ready'] or runtime.health_release(release)['ready']:
            raise AssertionError('unstarted modules granted readiness')
        if any(view['modules'][name]['state'] != 'STOPPED' for name in MODULE_IDS-{'terminan'}):
            raise AssertionError('another module was started')

        def get(path, limit):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            try:
                connection.request('GET', path)
                response = connection.getresponse()
                raw = response.read(limit+1)
                if len(raw) > limit:
                    raise ValueError('bounded loopback response exceeded')
                return response.status, raw
            finally:
                connection.close()

        stage = 'ACTUAL_RUNTIME_DISPLAY'
        status, raw = get('/api/runtime-v2', 262144)
        if status != 200 or json.loads(raw) != view:
            raise AssertionError('runtime display differs from actual supervisor snapshot')
        status, raw = get('/workspace/runtime', 65536)
        if status != 200 or b'Node-local runtime' not in raw:
            raise AssertionError('runtime workspace unavailable')
        stage = 'UNAUTHENTICATED_HEALTH_DENIAL'
        status, _ = get('/internal/v2/module/health', 16384)
        if status != 403:
            raise AssertionError('unauthenticated readiness accepted')
        report.update(authentication_required=True, runtime='OWNED_CLEAN_TERMINAN_READY',
                      display='ACTUAL_SUPERVISOR_SNAPSHOT_AND_RUNTIME_WORKSPACE',
                      sources=identity, program_file_pins_sha256=binding)
        failed = False
    except BaseException as exc:
        failed = True
        report.update(failure_stage=stage, error_class=type(exc).__name__)
        save()  # Preserve a public failure record before any owned cleanup.
    finally:
        if runtime is not None:
            try:
                runtime.stop(administrative=True)
                stopped = runtime.snapshot()
                if any(module['state'] != 'STOPPED' for module in stopped['modules'].values()):
                    raise AssertionError('reverse administrative stop incomplete')
                if any(driver.alive(operation) for operation in driver.children):
                    raise AssertionError('owned child remains alive')
                report['owned_stop_confirmed'] = True
            except Exception as exc:
                failed = True
                report.update(failure_stage='OWNED_STOP', error_class=type(exc).__name__)
                save()
                # Retry only exact driver-owned identities; never signal by name.
                for operation in driver.children:
                    try:
                        driver.stop(operation)
                    except Exception:
                        pass
        if fences is not None and all(fence.before is not None for fence in fences.values()):
            try:
                attest_imports()
                for fence in fences.values():
                    fence.finish()
            except Exception as exc:
                failed = True
                report.update(failure_stage='SOURCE_POSTCHECK', error_class=type(exc).__name__)
        if not failed:
            report.update(result='PASS', qualification='EXACT_SOURCE_CONSISTENT')
        else:
            report.pop('sources', None)
            report.pop('program_file_pins_sha256', None)
        save()
        # Keep private ownership records if cleanup could not prove termination.
        # They are never copied into the public evidence directory or stdout.
        if workspace is not None and (driver is None or all(not driver.alive(op) for op in driver.children)):
            try:
                shutil.rmtree(workspace)
            except OSError as exc:
                failed = True
                report.update(result='FAIL', failure_stage='PRIVATE_CLEANUP', error_class=type(exc).__name__)
                save()
    print(json.dumps(report, sort_keys=True))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
