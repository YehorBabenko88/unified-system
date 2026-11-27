"""Six sequential HTTPS IPv4 observations. No configuration or service changes.

Uses existing SSH trust, never TOFU. A common observation is NOT proof that
Bybit or every destination/time uses the same NAT route. Public IPs stay local.
"""
import base64,datetime,hashlib,ipaddress,json,pathlib,stat,subprocess,sys,time
sys.path.insert(0,'C:/Projects/UnifiedWorkspace/unified-system')
from unified_system.worker_transport import windows_ssh_environment
BASE=pathlib.Path(__file__).resolve().parent
HOME=pathlib.Path('C:/Users/LS-5')
SSH='C:/Windows/System32/OpenSSH/ssh.exe'
KEYGEN='C:/Windows/System32/OpenSSH/ssh-keygen.exe'
PS='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
NODES={'PC1':'192.168.2.11','PC2':'192.168.2.12','PC3':'192.168.2.104','PC4':'192.168.2.115','LS7':'192.168.2.141'}
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
script=r'''$ErrorActionPreference='Stop'
$env:PSModulePath=[IO.Path]::Combine([Environment]::SystemDirectory,'WindowsPowerShell/v1.0/Modules')
$issues=New-Object 'System.Collections.Generic.List[string]'
function Read-Part($n,[scriptblock]$s){try{&$s}catch{$issues.Add($n+':'+$_.Exception.GetType().Name);$null}}
$res=Read-Part 'resources' {$o=Get-CimInstance Win32_OperatingSystem;$d=Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'";[pscustomobject]@{os=$o.Caption;build=$o.BuildNumber;ram_kib=$o.TotalVisibleMemorySize;free_ram_kib=$o.FreePhysicalMemory;free_virtual_kib=$o.FreeVirtualMemory;disk_bytes=$d.Size;disk_free_bytes=$d.FreeSpace;cpu=@(Get-CimInstance Win32_Processor|Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)}}
$svc=Read-Part 'services' {Get-CimInstance Win32_Service|Where-Object{$_.Name -match '^(sshd|Tailscale|ekrn|ekrnEpfw|postgresql.*|Unified.*|consul)$'}|Select-Object Name,State,StartMode,ProcessId}
$fw=Read-Part 'firewall' {Get-NetFirewallProfile|Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction}
$ep=Read-Part 'policy' {Get-ExecutionPolicy -List|Select-Object Scope,ExecutionPolicy}
$tcp=Read-Part 'ports' {Get-NetTCPConnection -State Listen|Select-Object LocalAddress,LocalPort,OwningProcess}
$dns=Read-Part 'dns' {@(Resolve-DnsName www.microsoft.com -Type A -DnsOnly -QuickTimeout|Where-Object{$_.IPAddress}|Select-Object -ExpandProperty IPAddress)}
$https=Read-Part 'https' {$t=[Diagnostics.Stopwatch]::StartNew();$u=[IO.Path]::Combine([Environment]::SystemDirectory,'curl.exe');$c=&$u -sS -I -o NUL -w '%{http_code}' --connect-timeout 3 --max-time 5 'https://www.microsoft.com/';$e=$LASTEXITCODE;$t.Stop();[pscustomobject]@{http_status=[string]$c;exit=$e;latency_ms=$t.ElapsedMilliseconds}}
[pscustomobject]@{schema='unified.route-readonly-inventory.v1';node=[Environment]::MachineName;observed_utc=[DateTime]::UtcNow.ToString('o');exit_code=0;resources=$res;services=@($svc);firewall=@($fw);execution_policy=@($ep);ports=@($tcp);dns=$dns;https=$https;component_errors=@($issues);configuration_mutations=$false;service_mutations=$false;bybit_http_requests=0}|ConvertTo-Json -Depth 6 -Compress
exit 0
'''
encoded=base64.b64encode(script.encode('utf-16le')).decode()
remote=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand '+encoded
assert len(remote)<7000
directory=BASE/('inventory-readonly-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
directory.mkdir();empty=directory/'empty_config';empty.write_bytes(b'')
config=HOME/'.ssh/config';known=HOME/'.ssh/known_hosts';raw=config.read_bytes();prior=known.read_bytes()
sections={};current=None
for line in raw.decode('utf-8-sig').splitlines():
 line=line.strip()
 if not line or line.startswith('#'):continue
 key,value=line.split(None,1);key=key.lower()
 if key in ('include','match','proxycommand','proxyjump','knownhostscommand','localcommand','identityagent'):raise ValueError('SSH_CONFIG_REVIEW_REQUIRED')
 if key=='host':
  if value in sections or any(c in value for c in '*?![] '):raise ValueError('SSH_CONFIG_REVIEW_REQUIRED')
  current=value;sections[current]={}
 elif current is not None:
  if key in sections[current]:raise ValueError('SSH_CONFIG_REVIEW_REQUIRED')
  sections[current][key]=value
plans=[]
for node,address in NODES.items():
 row=sections[node.lower()];ipaddress.IPv4Address(address)
 identity=pathlib.Path(row['identityfile'].replace('~',str(HOME),1)).resolve(strict=True);info=identity.lstat()
 if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or getattr(info,'st_file_attributes',0)&1024:raise ValueError('IDENTITY_REVIEW_REQUIRED')
 lookup=subprocess.run([KEYGEN,'-F',row['hostname'],'-f',str(known)],capture_output=True,timeout=5)
 if lookup.returncode:raise ValueError('EXISTING_HOST_TRUST_UNAVAILABLE')
 keys={parts[2] for line in lookup.stdout.decode('ascii').splitlines() if len(parts:=line.split())>=3 and parts[1]=='ssh-ed25519'}
 if len(keys)!=1:raise ValueError('EXACT_ED25519_KEY_REQUIRED')
 key=keys.pop();blob=base64.b64decode(key,validate=True)
 if len(blob)!=51 or blob[:19]!=b'\0\0\0\x0bssh-ed25519\0\0\0\x20':raise ValueError('HOST_KEY_INVALID')
 alias='unified-inventory-'+node.lower();pin=directory/(node+'-known_hosts');pin.write_bytes((alias+' ssh-ed25519 '+key+'\n').encode())
 plans.append((node,address,row['user'],identity,(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns),alias,pin,sha(blob)))
if len({p[-1] for p in plans})!=5:raise ValueError('SHARED_HOST_KEY_REVIEW_REQUIRED')
report={'schema':'unified.readonly-route-observation.v1','started_utc':utc(),'script_sha256':sha(script.encode()),'source_config_sha256':sha(raw),'prior_known_hosts_sha256':sha(prior),'physical_fault_injection':False,'configuration_mutations':False,'adminit_contacted':False,'results':[],'bybit_route_equivalence':'NOT_PROVEN'}
def observe(node,args,env=None):
 started=utc();clock=time.monotonic()
 try:
  p=subprocess.run(args,stdin=subprocess.DEVNULL,env=env,capture_output=True,timeout=30)
 except subprocess.TimeoutExpired:
  report['results'].append({'node':node,'status':'TIMEOUT_UNKNOWN_HELPER_STATE','started_utc':started,'finished_utc':utc()});return False
 (directory/(node+'-stdout.bin')).write_bytes(p.stdout);(directory/(node+'-stderr.bin')).write_bytes(p.stderr)
 item={'node':node,'started_utc':started,'finished_utc':utc(),'duration_ms':round((time.monotonic()-clock)*1000),'process_exit_code':p.returncode,'stdout_sha256':sha(p.stdout),'stderr_sha256':sha(p.stderr),'stderr_bytes':len(p.stderr),'status':'FAIL'}
 try:
  if len(p.stdout)>65536:raise ValueError()
  data=json.loads(p.stdout.decode('utf-8-sig'))
  if p.returncode or data['node'].upper()!=node or data['exit_code']!=0 or data['schema']!='unified.route-readonly-inventory.v1':raise ValueError()
  item.update(observation=data,status='OBSERVED_READ_ONLY_INVENTORY')
 except (ValueError,KeyError,UnicodeError):pass
 report['results'].append(item)
 print(json.dumps({'node':node,'status':item['status'],'duration_ms':item['duration_ms']}),flush=True)
 return item['status']=='OBSERVED_READ_ONLY_INVENTORY'
def save():
 payload=(json.dumps(report,indent=2)+'\n').encode();(directory/'report.json').write_bytes(payload);(directory/'report.sha256').write_text(sha(payload)+'\n',encoding='ascii')
if not observe('LS5',[PS,'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',encoded]):
 save();raise SystemExit('Stopped after uncertain local probe; no automatic retry')
for node,address,user,identity,facts,alias,pin,fingerprint in plans:
 if config.read_bytes()!=raw or known.read_bytes()!=prior:save();raise SystemExit('Trust source changed')
 info=identity.lstat()
 if facts!=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns):save();raise SystemExit('Identity file changed')
 args=[SSH,'-F',str(empty),'-T','-p','22','-l',user,'-i',str(identity)]
 options={'HostKeyAlgorithms':'ssh-ed25519','StrictHostKeyChecking':'yes','BatchMode':'yes','ConnectTimeout':'5','HostKeyAlias':alias,'UserKnownHostsFile':str(pin),'GlobalKnownHostsFile':str(empty),'KnownHostsCommand':'none','UpdateHostKeys':'no','VerifyHostKeyDNS':'no','IdentitiesOnly':'yes','IdentityAgent':'none','PasswordAuthentication':'no','KbdInteractiveAuthentication':'no','GSSAPIAuthentication':'no','ProxyCommand':'none','ProxyJump':'none','PermitLocalCommand':'no','ClearAllForwardings':'yes','ControlMaster':'no','ControlPersist':'no','CanonicalizeHostname':'no','ServerAliveInterval':'5','ServerAliveCountMax':'2'}
 for key,value in options.items():args+=['-o',key+'='+value]
 args += [address,remote]
 if not observe(node,args,windows_ssh_environment()):save();raise SystemExit('Stopped after uncertain probe; no automatic retry')
 save()
good=[r['observation'] for r in report['results'] if r['status']=='OBSERVED_READ_ONLY_INVENTORY']
report.update(finished_utc=utc(),observed_nodes=len(good),runtime_readiness='NOT_QUALIFIED',installation_authorized=False)
save();print(json.dumps({'report':str(directory/'report.json'),'observed_nodes':len(good),'runtime_readiness':'NOT_QUALIFIED'}),flush=True)
