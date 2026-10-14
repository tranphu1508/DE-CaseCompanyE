param([string]$ReportDirectory = (Join-Path $PSScriptRoot '../reports/docker-storage-migration-20261013'))
$ErrorActionPreference = 'Stop'
# Read-only verification of Docker and source databases. Only report files are written.
function Invoke-DockerChecked {
    param([string[]]$DockerArgs)
    $result = @(& docker @DockerArgs)
    if ($LASTEXITCODE -ne 0) { throw "Docker verification failed: $($DockerArgs[0])" }
    return $result
}
$before = Get-Content -LiteralPath (Join-Path $ReportDirectory 'containers-before.json') -Raw | ConvertFrom-Json
$ids = @(Invoke-DockerChecked @('ps','-aq','--no-trunc'))
if (Compare-Object @($before.id | Sort-Object) @($ids | Sort-Object)) { throw 'Container IDs differ' }
$afterRaw = Invoke-DockerChecked (@('inspect') + $ids)
$after = ($afterRaw -join "`n") | ConvertFrom-Json
$containerChecks = foreach ($b in $before) {
    $a = $after | Where-Object Id -eq $b.id
    if ($a.Image -ne $b.image -or $a.State.Running -ne $b.running) { throw "State/image differs: $($b.name)" }
    $oldMounts = @($b.mounts | Sort-Object Destination) | ConvertTo-Json -Depth 10 -Compress
    $newMounts = @($a.Mounts | Sort-Object Destination) | ConvertTo-Json -Depth 10 -Compress
    if ($oldMounts -ne $newMounts) { throw "Mounts differ: $($b.name)" }
    if ($a.State.Running -and $a.State.Health -and $a.State.Health.Status -ne 'healthy') { throw "Not healthy: $($b.name)" }
    [pscustomobject]@{name=$a.Name; id=$a.Id; running=$a.State.Running; health=$a.State.Health.Status; image_and_mounts_match=$true}
}
$oldVolumes = Get-Content -LiteralPath (Join-Path $ReportDirectory 'volumes-before.json') -Raw | ConvertFrom-Json
$newVolumeNames = @(Invoke-DockerChecked @('volume','ls','-q'))
if (Compare-Object @($oldVolumes.Name | Sort-Object) @($newVolumeNames | Sort-Object)) { throw 'Volume names differ' }
$newVolumes = ((Invoke-DockerChecked (@('volume','inspect') + $newVolumeNames)) -join "`n") | ConvertFrom-Json
foreach ($old in $oldVolumes) {
    $new = $newVolumes | Where-Object Name -eq $old.Name
    if ($new.Driver -ne $old.Driver -or $new.Mountpoint -ne $old.Mountpoint -or $new.CreatedAt -ne $old.CreatedAt) { throw "Volume identity differs: $($old.Name)" }
}
$images = @(Invoke-DockerChecked @('image','ls','--no-trunc','--digests','--format','{{json .}}'))
$oldImages = @(Get-Content -LiteralPath (Join-Path $ReportDirectory 'images-before.jsonl'))
# Compare stable IDs/digests/tags; human-readable age can change between observations.
function Image-Keys($rows) { @($rows | ForEach-Object { $i=$_ | ConvertFrom-Json; "$($i.ID)|$($i.Digest)|$($i.Repository)|$($i.Tag)" } | Sort-Object) }
if (Compare-Object (Image-Keys $oldImages) (Image-Keys $images)) { throw 'Image inventory differs' }
$dbChecks = foreach ($db in @('hotel_ops','hotel_ops_v2','entertainment_ops','entertainment_ops_v2')) {
    $sql = "SELECT format('SELECT %L AS relation, count(*) AS rows FROM %I.%I', schemaname||'.'||tablename, schemaname, tablename) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname,tablename"
    $parts = @(Invoke-DockerChecked @('exec','companye-postgres-1','psql','-U','companye','-d',$db,'-Atc',$sql))
    $counts = @(Invoke-DockerChecked @('exec','companye-postgres-1','psql','-U','companye','-d',$db,'-Atc',($parts -join ' UNION ALL ')))
    $counts | Set-Content -LiteralPath (Join-Path $ReportDirectory "$db-counts-after.txt") -Encoding utf8
    $expected = @(Get-Content -LiteralPath (Join-Path $ReportDirectory "$db-counts-before.txt"))
    if (Compare-Object $expected $counts) { throw "Table counts differ: $db" }
    [pscustomobject]@{database=$db;tables=$counts.Count;rows=($counts | ForEach-Object {[long]($_ -split '\|')[-1]} | Measure-Object -Sum).Sum;counts_match=$true}
}
$settings = Get-Content -LiteralPath "$env:APPDATA\Docker\settings-store.json" -Raw | ConvertFrom-Json
$expectedLocation='E:\DockerDesktopData\DockerDesktopWSL'
if ($settings.CustomWslDistroDir -ne $expectedLocation) { throw 'Docker setting is not the expected E location' }
$vhdx=Get-Item -LiteralPath (Join-Path $expectedLocation 'disk/docker_data.vhdx')
$backup=Get-Content -LiteralPath (Join-Path $ReportDirectory 'backup.json') -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $backup.backup)) { throw 'Recovery copy missing' }
$hostVolumes=@(Get-Volume | Where-Object DriveLetter -in 'C','D','E' | Select-Object DriveLetter,FileSystem,Size,SizeRemaining)
$report=[ordered]@{
    status='PASSED'; verified_at=(Get-Date -Format o); method='Docker Desktop Settings > Resources > Advanced > Disk image location > Apply & restart > Yes, move it';
    windows_vhdx=$vhdx.FullName; vhdx_bytes=$vhdx.Length; custom_wsl_distro_dir=$settings.CustomWslDistroDir;
    docker_server_version=(@(Invoke-DockerChecked @('info','--format','{{.ServerVersion}}')))[0];
    old_c_vhdx_exists=(Test-Path -LiteralPath $backup.source); containers=$containerChecks; volume_count=$newVolumeNames.Count;
    volume_identity_checks='PASSED'; image_inventory_check='PASSED'; source_databases=$dbChecks; volumes=$hostVolumes;
    backup=$backup; limitations=@('Database verification compares table row counts, not every cell.','Recovery copy is a point-in-time snapshot; it does not contain writes after migration.','Bind mounts remain at their original host paths.','No new Oracle/Iceberg stack provisioned or stress test run.');
    startup_recovery='Preserved zero-length stale socket directories and recreated runtime directories for Docker/run and docker-secrets-engine; no factory reset or volume removal.'
}
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $ReportDirectory 'verification.json') -Encoding utf8
$newVolumes | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $ReportDirectory 'volumes-after.json') -Encoding utf8
$images | Set-Content -LiteralPath (Join-Path $ReportDirectory 'images-after.jsonl') -Encoding utf8
$report | ConvertTo-Json -Depth 12
