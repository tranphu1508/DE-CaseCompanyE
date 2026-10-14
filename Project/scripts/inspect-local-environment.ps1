param([string]$OutputPath = (Join-Path $PSScriptRoot '../reports/local_environment.json'))
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$report = [ordered]@{
    captured_at = (Get-Date).ToString('o')
    purpose = 'Read-only local development and benchmark capacity assessment; not a stress test'
    cpu = @($cpu | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,LoadPercentage)
    memory = @{total_visible_kib=$os.TotalVisibleMemorySize; free_physical_kib=$os.FreePhysicalMemory}
    os = @{caption=$os.Caption;version=$os.Version}
    volumes = @(Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,Size,SizeRemaining)
    disks = @(Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,Size)
    gpu_nvidia_csv = @(& nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader)
    docker_resources = (& docker info --format '{"cpus":{{.NCPU}},"memory_bytes":{{.MemTotal}}}') | ConvertFrom-Json
    companye_containers = @(& docker inspect companye-postgres-1 companye-spark-1 --format '{{.Name}} memory_bytes={{.HostConfig.Memory}} nano_cpus={{.HostConfig.NanoCpus}} image={{.Config.Image}}')
    container_usage = @(& docker stats --no-stream --format '{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}}' companye-postgres-1 companye-spark-1)
    wsl_version = @(& wsl --version | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ })
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
$report | ConvertTo-Json -Depth 6
