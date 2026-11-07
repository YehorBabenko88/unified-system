"""Execute the actual probe function with all three network seams replaced.

No DNS, socket, HTTP, SSH or office-node operation is performed by this fixture.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


PS = (str(Path(os.environ.get('SYSTEMROOT', r'C:\Windows')) /
          'System32/WindowsPowerShell/v1.0/powershell.exe')
      if os.name == 'nt' else shutil.which('pwsh'))


@unittest.skipUnless(PS and Path(PS).is_file(), 'PowerShell AST fixture unavailable')
class ProviderClosedTests(unittest.TestCase):
    def test_actual_function_blocks_provider_before_every_network_primitive(self):
        source = Path(__file__).resolve().parents[1] / 'scripts/network_readonly_probe.ps1'
        script = r'''
$ErrorActionPreference='Stop'
$source=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__SOURCE__'))
$tokens=$null; $errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'PARSE_REJECTED'}
$functions=@($ast.FindAll({param($a) $a -is [Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -ceq 'Probe-Public'},$true))
if($functions.Count -ne 1){throw 'FUNCTION_REJECTED'}
$fn=$functions[0]
$primitives=@($fn.FindAll({param($a)
  ($a -is [Management.Automation.Language.InvokeMemberExpressionAst] -and
   ($a.Extent.Text -match '^\[Net\.Dns\]::GetHostAddressesAsync\(' -or $a.Extent.Text -match '^\[Net\.HttpWebRequest\]::Create\(')) -or
  ($a -is [Management.Automation.Language.CommandAst] -and $a.GetCommandName() -eq 'New-Object' -and $a.Extent.Text -match '^New-Object Net\.Sockets\.TcpClient$')
},$true))
if($primitives.Count -ne 3){throw 'NETWORK_SEAM_COVERAGE_REJECTED'}
$body=$fn.Extent.Text
foreach($p in ($primitives|Sort-Object {$_.Extent.StartOffset} -Descending)){
  $start=$p.Extent.StartOffset-$fn.Extent.StartOffset
  $body=$body.Remove($start,$p.Extent.EndOffset-$p.Extent.StartOffset).Insert($start,'$( $script:primitiveCount++; throw ''NETWORK_PRIMITIVE_SENTINEL'' )')
}
Invoke-Expression $body
$vectors=@(
 @('api.bybit.com','https://api.bybit.com/v5/market/time',$true),
 @('api.bybit.com','https://api.bybit.com/v5/market/time',$false),
 @('API.BYBIT.COM','https://API.BYBIT.COM/v5/market/time',$false),
 @('www.microsoft.com','https://api.bybit.com/v5/market/time',$false),
 @('api.bybit.com','https://www.microsoft.com/',$false),
 @('unadmitted.invalid','https://unadmitted.invalid/',$false)
)
$results=@(foreach($v in $vectors){
 $script:primitiveCount=0
 $result=Probe-Public $v[0] $v[1] $v[2]
 [pscustomobject]@{result=$result;network_primitive_calls=$script:primitiveCount}
})
$script:primitiveCount=0
$general=Probe-Public 'www.microsoft.com' 'https://www.microsoft.com/' $false
$guard=@($fn.FindAll({param($a) $a -is [Management.Automation.Language.IfStatementAst] -and $a.Extent.Text.Contains('BYBIT_BUDGET_ADAPTER_NOT_ADMITTED')},$true))
$dominates=$guard.Count -eq 1 -and $guard[0].Extent.EndOffset -lt ($primitives|Sort-Object {$_.Extent.StartOffset}|Select-Object -First 1).Extent.StartOffset
[pscustomobject]@{vectors=$results;general_primitive_calls=$script:primitiveCount;general_dns=$general.dns;blocked_return_precedes_network=$dominates;instrumented_seams=$primitives.Count}|ConvertTo-Json -Depth 8 -Compress
'''.replace('__SOURCE__', base64.b64encode(str(source).encode()).decode())
        encoded = base64.b64encode(script.encode('utf-16le')).decode()
        p = subprocess.run([PS, '-NoLogo', '-NoProfile', '-NonInteractive',
                            '-EncodedCommand', encoded], capture_output=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr.decode(errors='replace'))
        data = json.loads(p.stdout.decode('utf-8-sig'))
        self.assertEqual(data['instrumented_seams'], 3)
        self.assertEqual(len(data['vectors']), 6)
        for row in data['vectors']:
            with self.subTest(result=row['result']):
                self.assertEqual(row['network_primitive_calls'], 0)
                self.assertEqual(row['result']['reason'], 'BYBIT_BUDGET_ADAPTER_NOT_ADMITTED')
                for field in ('dns', 'tcp443', 'https', 'api'):
                    self.assertEqual(row['result'][field], 'NOT_RUN')
        self.assertTrue(data['blocked_return_precedes_network'])
        self.assertEqual(data['general_primitive_calls'], 1)
        self.assertEqual(data['general_dns'], 'FAIL')
        # The frozen operational v1 guard must reject this blocked observation.
        # It is not inert-bootstrap evidence and cannot authorize deployment.
        from tests.test_network_deployment_guard import observation
        from unified_system.network_deployment_guard import NetworkDeploymentGuard, NetworkBlocked
        observed = observation()
        observed['checks'][1] = data['vectors'][0]['result']
        receipts = []
        guard = NetworkDeploymentGuard('PC1', 'owned-fixture', observe=lambda: observed,
                                       record=receipts.append, now=lambda: 1793890802.)
        with self.assertRaisesRegex(NetworkBlocked, 'NETWORK_CONNECTIVITY_DEGRADED'):
            guard.begin()
        self.assertTrue(guard.stopped)


if __name__ == '__main__':
    unittest.main()
