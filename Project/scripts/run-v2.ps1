param(
    [ValidateSet('all','generate','load','ingest','lake','verify','query')]
    [string]$Action='verify',
    [string]$Sql=''
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$runArgs=@('-X','utf8',(Join-Path $projectRoot 'src\manage_v2.py'),$Action)
if ($Sql) { $runArgs+=@('--sql',$Sql) }
& python @runArgs
if ($LASTEXITCODE -ne 0) { throw "CompanyE v2 failed: $LASTEXITCODE" }
