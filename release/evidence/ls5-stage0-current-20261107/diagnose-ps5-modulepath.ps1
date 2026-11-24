$ErrorActionPreference='Stop'
$o=[ordered]@{powershell=$PSVersionTable.PSVersion.ToString();inherited_module_search_paths=@($env:PSModulePath -split ';');security_modules=@(Get-Module -ListAvailable Microsoft.PowerShell.Security|Select-Object Version,Path);import='NOT_RUN'}
try{Import-Module Microsoft.PowerShell.Security -ErrorAction Stop;$o.import='IMPORTED'}catch{$o.import='FAILED';$o.exception_type=$_.Exception.GetType().FullName;$o.exception=$_.Exception.ToString().Substring(0,[Math]::Min(4096,$_.Exception.ToString().Length))}
$o|ConvertTo-Json -Depth 5
