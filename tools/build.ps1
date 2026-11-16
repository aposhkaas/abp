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
    $allArguments = @("DESIGNER", "/F", $InfoBasePath) + $Arguments + @("/DisableStartupMessages")
    $quotedArguments = $allArguments | ForEach-Object {
        if ($_ -match '\s') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }
    $process = Start-Process -FilePath $PlatformPath -ArgumentList $quotedArguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        throw "1C Designer failed with exit code $($process.ExitCode)"
    }
}

$loadLog = Join-Path $buildPath "load.log"
$updateLog = Join-Path $buildPath "update.log"
$checkLog = Join-Path $buildPath "check.log"

Invoke-1CDesigner @("/LoadConfigFromFiles", $sourcePath, "/Out", $loadLog)
Invoke-1CDesigner @("/UpdateDBCfg", "/Out", $updateLog)
Invoke-1CDesigner @("/CheckConfig", "-ConfigLogIntegrity", "-IncorrectReferences", "-ThinClient", "-Server", "-ExternalConnection", "/Out", $checkLog)

$checkText = Get-Content -LiteralPath $checkLog -Raw -Encoding UTF8
$successText = -join @(0x041E, 0x0448, 0x0438, 0x0431, 0x043E, 0x043A, 0x0020, 0x043D, 0x0435, 0x0020, 0x043E, 0x0431, 0x043D, 0x0430, 0x0440, 0x0443, 0x0436, 0x0435, 0x043D, 0x043E | ForEach-Object { [char]$_ })
if ($checkText -notmatch [regex]::Escape($successText)) {
    throw "Configuration check failed. See $checkLog"
}

$configurationFile = Join-Path $buildPath "CRM_Z1.cf"
$databaseFile = Join-Path $buildPath "CRM_Z1.dt"
Invoke-1CDesigner @("/DumpCfg", $configurationFile, "/Out", (Join-Path $buildPath "dump-cfg.log"))
Invoke-1CDesigner @("/DumpIB", $databaseFile, "/Out", (Join-Path $buildPath "dump-ib.log"))

if ((Get-Item -LiteralPath $configurationFile).Length -eq 0 -or (Get-Item -LiteralPath $databaseFile).Length -eq 0) {
    throw "Build artifacts were not created correctly"
}

Write-Output "Build completed: $buildPath"
