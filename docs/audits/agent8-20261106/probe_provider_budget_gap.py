"""Instrument exact PowerShell AST network primitives with in-memory sentinels."""
import argparse,base64,json,os,pathlib,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--source');parser.add_argument('--fixed',action='store_true');args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];out=root/'outputs'/('phase22' if args.fixed else 'phase21');out.mkdir(exist_ok=True);source=(root/args.source) if args.source else root/'work/review-network-034/scripts/network_readonly_probe.ps1'
ps=r'''
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($env:A8_PROBE_SOURCE,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'SOURCE_AST_INVALID'}
$f=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Probe-Public'},$true));if($f.Count -ne 1){throw 'FUNCTION_MISSING'};$f=$f[0]
$primitives=@($f.FindAll({param($n)
 if($n -is [Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Static -and $n.Expression -is [Management.Automation.Language.TypeExpressionAst]){return $n.Expression.TypeName.FullName -in @('Net.Dns','Net.HttpWebRequest')}
 if($n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'New-Object' -and $n.CommandElements.Count -gt 1){return $n.CommandElements[1].Extent.Text -eq 'Net.Sockets.TcpClient'}
 return $false
},$true));if($primitives.Count -ne 3){throw 'NETWORK_PRIMITIVE_INVENTORY_CHANGED'}
$text=$f.Extent.Text
foreach($p in @($primitives|Sort-Object {$_.Extent.StartOffset} -Descending)){
 $start=$p.Extent.StartOffset-$f.Extent.StartOffset;$length=$p.Extent.EndOffset-$p.Extent.StartOffset
 $text=$text.Remove($start,$length).Insert($start,"(& { `$script:A8_IO_HITS++; throw 'A8_NO_NETWORK_SENTINEL' })")
}
. ([scriptblock]::Create($text))
$results=@()
foreach($v in @(
 @{name='fixed_provider_true';hostName='api.bybit.com';url='https://api.bybit.com/v5/market/time';bybit=$true},
 @{name='provider_false_flag';hostName='api.bybit.com';url='https://api.bybit.com/v5/market/time';bybit=$false},
 @{name='provider_url_false_flag';hostName='www.microsoft.com';url='https://api.bybit.com/v5/market/time';bybit=$false}
)){
 $script:A8_IO_HITS=0;$r=Probe-Public $v.hostName $v.url $v.bybit
 $results+=@{case=$v.name;sentinel_hits=$script:A8_IO_HITS;dns=$r.dns;tcp443=$r.tcp443;https=$r.https;api=$r.api;reason=$r.reason;actual_network_calls=0}
}
@{schema='a8.provider-native-free-probe.v1';instrumented_actual_source_ast=$true;network_primitive_nodes=$primitives.Count;cases=$results}|ConvertTo-Json -Depth 5 -Compress
'''
env=os.environ.copy();env['A8_PROBE_SOURCE']=str(source)
run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(ps.encode('utf-16le')).decode()],env=env,capture_output=True,timeout=15)
(out/'provider-gap.stdout.log').write_bytes(run.stdout);(out/'provider-gap.stderr.log').write_bytes(run.stderr);assert run.returncode==0
report=json.loads(run.stdout.decode('utf-8-sig'))
if args.fixed:assert all(c['sentinel_hits']==0 and all(c[k]=='NOT_RUN' for k in ('dns','tcp443','https','api')) and c['reason']=='BYBIT_BUDGET_ADAPTER_NOT_ADMITTED' and c['actual_network_calls']==0 for c in report['cases'])
else:assert all(c['sentinel_hits']==1 and c['dns']=='FAIL' and c['actual_network_calls']==0 for c in report['cases'])
report.update(head='15dd9e8340cc332204ebbe6c13744f797ceca2f4' if args.fixed else '0346018b58ed612dbe62fba7861f3e0b6a63ee94',expected='BLOCK_BEFORE_NETWORK_PRIMITIVES_WITH_EXPLICIT_BUDGET_REASON',actual='FIXED_RETURNS_4NOT_RUN_BEFORE_NETWORK' if args.fixed else 'BASELINE_REACHES_DNS_SENTINEL_WITHOUT_PROVIDER_BUDGET_ADMISSION',F14='FIX_VERIFIED_OFFLINE_AST' if args.fixed else 'OPEN_P1',actual_network_calls=0)
(out/'provider-gap-review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
