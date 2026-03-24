# run_vagrant_tests.ps1 — Host-side orchestrator for Vagrant Windows 11 test cycle.
#
# Workflow:
#   1. Build the installer locally (PyInstaller + Inno Setup)
#   2. Ensure the Vagrant VM is running and has a "clean" snapshot
#   3. Restore to the clean snapshot
#   4. Transfer build assets to the VM and compile the installer (Inno Setup)
#   5. Run the test script inside the VM via PSSession
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
#   - Poetry environment set up
#   - The VM created and "clean" snapshot saved:
#       cd vagrant && vagrant up --provider=hyperv && vagrant snapshot save clean
#   Note: Inno Setup 6.7.1 is installed inside the VM by provision.ps1 — no host install needed.

[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipRevert,
    [string]$SnapshotName = "clean",
    [string]$LocalResultsDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot  = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$vmSession = $null   # PSSession — closed in finally block
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

    # ── Step 1: Build the Windows executable (host, PyInstaller only) ────────
    # Inno Setup runs inside the VM — no host install of Inno Setup required.

    $pyinstallerExe = Join-Path $RepoRoot "dist\android-file-handler-windows.exe"
    $AppVersion     = ""

    if ($SkipBuild) {
        Write-Step "Skipping PyInstaller build (-SkipBuild specified)"
        if (-not (Test-Path $pyinstallerExe)) {
            Write-Host "ERROR: -SkipBuild was specified but exe not found at $pyinstallerExe" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Step "Building Windows executable (PyInstaller)"

        Push-Location $RepoRoot
        try {
            Write-Host "  Running PyInstaller..." -ForegroundColor Yellow
            poetry run pyinstaller scripts\spec_scripts\android-file-handler-windows.spec --noconfirm
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
                exit 1
            }

            if (-not (Test-Path $pyinstallerExe)) {
                Write-Host "ERROR: PyInstaller output not found at $pyinstallerExe" -ForegroundColor Red
                exit 1
            }
            Write-Host "  PyInstaller output: $pyinstallerExe" -ForegroundColor Green
        }
        finally {
            Pop-Location
        }
    }

    # Capture version to pass to Inno Setup inside the VM
    Push-Location $RepoRoot
    try {
        $AppVersion = (poetry version -s).Trim()
        Write-Host "  App version: $AppVersion" -ForegroundColor DarkGray
    }
    finally {
        Pop-Location
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

    # ── Establish direct PSSession ────────────────────────────────────────────
    # vagrant winrm uses a subprocess whose args are subject to the Windows
    # command-line length limit (~32 KB). Large file transfers exceed that limit.
    # A direct PSSession has no such restriction and supports
    # Copy-Item -ToSession / -FromSession for binary files of any size.

    Write-Step "Establishing PSSession to VM"

    # Ensure host WinRM client is configured to allow Basic authentication
    # This is required for the connection to succeed when using -Authentication Basic
    if ((Get-Item WSMan:\localhost\Client\Auth\Basic).Value -ne "true") {
        Write-Host "  Enabling WinRM Client Basic authentication on host..." -ForegroundColor Yellow
        Set-Item WSMan:\localhost\Client\Auth\Basic -Value $true -Force
    }

    $remoteBuildRoot     = "C:\vagrant_build"
    $remoteInstallerPath = "$remoteBuildRoot\dist\android-file-handler-setup.exe"
    $remoteResultsDir    = "C:\vagrant_test_results"

    # vagrant winrm-config reports the plaintext port (5985) used by Vagrant itself.
    # We extract the host and port, then derive the HTTPS port (typically +1).
    # If the direct IP fails, we fallback to the forwarded port on localhost.
    $winrmConfig = & vagrant winrm-config 2>$null | Out-String
    $vmHost      = if ($winrmConfig -match 'HostName\s+(\S+)') { $Matches[1] } else { '127.0.0.1' }
    $vmPort      = if ($winrmConfig -match 'Port\s+(\d+)') { [int]$Matches[1] + 1 } else { 5986 }

    # If we have a direct IP but it's not reachable, fallback to the forwarded port
    if ($vmHost -ne '127.0.0.1' -and -not (Test-NetConnection -ComputerName $vmHost -Port $vmPort -InformationLevel Quiet)) {
        Write-Host "  Direct IP $vmHost`:$vmPort unreachable. Falling back to localhost..." -ForegroundColor Yellow
        $vmHost = '127.0.0.1'
        $vmPort = 55986   # The host-side forwarded port for 5986
    }

    # Verify connectivity before trying PSSession
    if (-not (Test-NetConnection -ComputerName $vmHost -Port $vmPort -InformationLevel Quiet)) {
        Write-Host "ERROR: Could not reach VM at $vmHost`:$vmPort. Ensure 'vagrant up' and provisioning completed successfully." -ForegroundColor Red
        exit 1
    }

    $vagrantCred = New-Object PSCredential 'vagrant',
                    (ConvertTo-SecureString 'vagrant' -AsPlainText -Force)
    # SkipCACheck / SkipCNCheck accept the self-signed cert created by provision.ps1.
    $sessionOpts = New-PSSessionOption -SkipCACheck -SkipCNCheck -SkipRevocationCheck
    $vmSession   = New-PSSession -ComputerName $vmHost -Port $vmPort `
                       -Credential $vagrantCred -Authentication Basic `
                       -UseSSL -SessionOption $sessionOpts

    Write-Host "  Connected to VM at $vmHost`:$vmPort" -ForegroundColor DarkGray

    # ── Step 4: Transfer build assets to VM and compile installer ────────────

    Write-Step "Transferring build assets to VM"

    Invoke-Command -Session $vmSession -ScriptBlock {
        param($root)
        @("$root\dist", "$root\scripts\windows", "$root\icon_media") |
            ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
    } -ArgumentList $remoteBuildRoot

    $transfers = @(
        @{ L = Join-Path $RepoRoot "dist\android-file-handler-windows.exe";          R = "$remoteBuildRoot\dist\android-file-handler-windows.exe"          },
        @{ L = Join-Path $RepoRoot "scripts\windows\android-file-handler-setup.iss"; R = "$remoteBuildRoot\scripts\windows\android-file-handler-setup.iss" },
        @{ L = Join-Path $RepoRoot "LICENSE.txt";                                    R = "$remoteBuildRoot\LICENSE.txt"                                    },
        @{ L = Join-Path $RepoRoot "icon_media\robot_files_256.ico";                 R = "$remoteBuildRoot\icon_media\robot_files_256.ico"                 },
        @{ L = Join-Path $RepoRoot "vagrant\test_installer.ps1";                     R = "$remoteBuildRoot\test_installer.ps1"                             }
    )
    foreach ($t in $transfers) {
        Copy-Item -Path $t.L -Destination $t.R -ToSession $vmSession -Force
        $sizeMB = [math]::Round((Get-Item $t.L).Length / 1MB, 1)
        Write-Host "  Sent: $(Split-Path -Leaf $t.L) (${sizeMB} MB)" -ForegroundColor DarkGray
    }

    # Unblock transferred files — Copy-Item -ToSession can mark files with a
    # Zone.Identifier ADS that execution policy may block even under -Scope Process Bypass.
    Invoke-Command -Session $vmSession -ScriptBlock {
        param($root)
        Get-ChildItem -Path $root -Recurse -File |
            ForEach-Object { Unblock-File -Path $_.FullName -ErrorAction SilentlyContinue }
    } -ArgumentList $remoteBuildRoot
    Write-Host "  Files unblocked on VM." -ForegroundColor DarkGray

    Write-Step "Building installer inside the VM (Inno Setup 6.7.1)"

    Invoke-Command -Session $vmSession -ScriptBlock {
        param($buildRoot, $version)
        & 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' `
            "$buildRoot\scripts\windows\android-file-handler-setup.iss" `
            "/DMyAppVersion=$version"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } -ArgumentList $remoteBuildRoot, $AppVersion

    Write-Host "  Installer built: $remoteInstallerPath" -ForegroundColor Green

    # ── Step 5: Run tests inside the VM ──────────────────────────────────────

    Write-Step "Running test suite inside the VM"

    $testExitCode = 0
    try {
        Invoke-Command -Session $vmSession -ScriptBlock {
            param($buildRoot, $installer)
            Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
            & "$buildRoot\test_installer.ps1" -InstallerPath $installer
            # Propagate the test script's exit code as output so the host can inspect it.
            $LASTEXITCODE
        } -ArgumentList $remoteBuildRoot, $remoteInstallerPath |
            ForEach-Object {
                if ($_ -is [int]) { $testExitCode = $_ }
            }
    }
    catch {
        $testExitCode = 1
        Write-Host "Test script encountered an error:" -ForegroundColor Yellow
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Category : $($_.CategoryInfo.Category)" -ForegroundColor Red
        Write-Host "  FullError: $_" -ForegroundColor Red
    }

    # Re-establish the PSSession if the test run left it in a non-Opened state.
    # An unhandled exception inside Invoke-Command can terminate the remote runspace.
    if ($vmSession.State -ne 'Opened') {
        Write-Host "  PSSession is '$($vmSession.State)' — re-establishing for results retrieval..." -ForegroundColor Yellow
        Remove-PSSession $vmSession -ErrorAction SilentlyContinue
        $vmSession = New-PSSession -ComputerName $vmHost -Port $vmPort `
                         -Credential $vagrantCred -Authentication Basic `
                         -UseSSL -SessionOption $sessionOpts
        Write-Host "  Session re-established." -ForegroundColor DarkGray
    }

    # ── Step 6: Retrieve results and screenshots ─────────────────────────────

    Write-Step "Retrieving test results and screenshots"

    if (-not (Test-Path $LocalResultsDir)) {
        New-Item -ItemType Directory -Path $LocalResultsDir -Force | Out-Null
    }

    try {
        $hasResults = Invoke-Command -Session $vmSession -ScriptBlock {
            param($dir) Test-Path $dir
        } -ArgumentList $remoteResultsDir

        if ($hasResults) {
            Copy-Item -Path "$remoteResultsDir\*" -Destination $LocalResultsDir `
                      -FromSession $vmSession -Recurse -Force
            Write-Host "  Retrieved results from $remoteResultsDir" -ForegroundColor DarkGray
        }
        else {
            Write-Host "  No results directory found on VM." -ForegroundColor Yellow
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

        $passCount = @($results | Where-Object { $_.Status -eq "PASS" }).Count
        $failCount = @($results | Where-Object { $_.Status -eq "FAIL" }).Count
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
    if ($vmSession) { Remove-PSSession $vmSession -ErrorAction SilentlyContinue }
    Pop-Location
}
