[CmdletBinding()]
param([switch]$Pause)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$launcher = Join-Path $PSScriptRoot 'Start-FusionStudio.ps1'
$windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$commandFile = Join-Path $projectRoot 'fusionstudio.cmd'
$exitCode = 0

Write-Output "Input project: $projectRoot"
Write-Output "Input launcher: $launcher"
Write-Output "Input command: $commandFile"
Write-Output 'Input/output setting: HKEY_CURRENT_USER\Environment\Path'
Write-Output 'Output files: None (register existing command files in the user PATH)'

try {
    Write-Output '[Command setup 1/4] Checking downloaded project files'
    foreach ($requiredFile in @($launcher, (Join-Path $projectRoot 'main.py'), $commandFile)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Required file missing: $requiredFile. Extract the complete project before running setup."
        }
    }

    Write-Output '[Command setup 2/4] Checking the installed Python environment and dataset pointer'
    & $windowsPowerShell -NoLogo -NoProfile -ExecutionPolicy Bypass -File $launcher -Check
    if ($LASTEXITCODE -ne 0) {
        throw 'Complete the README Installation steps, then run this setup again. PATH was not changed.'
    }

    Write-Output '[Command setup 3/4] Registering the project in the current-user PATH'
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $registeredPaths = @($userPath -split ';' | ForEach-Object {
        [Environment]::ExpandEnvironmentVariables($_.Trim().Trim('"')).TrimEnd('\')
    })
    if ($registeredPaths -contains $projectRoot.TrimEnd('\')) {
        Write-Output 'Project directory is already registered; no duplicate PATH entry added.'
    } else {
        $separator = if ([string]::IsNullOrEmpty($userPath) -or $userPath.EndsWith(';')) { '' } else { ';' }
        [Environment]::SetEnvironmentVariable('Path', ($userPath + $separator + $projectRoot), 'User')
        Write-Output 'Project directory added to the current-user PATH.'
    }

    Write-Output '[Command setup 4/4] Verifying the saved registration'
    $savedPaths = @([Environment]::GetEnvironmentVariable('Path', 'User') -split ';' | ForEach-Object {
        [Environment]::ExpandEnvironmentVariables($_.Trim().Trim('"')).TrimEnd('\')
    })
    if ($savedPaths -notcontains $projectRoot.TrimEnd('\')) {
        throw 'The user PATH could not be verified. Run setup again from a writable project folder.'
    }
    Write-Output 'Setup complete. Close and reopen PowerShell or cmd (restart Windows Terminal if used).'
    Write-Output 'Run fusionstudio from any directory to open Fusion Studio.'
    Write-Output 'Use fusionstudio -Check to check without opening a window.'
} catch {
    $exitCode = 1
    Write-Error "Command setup failed: $($_.Exception.Message)" -ErrorAction Continue
} finally {
    if ($Pause) { Read-Host 'Press Enter to close this setup window' | Out-Null }
}

exit $exitCode
