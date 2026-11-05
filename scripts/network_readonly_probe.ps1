# Read-only observations only. No repair or configuration command is permitted.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$started = [DateTime]::UtcNow.ToString('o')
function Probe-Public([string]$HostName, [string]$Url, [bool]$Bybit) {
    $watch=[Diagnostics.Stopwatch]::StartNew()
    $result = [ordered]@{host=$HostName; dns='UNAVAILABLE'; tcp443='NOT_RUN'; https='NOT_RUN'; api='NOT_RUN'}
    try {
        $task = [Net.Dns]::GetHostAddressesAsync($HostName)
        if (-not $task.Wait(5000)) { throw 'DNS_DEADLINE' }
        $addresses = @($task.Result | ForEach-Object { $_.IPAddressToString })
        if ($addresses.Count -lt 1 -or $addresses.Count -gt 64) { throw 'DNS_BOUNDS' }
        $result.dns='PASS'; $result.addresses=$addresses
    } catch { $result.dns='FAIL'; return $result }
    $client = New-Object Net.Sockets.TcpClient
    try {
        # Prefer IPv4 when present; an unavailable IPv6 route must not label
        # working IPv4 HTTPS as a total network outage. Record the tested IP.
        $tcpAddress=@($addresses | Sort-Object @{Expression={ $_.Contains(':') }})[0]
        $result.tcp_address=$tcpAddress
        $task = $client.ConnectAsync($tcpAddress,443)
        if (-not $task.Wait(5000) -or -not $client.Connected) { throw 'TCP_DEADLINE' }
        $result.tcp443='PASS'
    } catch { $result.tcp443='FAIL' } finally { $client.Dispose() }
    $response=$null; $stream=$null; $request=$null
    try {
        $request=[Net.HttpWebRequest]::Create($Url)
        $request.Method='GET'; $request.Timeout=5000; $request.ReadWriteTimeout=5000
        $request.AllowAutoRedirect=$false; $request.MaximumResponseHeadersLength=32
        $request.UserAgent='Unified-ReadOnly-Network-Probe/1'
        # Use Windows trust and protocol policy. No TLS callback or trust override.
        $response=$request.GetResponse()
        $result.http_status=[int]$response.StatusCode
        if ([int]$response.StatusCode -ne 200) { throw 'HTTP_STATUS' }
        $result.https='PASS'
        if ($Bybit) {
            $stream=$response.GetResponseStream(); $buffer=New-Object byte[] 4097
            $length=0
            while ($length -lt $buffer.Length) {
                # Bound the complete body, including a peer trickling bytes.
                # ReadWriteTimeout alone is per read, not a whole-body bound.
                $remaining=25000-[int]$watch.ElapsedMilliseconds
                if ($remaining -le 0) { throw 'API_DEADLINE' }
                $readTask=$stream.ReadAsync($buffer,$length,$buffer.Length-$length)
                if (-not $readTask.Wait([Math]::Min(5000,$remaining))) { throw 'API_DEADLINE' }
                $read=$readTask.Result
                if ($read -eq 0) { break }; $length+=$read
            }
            if ($length -gt 4096) { throw 'API_BOUNDS' }
            $data=Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject ([Text.Encoding]::UTF8.GetString($buffer,0,$length))
            if ($data.retCode -ne 0 -or -not $data.result.timeSecond) { throw 'API_RESPONSE' }
            $result.api='PASS'
        }
    } catch {
        if ($result.https -ne 'PASS') { $result.https='FAIL' }
        if ($Bybit) { $result.api='FAIL' }
    } finally {
        if ($null -ne $request) { $request.Abort() }
        if ($null -ne $stream) { $stream.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
    }
    return $result
}
$configuration=[ordered]@{
    adapters=@(Get-NetAdapter | Sort-Object InterfaceIndex | Select-Object InterfaceIndex,InterfaceGuid,Name,Status,MacAddress)
    interfaces=@(Get-NetIPInterface | Sort-Object InterfaceIndex,AddressFamily | Select-Object InterfaceIndex,AddressFamily,Dhcp,ConnectionState,InterfaceMetric)
    addresses=@(Get-NetIPAddress | Sort-Object InterfaceIndex,IPAddress | Select-Object InterfaceIndex,IPAddress,PrefixLength,PrefixOrigin,SuffixOrigin,AddressState)
    dns=@(Get-DnsClientServerAddress | Sort-Object InterfaceIndex,AddressFamily | Select-Object InterfaceIndex,AddressFamily,ServerAddresses)
    routes=@(Get-NetRoute | Sort-Object InterfaceIndex,DestinationPrefix,NextHop | Select-Object InterfaceIndex,DestinationPrefix,NextHop,RouteMetric,Protocol,PolicyStore)
    firewall=@(Get-NetFirewallProfile | Sort-Object Name | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction)
    services=@(Get-Service -Name Tailscale,Dnscache,Dhcp,NlaSvc,netprofm,WlanSvc,sshd,ekrn,ekrnEpfw -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object Name,@{n='status';e={$_.Status.ToString()}})
}
$checks=@(Probe-Public 'www.microsoft.com' 'https://www.microsoft.com/' $false; Probe-Public 'api.bybit.com' 'https://api.bybit.com/v5/market/time' $true)
[ordered]@{schema='unified.network-readonly-observation.v1';computer=[Environment]::MachineName;started_utc=$started;finished_utc=[DateTime]::UtcNow.ToString('o');mutations=$false;configuration=$configuration;checks=$checks} | Microsoft.PowerShell.Utility\ConvertTo-Json -Depth 9 -Compress
