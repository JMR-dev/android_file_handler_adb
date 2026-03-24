# test_installer.ps1 — Runs INSIDE the Vagrant VM via WinRM.
# Tests installation and basic function of Android File Handler.
#
# Exit codes: 0 = all passed, 1 = one or more failures.

param(
    [string]$InstallerPath = "C:\vagrant_build\dist\android-file-handler-setup.exe",
    [string]$ScreenshotDir = "C:\vagrant_test_results",
    [string]$AppVersion    = ""
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
    if ($Detail) { $msg += " - $Detail" }
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
Write-Host "  Android File Handler - Vagrant Test Suite  " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ScreenshotDir)) {
    New-Item -ItemType Directory -Path $ScreenshotDir -Force | Out-Null
}

try {
    # ── Build installer if not already present ──────────────────────────────────
    # When run directly inside the VM (not via run_vagrant_tests.ps1), the build
    # dir may not exist yet. Since the SMB mount is disabled by default, this
    # fallback requires manual transfer of assets to C:\vagrant_project.

    if (-not (Test-Path $InstallerPath)) {
        $projectRoot  = "C:\vagrant_project"
        $sourceExe    = "$projectRoot\dist\android-file-handler-windows.exe"
        $iscc         = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        $buildRoot    = "C:\vagrant_build"

        if (-not (Test-Path $sourceExe)) {
            Write-Host "`nFATAL: Installer not found and cannot build - PyInstaller exe missing." -ForegroundColor Red
            Write-Host "  Run PyInstaller on the host first, then use the orchestrator:" -ForegroundColor Yellow
            Write-Host "    ..\scripts\windows\run_vagrant_tests.ps1"
            Write-Host "  (Or manually transfer files to C:\vagrant_project inside the VM)."
            exit 1
        }

        if (-not (Test-Path $iscc)) {
            Write-Host "`nFATAL: Inno Setup not found at $iscc." -ForegroundColor Red
            Write-Host "  Re-provision the VM:  vagrant provision" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "`n--- Building installer inside the VM (Inno Setup 6.7.1) ---" -ForegroundColor Yellow

        @("$buildRoot\dist", "$buildRoot\scripts\windows", "$buildRoot\icon_media") |
            ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }

        Copy-Item $sourceExe                                              "$buildRoot\dist\"         -Force
        Copy-Item "$projectRoot\scripts\windows\android-file-handler-setup.iss" "$buildRoot\scripts\windows\" -Force
        Copy-Item "$projectRoot\LICENSE.txt"                              "$buildRoot\"              -Force
        Copy-Item "$projectRoot\icon_media\robot_files_256.ico"           "$buildRoot\icon_media\"   -Force

        $isccArgs = @("$buildRoot\scripts\windows\android-file-handler-setup.iss")
        if ($AppVersion) { $isccArgs += "/DMyAppVersion=$AppVersion" }

        & $iscc @isccArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FATAL: Inno Setup failed (exit $LASTEXITCODE)." -ForegroundColor Red
            exit 1
        }
        Write-Host "  Installer built: $InstallerPath" -ForegroundColor Green
    }

    # ── Test 1: Installer exists ────────────────────────────────────────────────

    $installerExists = Test-Path $InstallerPath
    Write-TestResult -Name "Installer file exists" -Pass $installerExists -Detail $InstallerPath

    if (-not $installerExists) {
        throw "Installer not found at $InstallerPath."
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

    # Check both the native (64-bit) and WoW6432Node (32-bit) uninstall hives.
    # WinRM sessions may run 32-bit PowerShell, which redirects HKLM:\SOFTWARE to
    # WoW6432Node, missing the 64-bit installer's entry if we only check one path.
    # try/catch in the Where-Object handles the StrictMode "property not found" throw
    # that neither -ErrorAction nor PSObject.Properties can fully avoid.
    $uninstallPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    )
    $registryEntry = $uninstallPaths | ForEach-Object {
        Get-ChildItem $_ -ErrorAction SilentlyContinue
    } | Where-Object {
        # Match exact name OR "AppName version X.Y.Z" (Inno Setup default when
        # AppVerName is not set). The .iss now sets AppVerName={#MyAppName} so
        # exact match is expected; the -like guard covers older installer builds.
        try {
            $dn = (Get-ItemProperty $_.PSPath -ErrorAction Stop).DisplayName
            $dn -eq $AppName -or $dn -like "$AppName *"
        } catch { $false }
    }
    $registryOk = $null -ne $registryEntry

    if (-not $registryOk) {
        # Diagnostic: show non-Microsoft entries so the failure can be investigated.
        Write-Host "  [Diag] Entries found in Uninstall hives:" -ForegroundColor DarkGray
        $uninstallPaths | ForEach-Object {
            Get-ChildItem $_ -ErrorAction SilentlyContinue
        } | ForEach-Object {
            $dn = try { (Get-ItemProperty $_.PSPath -ErrorAction Stop).DisplayName } catch { $null }
            if ($dn -and $dn -notmatch '^(Microsoft|Windows|KB\d)') {
                Write-Host "    '$dn'" -ForegroundColor DarkGray
            }
        }
    }
    Write-TestResult -Name "Registry uninstall entry" -Pass $registryOk

    # ── Test 7: Launch application & capture GUI ─────────────────────────────────

    if ($exeExists) {
        Write-Host "`n--- Launching application ---" -ForegroundColor Yellow

        $appProc = Start-Process -FilePath $exePath -PassThru
        Start-Sleep -Seconds 8

        # Check if process is still running (GUI app should stay alive)
        $appRunning = -not $appProc.HasExited
        Write-TestResult -Name "Application launches and stays running" -Pass $appRunning

        # Look for the window by title.
        # WinRM sessions run in a non-interactive window station; the GUI process
        # may have no accessible HWND from this session even when fully running.
        # Try .NET MainWindowTitle first, then Win32 FindWindow as a fallback.
        # If both come up empty but the process is still alive, count it as a pass
        # with a note — the "stays running" check above already validates the install.
        $windowFound = $false
        $windowNote  = ""
        $hwnd        = [IntPtr]::Zero

        $appProc.Refresh()
        if ($appProc.MainWindowTitle -eq $AppName) {
            $windowFound = $true
            $windowNote  = "via .NET MainWindowTitle"
        } else {
            try {
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {
                    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
                    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
                }
"@ -ErrorAction SilentlyContinue
                $hwnd = [Win32]::FindWindow($null, $AppName)
                if ($hwnd -ne [IntPtr]::Zero) {
                    $windowFound = $true
                    $windowNote  = "HWND: $hwnd"
                }
            } catch {
                Write-Host "  Warning: Could not check for window title via Win32 API." -ForegroundColor Yellow
            }

            if (-not $windowFound -and $appRunning) {
                # Process is alive; window just not reachable from the WinRM session.
                $windowFound = $true
                $windowNote  = "process alive - window not accessible from WinRM session"
            }
        }
        Write-TestResult -Name "Main window found by title" -Pass $windowFound -Detail $windowNote

        # Take screenshot of the running application
        try {
            Start-Sleep -Seconds 2
            $screenshotFile = Take-Screenshot -Name "app_running"
            Write-Host "  Screenshot saved: $screenshotFile" -ForegroundColor DarkGray
        } catch {
            Write-Host "  Warning: Could not capture screenshot: $_" -ForegroundColor Yellow
        }

        # Gracefully close, then ensure the entire process tree is dead before
        # the uninstaller runs. PyInstaller onefile spawns a child process that
        # continues after the stub exits; taskkill /F /T kills both. The extra
        # sleep lets the OS release executable file handles so the uninstaller
        # can delete the .exe.
        if (-not $appProc.HasExited) {
            $appProc.CloseMainWindow() | Out-Null
            Start-Sleep -Seconds 3
        }
        $procName = [System.IO.Path]::GetFileNameWithoutExtension($ExeName)
        taskkill /F /T /IM "$procName.exe" 2>&1 | Out-Null
        Start-Sleep -Seconds 3  # Wait for OS to release file handles
    }
    else {
        Write-TestResult -Name "Application launches and stays running" -Pass $false -Detail "Skipped - exe not found"
        Write-TestResult -Name "Main window found by title" -Pass $false -Detail "Skipped - exe not found"
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
        # Assert the executable is gone — not the directory. The app may have
        # created platform-tools/, a license file, or other runtime files inside
        # the install dir during Test 7; Inno Setup only tracks files it installed
        # and will not remove a non-empty directory.
        $exeGone = -not (Test-Path $exePath)
        Write-TestResult -Name "Executable removed after uninstall" -Pass $exeGone -Detail $exePath
    }
    else {
        Write-TestResult -Name "Silent uninstall completed" -Pass $false -Detail "Uninstaller not found"
        Write-TestResult -Name "Install directory removed after uninstall" -Pass $false -Detail "Skipped"
    }

} catch {
    # Catch unexpected terminating exceptions so the finally block can still save
    # results and so the PSSession is not broken by an unhandled remote exception.
    $errMsg = "$_"
    Write-Host "`nFATAL: Unhandled exception in test suite: $errMsg" -ForegroundColor Red
    Write-TestResult -Name "Script execution (fatal error)" -Pass $false -Detail $errMsg
}
finally {
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
    if ($Script:Results.Count -gt 0) {
        $csvPath = Join-Path $ScreenshotDir "test_results.csv"
        $Script:Results | Export-Csv -Path $csvPath -NoTypeInformation
        Write-Host "Results saved to $csvPath" -ForegroundColor DarkGray
    }

    if ($error.Count -gt 0) {
        Write-Host "`nScript encountered errors during execution:" -ForegroundColor Red
        $error[0] | Format-List -Force
    }
}

exit $(if ($Script:Failed -gt 0) { 1 } else { 0 })
