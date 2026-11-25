"""A2 (#151): hardened Windows PowerShell 5.1 children.

Pure environment/argv controls run everywhere. Real-child controls run on
Windows only and use the existing 15/30 s bounds (no bound is raised). Each
attack has a control that demonstrates the attack works without hardening, so
a passing hardened case is meaningful.
"""
import base64
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from unified_system import windows_powershell as wp

SYSTEM = PureWindowsPath(r'C:\Windows\System32')
POISON = {
    'PATH': r'C:\poison', 'PATHEXT': '.COM;.EXE;.BAT;.CMD;.PS1', 'PSModulePath': r'C:\poison\modules',
    'COR_ENABLE_PROFILING': '1', 'COR_PROFILER': '{00000000-0000-0000-0000-000000000000}',
    'COR_PROFILER_PATH': r'C:\poison\p.dll', 'COMPlus_EnableDiagnostics': '1', 'DOTNET_STARTUP_HOOKS': r'C:\poison\h.dll',
    'PSExecutionPolicyPreference': 'Bypass', '__PSLockdownPolicy': '0', 'BYBIT_API_SECRET': 'x', 'GITHUB_TOKEN': 'x',
    'SYSTEMROOT': r'C:\poison', 'WINDIR': r'C:\poison', 'ComSpec': r'C:\poison\cmd.exe',
    'TEMP': r'C:\Users\u\AppData\Local\Temp', 'TMP': r'\\server\share', 'USERPROFILE': r'C:\Users\u',
}


class EnvironmentControls(unittest.TestCase):
    def env(self, extra=None):
        return wp.environment(extra, parent=POISON, directory=SYSTEM)

    def test_closed_environment_rebuilt_from_system_directory(self):
        env = self.env()
        self.assertEqual(env['PATH'], r'C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem;'
                                      r'C:\Windows\System32\WindowsPowerShell\v1.0')
        self.assertEqual(env['PATHEXT'], '.COM;.EXE')
        self.assertEqual(env['PSModulePath'], r'C:\Windows\System32\WindowsPowerShell\v1.0\Modules')
        self.assertEqual((env['SYSTEMROOT'], env['WINDIR'], env['SYSTEMDRIVE']), (r'C:\Windows', r'C:\Windows', 'C:'))

    def test_injection_and_credential_variables_are_dropped(self):
        env = {k.upper() for k in self.env()}
        for key in ('COR_ENABLE_PROFILING', 'COR_PROFILER', 'COR_PROFILER_PATH', 'COMPLUS_ENABLEDIAGNOSTICS',
                    'DOTNET_STARTUP_HOOKS', 'PSEXECUTIONPOLICYPREFERENCE', '__PSLOCKDOWNPOLICY', 'BYBIT_API_SECRET',
                    'GITHUB_TOKEN', 'COMSPEC'):
            self.assertNotIn(key, env)

    def test_only_local_absolute_passthrough(self):
        env = self.env()
        self.assertEqual(env['TEMP'], r'C:\Users\u\AppData\Local\Temp')
        self.assertNotIn('TMP', env)                      # UNC refused
        self.assertEqual(set(env) - {'TEMP', 'USERPROFILE'},
                         {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'PATH', 'PATHEXT', 'PSModulePath'})

    def test_extra_is_unified_namespace_only(self):
        self.assertEqual(self.env({'UNIFIED_SERVICE_MODULE': 'm'})['UNIFIED_SERVICE_MODULE'], 'm')
        for key in ('PATH', 'PSModulePath', 'COR_PROFILER', 'unified_lower', 'UNIFIED_'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.env({key: 'x'})

    def test_argv_shape_and_prelude(self):
        argv = wp.argv('Write-Output 1', powershell=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe')
        self.assertEqual(argv[1:5], ['-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand'])
        script = base64.b64decode(argv[5]).decode('utf-16le')
        self.assertTrue(script.startswith("$PSModuleAutoLoadingPreference='None';"))
        self.assertTrue(script.endswith('Write-Output 1'))
        for name in wp.TRUSTED_MODULES:
            self.assertIn(name, script)
        self.assertNotIn('Bypass', script)
        self.assertNotIn('-ExecutionPolicy', argv)


@unittest.skipUnless(os.name == 'nt', 'real Windows PowerShell 5.1 children')
class RealChildControls(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='unified-ps-poison-'))
        self.marker = self.root / 'marker'
        escaped = str(self.marker).replace("'", "''")
        # Planted command reachable through PATH/PATHEXT or the current directory.
        (self.root / 'Get-UnifiedPoisonProbe.cmd').write_text('@echo POISON>"' + str(self.marker) + '"\r\n')
        # Planted module reachable through PSModulePath or the user module directory.
        for base in (self.root / 'modules', self.root / 'profile' / 'Documents' / 'WindowsPowerShell' / 'Modules'):
            module = base / 'UnifiedPoisonProbe'
            module.mkdir(parents=True)
            (module / 'evil.psm1').write_text("function Get-UnifiedPoisonProbe { [IO.File]::WriteAllText('" + escaped +
                                              "','loaded'); 'POISON' };Export-ModuleMember -Function Get-UnifiedPoisonProbe")
            (module / 'UnifiedPoisonProbe.psd1').write_text("@{RootModule='evil.psm1';ModuleVersion='1.0.0';"
                                                            "FunctionsToExport=@('Get-UnifiedPoisonProbe');CmdletsToExport=@();AliasesToExport=@()}")
        self.probe = "try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch{Write-Output 'POISON_NOT_FOUND'}"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def hardened(self, code, parent, cwd=None):
        from tests.native_phase_diagnostics import run_phased
        with patch.dict(os.environ, parent):
            env = wp.environment()
        return run_phased(wp.argv(code), env=env, cwd=cwd)

    def unhardened(self, code, parent, cwd=None):
        env = dict(os.environ, **parent)
        return subprocess.run([str(wp.executable()), '-NoProfile', '-NonInteractive', '-Command', code],
                              env=env, cwd=cwd, capture_output=True, timeout=120)

    def assert_blocked(self, parent, cwd=None):
        result = self.hardened(self.probe, parent, cwd)
        self.assertIn(b'POISON_NOT_FOUND', result.stdout)
        self.assertFalse(self.marker.exists())

    def assert_control_poisoned(self, parent, cwd=None, code=None):
        self.unhardened(code or self.probe, parent, cwd)
        self.assertTrue(self.marker.exists(), 'control must demonstrate the attack')
        self.marker.unlink()

    def test_path_and_pathext_planting(self):
        parent = {'PATH': str(self.root) + ';' + os.environ['PATH'], 'PATHEXT': '.COM;.EXE;.BAT;.CMD'}
        self.assert_control_poisoned(parent)
        self.assert_blocked(parent)

    def test_psmodulepath_planting(self):
        parent = {'PSModulePath': str(self.root / 'modules')}
        self.assert_control_poisoned(parent)
        self.assert_blocked(parent)

    def test_user_module_directory_planting(self):
        profile = self.root / 'profile'
        parent = {'USERPROFILE': str(profile), 'PSModulePath': str(profile / 'Documents' / 'WindowsPowerShell' / 'Modules')}
        self.assert_control_poisoned(parent)
        self.assert_blocked({'USERPROFILE': str(profile)})

    def test_current_directory_planting(self):
        # Control: a caller relying on the current directory runs the planted file.
        self.assert_control_poisoned({}, cwd=str(self.root), code='& .\\Get-UnifiedPoisonProbe.cmd')
        result = self.hardened("Write-Output (Get-Location).ProviderPath;" + self.probe, {}, cwd=None)
        self.assertEqual(result.stdout.decode().splitlines()[0].strip().casefold(),
                         str(wp.system_directory()).casefold())
        self.assertFalse(self.marker.exists())

    def test_product_run_uses_system_working_directory(self):
        from unified_system import installation_service as service
        previous = os.getcwd()
        os.chdir(self.root)
        try:
            output, code = service._run(wp.argv('Write-Output (Get-Location).ProviderPath'),
                                        env=service._environment(), timeout=15)
        finally:
            os.chdir(previous)
        self.assertEqual(code, 0)
        self.assertEqual(output.strip().casefold(), str(wp.system_directory()).casefold())

    def test_profiler_and_policy_variables_never_reach_child(self):
        parent = {'COR_ENABLE_PROFILING': '1', 'COR_PROFILER': '{00000000-0000-0000-0000-000000000000}',
                  'COR_PROFILER_PATH': str(self.root / 'missing.dll'), 'PSExecutionPolicyPreference': 'Bypass'}
        result = self.hardened("Write-Output ('P='+$env:COR_ENABLE_PROFILING+$env:COR_PROFILER_PATH+$env:PSExecutionPolicyPreference)", parent)
        self.assertEqual(result.stdout.decode().strip(), 'P=')

    def test_prelude_state_and_trusted_module_bases(self):
        result = self.hardened(
            "Write-Output $PSModuleAutoLoadingPreference;"
            "Get-Module | Sort-Object Name | ForEach-Object { Write-Output ($_.Name+'|'+$_.ModuleBase) }", {})
        lines = result.stdout.decode().split()
        self.assertEqual(lines[0], 'None')
        trusted = str(wp.module_path()).casefold()
        modules = dict(line.split('|', 1) for line in lines[1:])
        self.assertEqual(set(modules), set(wp.TRUSTED_MODULES))
        for base in modules.values():
            self.assertTrue(base.casefold().startswith(trusted))

    def test_former_slow_operations_complete_within_existing_bound(self):
        for code in ("$o=[pscustomobject]@{};$o|Add-Member -MemberType NoteProperty -Name a -Value 1;Write-Output OK",
                     "Add-Type -TypeDefinition ('public static class A2'+[guid]::NewGuid().ToString('N')+'{public static int F(){return 1;}}');Write-Output OK",
                     self.probe):
            with self.subTest(code=code[:30]):
                result = self.hardened(code, {})               # 15 s existing bound
                self.assertIn(b'O', result.stdout)


if __name__ == '__main__':
    unittest.main()
