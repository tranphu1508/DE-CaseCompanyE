param([Parameter(Mandatory=$true)][string]$Server,[Parameter(Mandatory=$true)][string]$Database,[Parameter(Mandatory=$true)][string]$ModelFile,[Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference='Stop'
$base='C:\Program Files (x86)\Microsoft SQL Server Management Studio 20\Common7\IDE'
Add-Type -Path "$base\Microsoft.AnalysisServices.Core.dll"
Add-Type -Path "$base\Microsoft.AnalysisServices.Tabular.dll"
$definition=Get-Content -LiteralPath $ModelFile -Raw -Encoding UTF8 | ConvertFrom-Json
$serverObject=New-Object Microsoft.AnalysisServices.Tabular.Server
$serverObject.Connect("Data Source=$Server")
try {
    $db=$serverObject.Databases.FindByName($Database)
    if(-not $db){throw 'Requested Desktop database not found'}
    $changed=[System.Collections.Generic.List[object]]::new()
    foreach($table in $definition.model.tables){
        foreach($measure in $table.measures){
            $target=$db.Model.Tables.Find($table.name).Measures.Find($measure.name)
            if(-not $target){throw "Missing measure $($measure.name)"}
            if($target.Expression -ne $measure.expression){
                $changed.Add(@{table=$table.name;measure=$measure.name;old_expression=$target.Expression;new_expression=$measure.expression})
                $target.Expression=$measure.expression
            }
        }
    }
    $db.Model.SaveChanges() | Out-Null
    ConvertTo-Json -InputObject $changed.ToArray() -Depth 8 | Set-Content -LiteralPath $OutputFile -Encoding UTF8
    Write-Output "MEASURES_UPDATED $($changed.Count)"
} finally {$serverObject.Disconnect()}
