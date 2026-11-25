"""Workstream A2 round 3: does the hardened prelude (autoload off + explicit trusted
system modules + fixed system PATH, PSModulePath still restricted) remove the delay?"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2])); sys.path.insert(0, str(Path(__file__).parent))
from windows_powershell_probe import PRELUDE, restricted_env, run  # noqa
EXE = str(Path(os.environ['SystemRoot']) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe')
S = Path(os.environ['SystemRoot']) / 'System32'
HARD = ("$PSModuleAutoLoadingPreference='None';"
        "foreach($n in 'Microsoft.PowerShell.Utility','Microsoft.PowerShell.Management','Microsoft.PowerShell.Security')"
        "{Import-Module -Name (Join-Path (Join-Path $PSHOME 'Modules') (Join-Path $n ($n+'.psd1')))};P 'IMPORTS_END';")
OPS = {"ADD_MEMBER": "$o=[pscustomobject]@{};$o|Add-Member -MemberType NoteProperty -Name a -Value 1;P 'OP_END'",
       "ADD_TYPE": "Add-Type -TypeDefinition ('public static class H'+[guid]::NewGuid().ToString('N')+'{public static int F(){return 1;}}');P 'OP_END'",
       "CMD_LOOKUP": "try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch [System.Management.Automation.CommandNotFoundException]{P 'NOT_FOUND'};P 'OP_END'",
       "JSON": "$x='{\"a\":1}'|ConvertFrom-Json;$x|ConvertTo-Json -Compress|Out-Null;P 'OP_END'",
       "ACL": "Get-Acl -Path $env:SystemRoot|Out-Null;Get-FileHash -Path (Join-Path $PSHOME 'powershell.exe')|Out-Null;P 'OP_END'"}
base = restricted_env()
fixed_path = ';'.join(str(p) for p in (S, S.parent, S / 'Wbem', S / 'WindowsPowerShell' / 'v1.0'))
variants = {"RESTRICTED_UNHARDENED": (base, ""), "HARDENED_PRELUDE_ONLY": (base, HARD),
            "HARDENED_PRELUDE+FIXED_PATH": (dict(base, PATH=fixed_path), HARD),
            "FIXED_PATH_ONLY": (dict(base, PATH=fixed_path), "")}
print('VARIANT OP cold_ms warm_ms phases')
for v, (env, pre) in variants.items():
    for op, code in OPS.items():
        r = [run(EXE, PRELUDE + pre + code, env) for _ in range(2)]
        print(f"{v:30} {op:10} {r[0]['wall_ms']:>7} {r[1]['wall_ms']:>7} {r[1]['phases']} {r[1]['stderr_other'][:1]}", flush=True)
