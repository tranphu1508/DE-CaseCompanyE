param([Parameter(Mandatory=$true)][string]$Server,[string]$Database,[string]$QueryFile,[string]$VectorsFile,[Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files (x86)\Microsoft SQL Server Management Studio 20\Common7\IDE\Microsoft.AnalysisServices.AdomdClient.dll'
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection
$connection.ConnectionString = "Data Source=$Server;" + $(if($Database){"Initial Catalog=$Database;"}else{''})
$connection.Open()
function Invoke-Dax([string]$query) {
    $command = $connection.CreateCommand(); $command.CommandText=$query; $command.CommandTimeout=120
    $reader=$command.ExecuteReader();$result=[System.Collections.Generic.List[object]]::new()
    try {
        while($reader.Read()) {
            $row=[ordered]@{}
            for($i=0;$i -lt $reader.FieldCount;$i++) {
                $value=$reader.GetValue($i)
                $row[$reader.GetName($i)] = if($value -is [DBNull]){$null}else{$value}
            }
            $result.Add($row)
        }
    } finally {$reader.Close();$command.Dispose()}
    return ,$result.ToArray()
}
try {
    if($VectorsFile){
        $vectors=Get-Content -LiteralPath $VectorsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $results=[System.Collections.Generic.List[object]]::new()
        foreach($case in $vectors.cases){
            try {$rows=Invoke-Dax $case.query;$results.Add(@{id=$case.id;rows=$rows})}
            catch {$results.Add(@{id=$case.id;error=$_.Exception.Message})}
        }
        $results.ToArray() | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutputFile -Encoding UTF8
        Write-Output "DAX_QUERIES_EXECUTED $($results.Count)"
    } else {
        $rows=Invoke-Dax (Get-Content -LiteralPath $QueryFile -Raw -Encoding UTF8)
        ConvertTo-Json -InputObject $rows -Depth 12 | Set-Content -LiteralPath $OutputFile -Encoding UTF8
        Write-Output "ROWS $($rows.Count)"
    }
} finally {$connection.Close();$connection.Dispose()}
