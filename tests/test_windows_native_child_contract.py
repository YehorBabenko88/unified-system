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


    def test_restricted_windows_launch_uses_detached_original_handle_contract(self):
        """Portable call-contract test of original A Win32 function, no spawn."""
        import ctypes
        from ctypes import wintypes as w
        from types import SimpleNamespace
        from unified_system.runtime_process import _WindowsNonServiceLabToken

        captured = []
        def fake_create_process(*args):
            captured.append(args)
            return 1

        token = object.__new__(_WindowsNonServiceLabToken)
        token._handle = w.HANDLE(17)
        token._a = SimpleNamespace(CreateProcessAsUserW=fake_create_process)
        scalar = ctypes.c_ulong()
        self.assertTrue(token.create_suspended(
            None, [str(self.system / 'python.exe')],
            ctypes.create_unicode_buffer('python.exe'),
            ctypes.create_unicode_buffer('X=Y' + chr(0) * 2),
            str(self.system), scalar, scalar))
        self.assertEqual(len(captured), 1)
        args = captured[0]
        self.assertEqual(args[0].value, 17)  # original restricted primary token
        self.assertEqual(args[5], False)  # inherit NO handles
        self.assertEqual(args[6], 0x00000004 | 0x00000400 | 0x00000008)
        self.assertEqual(args[8], str(self.system))
        self.assertEqual(args[3:5], (None, None))

    def test_restricted_pinned_artifact_read_with_original_token(self):
        """Execute canonical pinned SHA read while original token impersonates."""
        import ctypes
        import hashlib
        from ctypes import wintypes as w
        from types import SimpleNamespace
        from unified_system.runtime_process import _WindowsNonServiceLabToken

        worker = self.system / 'job_worker.py'
        worker.write_bytes(b'import sys\\nsys.exit(71)\\n')
        digest = hashlib.sha256(worker.read_bytes()).hexdigest()
        calls = []
        token = object.__new__(_WindowsNonServiceLabToken)
        token._handle = w.HANDLE(17)
        token._a = SimpleNamespace(
            ImpersonateLoggedOnUser=lambda handle: calls.append(('enter', handle.value)) or True,
            RevertToSelf=lambda: calls.append(('leave',)) or True)
        token.verify_restricted_pinned_read(
            str(self.system), {'job_worker.py': digest}, {})
        self.assertEqual(calls, [('enter', 17), ('leave',)])
        with self.assertRaisesRegex(ValueError, 'read denied'):
            token.verify_restricted_pinned_read(
                str(self.system), {'job_worker.py': '0' * 64}, {})
        self.assertEqual(calls[-2:], [('enter', 17), ('leave',)])

    def test_restricted_pinned_artifact_permission_denied_fails_closed(self):
        """A denied LOW-token read never yields a positive artifact witness."""
        import ctypes
        import hashlib
        from ctypes import wintypes as w
        from types import SimpleNamespace
        from unified_system.runtime_process import _WindowsNonServiceLabToken

        worker = self.system / 'job_worker.py'
        worker.write_bytes(b'only-disposable-test-bytes')
        digest = hashlib.sha256(worker.read_bytes()).hexdigest()
        calls = []
        token = object.__new__(_WindowsNonServiceLabToken)
        token._handle = w.HANDLE(17)
        token._a = SimpleNamespace(
            ImpersonateLoggedOnUser=lambda handle: calls.append('enter') or True,
            RevertToSelf=lambda: calls.append('leave') or True)
        with patch('unified_system.runtime_process._sha',
                   side_effect=PermissionError('restricted ACL denied')):
            with self.assertRaisesRegex(ValueError, 'read denied'):
                token.verify_restricted_pinned_read(
                    str(self.system), {'job_worker.py': digest}, {})
        self.assertEqual(calls, ['enter', 'leave'])
        with self.assertRaisesRegex(ValueError, 'pinned artifact invalid'):
            token.verify_restricted_pinned_read(
                str(self.system), {'../private/secret': digest}, {})
        self.assertEqual(calls, ['enter', 'leave'],
                         'invalid path must reject before impersonation')

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
        driver.prestart_rejections = {}
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
        driver.prestart_rejections = {}
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
        driver.prestart_rejections = {}
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
        # This synthetic fixture bypasses __init__ to test stale-identity
        # refusal. A program policy must nevertheless exist so start()
        # reaches the *original existing operation* guard, never a spawn.
        self.driver.programs = {'market_data': {
            'argv': ['/isolated/python'],
            'cwd': '/isolated',
            'health_url': 'http://127.0.0.1:18766/health',
            'executable_sha256': 'a' * 64,
            'file_pins': {'worker.py': 'b' * 64}}}
        # Prevent unrelated preflight fixture gaps from masking the intended
        # old-operation OS-identity refusal before any spawn attempt.
        self.driver._job_launch_bindings = {}
        self.driver._job_receipts = {}
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
             patch.object(self.driver, 'alive', return_value=True), \
             patch.object(self.driver, 'owned_process_state', return_value='UNKNOWN'):
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
        # The hosted runner's user-private TEMP root denies file reads to
        # the original restricted LOW token (observed Win2022 Py3.12/3.13).
        # Use a disposable private fixture under the checked-out workspace,
        # whose access must still pass the original LOW-token SHA preflight.
        # No ACL, integrity label, privileges, or child-token change.
        workspace = Path(__file__).resolve().parent.parent
        fixture_parent = workspace / '.a2-disposable-native-child'
        fixture_parent.mkdir(exist_ok=True)
        self.addCleanup(lambda: fixture_parent.rmdir()
                        if fixture_parent.is_dir() and not any(fixture_parent.iterdir())
                        else None)
        self.tmp = tempfile.TemporaryDirectory(
            prefix='a-round33-job-', dir=str(fixture_parent))
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
        self.assertIs(type(child._job._no_scm_capability_verified), object)
        self.assertGreaterEqual(child._job.active_process_count(), 1)
        self.assertIn(child.pid, child._job.observe_member_pids())
        self.assertEqual(self.driver.owned_process_state(op), 'STILL_ALIVE')
        self.assertEqual(self.driver.owned_job_stop_state(op), 'STILL_ALIVE')
        self.driver.stop(op)
        self.assertEqual(self.driver.owned_job_stop_state(op), 'EXTINCT')
        self.assertEqual(self.driver._load(op)['state'], 'STOPPED')
        self.assertEqual(self.driver.owned_process_state(op), 'EXTINCT')
        receipt = self.driver.job_extinction_receipt(op)
        self.assertEqual(receipt.active_members, 0)
        self.assertEqual(receipt.process_handle, child._handle)
        self.assertEqual(receipt.job_handle, child._job._handle)
        self.assertEqual(receipt.instance_token, self.driver._load(op)['token'])
        self.assertEqual(receipt.release_id, 'disposable-lab')
        self.assertEqual(receipt.listener_owners, ())
        self.assertEqual(receipt.scm_owners, ())
        with self.assertRaisesRegex(ValueError, 'receipt invalid'):
            self.driver.consume_job_extinction(
                receipt, release_id='wrong-release', operation_id=op)
        self.assertIs(self.driver.job_extinction_receipt(op), receipt)
        self.assertIs(self.driver.consume_job_extinction(
            receipt, release_id='disposable-lab', operation_id=op), receipt)
        self.assertIsNone(child._handle)
        self.assertIsNone(child._job._handle)
        self.assertEqual(self.driver.owned_job_stop_state(op), 'UNKNOWN')
        with self.assertRaises(ValueError):
            self.driver.consume_job_extinction(
                receipt, release_id='disposable-lab', operation_id=op)

    def _cleanup(self):
        child = self.driver.children.get(self.op)
        if child is None or child._handle is None:
            return
        try:
            if self.driver._load(self.op)['state'] != 'STOPPED':
                self.driver.stop(self.op)
            receipt = self.driver.job_extinction_receipt(self.op)
            self.driver.consume_job_extinction(
                receipt, release_id='disposable-lab', operation_id=self.op)
        finally:
            # Disposable test-only original Job owner; cleanup is not a
            # Root admission or a service/process operation on any other PID.
            if child._handle is not None:
                child.close_owned_handles()

    def test_native_receipt_denied_if_protected_token_witness_missing(self):
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        issuer_proof = child._job._no_scm_capability_verified
        child._job._no_scm_capability_verified = True
        with self.assertRaisesRegex(
                ValueError, 'historical Windows SCM process membership unproven'):
            self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'RUNNING')
        self.assertNotIn(op, self.driver._job_receipts)
        self.assertEqual(child._job.active_process_count(), 0)
        self.assertEqual(self.driver.owned_job_stop_state(op), 'EXTINCT')
        self.assertIsNotNone(child._handle)
        child._job._no_scm_capability_verified = issuer_proof
        self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'STOPPED')

    def test_native_exited_image_lookup_unavailable_but_original_kernel_creation_verified(self):
        """Real original Job + process handles; post-exit image lookup is not usable."""
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import _win_api, _win_creation_time
        op = self.driver.start(ModuleSpec('market_data', '1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        bound = self.driver._job_launch_bindings[op]
        k, w = _win_api()
        self.assertEqual(_win_creation_time(k, w, child._handle), bound[2][0])
        self.driver.stop(op)
        self.assertEqual(self.driver.owned_job_stop_state(op), 'EXTINCT')
        with patch('unified_system.runtime_process._win_identity',
                   side_effect=ValueError('injected image query unavailable after exit')):
            # The original process kernel HANDLE, creation timestamp and
            # launch-bound image hash still must qualify the same receipt.
            receipt = self.driver.job_extinction_receipt(op)
            self.assertEqual(receipt.creation_time, bound[2][0])
            self.assertEqual(receipt.executable, bound[2][1])
            self.assertEqual(receipt.process_handle, child._handle)
            self.assertEqual(receipt.job_handle, child._job._handle)
        # Mutating original creation-time witness must never allow a receipt.
        with patch('unified_system.runtime_process._win_creation_time',
                   return_value='0'):
            with self.assertRaisesRegex(ValueError, 'creation identity changed'):
                self.driver.job_extinction_receipt(op)

    def test_native_foreign_driver_cannot_observe_exact_job_stop(self):
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import ProcessDriver
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        other = ProcessDriver(self.driver.root, self.driver.programs,
                              authorize=lambda *_: False)
        self.assertEqual(other.owned_job_stop_state(op), 'UNKNOWN')
        self.assertEqual(self.driver.owned_job_stop_state(op), 'STILL_ALIVE')
        self.driver.stop(op)
        self.assertEqual(self.driver.owned_job_stop_state(op), 'EXTINCT')
        self.assertEqual(other.owned_job_stop_state(op), 'UNKNOWN')

    def test_native_historical_child_scm_association_denies(self):
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        historical_pid = child.pid + 100000
        child._job._historical_member_pids.add(historical_pid)
        with patch('unified_system.runtime_process._windows_service_process_roster',
                   return_value=(('historical-child-service', historical_pid),)):
            with self.assertRaisesRegex(ValueError, 'TCP or SCM ownership unresolved'):
                self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'RUNNING')
        self.assertNotIn(op, self.driver._job_receipts)

    def test_native_foreign_tcp_listener_denies_job_receipt(self):
        import socket
        from urllib.parse import urlsplit
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        port = urlsplit(self.driver.programs['market_data']['health_url']).port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(('127.0.0.1', port))
            server.listen(1)
            with self.assertRaisesRegex(
                    ValueError, 'TCP or SCM ownership unresolved'):
                self.driver.stop(op)
            # Denial must not publish durable STOPPED or any receipt.
            self.assertEqual(self.driver._load(op)['state'], 'RUNNING')
            self.assertNotIn(op, self.driver._job_receipts)
        self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'STOPPED')

    def test_native_foreign_ipv6_listener_denies_job_receipt(self):
        import socket
        from urllib.parse import urlsplit
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        port = urlsplit(self.driver.programs['market_data']['health_url']).port
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as server:
            server.bind(('::1', port))
            server.listen(1)
            with self.assertRaisesRegex(
                    ValueError, 'TCP or SCM ownership unresolved'):
                self.driver.stop(op)
            self.assertEqual(self.driver._load(op)['state'], 'RUNNING')
            self.assertNotIn(op, self.driver._job_receipts)
            self.assertEqual(self.driver.owned_job_stop_state(op), 'EXTINCT')
        self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'STOPPED')

    def test_native_scm_root_ownership_denies_receipt(self):
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        # Inject a positive SCM ownership fact; not a native SCM E2E PASS.
        with patch('unified_system.runtime_process._windows_service_process_roster',
                   return_value=(('foreign-test-service', child.pid),)):
            with self.assertRaisesRegex(
                    ValueError, 'TCP or SCM ownership unresolved'):
                self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'RUNNING')
        self.assertNotIn(op, self.driver._job_receipts)
        self.driver.stop(op)

    def test_native_tampered_executable_digest_denies_receipt(self):
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        original = self.driver._job_launch_bindings[op]
        self.driver._job_launch_bindings[op] = (
            *original[:3], '0'*64, *original[4:])
        with self.assertRaisesRegex(ValueError, 'executable bytes changed'):
            self.driver.stop(op)
        self.assertEqual(self.driver._load(op)['state'], 'RUNNING')
        self.driver._job_launch_bindings[op] = original
        self.driver.stop(op)

    def test_native_restricted_child_reports_explicit_abnormal_exit(self):
        """Unexpected loader exit cannot become executable/SCM success evidence."""
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data', '1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        self.assertIsNone(child.poll(), 'restricted process exited before executing pinned fixture')
        # Native Windows loader errors such as 0xC0000142 must not be
        # mislabelled as a normal Python child return code.
        self.assertEqual(self.driver.owned_job_stop_state(op), 'STILL_ALIVE')

    def test_native_detached_console_diagnostic_preserves_restricted_token_and_job(self):
        """Test-only console differential, never a production flag change."""
        import ctypes
        import sys
        from ctypes import wintypes as w

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetConsoleWindow.restype = w.HWND
        host_console = bool(kernel.GetConsoleWindow())
        print('LAB_DLL_INIT_DIAG parent_console=%s python=%s'
              % (host_console, sys.version.split()[0]), flush=True)
        op, child = self._start_detached_diagnostic_child()
        status = child.poll()
        print('LAB_DLL_INIT_DIAG detached_status=%s original_job=%s'
              % (('STILL_ALIVE' if status is None else
                  '0x%08X' % status), bool(child._job._assigned)), flush=True)
        self.assertIsNone(
            status, 'restricted child did not survive isolated DETACHED_PROCESS '
                    'console-topology experiment')

    def _start_detached_diagnostic_child(self):
        """Legacy test name; use the exact canonical restricted Job launcher.

        A second test-only CreateProcessAsUserW implementation previously
        duplicated the production call. The owner launch now uses the
        already native-proven detached console flag itself, so tests must
        exercise its original token, suspended Job and retained handles.
        """
        from unified_system.runtime import ModuleSpec
        op = self.driver.start(ModuleSpec('market_data', '1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        return op, self.driver.children[op]

    def test_native_detached_relative_script_access_differential(self):
        """Compare absolute versus same-cwd relative pinned worker arguments.

        Exact restricted token, original Job/handles, worker byte pin and
        test-local console flag are unchanged. No ACL or privilege change.
        """
        import hashlib

        self.worker.write_text('import sys\nsys.exit(71)\n', encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        original_argv = program['argv']
        self.addCleanup(lambda: program.__setitem__('argv', original_argv))
        # Same pinned script/cwd; alter only the argv path spelling.
        program['argv'] = [original_argv[0], self.worker.name]
        op, child = self._start_detached_diagnostic_child()
        status = child.wait(timeout=8)
        print('LAB_FILE_ACCESS_DIAG relative_worker_exit=%s' % status,
              flush=True)
        self.assertEqual(
            status, 71, 'restricted relative-path worker could not execute')
        self.driver.stop(op)
        self.assertEqual(self.driver.job_extinction_receipt(op).active_members, 0)

    def test_native_detached_file_access_matches_low_token(self):
        """Pinned file read from same restricted child; no filesystem mutation.

        A child that can read the exact bytes exits 71; failures retain their
        original non-71 status. Original LOW token and Job remain unchanged.
        """
        import hashlib

        self.worker.write_text('import sys\nsys.exit(71)\n', encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        original_argv = program['argv']
        self.addCleanup(lambda: program.__setitem__('argv', original_argv))
        code = (
            'import pathlib,sys;'
            'p=pathlib.Path(%r)\n'
            'try:\n'
            ' data=p.read_bytes()\n'
            'except OSError as e:\n'
            ' sys.exit(80 if isinstance(e, PermissionError) else 81)\n'
            'sys.exit(71 if data==%r else 76)'
            % (str(self.worker), self.worker.read_bytes()))
        program['argv'] = [original_argv[0], '-c', code]
        op, child = self._start_detached_diagnostic_child()
        status = child.wait(timeout=8)
        print('LAB_FILE_ACCESS_DIAG inline_file_read_exit=%s' % status,
              flush=True)
        self.assertEqual(
            status, 71, 'original restricted token cannot read pinned worker')
        self.driver.stop(op)
        self.assertEqual(self.driver.job_extinction_receipt(op).active_members, 0)

    def test_native_detached_imports_without_owner_pycache_prefix(self):
        """Restricted Python imports stdlib without referencing owner cache.

        The original LOW token, original Windows Job and retained process
        handle are unchanged; no cache ACL or directory is granted to child.
        A positive diagnostic cannot qualify the standard console mode.
        """
        program = self.driver.programs['market_data']
        original_argv = program['argv']
        self.addCleanup(lambda: program.__setitem__('argv', original_argv))
        code = (
            'import os,sys,pathlib;'
            'sys.exit(71 if os.environ.get("PYTHONPYCACHEPREFIX") is None '
            'and os.environ.get("PYTHONDONTWRITEBYTECODE")=="1" '
            'and sys.dont_write_bytecode else 78)'
        )
        program['argv'] = [original_argv[0], '-c', code]
        op, child = self._start_detached_diagnostic_child()
        status = child.wait(timeout=8)
        print('LAB_PYCACHE_DIAG restricted_stdlib_exit=%s' % status,
              flush=True)
        self.assertEqual(status, 71,
                         'restricted Python failed cache-free stdlib import')
        self.driver.stop(op)
        self.assertEqual(self.driver.job_extinction_receipt(op).active_members, 0)

    def test_native_detached_inline_python_distinguishes_script_open_failure(self):
        """Use pinned Python -c to separate interpreter startup from file open.

        Still the original LOW restricted token, suspended Job, original handles
        and test-only DETACHED_PROCESS. An inline PASS cannot qualify the
        file-backed production worker, SCM child or release admission.
        """
        program = self.driver.programs['market_data']
        argv = program['argv']
        # Only this disposable test substitutes arguments. Executable pin,
        # token, environment, Job and its original handles remain unchanged.
        program['argv'] = [argv[0], '-c', 'import sys; sys.exit(71)']
        self.addCleanup(lambda: program.__setitem__('argv', argv))
        op, child = self._start_detached_diagnostic_child()
        status = child.wait(timeout=8)
        print('LAB_CHILD_EXIT2_DIAG inline_python_exit=%s file_python_exit_prior=2'
              % status, flush=True)
        self.assertEqual(
            status, 71, 'detached restricted Python inline startup not proven')
        self.driver.stop(op)
        receipt = self.driver.job_extinction_receipt(op)
        self.assertEqual(receipt.active_members, 0)
        self.assertEqual(receipt.process_handle, child._handle)
        self.assertEqual(receipt.job_handle, child._job._handle)

    def test_native_detached_worker_executes_and_single_use_receipt(self):
        """A distinctive child exit proves script execution, not just DLL load."""
        import hashlib

        # A Low Integrity child cannot be assumed to have write access to
        # medium-integrity TEMP. Exit code is observed on its original handle.
        self.worker.write_text(
            'import sys\n'
            'sys.exit(71)\n', encoding='utf-8')
        self.driver.programs['market_data']['file_pins']['job_worker.py'] = (
            hashlib.sha256(self.worker.read_bytes()).hexdigest())
        op, child = self._start_detached_diagnostic_child()
        self.assertEqual(child.wait(timeout=8), 71,
                         'restricted child did not execute pinned Python code')
        self.driver.stop(op)
        receipt = self.driver.job_extinction_receipt(op)
        self.assertEqual(receipt.active_members, 0)
        self.assertEqual(receipt.process_handle, child._handle)
        self.assertEqual(receipt.job_handle, child._job._handle)
        self.assertIs(self.driver.consume_job_extinction(
            receipt, release_id='disposable-lab', operation_id=op), receipt)
        with self.assertRaises(ValueError):
            self.driver.consume_job_extinction(
                receipt, release_id='disposable-lab', operation_id=op)

    def _assert_detached_descendant_extinction(self, op, child):
        """Shared original Job/retained-handle proof for both native fixtures."""
        import time
        from unified_system.runtime_process import RetainedOsProcessWait, _identity

        deadline = time.monotonic() + 5
        members = ()
        while time.monotonic() < deadline:
            if child.poll() is not None:
                break
            members = child._job.observe_member_pids()
            if len(members) >= 2:
                break
            time.sleep(.05)
        self.assertIsNone(child.poll(), 'detached original child exited early')
        self.assertEqual(len(members), 2, 'detached worker never created a Job descendant')
        descendants = set(members) - {child.pid}
        self.assertEqual(len(descendants), 1)
        descendant_pid = descendants.pop()
        incarnation = _identity(descendant_pid)
        self.assertIsNotNone(incarnation)
        with RetainedOsProcessWait(descendant_pid, incarnation) as retained:
            self.driver.stop(op)
            self.assertTrue(retained.wait_exited(0))
        receipt = self.driver.job_extinction_receipt(op)
        self.assertEqual(receipt.active_members, 0)
        self.assertIs(self.driver.consume_job_extinction(
            receipt, release_id='disposable-lab', operation_id=op), receipt)

    def test_native_detached_inline_descendant_job_differential(self):
        """One variable: nested inline Python, rather than a second script.

        Test-only DETACHED_PROCESS, exact original LOW restricted primary token,
        pre-resume Job and original handles are preserved. Even a positive
        result does not qualify file-backed production worker or SCM.
        """
        program = self.driver.programs['market_data']
        original_argv = program['argv']
        self.addCleanup(lambda: program.__setitem__('argv', original_argv))
        parent_code = (
            'import subprocess,sys,time;'
            'p=subprocess.Popen([sys.executable,"-c",'
            '"import time;time.sleep(30)"],close_fds=True);'
            'time.sleep(2);'
            'sys.exit(83) if p.poll() is not None else time.sleep(28)'
        )
        program['argv'] = [original_argv[0], '-c', parent_code]
        op, child = self._start_detached_diagnostic_child()
        self._assert_detached_descendant_extinction(op, child)

    def test_native_detached_child_descendants_exit_with_original_job(self):
        """Actual pinned nested Python must join original pre-resume Job."""
        import hashlib

        secondary = self.worker.with_name('descendant_worker.py')
        secondary.write_text('import time\ntime.sleep(30)\n', encoding='utf-8')
        self.worker.write_text(
            'import subprocess, sys, os, time\n'
            'subprocess.Popen([sys.executable, os.path.join('
            'os.path.dirname(__file__), "descendant_worker.py")], close_fds=True)\n'
            'time.sleep(30)\n', encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        program['file_pins']['descendant_worker.py'] = hashlib.sha256(
            secondary.read_bytes()).hexdigest()
        op, child = self._start_detached_diagnostic_child()
        self._assert_detached_descendant_extinction(op, child)

    def test_native_detached_worker_proves_actual_scm_create_denial(self):
        """Never create service: test restricted child OpenSCManagerW CREATE."""
        import hashlib
        self.worker.write_text(
            'import ctypes, sys\n'
            'from ctypes import wintypes as w\n'
            'a=ctypes.WinDLL("advapi32",use_last_error=True)\n'
            'a.OpenSCManagerW.argtypes=[w.LPCWSTR,w.LPCWSTR,w.DWORD]\n'
            'a.OpenSCManagerW.restype=w.HANDLE\n'
            'h=a.OpenSCManagerW(None,None,2)\n'
            'if h:\n'
            ' a.CloseServiceHandle.argtypes=[w.HANDLE]\n'
            ' a.CloseServiceHandle(h)\n'
            ' sys.exit(74)\n'
            'sys.exit(73 if ctypes.get_last_error()==5 else 75)\n',
            encoding='utf-8')
        self.driver.programs['market_data']['file_pins']['job_worker.py'] = (
            hashlib.sha256(self.worker.read_bytes()).hexdigest())
        op, child = self._start_detached_diagnostic_child()
        self.assertEqual(child.wait(timeout=8), 73,
                         'LOW-integrity child did not prove SCM CREATE denial')
        self.driver.stop(op)
        self.assertEqual(self.driver.job_extinction_receipt(op).active_members, 0)

    def test_native_restricted_child_cannot_obtain_scm_create_right(self):
        import hashlib
        from unified_system.runtime import ModuleSpec
        self.worker.write_text(
            'import ctypes, sys, time\n'
            'from ctypes import wintypes as w\n'
            'a = ctypes.WinDLL("advapi32", use_last_error=True)\n'
            'a.OpenSCManagerW.argtypes = [w.LPCWSTR, w.LPCWSTR, w.DWORD]\n'
            'a.OpenSCManagerW.restype = w.HANDLE\n'
            'time.sleep(1)\n'
            'h = a.OpenSCManagerW(None, None, 2)\n'
            'if h:\n'
            ' a.CloseServiceHandle.argtypes = [w.HANDLE]\n'
            ' a.CloseServiceHandle(h)\n'
            ' sys.exit(74)\n'
            'sys.exit(73 if ctypes.get_last_error() == 5 else 75)\n',
            encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        self.assertEqual(self.driver.children[op].wait(timeout=8), 73)
        self.assertEqual(self.driver.owned_process_state(op), 'EXTINCT')
        self.driver.stop(op)
        self.assertEqual(self.driver.job_extinction_receipt(op).active_members, 0)

    def test_native_unqualified_environment_denies_restricted_launch(self):
        from unified_system.runtime import ModuleSpec
        self.driver.programs['market_data']['env'] = {
            'PRIVILEGED_SERVICE_CREDENTIALS': 'unqualified'}
        with self.assertRaisesRegex(ValueError, 'restricted LAB environment unqualified'):
            self.driver.start(ModuleSpec('market_data','1.0.0'),
                              'disposable-lab', self.op)
        self.assertNotIn(self.op, self.driver.children)
        self.assertNotIn(self.op, self.driver._job_receipts)
        self.assertFalse(self.driver._file(self.op).exists(),
                         'unqualified policy must reject before STARTING')

    def test_native_token_verification_denies_before_resume(self):
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import _WindowsNonServiceLabToken
        with patch.object(_WindowsNonServiceLabToken, 'verify_suspended_process',
                          side_effect=ValueError('forced restricted child denial')):
            with self.assertRaisesRegex(ValueError, 'forced restricted child denial'):
                self.driver.start(ModuleSpec('market_data','1.0.0'),
                                  'disposable-lab', self.op)
        self.assertNotIn(self.op, self.driver.children)
        self.assertNotIn(self.op, self.driver._job_launch_bindings)
        self.assertEqual(self.driver._load(self.op)['state'], 'STARTING')

    def test_native_missing_restricted_token_never_falls_back(self):
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import _WindowsNonServiceLabToken
        with patch.object(_WindowsNonServiceLabToken, '__init__',
                          side_effect=ValueError('forced restricted token unavailable')):
            with self.assertRaisesRegex(ValueError, 'forced restricted token unavailable'):
                self.driver.start(ModuleSpec('market_data','1.0.0'),
                                  'disposable-lab', self.op)
        self.assertNotIn(self.op, self.driver.children)
        self.assertNotIn(self.op, self.driver._job_launch_bindings)
        self.assertNotIn(self.op, self.driver._job_receipts)
        self.assertEqual(self.driver._load(self.op)['state'], 'STARTING')

    def test_native_child_token_has_no_reenableable_privileges(self):
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import _WindowsNonServiceLabToken
        op = self.driver.start(ModuleSpec('market_data','1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        # Re-query the actual suspended-launch child's token, not a user
        # supplied privilege set. The helper's internal token is already
        # closed; the kernel process object is the sole source.
        from ctypes import wintypes as w
        import ctypes
        a = ctypes.WinDLL('advapi32', use_last_error=True)
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        a.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
        a.OpenProcessToken.restype = w.BOOL
        k.CloseHandle.argtypes = [w.HANDLE]
        token = w.HANDLE()
        self.assertTrue(a.OpenProcessToken(child._handle, 0x0002 | 0x0004 | 0x0008,
                                           ctypes.byref(token)))
        try:
            # Construct a read-only verifier without creating a second token
            # or acting as an independent lifecycle supervisor.
            verifier = object.__new__(_WindowsNonServiceLabToken)
            verifier._a, verifier._k = a, k
            roster = verifier._token_privileges(token)
            class Luid(ctypes.Structure):
                _fields_ = [('low', w.DWORD), ('high', w.LONG)]
            a.LookupPrivilegeValueW.argtypes = [
                w.LPCWSTR, w.LPCWSTR, ctypes.POINTER(Luid)]
            a.LookupPrivilegeValueW.restype = w.BOOL
            allowed = Luid()
            self.assertTrue(a.LookupPrivilegeValueW(
                None, 'SeChangeNotifyPrivilege', ctypes.byref(allowed)))
            self.assertTrue(all((lo, hi) == (allowed.low, allowed.high)
                                for lo, hi, attrs in roster), roster)
        finally:
            k.CloseHandle(token)

    def test_native_createprocess_failure_no_published_child(self):
        import os
        from unified_system.runtime_process import _launch_owned_windows_job_process
        not_an_executable = self.worker.with_name('absent-program.exe')
        self.assertFalse(not_an_executable.exists())
        with self.assertRaisesRegex(
                ValueError, 'suspended process creation denied'):
            _launch_owned_windows_job_process(
                [str(not_an_executable)], str(self.worker.parent),
                dict(os.environ))
        self.assertNotIn(self.op, self.driver.children)
        self.assertNotIn(self.op, self.driver._job_launch_bindings)

    def test_native_failed_launch_does_not_leak_kernel_handles(self):
        import ctypes
        import os
        from ctypes import wintypes as w
        from unified_system.runtime_process import _launch_owned_windows_job_process
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.GetCurrentProcess.restype = w.HANDLE
        k.GetProcessHandleCount.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
        k.GetProcessHandleCount.restype = w.BOOL
        count = w.DWORD()
        self.assertTrue(k.GetProcessHandleCount(k.GetCurrentProcess(),
                                                ctypes.byref(count)))
        initial = int(count.value)
        missing = self.worker.with_name('never-created-test.exe')
        for _ in range(4):
            with self.assertRaises(ValueError):
                _launch_owned_windows_job_process(
                    [str(missing)], str(self.worker.parent), dict(os.environ))
        self.assertTrue(k.GetProcessHandleCount(k.GetCurrentProcess(),
                                                ctypes.byref(count)))
        self.assertLessEqual(int(count.value), initial + 2,
                             'original token, process, thread or Job handle leaked')

    def test_native_assignment_failure_never_resumes_child(self):
        import hashlib
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import OwnedWindowsJob
        sentinel = self.worker.with_name('execution-sentinel')
        self.worker.write_text(
            'import os\n'
            'with open(os.environ["JOB_TEST_SENTINEL"], "w") as f:'
            ' f.write("ran")\n',
            encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        program['env'] = {'JOB_TEST_SENTINEL': str(sentinel)}
        with patch.object(OwnedWindowsJob, '_assign_created_process',
                          side_effect=ValueError('forced native assignment denial')):
            with self.assertRaisesRegex(
                    ValueError, 'forced native assignment denial'):
                self.driver.start(ModuleSpec('market_data','1.0.0'),
                                  'disposable-lab', self.op)
        self.assertFalse(sentinel.exists())
        self.assertNotIn(self.op, self.driver.children)
        self.assertNotIn(self.op, self.driver._job_launch_bindings)
        self.assertEqual(self.driver._load(self.op)['state'], 'STARTING')

    def test_native_resume_failure_cleans_job_and_child(self):
        import hashlib
        from unified_system.runtime import ModuleSpec
        sentinel = self.worker.with_name('resume-execution-sentinel')
        self.worker.write_text(
            'import os\n'
            'with open(os.environ["JOB_TEST_SENTINEL"], "w") as f:'
            ' f.write("ran")\n',
            encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        program['env'] = {'JOB_TEST_SENTINEL': str(sentinel)}
        with patch('unified_system.runtime_process._resume_original_suspended_thread',
                   side_effect=ValueError('forced native resume denial')):
            with self.assertRaisesRegex(ValueError, 'forced native resume denial'):
                self.driver.start(ModuleSpec('market_data','1.0.0'),
                                  'disposable-lab', self.op)
        self.assertFalse(sentinel.exists())
        self.assertNotIn(self.op, self.driver.children)
        self.assertEqual(self.driver._load(self.op)['state'], 'STARTING')

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

    def test_native_nested_child_in_same_job_exits_on_owner_stop(self):
        import hashlib
        import time
        from unified_system.runtime import ModuleSpec
        from unified_system.runtime_process import RetainedOsProcessWait, _identity

        secondary = self.worker.with_name('descendant_worker.py')
        secondary.write_text('import time\ntime.sleep(30)\n', encoding='utf-8')
        self.worker.write_text(
            'import os, subprocess, sys, time\n'
            'p = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__),'
            ' "descendant_worker.py")], close_fds=True)\n'
            'time.sleep(30)\n',
            encoding='utf-8')
        program = self.driver.programs['market_data']
        program['file_pins']['job_worker.py'] = hashlib.sha256(
            self.worker.read_bytes()).hexdigest()
        program['file_pins']['descendant_worker.py'] = hashlib.sha256(
            secondary.read_bytes()).hexdigest()
        program['env'] = {}
        op = self.driver.start(ModuleSpec('market_data', '1.0.0'),
                               'disposable-lab', self.op)
        self.addCleanup(self._cleanup)
        child = self.driver.children[op]
        deadline = time.monotonic() + 5
        members = ()
        while time.monotonic() < deadline:
            members = child._job.observe_member_pids()
            if len(members) >= 2:
                break
            time.sleep(.05)
        self.assertEqual(len(members), 2, 'LAB child never created a Job descendant')
        descendants = set(members) - {child.pid}
        self.assertEqual(len(descendants), 1)
        pid = descendants.pop()
        identity = _identity(pid)
        self.assertIsNotNone(identity)
        with RetainedOsProcessWait(pid, identity) as witness:
            self.assertGreaterEqual(child._job.active_process_count(), 2)
            self.driver.stop(op)
            self.assertTrue(witness.wait_exited(0))
        self.assertEqual(self.driver._load(op)['state'], 'STOPPED')

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

    def test_owned_ipv6_loopback_listener_has_current_pid(self):
        import socket
        from unified_system.runtime_process import _windows_tcp_listener_owner_pids

        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as listener:
            listener.bind(('::1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertIn(os.getpid(), _windows_tcp_listener_owner_pids(port))

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
