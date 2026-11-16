param(
    [Parameter(Mandatory = $true)]
    [string]$InfoBasePath,

    [string]$PlatformPath = "C:\Program Files (x86)\1cv8t\8.3.21.1644\bin\1cv8t.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $repoRoot "src"
$buildPath = Join-Path $repoRoot "build"

if (-not (Test-Path -LiteralPath $PlatformPath)) {
    throw "1C executable not found: $PlatformPath"
}
if (-not (Test-Path -LiteralPath $InfoBasePath)) {
    throw "Information base not found: $InfoBasePath"
}

New-Item -ItemType Directory -Force -Path $buildPath | Out-Null

function Invoke-1CDesigner {
    param([string[]]$Arguments)
    & $PlatformPath DESIGNER /F $InfoBasePath @Arguments /DisableStartupMessages
    if ($LASTEXITCODE -ne 0) {
        throw "1C Designer failed with exit code $LASTEXITCODE"
    }
}

$loadLog = Join-Path $buildPath "load.log"
$updateLog = Join-Path $buildPath "update.log"
$checkLog = Join-Path $buildPath "check.log"

Invoke-1CDesigner @("/LoadConfigFromFiles", $sourcePath, "/Out", $loadLog)
Invoke-1CDesigner @("/UpdateDBCfg", "/Out", $updateLog)
Invoke-1CDesigner @("/CheckConfig", "-ConfigLogIntegrity", "-IncorrectReferences", "-ThinClient", "-Server", "-ExternalConnection", "/Out", $checkLog)

$checkText = Get-Content -LiteralPath $checkLog -Raw -Encoding Default
if ($checkText -notmatch "Ошибок не обнаружено") {
    throw "Configuration check failed. See $checkLog"
}

Invoke-1CDesigner @("/DumpCfg", (Join-Path $buildPath "CRM_Z1.cf"))
Invoke-1CDesigner @("/DumpIB", (Join-Path $buildPath "CRM_Z1.dt"))

Write-Output "Build completed: $buildPath"
