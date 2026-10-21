[CmdletBinding()]
param([switch]$Check)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$entryPoint = Join-Path $projectRoot 'main.py'
$python = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$consolePython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dataPointer = Join-Path $projectRoot 'data\attack\active.json'
if (-not (Test-Path -LiteralPath $dataPointer -PathType Leaf)) {
    $dataPointer = Join-Path $projectRoot 'data\attack\latest.json'
}
$logDirectory = Join-Path $projectRoot 'artifacts\launch'
$launchId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'), $PID
$outputLog = Join-Path $logDirectory "$launchId.log"
$errorLog = Join-Path $logDirectory "$launchId-errors.log"

Write-Output "Input program: $entryPoint"
Write-Output "Input Python: $python"
Write-Output "Input dataset pointer: $dataPointer"
Write-Output "Input/output settings: $(Join-Path $projectRoot 'data\ui-settings.ini')"
Write-Output "Input/output session: $(Join-Path $projectRoot 'data\workspace-session.json')"
if ($Check) {
    Write-Output 'Output files: None (launcher check only)'
} else {
    Write-Output "Output log: $outputLog"
    Write-Output "Output errors: $errorLog"
}

try {
    Write-Output '[ttpselector 1/3] Checking application, environment and dataset paths'
    foreach ($requiredPath in @($entryPoint, $python, $consolePython, $dataPointer)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required file missing: $requiredPath. See the project README setup instructions."
        }
    }
    if ($Check) {
        Write-Output '[ttpselector 2/3] Checking desktop dependencies without opening a window'
        & $consolePython -B -c 'import PySide6.QtWidgets, mitreattack, openpyxl, markdown'
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency check failed.' }
        Write-Output '[ttpselector 3/3] Ready; run ttpselector to open TTP Selection Studio'
        exit 0
    }

    Write-Output '[ttpselector 2/3] Opening TTP Selection Studio'
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $env:QT_QPA_PLATFORM = 'windows'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONUNBUFFERED = '1'
    $application = Start-Process -FilePath $python -ArgumentList @('-B', ('"' + $entryPoint + '"')) -WorkingDirectory $projectRoot -WindowStyle Normal -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog -PassThru
    Start-Sleep -Milliseconds 800
    $application.Refresh()
    if ($application.HasExited -and $application.ExitCode -ne 0) {
        throw "Application exited with code $($application.ExitCode). See $errorLog"
    }
    Write-Output "[ttpselector 3/3] Launch requested (PID $($application.Id)); the window may take a moment to load"
} catch {
    Write-Error "ttpselector failed: $($_.Exception.Message)"
    exit 1
}
