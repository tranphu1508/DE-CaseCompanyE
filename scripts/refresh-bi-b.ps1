param(
    [Parameter(Mandatory=$true)][string]$Server,
    [Parameter(Mandatory=$true)][string]$Database,
    [Parameter(Mandatory=$true)][string]$Publication
)
# Run with Windows PowerShell 5.1, for the installed .NET Framework TOM library.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$base='C:\Program Files (x86)\Microsoft SQL Server Management Studio 20\Common7\IDE'
Add-Type -Path "$base\Microsoft.AnalysisServices.Core.dll"
Add-Type -Path "$base\Microsoft.AnalysisServices.Tabular.dll"
$tom=New-Object Microsoft.AnalysisServices.Tabular.Server
$tom.Connect("Data Source=$Server")
try {
    $db=$tom.Databases.FindByName($Database)
    if(-not $db){throw 'Requested Desktop model not found'}
    $measure=@($db.Model.Tables | ForEach-Object {$_.Measures} | Where-Object {$_.Name -eq 'Publication'})
    if($measure.Count -ne 1 -or -not $measure[0].Expression.Contains($Publication) -or -not $Publication.StartsWith('b_')) {
        throw 'Refusing refresh: target is not the requested B publication'
    }
    $model=Get-Content -LiteralPath (Join-Path $root 'Project\powerbi-b\CompanyE.SemanticModel\model.bim') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach($table in $model.model.tables){
        foreach($part in $table.partitions){
            $actual=$db.Model.Tables.Find($table.name).Partitions.Find($part.name)
            if($actual.Source.Expression -ne $part.source.expression){throw "Partition mismatch: $($table.name)"}
        }
    }
    $db.Model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
    $db.Model.SaveChanges() | Out-Null
    @{status='REFRESHED';publication_id=$Publication;tables=$db.Model.Tables.Count;verified_partition_definitions=$true} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'Project\reports\bi-migration\desktop-refresh.json') -Encoding UTF8
    Write-Output 'B_DESKTOP_REFRESHED'
} finally {$tom.Disconnect()}
