"""Single hardened launcher for local Windows PowerShell 5.1 children (A2, #151).

Owner decision 2026-11-25: stay on Windows PowerShell 5.1 (no PowerShell 7
dependency). Every local child started through this module gets:

- the executable derived from GetSystemDirectoryW (never from environment);
- a minimal, closed environment: fixed system PATH, PATHEXT=.COM;.EXE,
  PSModulePath restricted to the in-box System32 module directory, no profiler,
  .NET, PowerShell policy or credential variables inherited from the parent;
- the working directory fixed to System32 (no current-directory planting);
- a prelude that disables module autoloading, verifies $PSHOME, imports only
  the in-box Utility/Management/Security modules by absolute manifest path and
  verifies each loaded module's base directory.

Measured root cause (runs 45609131011, 45612377465): with the restricted
environment and autoloading enabled, the first cmdlet/type/command resolution
in PowerShell 5.1 takes 18-28 s. Bounds are not raised; the cause is removed.
"""
import base64
import ctypes
import os
import re
from pathlib import Path, PureWindowsPath

TRUSTED_MODULES = ('Microsoft.PowerShell.Utility', 'Microsoft.PowerShell.Management',
                   'Microsoft.PowerShell.Security')
# Parent values that are passed through after validation; everything else is
# rebuilt from the system directory or dropped.
_PASSTHROUGH = ('TEMP', 'TMP', 'PROGRAMDATA', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA')
_EXTRA = re.compile(r'UNIFIED_[A-Z0-9_]{1,60}')

PRELUDE = (
    "$PSModuleAutoLoadingPreference='None';$ErrorActionPreference='Stop';"
    "$UnifiedTrustedHome=[IO.Path]::Combine([Environment]::SystemDirectory,'WindowsPowerShell','v1.0');"
    "if(-not [string]::Equals($PSHOME.TrimEnd('\\'),$UnifiedTrustedHome,[StringComparison]::OrdinalIgnoreCase))"
    "{throw 'UNTRUSTED_PSHOME'};"
    "$UnifiedTrustedModules=[IO.Path]::Combine($UnifiedTrustedHome,'Modules')+'\\';"
    "foreach($UnifiedModuleName in '" + "','".join(TRUSTED_MODULES) + "'){"
    "$UnifiedModule=Import-Module -Name ([IO.Path]::Combine($UnifiedTrustedModules,$UnifiedModuleName,$UnifiedModuleName+'.psd1')) -PassThru;"
    "if(-not ([string]$UnifiedModule.ModuleBase+'\\').StartsWith($UnifiedTrustedModules,[StringComparison]::OrdinalIgnoreCase))"
    "{throw 'UNTRUSTED_MODULE_BASE'}};"
    "Remove-Variable UnifiedModule,UnifiedModuleName;"
)


def _need(ok, code='POWERSHELL_CHILD_REJECTED'):
    if not ok:
        raise ValueError(code)


def system_directory():
    _need(os.name == 'nt', 'WINDOWS_ONLY')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    function = kernel.GetSystemDirectoryW
    function.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
    function.restype = ctypes.c_uint
    buffer = ctypes.create_unicode_buffer(32768)
    count = function(buffer, len(buffer))
    _need(0 < count < len(buffer))
    directory = Path(buffer.value)
    _need(directory.is_absolute() and directory.name.casefold() == 'system32'
          and not str(directory).startswith('\\\\'))
    return directory


def executable(directory=None):
    directory = system_directory() if directory is None else directory
    return directory / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'


def module_path(directory=None):
    directory = PureWindowsPath(system_directory() if directory is None else directory)
    return directory / 'WindowsPowerShell' / 'v1.0' / 'Modules'


def fixed_path(directory=None):
    directory = PureWindowsPath(system_directory() if directory is None else directory)
    return ';'.join(str(p) for p in (directory, directory.parent, directory / 'Wbem',
                                     directory / 'WindowsPowerShell' / 'v1.0'))


def _local_absolute(value):
    path = PureWindowsPath(value)
    return (type(value) is str and path.is_absolute() and bool(path.drive) and not value.startswith('\\\\') and ';' not in value
            and '\x00' not in value and len(value) < 1024)


def environment(extra=None, *, parent=None, directory=None):
    """Closed child environment. ``extra`` may only add UNIFIED_* keys."""
    directory = PureWindowsPath(system_directory() if directory is None else directory)
    parent = os.environ if parent is None else parent
    env = {}
    for key, value in parent.items():
        upper = key.upper()
        if upper in _PASSTHROUGH and _local_absolute(value):
            env[upper] = value
    root = str(directory.parent)
    env.update(SYSTEMROOT=root, WINDIR=root, SYSTEMDRIVE=root[:2], PATH=fixed_path(directory),
               PATHEXT='.COM;.EXE', PSModulePath=str(module_path(directory)))
    for key, value in (extra or {}).items():
        _need(type(key) is str and _EXTRA.fullmatch(key) is not None and type(value) is str
              and '\x00' not in value, 'POWERSHELL_EXTRA_ENV_REJECTED')
        env[key] = value
    return env


def encoded(code):
    _need(type(code) is str and '\x00' not in code)
    return base64.b64encode((PRELUDE + code).encode('utf-16le')).decode('ascii')


def argv(code, *, powershell=None):
    """Arguments for one hardened child. ``code`` must be static text."""
    exe = executable() if powershell is None else Path(powershell)
    return [str(exe), '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded(code)]


def working_directory(directory=None):
    return str(system_directory() if directory is None else directory)
