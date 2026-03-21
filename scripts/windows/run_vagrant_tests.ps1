# run_vagrant_tests.ps1 — Host-side orchestrator for Vagrant Windows 11 test cycle.
#
# Workflow:
#   1. Build the installer locally (PyInstaller + Inno Setup)
#   2. Ensure the Vagrant VM is running and has a "clean" snapshot
#   3. Restore to the clean snapshot
#   4. Push the installer to the VM
#   5. Run the test script inside the VM via WinRM
#   6. Retrieve screenshots and results to the host
#   7. Print results summary to CLI
#   8. Revert VM back to clean snapshot
#
# Usage (from repo root):
#   .\scripts\windows\run_vagrant_tests.ps1
#   .\scripts\windows\run_vagrant_tests.ps1 -SkipBuild
#   .\scripts\windows\run_vagrant_tests.ps1 -SkipRevert
#
# Prerequisites:
#   - Vagrant and Hyper-V enabled on the host
#   - Inno Setup 6 installed (default path or in PATH)
#   - Poetry environment set up
#   - The VM created and "clean" snapshot saved:
#       cd vagrant && vagrant up --provider=hyperv && vagrant snapshot save clean

[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipRevert,
    [string]$SnapshotName = "clean",
    [string]$LocalResultsDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VagrantDir = Join-Path $RepoRoot "vagrant"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (-not $LocalResultsDir) {
    $LocalResultsDir = Join-Path $RepoRoot "vagrant_test_results\$Timestamp"
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n>>> $Message" -ForegroundColor Cyan
}

# ── Ensure we're in the vagrant directory ────────────────────────────────────

Push-Location $VagrantDir
try {

    # ── Step 1: Build the installer locally ──────────────────────────────────

    $installerPath = Join-Path $RepoRoot "dist\android-file-handler-setup.exe"

    if ($SkipBuild) {
        Write-Step "Skipping build (-SkipBuild specified)"
        if (-not (Test-Path $installerPath)) {
            Write-Host "ERROR: -SkipBuild was specified but installer not found at $installerPath" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Step "Building installer locally (PyInstaller + Inno Setup)"

        # PyInstaller — compile the exe
        Push-Location $RepoRoot
        try {
            Write-Host "  Running PyInstaller..." -ForegroundColor Yellow
            poetry run pyinstaller scripts\spec_scripts\android-file-handler-windows.spec --noconfirm
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
                exit 1
            }

            $pyinstallerExe = Join-Path $RepoRoot "dist\android-file-handler-windows.exe"
            if (-not (Test-Path $pyinstallerExe)) {
                Write-Host "ERROR: PyInstaller output not found at $pyinstallerExe" -ForegroundColor Red
                exit 1
            }
            Write-Host "  PyInstaller output: $pyinstallerExe" -ForegroundColor Green

            # Inno Setup — compile the installer
            Write-Host "  Running Inno Setup..." -ForegroundColor Yellow
            $isccPaths = @(
                "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                "C:\Program Files\Inno Setup 6\ISCC.exe"
            )
            $iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
            if (-not $iscc) {
                $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
            }
            if (-not $iscc) {
                Write-Host "ERROR: Inno Setup (ISCC.exe) not found. Install Inno Setup 6 or add it to PATH." -ForegroundColor Red
                exit 1
            }

            & $iscc "scripts\windows\android-file-handler-setup.iss"
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: Inno Setup failed with exit code $LASTEXITCODE" -ForegroundColor Red
                exit 1
            }

            if (-not (Test-Path $installerPath)) {
                Write-Host "ERROR: Installer not found at $installerPath after Inno Setup" -ForegroundColor Red
                exit 1
            }
            Write-Host "  Installer built: $installerPath" -ForegroundColor Green
        }
        finally {
            Pop-Location
        }
    }

    # ── Step 2: Verify VM and snapshot exist ─────────────────────────────────

    Write-Step "Checking Vagrant VM status"
    $status = vagrant status --machine-readable 2>&1 |
        Select-String "state,running" -Quiet

    if (-not $status) {
        Write-Host "VM is not running. Starting it..." -ForegroundColor Yellow
        vagrant up --provider=hyperv
    }

    Write-Step "Verifying '$SnapshotName' snapshot exists"
    $snapshots = vagrant snapshot list 2>&1
    if ($snapshots -notmatch [regex]::Escape($SnapshotName)) {
        Write-Host "Snapshot '$SnapshotName' not found. Creating it now..." -ForegroundColor Yellow
        vagrant snapshot save $SnapshotName
    }

    # ── Step 3: Restore to clean snapshot ────────────────────────────────────

    Write-Step "Restoring VM to '$SnapshotName' snapshot"
    vagrant snapshot restore $SnapshotName

    # ── Step 4: Push installer to the VM ─────────────────────────────────────

    Write-Step "Pushing installer to the VM"

    $remoteInstallerDir = "C:\vagrant_installer"
    $remoteInstallerPath = "$remoteInstallerDir\android-file-handler-setup.exe"

    vagrant winrm --shell powershell --command `
        "New-Item -ItemType Directory -Path '$remoteInstallerDir' -Force | Out-Null"

    # Base64-encode the installer, transfer via WinRM, decode on the VM
    $installerBytes = [IO.File]::ReadAllBytes($installerPath)
    $installerSizeMB = [math]::Round($installerBytes.Length / 1MB, 1)
    Write-Host "  Installer size: ${installerSizeMB} MB — transferring via WinRM..." -ForegroundColor Yellow

    # Split into chunks to avoid WinRM message size limits (< 2MB per command)
    $chunkSize = 1 * 1024 * 1024  # 1 MB chunks
    $totalChunks = [math]::Ceiling($installerBytes.Length / $chunkSize)

    vagrant winrm --shell powershell --command `
        "if (Test-Path '$remoteInstallerPath') { Remove-Item '$remoteInstallerPath' -Force }"

    for ($idx = 0; $idx -lt $totalChunks; $idx++) {
        $offset = $idx * $chunkSize
        $length = [math]::Min($chunkSize, $installerBytes.Length - $offset)
        $chunk = New-Object byte[] $length
        [Array]::Copy($installerBytes, $offset, $chunk, 0, $length)
        $b64Chunk = [Convert]::ToBase64String($chunk)

        $appendScript = if ($idx -eq 0) {
            "[IO.File]::WriteAllBytes('$remoteInstallerPath', [Convert]::FromBase64String('$b64Chunk'))"
        }
        else {
            "`$bytes = [Convert]::FromBase64String('$b64Chunk'); " +
            "`$stream = [IO.File]::Open('$remoteInstallerPath', 'Append'); " +
            "`$stream.Write(`$bytes, 0, `$bytes.Length); `$stream.Close()"
        }
        vagrant winrm --shell powershell --command $appendScript
        Write-Host "  Chunk $($idx + 1)/$totalChunks transferred" -ForegroundColor DarkGray
    }

    # Verify transfer
    $remoteSize = vagrant winrm --shell powershell --command `
        "(Get-Item '$remoteInstallerPath').Length"
    Write-Host "  Remote file size: $($remoteSize.Trim()) bytes (expected: $($installerBytes.Length))" -ForegroundColor DarkGray

    # ── Step 5: Run tests inside the VM ──────────────────────────────────────

    Write-Step "Running test suite inside the VM"

    $testExitCode = 0
    try {
        vagrant winrm --shell powershell --command `
            "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; & C:\vagrant_project\vagrant\test_installer.ps1 -InstallerPath 'C:\vagrant_installer\android-file-handler-setup.exe'"
    }
    catch {
        $testExitCode = 1
        Write-Host "Test script returned failures." -ForegroundColor Yellow
    }

    # ── Step 6: Retrieve results and screenshots ─────────────────────────────

    Write-Step "Retrieving test results and screenshots"

    if (-not (Test-Path $LocalResultsDir)) {
        New-Item -ItemType Directory -Path $LocalResultsDir -Force | Out-Null
    }

    # Copy results from shared folder on VM via vagrant scp or direct file copy
    # The test writes to C:\vagrant_test_results inside the VM.
    # We retrieve via WinRM by reading files.
    try {
        # Get list of result files
        $remoteFiles = vagrant winrm --shell powershell --command `
            "if (Test-Path 'C:\vagrant_test_results') { Get-ChildItem 'C:\vagrant_test_results' -Name }" 2>&1 |
            Where-Object { $_ -is [string] -and $_.Trim() -ne "" }

        foreach ($fileName in $remoteFiles) {
            $trimmedName = $fileName.Trim()
            if (-not $trimmedName) { continue }

            $remotePath = "C:\vagrant_test_results\$trimmedName"
            $localPath = Join-Path $LocalResultsDir $trimmedName

            if ($trimmedName -match '\.csv$') {
                # Text file — read content and save
                $content = vagrant winrm --shell powershell --command `
                    "Get-Content -Path '$remotePath' -Raw"
                $content | Out-File -FilePath $localPath -Encoding utf8
                Write-Host "  Retrieved: $trimmedName" -ForegroundColor DarkGray
            }
            elseif ($trimmedName -match '\.(png|jpg|bmp)$') {
                # Binary file — base64 encode, transfer, decode
                $b64 = vagrant winrm --shell powershell --command `
                    "[Convert]::ToBase64String([IO.File]::ReadAllBytes('$remotePath'))"
                [IO.File]::WriteAllBytes($localPath, [Convert]::FromBase64String($b64.Trim()))
                Write-Host "  Retrieved: $trimmedName" -ForegroundColor DarkGray
            }
        }
    }
    catch {
        Write-Host "  Warning: Could not retrieve some result files: $_" -ForegroundColor Yellow
    }

    # ── Step 7: Print local summary ──────────────────────────────────────────

    Write-Step "Test Results"

    $csvPath = Join-Path $LocalResultsDir "test_results.csv"
    if (Test-Path $csvPath) {
        $results = Import-Csv $csvPath
        $results | Format-Table -AutoSize

        $passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
        $failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
        Write-Host "  Passed: $passCount  |  Failed: $failCount  |  Total: $($passCount + $failCount)" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
    }
    else {
        Write-Host "  No results CSV found. Check VM output above." -ForegroundColor Yellow
    }

    Write-Host "`n  Results directory: $LocalResultsDir" -ForegroundColor White

    # List screenshots
    $screenshots = Get-ChildItem $LocalResultsDir -Filter "*.png" -ErrorAction SilentlyContinue
    if ($screenshots) {
        Write-Host "  Screenshots:" -ForegroundColor White
        foreach ($shot in $screenshots) {
            Write-Host "    - $($shot.FullName)" -ForegroundColor DarkGray
        }
    }

    # ── Step 8: Revert to clean snapshot ─────────────────────────────────────

    if (-not $SkipRevert) {
        Write-Step "Reverting VM to '$SnapshotName' snapshot"
        vagrant snapshot restore $SnapshotName
        Write-Host "VM reverted to clean state." -ForegroundColor Green
    }
    else {
        Write-Host "`n  -SkipRevert specified, VM left in current state." -ForegroundColor Yellow
    }

    # ── Exit ─────────────────────────────────────────────────────────────────

    Write-Host ""
    if ($testExitCode -ne 0) {
        Write-Host "One or more tests FAILED." -ForegroundColor Red
        exit 1
    }
    else {
        Write-Host "All tests PASSED." -ForegroundColor Green
        exit 0
    }

}
finally {
    Pop-Location
}
