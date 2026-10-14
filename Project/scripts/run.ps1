param(
    [ValidateSet('all','up','load','ingest','lake','verify','query','status')]
    [string]$Action = 'all',
    [string]$Sql = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $projectRoot 'src\manage.py'
$commandArgs = @('-X','utf8',$scriptPath,$Action)
if ($Sql) { $commandArgs += @('--sql',$Sql) }
& python @commandArgs
if ($LASTEXITCODE -ne 0) { throw "CompanyE command failed with exit code $LASTEXITCODE" }
