"""Workstream C: LAB_SIMULATION startup admission, lifecycle and fail-closed controls."""
import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from unified_system import lab_simulation as lab
from unified_system.lab_simulation_admission import (LabAdmissionRejected, LabGrant, SCHEMA_AUTHORIZATION,
                                                     SCHEMA_CAPABILITY, child_environment, components_digest,
                                                     load_authorization, loopback_dsn, tree_identity)

PACKAGE = Path(lab.__file__).absolute().parent

FAKE_SERVER = textwrap.dedent('''
    import hmac, json, os
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    MODULE = {module!r}
    def main(argv=None, *, startup_admission=None):
        if startup_admission is None or startup_admission.require_current() is not True:
            raise RuntimeError('admission required')
        if os.environ.get('BYBIT_API_KEY') is not None:
            raise RuntimeError('credential leaked into child')
        port = int(os.environ['MARKET_DATA_PORT']) if MODULE == 'market_data' else int(argv[argv.index('--port') + 1])
        token = os.environ['UNIFIED_INSTANCE_TOKEN']
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                ok = hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token)
                try:
                    current = startup_admission.require_current() is True
                except Exception:
                    current = False
                body = dict(module_id=MODULE, ready=True, instance_token=token) if ok and current else dict(ready=False)
                data = json.dumps(body).encode()
                self.send_response(200 if ok and current else 401)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *a):
                pass
        with ThreadingHTTPServer(('127.0.0.1', port), Handler) as server:
            server.serve_forever()
''')


def authorization(path, digest, **change):
    now = int(time.time() * 1000)
    value = dict(schema=SCHEMA_AUTHORIZATION, mode='LAB_SIMULATION', components_sha256=digest,
                 release_id='lab-test', issued_at_ms=now - 1000, expires_at_ms=now + 600_000,
                 loopback_only=True, trading_authorized=False, production_credentials=False, operator='test')
    value.update(change)
    Path(path).write_text(json.dumps(value))
    return path


class Fixture:
    """Isolated copies of the admitted trees, free of bytecode caches."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='lab-sim-test-')).resolve()
        unified = self.root / 'unified' / 'unified_system'
        unified.mkdir(parents=True)
        for name in ('__init__.py', 'lab_simulation_admission.py', 'lab_simulation_child.py'):
            shutil.copyfile(PACKAGE / name, unified / name)
        self.child = unified / 'lab_simulation_child.py'
        trees = {'market_data': ('md', 'market_data', 'cli.py'), 'terminan': ('term', 'terminan', 'server.py')}
        self.spec = dict(release_id='lab-test', dependency_roots=[], sources=dict(
            unified_system=dict(root=str(unified), import_root=str(unified.parent), commit='1' * 40, version='0.1.0')))
        for module_id, (top, package, entry) in trees.items():
            directory = self.root / top / package
            directory.mkdir(parents=True)
            (directory / '__init__.py').write_text('')
            (directory / entry).write_text(FAKE_SERVER.format(module=module_id))
            self.spec['sources'][module_id] = dict(root=str(directory), import_root=str(directory.parent),
                                                   commit='2' * 40, version='0.1.0')
        math = self.root / 'math' / 'python'
        math.mkdir(parents=True)
        (math / 'market_math.py').write_text('VALUE = 1\n')
        self.spec['sources']['math'] = dict(root=str(math), import_root=str(math), commit='3' * 40, version='0.1.0')

    def resolve(self):
        with patch.object(lab, 'CHILD', self.child):
            return lab.resolve_sources(self.spec)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TreeIdentityTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp()).resolve()
        (self.dir / 'a.py').write_text('x = 1\n')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_identity_changes_with_content(self):
        first = tree_identity(self.dir)['sha256']
        (self.dir / 'a.py').write_text('x = 2\n')
        self.assertNotEqual(first, tree_identity(self.dir)['sha256'])

    def test_bytecode_cache_and_pyc_are_refused(self):
        (self.dir / '__pycache__').mkdir()
        with self.assertRaisesRegex(LabAdmissionRejected, 'BYTECODE'):
            tree_identity(self.dir)
        shutil.rmtree(self.dir / '__pycache__')
        (self.dir / 'b.pyc').write_bytes(b'x')
        with self.assertRaisesRegex(LabAdmissionRejected, 'BYTECODE'):
            tree_identity(self.dir)

    @unittest.skipIf(os.name == 'nt', 'symlink creation needs privilege on Windows')
    def test_links_are_refused(self):
        os.symlink(self.dir / 'a.py', self.dir / 'link.py')
        with self.assertRaisesRegex(LabAdmissionRejected, 'LINK'):
            tree_identity(self.dir)


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / 'auth.json'
        self.digest = 'a' * 64

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_valid_authorization(self):
        self.assertEqual(load_authorization(authorization(self.path, self.digest), self.digest)['mode'], 'LAB_SIMULATION')

    def test_refusals(self):
        now = int(time.time() * 1000)
        cases = {'COMPONENTS_MISMATCH': dict(components_sha256='b' * 64),
                 'EXPIRED': dict(expires_at_ms=now - 1),
                 'SCOPE': dict(trading_authorized=True)}
        for code, change in cases.items():
            with self.subTest(code=code), self.assertRaisesRegex(LabAdmissionRejected, code):
                load_authorization(authorization(self.path, self.digest, **change), self.digest)
        for change in (dict(loopback_only=False), dict(production_credentials=True), dict(mode='TRUSTED_RELEASE'),
                       dict(expires_at_ms=now + 25 * 3600 * 1000), dict(extra=1)):
            with self.subTest(change=change), self.assertRaises(LabAdmissionRejected):
                load_authorization(authorization(self.path, self.digest, **change), self.digest)
        self.path.write_text('{"schema":1,"schema":2}')
        with self.assertRaises(LabAdmissionRejected):
            load_authorization(self.path, self.digest)


class EnvironmentTests(unittest.TestCase):
    def test_credentials_never_forwarded(self):
        env = child_environment({'PATH': '/bin', 'BYBIT_API_KEY': 'k', 'BYBIT_API_SECRET': 's', 'PGPASSWORD': 'p',
                                 'GITHUB_TOKEN': 't'}, {'UNIFIED_MODULE_ID': 'terminan'})
        self.assertEqual(set(env) & {'BYBIT_API_KEY', 'BYBIT_API_SECRET', 'PGPASSWORD', 'GITHUB_TOKEN'}, set())
        self.assertEqual(env['UNIFIED_TRADING_AUTHORIZED'], 'false')
        with self.assertRaisesRegex(LabAdmissionRejected, 'CREDENTIAL'):
            child_environment({}, {'BYBIT_API_SECRET': 'x'})

    def test_only_loopback_dsn(self):
        self.assertTrue(loopback_dsn('postgresql://reader:' + 'a' * 16 + '@127.0.0.1:5433/lab'))
        for dsn in ('postgresql://reader:' + 'a' * 16 + '@10.0.0.5:5432/lab', 'postgresql://reader@127.0.0.1:5432/lab'):
            self.assertFalse(loopback_dsn(dsn))
            with self.assertRaisesRegex(LabAdmissionRejected, 'LOOPBACK'):
                child_environment({}, {'MARKET_DATA_DSN': dsn})


class GrantTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.sources, _ = self.fixture.resolve()
        self.temp = Path(tempfile.mkdtemp())
        info = self.temp.lstat()
        self.capability = dict(schema=SCHEMA_CAPABILITY, module_id='terminan', instance_token='c' * 64,
                               release_id='lab-test', deadline_ms=int(time.time() * 1000) + 60_000,
                               temp_root=str(self.temp), temp_identity=[info.st_dev, info.st_ino], port=1,
                               sources=self.sources)

    def tearDown(self):
        self.fixture.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_current_then_revoked_by_closed_lifeline(self):
        stream = io.BytesIO(b'')
        grant = LabGrant(self.capability, watch_stream=stream)
        deadline = time.monotonic() + 5
        while not grant.revoked and time.monotonic() < deadline:
            time.sleep(0.01)
        with self.assertRaisesRegex(LabAdmissionRejected, 'REVOKED'):
            grant.require_current()

    def test_deadline_component_change_and_temp_identity(self):
        clock = [time.time()]
        grant = LabGrant(self.capability, clock=lambda: clock[0])
        self.assertIs(grant.require_current(), True)
        self.assertEqual(grant.source_identity('market_data')['commit'], '2' * 40)
        clock[0] += 120
        with self.assertRaisesRegex(LabAdmissionRejected, 'EXPIRED'):
            grant.require_current()
        clock[0] -= 120
        target = Path(self.sources['market_data']['root']) / 'cli.py'
        target.write_text(target.read_text() + '\n# changed\n')
        with self.assertRaisesRegex(LabAdmissionRejected, 'CHANGED'):
            grant.require_current()

    def test_tampered_source_refused_at_construction(self):
        (Path(self.sources['terminan']['root']) / 'server.py').write_text('raise SystemExit\n')
        with self.assertRaisesRegex(LabAdmissionRejected, 'IDENTITY'):
            LabGrant(self.capability)


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.sources, self.deps = self.fixture.resolve()
        self.auth = authorization(self.fixture.root / 'auth.json', components_digest(self.sources))
        self.before = set(Path(tempfile.gettempdir()).glob('unified-lab-*'))

    def tearDown(self):
        self.fixture.close()

    def simulation(self, **kw):
        with patch.object(lab, 'CHILD', self.fixture.child):
            return lab.LabSimulation(self.sources, self.deps, self.auth, base_env=dict(os.environ, BYBIT_API_KEY='x'),
                                     ready_timeout_s=30, **kw)

    def test_owned_start_authenticated_readiness_stop_and_cleanup(self):
        simulation = self.simulation()
        with simulation:
            self.assertTrue(simulation.unauthenticated_denied())
            pids = [c['process'].pid for c in simulation.children.values()]
            self.assertEqual(len(pids), 2)
        report = simulation.report
        self.assertTrue(report['stopped'] and report['cleaned'])
        for module_id in ('market_data', 'terminan'):
            self.assertTrue(report['modules'][module_id]['ready'])
            self.assertEqual(report['modules'][module_id]['stopped'], 'LIFELINE')
            self.assertEqual(report['modules'][module_id]['exit_code'], 0)
        self.assertEqual(set(Path(tempfile.gettempdir()).glob('unified-lab-*')), self.before)
        self.assertFalse(report['trading_authorized'])

    def test_wrong_authorization_starts_nothing(self):
        authorization(self.auth, 'f' * 64)
        with patch('subprocess.Popen', side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(LabAdmissionRejected, 'COMPONENTS_MISMATCH'):
                self.simulation()
        self.assertEqual(set(Path(tempfile.gettempdir()).glob('unified-lab-*')), self.before)

    def test_source_changed_after_admission_fails_closed_and_cleans(self):
        simulation = self.simulation()
        target = Path(self.sources['market_data']['root']) / 'cli.py'
        target.write_text(target.read_text() + '\n# tampered\n')
        with self.assertRaisesRegex(LabAdmissionRejected, 'LAB_CHILD_EXITED_MARKET_DATA'):
            simulation.start()
        self.assertTrue(simulation.report['stopped'] and simulation.report['cleaned'])
        self.assertIn('BLOCKED_LAB_CHILD', simulation.report['modules']['market_data']['log_tail'])
        self.assertEqual(simulation.report['modules']['market_data']['exit_code'], 78)

    def test_supervisor_must_be_admitted_unified_package(self):
        with self.assertRaisesRegex(LabAdmissionRejected, 'SUPERVISOR_NOT_ADMITTED'):
            lab.resolve_sources(self.fixture.spec)


class ExistingGateUnchangedTests(unittest.TestCase):
    def test_lab_runtime_execute_still_blocked(self):
        from unified_system import lab_runtime
        with patch.object(lab_runtime, 'prepare', side_effect=AssertionError('must not prepare')):
            self.assertEqual(lab_runtime.main(['--mode', 'LAB_SIMULATION', '--root', str(Path.cwd()),
                                               '--manifest-sha256', 'a' * 64, '--execute']), 1)


if __name__ == '__main__':
    unittest.main()
