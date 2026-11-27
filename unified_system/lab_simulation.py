"""LAB_SIMULATION supervisor (Workstream C, MASTER #111).

Starts market_data and terminan as owned child processes under the explicit,
digest-bound LAB authorization from ``lab_simulation_admission``; verifies
authenticated readiness; stops children and removes only its own temporary
resources. Loopback only, no trading, no production credentials. This path is
separate from, and does not alter, ``lab_runtime --execute`` or the protected
Windows service activation.

Run the supervisor itself with ``python -B`` so admitted source trees stay
free of bytecode caches.

CLI:
  python -B -m unified_system.lab_simulation plan --sources SOURCES.json
  python -B -m unified_system.lab_simulation run  --sources SOURCES.json --authorization AUTH.json [--hold SECONDS]
SOURCES.json: {"release_id": str, "dependency_roots": [abs paths],
  "sources": {module_id: {"root": abs package dir, "import_root": abs dir,
                          "commit": 40-hex, "version": "x.y.z"}}}
"""
import argparse
import http.client
import json
import os
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from .lab_simulation_admission import (HEX40, MODULES, SCHEMA_CAPABILITY, LabAdmissionRejected,
                                       child_environment, components_digest, load_authorization, need,
                                       tree_identity)

CHILD = Path(__file__).absolute().with_name('lab_simulation_child.py')
MARKER = '.unified-lab-simulation-owned'
VERSION = r'[0-9]+\.[0-9]+\.[0-9]+'


def _free_loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _health(port, token, timeout=2.0):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        connection.request('GET', '/health', headers={'Authorization': 'Bearer ' + token})
        response = connection.getresponse()
        body = response.read(65536)
        return response.status, json.loads(body or b'{}')
    finally:
        connection.close()


def resolve_sources(spec):
    need(type(spec) is dict and set(spec) <= {'release_id', 'dependency_roots', 'sources'}, 'LAB_SOURCES_REJECTED')
    sources = {}
    for module_id, item in spec['sources'].items():
        need(module_id in MODULES and type(item) is dict
             and set(item) == {'root', 'import_root', 'commit', 'version'}, 'LAB_SOURCES_REJECTED')
        root, import_root = Path(item['root']), Path(item['import_root'])
        need(root.is_absolute() and import_root.is_absolute() and (root == import_root or import_root in root.parents),
             'LAB_SOURCES_REJECTED')
        need(type(item['commit']) is str and HEX40.fullmatch(item['commit']) is not None, 'LAB_SOURCES_REJECTED')
        need(type(item['version']) is str and __import__('re').fullmatch(VERSION, item['version']) is not None,
             'LAB_SOURCES_REJECTED')
        identity = tree_identity(root)
        sources[module_id] = dict(root=str(root), import_root=str(import_root), commit=item['commit'],
                                  version=item['version'], tree_sha256=identity['sha256'])
    need(set(sources) == set(MODULES), 'LAB_SOURCES_INCOMPLETE')
    need(Path(sources['unified_system']['root']) == CHILD.parent, 'LAB_SUPERVISOR_NOT_ADMITTED')
    deps = [str(Path(p)) for p in spec.get('dependency_roots', [])]
    need(all(Path(p).is_absolute() and Path(p).is_dir() for p in deps), 'LAB_SOURCES_REJECTED')
    return sources, deps


class LabSimulation:
    def __init__(self, sources, dependency_roots, authorization_path, *, python=None,
                 deadline_s=3600, ready_timeout_s=30, base_env=None, now_ms=None):
        self.sources = sources
        self.dependency_roots = list(dependency_roots)
        self.digest = components_digest(sources)
        self.authorization = load_authorization(authorization_path, self.digest, now_ms=now_ms)
        self.python = python or sys.executable
        self.child = CHILD
        self.deadline_ms = min(int(time.time() * 1000) + deadline_s * 1000, self.authorization['expires_at_ms'])
        self.ready_timeout_s = ready_timeout_s
        self.base_env = dict(os.environ if base_env is None else base_env)
        self.temp = None
        self.temp_identity = None
        self.children = {}
        self.report = dict(schema='unified.lab-simulation-run.v1', mode='LAB_SIMULATION',
                           components_sha256=self.digest, release_id=self.authorization['release_id'],
                           trading_authorized=False, execution_authority=False, production='NO_GO',
                           modules={}, stopped=False, cleaned=False)

    # resources -----------------------------------------------------------
    def _create_temp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='unified-lab-'))
        os.chmod(self.temp, 0o700)
        (self.temp / MARKER).write_text(self.digest + '\n')
        info = self.temp.lstat()
        self.temp_identity = [info.st_dev, info.st_ino]

    def _cleanup_temp(self):
        if self.temp is None:
            return
        info = self.temp.lstat()
        # Remove only what this supervisor created and still owns.
        need(stat.S_ISDIR(info.st_mode) and [info.st_dev, info.st_ino] == self.temp_identity
             and (self.temp / MARKER).read_text() == self.digest + '\n'
             and Path(tempfile.gettempdir()).resolve() in self.temp.resolve().parents, 'LAB_CLEANUP_REFUSED')
        shutil.rmtree(self.temp)
        self.report['cleaned'] = not self.temp.exists()
        self.temp = None

    # children ------------------------------------------------------------
    def _launch(self, module_id, port, token, extra_env):
        capability = dict(schema=SCHEMA_CAPABILITY, module_id=module_id, instance_token=token,
                          release_id=self.authorization['release_id'], deadline_ms=self.deadline_ms,
                          temp_root=str(self.temp), temp_identity=self.temp_identity, port=port,
                          sources=self.sources, dependency_roots=self.dependency_roots)
        env = child_environment(self.base_env, dict(
            UNIFIED_MODULE_ID=module_id, UNIFIED_MODULE_VERSION=self.sources[module_id]['version'],
            UNIFIED_RELEASE_ID=self.authorization['release_id'], UNIFIED_INSTANCE_TOKEN=token, **extra_env))
        log = open(self.temp / f'{module_id}.log', 'wb')
        process = subprocess.Popen([self.python, '-I', '-B', str(self.child)], stdin=subprocess.PIPE,
                                   stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(self.temp))
        process.stdin.write(json.dumps(capability, sort_keys=True).encode() + b'\n')
        process.stdin.flush()
        self.children[module_id] = dict(process=process, port=port, token=token, log=log)
        return process

    def _await_ready(self, module_id):
        child = self.children[module_id]
        end = time.monotonic() + self.ready_timeout_s
        last = None
        while time.monotonic() < end:
            need(child['process'].poll() is None, 'LAB_CHILD_EXITED_' + module_id.upper())
            try:
                status, body = _health(child['port'], child['token'])
                last = status
                if status == 200 and body.get('ready') is True and body.get('module_id') == module_id \
                        and body.get('instance_token') == child['token']:
                    self.report['modules'][module_id] = dict(port=child['port'], ready=True,
                                                             pid=child['process'].pid, health_status=status)
                    return body
            except (OSError, ValueError):
                pass
            time.sleep(0.2)
        raise LabAdmissionRejected('LAB_CHILD_NOT_READY_' + module_id.upper() + ('' if last is None else f'_{last}'))

    def start(self):
        try:
            self._create_temp()
            md_port, md_token = _free_loopback_port(), secrets.token_hex(32)
            md_env = dict(MARKET_DATA_PORT=str(md_port))
            dsn = self.base_env.get('LAB_MARKET_DATA_DSN')
            if dsn:
                md_env['MARKET_DATA_DSN'] = dsn
            self._launch('market_data', md_port, md_token, md_env)
            self._await_ready('market_data')
            record = dict(port=md_port, token=md_token, source_commit=self.sources['market_data']['commit'],
                          release_id=self.authorization['release_id'], epoch=str(uuid.uuid4()))
            self._launch('terminan', _free_loopback_port(), secrets.token_hex(32),
                         dict(UNIFIED_MARKET_DATA_READ_CAPABILITY=json.dumps(record, sort_keys=True)))
            self._await_ready('terminan')
            return self
        except BaseException:
            self.stop()
            raise

    def unauthenticated_denied(self):
        """Unauthenticated health must be refused by every module."""
        result = {}
        for module_id, child in self.children.items():
            connection = http.client.HTTPConnection('127.0.0.1', child['port'], timeout=2)
            try:
                connection.request('GET', '/health')
                response = connection.getresponse()
                response.read(65536)
                result[module_id] = response.status
            finally:
                connection.close()
        self.report['unauthenticated_health'] = result
        return all(status in (401, 503) for status in result.values())

    def terminan_get(self, path):
        child = self.children['terminan']
        connection = http.client.HTTPConnection('127.0.0.1', child['port'], timeout=5)
        try:
            connection.request('GET', path)
            response = connection.getresponse()
            return response.status, response.read(1 << 20)
        finally:
            connection.close()

    def stop(self):
        for module_id in reversed(list(self.children)):
            child = self.children[module_id]
            process = child['process']
            try:
                process.stdin.close()            # lifeline: child revokes and exits
            except OSError:
                pass
            try:
                process.wait(timeout=10)
                how = 'LIFELINE'
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                    how = 'TERMINATED'
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    how = 'KILLED'
            child['log'].close()
            entry = self.report['modules'].setdefault(module_id, {})
            entry.update(stopped=how, exit_code=process.returncode)
            log = self.temp / f'{module_id}.log' if self.temp else None
            if log and log.exists():
                entry['log_tail'] = log.read_bytes()[-2000:].decode('utf-8', 'replace')
        self.report['stopped'] = all(c['process'].poll() is not None for c in self.children.values())
        self._cleanup_temp()
        return self.report

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('command', choices=('plan', 'run'))
    parser.add_argument('--sources', required=True)
    parser.add_argument('--authorization')
    parser.add_argument('--hold', type=int, default=0, choices=range(0, 3601))
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    try:
        need(sys.flags.dont_write_bytecode, 'LAB_SUPERVISOR_BYTECODE_REJECTED')
        spec = json.loads(Path(args.sources).read_text(encoding='utf-8'))
        sources, deps = resolve_sources(spec)
        digest = components_digest(sources)
        if args.command == 'plan':
            print(json.dumps(dict(components_sha256=digest, sources={m: {k: s[k] for k in ('commit', 'version', 'tree_sha256')}
                                  for m, s in sources.items()}), indent=1, sort_keys=True))
            return 0
        need(args.authorization is not None, 'LAB_AUTHORIZATION_REQUIRED')
        lab = LabSimulation(sources, deps, args.authorization)
        with lab:
            lab.report['unauthenticated_denied'] = lab.unauthenticated_denied()
            status, body = lab.terminan_get('/api/status')
            lab.report['terminan_status'] = dict(http=status, body=json.loads(body))
            status, body = lab.terminan_get('/api/candles?symbol=BTCUSDT&timeframe=1m')
            lab.report['terminan_candles'] = dict(http=status, body=json.loads(body))
            time.sleep(args.hold)
        report = lab.report
        if args.report:
            Path(args.report).write_text(json.dumps(report, indent=1, sort_keys=True))
        print(json.dumps(report, indent=1, sort_keys=True))
        ok = (report['stopped'] and report['cleaned'] and report.get('unauthenticated_denied')
              and all(m.get('ready') for m in report['modules'].values()))
        return 0 if ok else 1
    except LabAdmissionRejected as error:
        print('BLOCKED: ' + str(error) + '; trading_authorized=false')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
