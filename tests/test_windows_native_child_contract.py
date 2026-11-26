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


if __name__ == '__main__':
    unittest.main()
