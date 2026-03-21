# test_installer.ps1 — Runs INSIDE the Vagrant VM via WinRM.
# Tests installation and basic function of Android File Handler.
#
# Exit codes: 0 = all passed, 1 = one or more failures.

param(
    [string]$InstallerPath = "C:\vagrant_project\dist\android-file-handler-setup.exe",
    [string]$ScreenshotDir = "C:\vagrant_test_results"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────

$Script:Passed = 0
$Script:Failed = 0
$Script:Results = @()

function Write-TestResult {
    param([string]$Name, [bool]$Pass, [string]$Detail = "")
    $status = if ($Pass) { "PASS" } else { "FAIL" }
    $color  = if ($Pass) { "Green" } else { "Red" }
    $msg    = "[$status] $Name"
    if ($Detail) { $msg += " — $Detail" }
    Write-Host $msg -ForegroundColor $color
    if ($Pass) { $Script:Passed++ } else { $Script:Failed++ }
    $Script:Results += [PSCustomObject]@{ Test = $Name; Status = $status; Detail = $Detail }
}

function Take-Screenshot {
    param([string]$Name)
    if (-not (Test-Path $ScreenshotDir)) {
        New-Item -ItemType Directory -Path $ScreenshotDir -Force | Out-Null
    }
    $outFile = Join-Path $ScreenshotDir "$Name.png"
    $nircmd = Get-Command nircmd -ErrorAction SilentlyContinue
    if ($nircmd) {
        Start-Process -FilePath $nircmd.Source -ArgumentList "savescreenshot", $outFile -NoNewWindow -Wait
        return $outFile
    }
    # Fallback: .NET screenshot
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
    $bitmap.Save($outFile, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    return $outFile
}

# ── Setup ────────────────────────────────────────────────────────────────────

$AppName        = "Android File Handler"
$ExeName        = "android-file-handler-windows.exe"
$DefaultInstDir = Join-Path $env:ProgramFiles $AppName

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Android File Handler — Vagrant Test Suite  " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ScreenshotDir)) {
    New-Item -ItemType Directory -Path $ScreenshotDir -Force | Out-Null
}

# ── Test 1: Installer exists ────────────────────────────────────────────────

$installerExists = Test-Path $InstallerPath
Write-TestResult -Name "Installer file exists" -Pass $installerExists -Detail $InstallerPath

if (-not $installerExists) {
    Write-Host "`nFATAL: Installer not found at $InstallerPath. Build the installer first." -ForegroundColor Red
    Write-Host "  poetry run pyinstaller scripts\spec_scripts\android-file-handler-windows.spec"
    Write-Host "  iscc scripts\windows\android-file-handler-setup.iss"
    exit 1
}

# ── Test 2: Silent install ──────────────────────────────────────────────────

Write-Host "`n--- Running silent install ---" -ForegroundColor Yellow
$installProc = Start-Process -FilePath $InstallerPath `
    -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-" `
    -Wait -PassThru

$installOk = $installProc.ExitCode -eq 0
Write-TestResult -Name "Silent install completed" -Pass $installOk -Detail "Exit code: $($installProc.ExitCode)"

# ── Test 3: Install directory created ────────────────────────────────────────

$dirExists = Test-Path $DefaultInstDir
Write-TestResult -Name "Install directory exists" -Pass $dirExists -Detail $DefaultInstDir

# ── Test 4: Executable present ──────────────────────────────────────────────

$exePath = Join-Path $DefaultInstDir $ExeName
$exeExists = Test-Path $exePath
Write-TestResult -Name "Executable exists" -Pass $exeExists -Detail $exePath

# ── Test 5: Start Menu shortcut ─────────────────────────────────────────────

$startMenuDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\$AppName"
$shortcutPath = Join-Path $startMenuDir "$AppName.lnk"
$shortcutExists = Test-Path $shortcutPath
Write-TestResult -Name "Start Menu shortcut exists" -Pass $shortcutExists -Detail $shortcutPath

# ── Test 6: Registry uninstall entry ────────────────────────────────────────

$uninstallKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
$registryEntry = Get-ChildItem $uninstallKey -ErrorAction SilentlyContinue |
    Where-Object { (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DisplayName -eq $AppName }
$registryOk = $null -ne $registryEntry
Write-TestResult -Name "Registry uninstall entry" -Pass $registryOk

# ── Test 7: Launch application & capture GUI ─────────────────────────────────

if ($exeExists) {
    Write-Host "`n--- Launching application ---" -ForegroundColor Yellow

    $appProc = Start-Process -FilePath $exePath -PassThru
    Start-Sleep -Seconds 8

    # Check if process is still running (GUI app should stay alive)
    $appRunning = -not $appProc.HasExited
    Write-TestResult -Name "Application launches and stays running" -Pass $appRunning

    # Look for the window by title
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    }
"@
    $hwnd = [Win32]::FindWindow($null, $AppName)
    $windowFound = $hwnd -ne [IntPtr]::Zero
    Write-TestResult -Name "Main window found by title" -Pass $windowFound -Detail "HWND: $hwnd"

    # Take screenshot of the running application
    Start-Sleep -Seconds 2
    $screenshotFile = Take-Screenshot -Name "app_running"
    Write-Host "  Screenshot saved: $screenshotFile" -ForegroundColor DarkGray

    # Gracefully close
    if (-not $appProc.HasExited) {
        $appProc.CloseMainWindow() | Out-Null
        Start-Sleep -Seconds 3
        if (-not $appProc.HasExited) {
            $appProc.Kill()
        }
    }
}
else {
    Write-TestResult -Name "Application launches and stays running" -Pass $false -Detail "Skipped — exe not found"
    Write-TestResult -Name "Main window found by title" -Pass $false -Detail "Skipped — exe not found"
}

# ── Test 8: Silent uninstall ────────────────────────────────────────────────

Write-Host "`n--- Running silent uninstall ---" -ForegroundColor Yellow
$uninstallerPath = Join-Path $DefaultInstDir "unins000.exe"
if (Test-Path $uninstallerPath) {
    $uninstProc = Start-Process -FilePath $uninstallerPath `
        -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" `
        -Wait -PassThru
    $uninstallOk = $uninstProc.ExitCode -eq 0
    Write-TestResult -Name "Silent uninstall completed" -Pass $uninstallOk -Detail "Exit code: $($uninstProc.ExitCode)"

    Start-Sleep -Seconds 2
    $dirGone = -not (Test-Path $DefaultInstDir)
    Write-TestResult -Name "Install directory removed after uninstall" -Pass $dirGone
}
else {
    Write-TestResult -Name "Silent uninstall completed" -Pass $false -Detail "Uninstaller not found"
    Write-TestResult -Name "Install directory removed after uninstall" -Pass $false -Detail "Skipped"
}

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Passed : $Script:Passed" -ForegroundColor Green
Write-Host "  Failed : $Script:Failed" -ForegroundColor $(if ($Script:Failed -gt 0) { "Red" } else { "Green" })
Write-Host "  Total  : $($Script:Passed + $Script:Failed)" -ForegroundColor White
Write-Host ""

$Script:Results | Format-Table -AutoSize

# Export results as CSV for retrieval
$csvPath = Join-Path $ScreenshotDir "test_results.csv"
$Script:Results | Export-Csv -Path $csvPath -NoTypeInformation
Write-Host "Results saved to $csvPath" -ForegroundColor DarkGray

exit $(if ($Script:Failed -gt 0) { 1 } else { 0 })
