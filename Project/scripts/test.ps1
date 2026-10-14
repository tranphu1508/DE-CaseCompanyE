param([switch]$Build, [string]$Select = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot 'compose.test.yaml'
$argsBase = @('compose', '--project-directory', $projectRoot, '-f', $composeFile)
if ($Build) {
    & docker @argsBase build tester
    if ($LASTEXITCODE -ne 0) { throw 'Test image build failed' }
}
try {
    & docker @argsBase up -d --wait postgres-test
    if ($LASTEXITCODE -ne 0) { throw 'Isolated PostgreSQL startup failed' }
    $imageId = & docker image inspect 'companye-tests:py311-spark357-gx124' --format '{{.Id}}'
    if ($LASTEXITCODE -ne 0) { throw 'Run with -Build to create the testing image first' }
    $runArgs = @('run', '--rm', '-e', "COMPANYE_TEST_IMAGE_ID=$imageId", 'tester', 'python', 'testing/run_suite.py')
    if ($Select) { $runArgs += @('-m', $Select) }
    & docker @argsBase @runArgs
    $testExit = $LASTEXITCODE
} finally {
    # Only the dedicated test project; operational companye services are untouched.
    & docker @argsBase down
}
if ($testExit -ne 0) { throw "CompanyE tests failed: $testExit" }
