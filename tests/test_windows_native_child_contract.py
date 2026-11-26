"""A2 (unified-system#151): controlled Windows PowerShell 5.1 child contract.

Portable tests check the environment/argv contract on any OS. Windows tests run
the real powershell.exe and try to hijack the child through PATH, PSModulePath,
the current working directory and user profile directories. Every Windows test
uses the existing bounded runner (no new or larger timeouts).
"""
import base64
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from unified_system import installation_service as service

WINDOWS = os.name == 'nt'


def decoded(argv):
    return base64.b64decode(argv[argv.index('-EncodedCommand') + 1]).decode('utf-16le')


class PortableContractTests(unittest.TestCase):
    def setUp(self):
        self.system = Path(tempfile.mkdtemp()) / 'Windows' / 'System32'
        self.system.mkdir(parents=True)
        patcher = patch.object(service, '_system_directory', return_value=self.system)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.system.parents[1], True)

    def test_environment_is_minimal_and_path_is_fixed_not_inherited(self):
        hostile = {'PATH': r'C:\Users\x\poison;C:\Python', 'PSModulePath': r'C:\Users\x\Modules',
                   'PATHEXT': '.PS1;.BAT', 'ComSpec': r'C:\poison\cmd.exe', 'PYTHONPATH': 'x',
                   'TEMP': r'C:\Temp', 'USERPROFILE': r'C:\Users\x', 'BYBIT_API_KEY': 'k'}
        with patch.dict(os.environ, hostile, clear=True):
            env = service._environment()
        self.assertEqual(env['PATH'], ';'.join(str(p) for p in (self.system, self.system.parent, self.system / 'Wbem',
                                                                self.system / 'WindowsPowerShell/v1.0')))
        self.assertNotIn('poison', env['PATH'])
        self.assertEqual(env['PSModulePath'], str(self.system / 'WindowsPowerShell/v1.0/Modules'))
        self.assertEqual(env['PATHEXT'], '.COM;.EXE')
        self.assertEqual(env['ComSpec'], str(self.system / 'cmd.exe'))
        self.assertEqual(set(env), {'PATH', 'PSModulePath', 'PATHEXT', 'ComSpec', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'USERPROFILE'})

    def test_argv_is_absolute_noprofile_encoded_with_trusted_prelude(self):
        exe = str(self.system / 'WindowsPowerShell/v1.0/powershell.exe')
        argv = service.powershell_argv(exe, 'Write-Output 1')
        self.assertEqual(argv[:5], [exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand'])
        script = decoded(argv)
        self.assertTrue(script.startswith("$PSModuleAutoLoadingPreference='None';"))
        self.assertTrue(script.endswith('Write-Output 1'))
        self.assertIn('[Environment]::SystemDirectory', script)
        for name in service.TRUSTED_POWERSHELL_MODULES:
            self.assertIn(name, script)
        self.assertNotIn('$env:', script.split('Write-Output 1')[0], 'prelude must not trust environment paths')

    def test_argv_refuses_relative_or_foreign_executables(self):
        for exe in ('powershell.exe', str(self.system / 'pwsh.exe'), str(self.system / 'cmd.exe'),
                    str(self.system.parent / 'powershell.exe'),
                    str(self.system / 'untrusted' / 'powershell.exe'),
                    str(self.system / 'WindowsPowerShell/v1.0/other' / 'powershell.exe')):
            with self.subTest(exe=exe), self.assertRaises(ValueError):
                service.powershell_argv(exe, 'x')

    def test_argv_rejects_lookalike_same_basename_outside_system_directory(self):
        accepted = str(self.system / 'WindowsPowerShell/v1.0/powershell.exe')
        for root in (self.system.parent, self.system / 'Wbem', self.system / 'untrusted'):
            with self.subTest(root=str(root)), self.assertRaises(ValueError):
                service.powershell_argv(str(root / 'powershell.exe'), 'Write-Output 1')
        self.assertEqual(service.powershell_argv(accepted, 'Write-Output 1')[0], accepted)

    def test_run_uses_system_directory_as_working_directory(self):
        seen = {}

        class Done:
            returncode = 0
            def poll(self): return 0
            def wait(self, timeout=None): return 0

        def popen(argv, **kw):
            seen.update(kw)
            return Done()
        with patch.object(service, 'child_directory', return_value=str(self.system)), \
                patch('subprocess.Popen', side_effect=popen):
            service._run(['x'], env={})
        self.assertEqual(seen['cwd'], str(self.system))


@unittest.skipUnless(WINDOWS, 'real Windows PowerShell 5.1 child')
class WindowsHijackTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='unified-a2-'))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.marker = self.root / 'POISON_EXECUTED'
        self.exe = service._native_tools()['powershell']['path']
        self.system = str(service._system_directory())

    def poison_module(self, directory, name):
        module = directory / name
        module.mkdir(parents=True, exist_ok=True)
        escaped = str(self.marker).replace("'", "''")
        (module / (name + '.psm1')).write_text(
            "[IO.File]::WriteAllText('" + escaped + "','" + name + "');function Get-UnifiedPoisonProbe {'POISON'}")
        (module / (name + '.psd1')).write_text("@{RootModule='" + name + ".psm1';ModuleVersion='99.0.0';FunctionsToExport='*'}")

    def run_child(self, code, *, parent_env=None, parent_cwd=None):
        with patch.dict(os.environ, parent_env or {}):
            env = service._environment()
        previous = os.getcwd()
        try:
            if parent_cwd is not None:
                os.chdir(parent_cwd)
            output, status = service._run(service.powershell_argv(self.exe, code), env=env, timeout=15)
        finally:
            os.chdir(previous)
        self.assertEqual(status, 0, output)
        return json.loads(output)

    REPORT = ("$r=[ordered]@{autoload=$PSModuleAutoLoadingPreference;pwd=$PWD.ProviderPath;path=$env:PATH;"
              "modules=@(Get-Module|ForEach-Object{$_.Path});"
              "whoami=(Get-Command whoami -CommandType Application -ErrorAction SilentlyContinue|Select-Object -First 1).Source;"
              "probe=$(try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch{'NOT_FOUND'})};$r|ConvertTo-Json -Compress")

    def assert_clean(self, report):
        trusted = (self.system + '\\WindowsPowerShell\\v1.0\\Modules\\').casefold()
        self.assertEqual(report['autoload'], 'None')
        self.assertEqual(report['pwd'].rstrip('\\').casefold(), self.system.casefold())
        self.assertTrue(report['modules'])
        for path in report['modules']:
            self.assertTrue(path.casefold().startswith(trusted), path)
        self.assertTrue(str(report['whoami']).casefold().startswith(self.system.casefold()), report['whoami'])
        self.assertEqual(report['probe'], 'NOT_FOUND')
        self.assertFalse(self.marker.exists(), 'poison code executed')

    def test_clean_baseline(self):
        self.assert_clean(self.run_child(self.REPORT))

    def test_path_hijack_is_ignored(self):
        poison = self.root / 'path'
        poison.mkdir()
        (poison / 'whoami.com').write_bytes(b'\xc3')
        (poison / 'whoami.exe').write_bytes(b'MZ')
        report = self.run_child(self.REPORT, parent_env={'PATH': str(poison) + ';' + os.environ.get('PATH', ''),
                                                         'PATHEXT': '.PS1;.COM;.EXE'})
        self.assertNotIn(str(poison).casefold(), report['path'].casefold())
        self.assert_clean(report)

    def test_psmodulepath_hijack_with_trusted_module_names_is_ignored(self):
        poison = self.root / 'modules'
        for name in service.TRUSTED_POWERSHELL_MODULES + ('UnifiedPoisonProbe',):
            self.poison_module(poison, name)
        self.assert_clean(self.run_child(self.REPORT, parent_env={'PSModulePath': str(poison)}))

    def test_current_directory_hijack_is_ignored(self):
        poison = self.root / 'cwd'
        poison.mkdir()
        for name in service.TRUSTED_POWERSHELL_MODULES:
            self.poison_module(poison, name)
        (poison / 'whoami.exe').write_bytes(b'MZ')
        (poison / 'powershell.exe').write_bytes(b'MZ')
        self.assert_clean(self.run_child(self.REPORT, parent_cwd=poison))

    def test_user_profile_and_user_module_directories_are_ignored(self):
        profile = self.root / 'profile'
        documents = profile / 'Documents' / 'WindowsPowerShell'
        for name in service.TRUSTED_POWERSHELL_MODULES + ('UnifiedPoisonProbe',):
            self.poison_module(documents / 'Modules', name)
        escaped = str(self.marker).replace("'", "''")
        for script in ('profile.ps1', 'Microsoft.PowerShell_profile.ps1'):
            (documents / script).write_text("[IO.File]::WriteAllText('" + escaped + "','profile')")
        self.assert_clean(self.run_child(self.REPORT, parent_env={'USERPROFILE': str(profile),
                                                                 'APPDATA': str(profile / 'AppData' / 'Roaming'),
                                                                 'LOCALAPPDATA': str(profile / 'AppData' / 'Local')}))

    def test_autoload_disabled_command_outside_trusted_set_is_not_found(self):
        report = self.run_child("$x=$(try{Get-NetIPAddress -ErrorAction Stop;'LOADED'}catch [System.Management.Automation.CommandNotFoundException]{'NOT_FOUND'});"
                                "@{x=$x;m=@(Get-Module|ForEach-Object{$_.Name})}|ConvertTo-Json -Compress")
        self.assertEqual(report['x'], 'NOT_FOUND')
        self.assertEqual(sorted(report['m']), sorted(service.TRUSTED_POWERSHELL_MODULES))

    def test_trusted_module_manifests_are_regular_system_files(self):
        manifests = service.trusted_module_manifests()
        self.assertEqual(len(manifests), 3)
        for path in manifests:
            self.assertTrue(PureWindowsPath(path).is_absolute() and path.casefold().startswith(self.system.casefold()))


@unittest.skipUnless(WINDOWS, 'requires real disposable Windows process/loopback listener')
class WindowsOwnedListenerExtinctionTests(unittest.TestCase):
    """Native Windows process/port evidence only; never a trusted Root grant."""

    WORKER = r'''import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = os.environ["UNIFIED_INSTANCE_TOKEN"]
        if self.path != "/health" or self.headers.get("Authorization") != "Bearer " + token:
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data = json.dumps(dict(module_id=os.environ["UNIFIED_MODULE_ID"],
                               version=os.environ["UNIFIED_MODULE_VERSION"],
                               release_id=os.environ["UNIFIED_RELEASE_ID"],
                               instance_token=token, ready=True)).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args): pass
HTTPServer(("127.0.0.1", int(os.environ["PORT"])), Handler).serve_forever()
'''

    def setUp(self):
        import hashlib
        import socket
        import sys
        from unified_system.runtime_process import ProcessDriver

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.worker = self.root / 'isolated_worker.py'
        self.worker.write_text(self.WORKER, encoding='utf-8')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        python = Path(sys.executable).resolve()
        self.program = dict(
            argv=[str(python), str(self.worker)], cwd=str(self.root),
            executable_sha256=hashlib.sha256(python.read_bytes()).hexdigest(),
            file_pins={'isolated_worker.py': hashlib.sha256(self.worker.read_bytes()).hexdigest()},
            health_url='http://127.0.0.1:%d/health' % self.port,
            env={'PORT': str(self.port)},
        )
        self.driver = ProcessDriver(
            self.root / 'private', {'market_data': self.program},
            authorize=lambda action, module: action == 'start' and module == 'market_data')

    def _ready(self, driver, op):
        import time
        from unified_system.runtime import ModuleSpec
        spec = ModuleSpec('market_data', '1.0.0')
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if driver.ready(spec, op, 'disposable-lab')['ready']:
                return
            time.sleep(.05)
        self.fail('disposable native Windows listener never became ready')

    def _token_response(self, token):
        import http.client
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=.5)
        try:
            conn.request('GET', '/health', headers={'Authorization': 'Bearer ' + token})
            result = conn.getresponse()
            result.read()
            return result.status
        finally:
            conn.close()

    def test_real_old_process_exits_port_closes_and_rebound_rejects_old_token(self):
        import socket
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import ProcessDriver, _identity

        spec = ModuleSpec('market_data', '1.0.0')
        old_op, new_op = '1' * 32, '2' * 32
        self.driver.start(spec, 'disposable-lab', old_op)
        self.addCleanup(lambda: self.driver.stop(old_op))
        self._ready(self.driver, old_op)
        old = self.driver._load(old_op)
        self.assertIsNotNone(old['created'])
        self.assertEqual(_identity(old['pid']), old['created'])
        self.assertEqual(self._token_response(old['token']), 200)

        # Cross-driver stop proves the persisted OS identity is not just Popen.poll().
        external_driver = ProcessDriver(
            self.root / 'private', {'market_data': self.program},
            authorize=lambda *_: False)
        external_driver.stop(old_op)
        self.assertEqual(self.driver.children[old_op].wait(timeout=2), 0)
        self.assertFalse(external_driver.alive(old_op))
        self.assertNotEqual(_identity(old['pid']), old['created'])
        self.assertEqual(external_driver._load(old_op)['state'], 'STOPPED')

        with self.assertRaises((ConnectionRefusedError, OSError)):
            with socket.create_connection(('127.0.0.1', self.port), timeout=.3):
                pass

        self.driver.start(spec, 'disposable-lab', new_op)
        self.addCleanup(lambda: self.driver.stop(new_op))
        self._ready(self.driver, new_op)
        new = self.driver._load(new_op)
        self.assertNotEqual(new['token'], old['token'])
        self.assertEqual(self._token_response(old['token']), 403)
        self.assertEqual(self._token_response(new['token']), 200)
        self.assertFalse(external_driver.alive(old_op))

    def test_reused_identity_simulation_must_not_kill_live_owned_child(self):
        from unittest.mock import patch
        from unified_system.runtime import ModuleSpec

        op = '3' * 32
        self.driver.start(ModuleSpec('market_data', '1.0.0'), 'disposable-lab', op)
        self.addCleanup(lambda: self.driver.stop(op))
        self._ready(self.driver, op)
        child = self.driver.children[op]
        with patch('unified_system.runtime_process._identity', return_value=['reused-pid', 'foreign.exe']):
            with self.assertRaisesRegex(ValueError, 'unrelated process'):
                self.driver.stop(op)
        self.assertIsNone(child.poll(), 'foreign identity must never be terminated')
        self.assertEqual(self.driver._load(op)['state'], 'RUNNING')


class OwnedProcessProofFailureTests(unittest.TestCase):
    """Synthetic negative cases: absence/uncertainty never authorizes replacement.

    These intentionally do not assert host-wide Windows TCP ownership or
    PostgreSQL backend extinction. They prove the existing driver must not
    signal an unrelated PID and expose a fail-closed requirement for Root.
    """

    def test_stale_pid_creation_identity_refuses_stop_before_signal(self):
        from unified_system.runtime_process import ProcessDriver
        driver = object.__new__(ProcessDriver)
        driver.root = Path(tempfile.mkdtemp(prefix='a-os-identity-'))
        self.addCleanup(shutil.rmtree, driver.root, True)
        op = 'a' * 32
        driver._save(op, dict(pid=34567, created=['old-boot:1', 'old.exe'],
                              module_id='market_data', version='1.0',
                              release_id='lab', token='b' * 64,
                              state='RUNNING'), new=True)
        driver.children = {}
        with patch('unified_system.runtime_process._identity',
                   return_value=['new-boot:2', 'other.exe']):
            with self.assertRaisesRegex(ValueError, 'refuse unrelated process'):
                driver.stop(op)
            self.assertEqual(driver._load(op)['state'], 'RUNNING')

    def test_unavailable_identity_must_not_be_treated_as_verified_extinction(self):
        from unified_system.runtime_process import ProcessDriver
        driver = object.__new__(ProcessDriver)
        driver.root = Path(tempfile.mkdtemp(prefix='a-os-uncertain-'))
        self.addCleanup(shutil.rmtree, driver.root, True)
        op = 'c' * 32
        driver._save(op, dict(pid=34567, created=['old-boot:1', 'old.exe'],
                              module_id='market_data', version='1.0',
                              release_id='lab', token='d' * 64,
                              state='RUNNING'), new=True)
        driver.children = {}
        with patch('unified_system.runtime_process._identity',
                   side_effect=ValueError('access denied')):
            # Existing alive() is a liveness hint, NOT an extinction receipt.
            self.assertFalse(driver.alive(op))
            self.assertEqual(driver._load(op)['state'], 'RUNNING')
            with self.assertRaisesRegex(ValueError, 'access denied'):
                driver.stop(op)
            self.assertEqual(driver._load(op)['state'], 'RUNNING')

    def test_stopped_record_is_not_an_os_exit_receipt(self):
        from unified_system.runtime_process import ProcessDriver
        driver = object.__new__(ProcessDriver)
        driver.root = Path(tempfile.mkdtemp(prefix='a-os-record-'))
        self.addCleanup(shutil.rmtree, driver.root, True)
        op = 'e' * 32
        driver._save(op, dict(pid=34567, created=['old-boot:1', 'old.exe'],
                              module_id='market_data', version='1.0',
                              release_id='lab', token='f' * 64,
                              state='STOPPED'), new=True)
        driver.children = {}
        with patch('unified_system.runtime_process._identity',
                   return_value=['old-boot:1', 'old.exe']):
            self.assertFalse(driver.alive(op))
            # A still-live original incarnation must block fresh owner admission.
            self.assertEqual(driver._load(op)['state'], 'STOPPED')
            self.assertEqual(
                __import__('unified_system.runtime_process', fromlist=['_identity'])._identity(34567),
                ['old-boot:1', 'old.exe'])


class RetainedRootProcessStateTests(unittest.TestCase):
    """Synthetic state transitions; no listener/backend authenticity claimed."""

    def setUp(self):
        from unified_system.runtime_process import ProcessDriver
        self.driver = object.__new__(ProcessDriver)
        self.driver.root = Path(tempfile.mkdtemp(prefix='a-tristate-'))
        self.addCleanup(shutil.rmtree, self.driver.root, True)
        self.driver.children = {}
        self.op = '9' * 32
        self.pid = 23456
        self.created = ['root-boot:100', '/isolated/lab/python.exe']
        self.driver._save(self.op, dict(pid=self.pid, created=self.created,
                          module_id='market_data', version='1.0',
                          release_id='disposable-lab', token='a'*64,
                          state='RUNNING'), new=True)

    def child(self, result):
        class Child:
            pid = 23456
            def poll(self):
                return result
        self.driver.children[self.op] = Child()

    def test_original_child_still_alive(self):
        self.child(None)
        with patch('unified_system.runtime_process._identity',
                   return_value=self.created):
            self.assertEqual(self.driver.owned_process_state(self.op), 'STILL_ALIVE')

    def test_original_child_exit_proves_only_os_exit(self):
        self.child(0)
        with patch('unified_system.runtime_process._identity', return_value=None):
            self.assertEqual(self.driver.owned_process_state(self.op), 'EXTINCT')

    def test_weak_stopped_record_without_retained_handle_is_unknown(self):
        d = self.driver._load(self.op)
        d['state'] = 'STOPPED'
        self.driver._save(self.op, d)
        with patch('unified_system.runtime_process._identity', return_value=None):
            self.assertEqual(self.driver.owned_process_state(self.op), 'UNKNOWN')

    def test_foreign_pid_reuse_without_original_exit_is_unknown(self):
        self.child(None)
        with patch('unified_system.runtime_process._identity',
                   return_value=['root-boot:200', '/other/exe']):
            self.assertEqual(self.driver.owned_process_state(self.op), 'UNKNOWN')

    def test_identity_access_denied_is_unknown(self):
        self.child(None)
        with patch('unified_system.runtime_process._identity',
                   side_effect=ValueError('access denied')):
            self.assertEqual(self.driver.owned_process_state(self.op), 'UNKNOWN')

    def test_original_process_handle_absent_is_unknown(self):
        with patch('unified_system.runtime_process._identity', return_value=None):
            self.assertEqual(self.driver.owned_process_state(self.op), 'UNKNOWN')

    def test_running_process_but_corrupt_record_is_unknown(self):
        self.child(None)
        d = self.driver._load(self.op)
        d['created'] = None
        self.driver._save(self.op, d)
        self.assertEqual(self.driver.owned_process_state(self.op), 'UNKNOWN')

    def test_poll_error_is_unknown(self):
        class Child:
            pid = 23456
            def poll(self):
                raise OSError('process handle unavailable')
        self.driver.children[self.op] = Child()
        self.assertEqual(self.driver.owned_process_state(self.op), 'UNKNOWN')





class ProcessDriverFailClosedStopTests(unittest.TestCase):
    """Synthetic negatives only; no OS process or foreign PID is touched."""

    def setUp(self):
        from unified_system.runtime_process import ProcessDriver
        self.driver = object.__new__(ProcessDriver)
        self.driver.root = Path(tempfile.mkdtemp(prefix='a-round15-stop-'))
        self.addCleanup(shutil.rmtree, self.driver.root, True)
        self.driver.children = {}
        self.driver.prestart_rejections = {}
        self.driver.authorize = lambda action, module: True
        self.op = '7' * 32
        self.driver._save(self.op, dict(
            pid=98765, created=['boot:7', '/isolated/python'],
            module_id='market_data', version='1.0',
            release_id='lab', token='b' * 64,
            state='RUNNING'), new=True)

    def test_disappearing_pid_without_retained_exit_denies_stopped(self):
        with patch('unified_system.runtime_process._identity', return_value=None):
            with self.assertRaisesRegex(ValueError, 'extinction unverified'):
                self.driver.stop(self.op)
        self.assertEqual(self.driver._load(self.op)['state'], 'RUNNING')

    def test_stale_stopped_record_without_handle_denies_stop_receipt(self):
        record = self.driver._load(self.op)
        record['state'] = 'STOPPED'
        self.driver._save(self.op, record)
        with self.assertRaisesRegex(ValueError, 'extinction unverified'):
            self.driver.stop(self.op)

    def test_reused_operation_cannot_rely_on_boolean_alive_hint(self):
        from types import SimpleNamespace
        record = self.driver._load(self.op)
        spec = SimpleNamespace(module_id='market_data', version='1.0')
        with patch.object(self.driver, '_verify', return_value=None), \
             patch.object(self.driver, 'alive', return_value=True):
            with self.assertRaisesRegex(ValueError, 'ambiguous prior'):
                self.driver.start(spec, record['release_id'], self.op)
        self.assertEqual(self.driver._load(self.op)['state'], 'RUNNING')



@unittest.skipUnless(WINDOWS, 'requires native Windows Job Object')
class WindowsNativeJobContainmentTests(unittest.TestCase):
    """Temporary Job Object only; no production child or service is touched."""

    def test_empty_owned_job_has_zero_members_and_no_external_adoption(self):
        from unified_system.runtime_process import OwnedWindowsJob
        with OwnedWindowsJob() as job:
            self.assertEqual(job.active_process_count(), 0)
            self.assertFalse(job._assigned)
            with self.assertRaisesRegex(ValueError, 'public assignment denied'):
                job.assign_suspended_child(None)
            with self.assertRaisesRegex(ValueError, 'public assignment denied'):
                job.assign_suspended_child(None, created_suspended=True)
            self.assertFalse(hasattr(job, 'resume_suspended_child'))
        with self.assertRaisesRegex(ValueError, 'closed'):
            job.active_process_count()

    def test_job_is_not_an_exit_receipt_for_uncontained_process(self):
        from unified_system.runtime_process import OwnedWindowsJob
        with OwnedWindowsJob() as job:
            self.assertEqual(job.active_process_count(), 0)
            # A separate child can remain alive despite zero members in our
            # empty Job. Never treat empty-Job evidence as global extinction.
            import subprocess
            import sys
            with subprocess.Popen(
                    [sys.executable, '-c', 'import time; time.sleep(5)'],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL) as child:
                try:
                    self.assertIsNone(child.poll())
                    self.assertEqual(job.active_process_count(), 0)
                finally:
                    if child.poll() is None:
                        child.terminate()
                    child.wait(timeout=5)



@unittest.skipUnless(WINDOWS, 'requires disposable Windows Job child')
class WindowsNativeSuspendedLaunchTests(unittest.TestCase):
    """Real isolated Python child, only pre-pinned Lab ProcessDriver actions."""

    def setUp(self):
        import hashlib
        import socket
        import sys
        from unified_system.runtime_process import ProcessDriver
        self.tmp = tempfile.TemporaryDirectory(prefix='a-round17-job-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.worker = root / 'job_worker.py'
        self.worker.write_text(
            'import time\n'
            'time.sleep(30)\n', encoding='utf-8')
        python = Path(sys.executable).resolve()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        program = dict(
            argv=[str(python), str(self.worker)],
            cwd=str(root), executable_sha256=hashlib.sha256(
                python.read_bytes()).hexdigest(),
            file_pins={'job_worker.py':hashlib.sha256(
                self.worker.read_bytes()).hexdigest()},
            health_url='http://127.0.0.1:%d/health' % port,
            disposable_lab_windows_job=True)
        self.driver = ProcessDriver(
            root / 'private', {'market_data':program},
            authorize=lambda action, module: action == 'start'
            and module == 'market_data')
        self.op = '8' * 32

    def test_native_suspend_assign_resume_and_retained_stop(self):
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import _OwnedWindowsChild
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        self.assertIsInstance(child, _OwnedWindowsChild)
        self.assertTrue(child._job._assigned)
        self.assertGreaterEqual(child._job.active_process_count(), 1)
        self.assertEqual(self.driver.owned_process_state(op), 'STILL_ALIVE')
        self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'STOPPED')
        self.assertEqual(self.driver.owned_process_state(op), 'EXTINCT')

    def _cleanup(self):
        if self.op in self.driver.children:
            child = self.driver.children[self.op]
            if child.poll() is None:
                self.driver.stop(self.op)

    def test_external_driver_cannot_stop_original_job_without_handle(self):
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import ProcessDriver
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        external = ProcessDriver(
            self.driver.root, self.driver.programs,
            authorize=lambda *_: False)
        with self.assertRaisesRegex(ValueError, 'original handle required'):
            external.stop(op)
        self.assertEqual(external._load(op)['state'], 'RUNNING')
        self.assertIsNone(self.driver.children[op].poll())
        self.assertGreaterEqual(
            self.driver.children[op]._job.active_process_count(), 1)

    def test_invalid_lab_release_denied_without_start_record(self):
        from unified_system.runtime import ModuleSpec
        with self.assertRaisesRegex(ValueError, 'requires disposable LAB'):
            self.driver.start(ModuleSpec('market_data','1.0.0'),
                              'not-disposable-lab', self.op)
        self.assertFalse(self.driver._file(self.op).exists())
        self.assertNotIn(self.op, self.driver.children)

    def test_refuse_untrusted_job_attach_even_with_true(self):
        from unified_system.runtime_process import OwnedWindowsJob
        with OwnedWindowsJob() as job:
            with self.assertRaisesRegex(ValueError, 'public assignment denied'):
                job.assign_suspended_child(None, created_suspended=True)
            self.assertEqual(job.active_process_count(), 0)


@unittest.skipUnless(WINDOWS, 'requires native Windows SCM enumeration')
class WindowsNativeScmCensusTests(unittest.TestCase):
    """Read-only native SCM census, not a signed Root ownership receipt."""

    def test_kernel_scm_roster_is_bounded_and_stable_shape(self):
        from unified_system.runtime_process import _windows_service_process_roster
        entries = _windows_service_process_roster()
        self.assertIsInstance(entries, tuple)
        self.assertEqual(entries, tuple(sorted(set(entries))))
        for service_name, pid in entries:
            self.assertTrue(service_name)
            self.assertGreater(pid, 0)


@unittest.skipUnless(WINDOWS, 'requires native Windows IP Helper ownership table')
class WindowsKernelTcpOwnershipTests(unittest.TestCase):
    """Actual local socket; diagnostic kernel table, not a Root grant."""

    def test_owned_ipv4_loopback_listener_has_current_pid(self):
        import socket
        from unified_system.runtime_process import _windows_tcp_listener_owner_pids

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            owners = _windows_tcp_listener_owner_pids(port)
            self.assertIn(os.getpid(), owners)
        # Port release is not itself proof old process or descendants exited.
        self.assertIsInstance(owners, tuple)

    def test_reject_unqualified_kernel_port(self):
        from unified_system.runtime_process import _windows_tcp_listener_owner_pids
        for bad_port in (0, -1, 65536, None, True, '18766'):
            with self.subTest(port=bad_port):
                with self.assertRaisesRegex(ValueError, 'unavailable'):
                    _windows_tcp_listener_owner_pids(bad_port)


@unittest.skipUnless(WINDOWS, 'requires disposable native Windows process identity')
class WindowsRootProcessExitRaceTests(unittest.TestCase):
    """Exercise native retained process identity without production services.

    E owns the canonical sealed RootProcessObservation implementation. These
    tests use the already-existing A ProcessDriver and do NOT issue receipts,
    claim listener ownership, or touch PostgreSQL.
    """

    def setUp(self):
        import subprocess
        import sys
        self.root = Path(tempfile.mkdtemp(prefix='a-exit-race-'))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.child = subprocess.Popen(
            [sys.executable, '-c', 'import time; time.sleep(30)'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, cwd=str(self.root))
        self.addCleanup(self._cleanup_child)
        from unified_system.runtime_process import _identity
        self.pid = self.child.pid
        self.created = _identity(self.pid)
        self.assertIsNotNone(self.created)

    def _cleanup_child(self):
        if self.child.poll() is None:
            self.child.terminate()
        self.child.wait(timeout=5)

    def test_native_retained_handle_exit_not_equivalent_to_pid_only(self):
        from unified_system.runtime_process import _identity
        self.assertEqual(_identity(self.pid), self.created)
        self.assertIsNone(self.child.poll())
        self.child.terminate()
        self.child.wait(timeout=5)
        self.assertIsNotNone(self.child.poll())
        # Retained handle observed actual exit; a PID-only lookup is merely
        # a second, non-authoritative sample and can be inaccessible/reused.
        try:
            after = _identity(self.pid)
        except ValueError:
            after = None
        self.assertNotEqual(after, self.created)

    def test_retained_kernel_handle_waits_for_exact_child_exit(self):
        from unified_system.runtime_process import RetainedOsProcessWait
        with RetainedOsProcessWait(self.pid, self.created) as witness:
            self.assertFalse(witness.wait_exited(0))
            self.child.terminate()
            self.assertTrue(witness.wait_exited(5))
            self.child.wait(timeout=5)
        with self.assertRaisesRegex(ValueError, 'closed'):
            witness.wait_exited(0)

    def test_retained_kernel_handle_refuses_foreign_creation(self):
        from unified_system.runtime_process import RetainedOsProcessWait
        with self.assertRaisesRegex(ValueError, 'incarnation changed'):
            RetainedOsProcessWait(self.pid, ['other-boot', self.created[1]])
        self.assertIsNone(self.child.poll())


    def test_toolhelp_descendants_find_our_real_child(self):
        from unified_system.runtime_process import (
            _identity, _windows_process_descendant_snapshot)
        own_created = _identity(os.getpid())
        self.assertIsNotNone(own_created)
        seen = dict(_windows_process_descendant_snapshot(os.getpid(), own_created))
        self.assertIn(self.pid, seen)
        self.assertEqual(seen[self.pid], tuple(self.created))

    def test_toolhelp_foreign_root_incarnation_is_denied(self):
        from unified_system.runtime_process import _windows_process_descendant_snapshot
        with self.assertRaisesRegex(ValueError, 'root identity changed'):
            _windows_process_descendant_snapshot(
                os.getpid(), ['foreign-creation', '/foreign/exe'])
        self.assertIsNone(self.child.poll())


    def test_retained_descendant_census_blocks_unsealed_extinction(self):
        from unified_system.runtime_process import (
            _identity, RetainedWindowsDescendantCensus)
        root_pid = os.getpid()
        with RetainedWindowsDescendantCensus(
                root_pid, _identity(root_pid)) as census:
            with self.assertRaisesRegex(ValueError, 'containment not proven'):
                census.verify_complete_extinction(creation_barrier=True)
            self.assertFalse(census.wait_observed_exited(0))
        self.assertIsNone(self.child.poll())

    def test_retained_descendant_census_denies_foreign_root(self):
        from unified_system.runtime_process import RetainedWindowsDescendantCensus
        with self.assertRaisesRegex(ValueError, 'incarnation changed'):
            RetainedWindowsDescendantCensus(os.getpid(), ['foreign', '/foreign.exe'])
        self.assertIsNone(self.child.poll())


    def test_native_live_process_identity_is_not_exit(self):
        from unified_system.runtime_process import _identity
        self.assertIsNone(self.child.poll())
        self.assertEqual(_identity(self.pid), self.created)
        # No attempt to stop a foreign process or manipulate system services.



if __name__ == '__main__':
    unittest.main()
