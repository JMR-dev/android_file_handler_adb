# bootstrap.ps1 — Windows developer environment bootstrapper for Android File Handler
# - Installs Chocolatey (if missing)
# - Installs Vagrant (Chocolatey or direct from HashiCorp)
# - Installs pyenv-win (if missing)
# - Installs Python build dependencies (Chocolatey)
# - Installs zlib from source (https://zlib.net/current/zlib.tar.gz)
# - Installs libffi from GitHub releases (https://github.com/libffi/libffi)
# - Installs latest Python (from pyproject.toml)
# - Sets that Python as global default

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== Android File Handler Windows Dev Bootstrap ===" -ForegroundColor Cyan

# --- Install Chocolatey ---
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# --- Install Vagrant ---
$vagrantInstalled = Get-Command vagrant -ErrorAction SilentlyContinue
if (-not $vagrantInstalled) {
    Write-Host "Installing Vagrant..." -ForegroundColor Yellow
    $chocoAvailable = Get-Command choco -ErrorAction SilentlyContinue
    if ($chocoAvailable) {
        Write-Host "  Installing via Chocolatey..." -ForegroundColor Yellow
        choco install vagrant -y --no-progress
    }
    else {
        Write-Host "  Chocolatey not available — downloading from HashiCorp..." -ForegroundColor Yellow
        $vagrantVersion = "2.4.9"
        $msiUrl = "https://releases.hashicorp.com/vagrant/$vagrantVersion/vagrant_${vagrantVersion}_windows_amd64.msi"
        $msiPath = "$env:TEMP\vagrant_${vagrantVersion}_windows_amd64.msi"
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
        Write-Host "  Downloading $msiUrl ..." -ForegroundColor Yellow
        (New-Object System.Net.WebClient).DownloadFile($msiUrl, $msiPath)
        Write-Host "  Installing MSI..." -ForegroundColor Yellow
        $msiProc = Start-Process -FilePath "msiexec.exe" `
            -ArgumentList "/i", $msiPath, "/qn", "/norestart" `
            -Wait -PassThru
        if ($msiProc.ExitCode -ne 0) {
            Write-Host "ERROR: Vagrant MSI install failed with exit code $($msiProc.ExitCode)" -ForegroundColor Red
            exit 1
        }
        Remove-Item $msiPath -Force -ErrorAction SilentlyContinue
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Host "  Vagrant installed: $(vagrant --version)" -ForegroundColor Green
}
else {
    Write-Host "Vagrant already installed: $(vagrant --version)" -ForegroundColor Green
}

# --- Install pyenv-win ---
$pyenvRoot = "$env:USERPROFILE\.pyenv"
$pyenvBin = "$pyenvRoot\pyenv-win\bin\pyenv.bat"
if (-not (Test-Path $pyenvBin)) {
    Write-Host "Installing pyenv-win..." -ForegroundColor Yellow
    choco install pyenv-win -y --no-progress
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
else {
    Write-Host "pyenv-win already installed." -ForegroundColor Green
}

# --- Install Python build dependencies ---
# Package IDs verified against https://community.chocolatey.org/packages
# zlib has no Chocolatey package; libffi has no Chocolatey package — both omitted
$buildDeps = @('visualcpp-build-tools', 'make', 'openssl.light', 'bzip2', 'SQLite')
$installedPkgs = choco list --no-progress --limit-output 2>&1 |
    Where-Object { $_ -match '\|' } |
    ForEach-Object { ($_ -split '\|')[0].ToLower() }
$toInstall = @($buildDeps | Where-Object { $_.ToLower() -notin $installedPkgs })
if ($toInstall.Count -gt 0) {
    Write-Host "Installing Python build dependencies: $($toInstall -join ', ')..." -ForegroundColor Yellow
    choco install -y --no-progress @toInstall
} else {
    Write-Host "Python build dependencies already installed." -ForegroundColor Green
}


# Shared install root for libraries not on Chocolatey
$devLibsRoot = "$env:USERPROFILE\.devlibs"
New-Item -ItemType Directory -Path $devLibsRoot -Force | Out-Null

# --- Install zlib from source (https://zlib.net/current/zlib.tar.gz) ---
$zlibInstallDir = "$devLibsRoot\zlib"
if (-not (Test-Path "$zlibInstallDir\include\zlib.h")) {
    Write-Host "Installing zlib from source..." -ForegroundColor Yellow

    # Locate MSVC build environment via vswhere
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) {
        Write-Host "ERROR: vswhere.exe not found — Visual Studio Build Tools required to build zlib." -ForegroundColor Red
        exit 1
    }
    $vsPath = (& $vswhere -latest -products * -requires Microsoft.VisualCpp.Tools.HostX86.TargetX64 -property installationPath 2>&1).Trim()
    $vcvarsall = "$vsPath\VC\Auxiliary\Build\vcvarsall.bat"
    if (-not (Test-Path $vcvarsall)) {
        Write-Host "ERROR: vcvarsall.bat not found at $vcvarsall" -ForegroundColor Red
        exit 1
    }

    # Download source tarball
    $zlibTar = "$env:TEMP\zlib.tar.gz"
    Write-Host "  Downloading zlib source..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    (New-Object System.Net.WebClient).DownloadFile('https://zlib.net/current/zlib.tar.gz', $zlibTar)

    # Extract (tar.exe ships with Windows 10 1803+)
    $zlibBuildDir = "$env:TEMP\zlib-build"
    if (Test-Path $zlibBuildDir) { Remove-Item $zlibBuildDir -Recurse -Force }
    New-Item -ItemType Directory -Path $zlibBuildDir | Out-Null
    tar -xzf $zlibTar -C $zlibBuildDir --strip-components=1

    # Build with MSVC nmake via a wrapper cmd script
    Write-Host "  Building zlib with MSVC nmake..." -ForegroundColor Yellow
    $buildCmd = "$env:TEMP\zlib-build.cmd"
    "@echo off`r`ncall `"$vcvarsall`" x64`r`ncd /d `"$zlibBuildDir`"`r`nnmake -f win32\Makefile.msc`r`n" |
        Set-Content $buildCmd -Encoding ASCII
    $proc = Start-Process cmd.exe -ArgumentList "/c `"$buildCmd`"" -Wait -PassThru -NoNewWindow
    Remove-Item $buildCmd -Force -ErrorAction SilentlyContinue
    if ($proc.ExitCode -ne 0) {
        Write-Host "ERROR: zlib build failed (exit $($proc.ExitCode))" -ForegroundColor Red
        exit 1
    }

    # Install headers and libs
    New-Item -ItemType Directory -Path "$zlibInstallDir\include" -Force | Out-Null
    New-Item -ItemType Directory -Path "$zlibInstallDir\lib"     -Force | Out-Null
    New-Item -ItemType Directory -Path "$zlibInstallDir\bin"     -Force | Out-Null
    Copy-Item "$zlibBuildDir\zlib.h"    "$zlibInstallDir\include\"
    Copy-Item "$zlibBuildDir\zconf.h"   "$zlibInstallDir\include\"
    Copy-Item "$zlibBuildDir\zlib.lib"  "$zlibInstallDir\lib\"
    Copy-Item "$zlibBuildDir\zdll.lib"  "$zlibInstallDir\lib\"  -ErrorAction SilentlyContinue
    Copy-Item "$zlibBuildDir\zlib1.dll" "$zlibInstallDir\bin\"  -ErrorAction SilentlyContinue

    # Cleanup
    Remove-Item $zlibTar     -Force          -ErrorAction SilentlyContinue
    Remove-Item $zlibBuildDir -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "zlib installed to $zlibInstallDir" -ForegroundColor Green
} else {
    Write-Host "zlib already installed at $zlibInstallDir" -ForegroundColor Green
}

# Add zlib bin dir to user PATH (persists across sessions; also updates current session)
$zlibBinDir = "$zlibInstallDir\bin"
$userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notmatch [regex]::Escape($zlibBinDir)) {
    [System.Environment]::SetEnvironmentVariable('Path', "$userPath;$zlibBinDir", 'User')
    Write-Host "  Added $zlibBinDir to user PATH" -ForegroundColor Green
}
$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [System.Environment]::GetEnvironmentVariable('Path', 'User')

# --- Install libffi from GitHub releases (https://github.com/libffi/libffi) ---
$libffiInstallDir = "$devLibsRoot\libffi"
if (-not (Test-Path "$libffiInstallDir\include\ffi.h")) {
    Write-Host "Fetching latest libffi release from GitHub..." -ForegroundColor Yellow

    $apiResponse = Invoke-RestMethod `
        -Uri 'https://api.github.com/repos/libffi/libffi/releases/latest' `
        -Headers @{ 'User-Agent' = 'android-file-handler-bootstrap' }
    $libffiTag     = $apiResponse.tag_name          # e.g. "v3.5.2"
    $libffiVersion = $libffiTag -replace '^v', ''   # e.g. "3.5.2"
    Write-Host "  Latest libffi: $libffiTag" -ForegroundColor Yellow

    $zipName     = "libffi-$libffiVersion-x86-64bit-msvc-binaries.zip"
    $downloadUrl = "https://github.com/libffi/libffi/releases/download/$libffiTag/$zipName"
    $zipPath     = "$env:TEMP\$zipName"

    Write-Host "  Downloading $zipName..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    (New-Object System.Net.WebClient).DownloadFile($downloadUrl, $zipPath)

    # Extract — zip contains a single top-level subdirectory
    $extractTemp = "$env:TEMP\libffi-extract"
    if (Test-Path $extractTemp) { Remove-Item $extractTemp -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractTemp -Force

    if (Test-Path $libffiInstallDir) { Remove-Item $libffiInstallDir -Recurse -Force }
    $innerDir = Get-ChildItem $extractTemp -Directory | Select-Object -First 1
    if ($innerDir) {
        Move-Item $innerDir.FullName $libffiInstallDir
    } else {
        # Flat zip — use the extract root directly
        Move-Item $extractTemp $libffiInstallDir
    }

    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    if (Test-Path $extractTemp) { Remove-Item $extractTemp -Recurse -Force -ErrorAction SilentlyContinue }

    Write-Host "libffi $libffiVersion installed to $libffiInstallDir" -ForegroundColor Green
} else {
    Write-Host "libffi already installed at $libffiInstallDir" -ForegroundColor Green
}

# --- Parse Python version from pyproject.toml ---
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"
if (-not (Test-Path $pyprojectPath)) {
    Write-Host "ERROR: pyproject.toml not found at $pyprojectPath" -ForegroundColor Red
    exit 1
}
$pyproject = Get-Content $pyprojectPath -Raw
$pyverMatch = $pyproject | Select-String -Pattern 'requires-python\s*=\s*"([^"]+)"' | ForEach-Object { $_.Matches[0].Groups[1].Value }
if (-not $pyverMatch) {
    Write-Host "ERROR: Could not find requires-python in pyproject.toml" -ForegroundColor Red
    exit 1
}
# Use the highest version in the range (e.g. ">=3.13, <3.15" → 3.14.x)
$pyver = $pyverMatch -replace '[^0-9.,<>= ]', ''
$maxVer = ($pyver -split ',') | Where-Object { $_ -match '<' } | ForEach-Object { $_ -replace '[^0-9.]', '' } | Sort-Object -Descending | Select-Object -First 1
if ($maxVer) {
    $major, $minor = $maxVer -split '\.'
    $targetMinor = [int]$minor - 1
    $targetVer = "$major.$targetMinor.x"
} else {
    $targetVer = $pyver -replace '[^0-9.]', ''
}
Write-Host "Target Python version: $targetVer" -ForegroundColor Cyan

# --- Install and set global Python version ---
$pyenv = "pyenv"
if (-not (Get-Command $pyenv -ErrorAction SilentlyContinue)) {
    $pyenv = "$pyenvBin"
}

$versionPrefix = $targetVer -replace '\.x$', ''
$installedVersions = (& $pyenv versions 2>&1) | Out-String
if ($installedVersions -notmatch [regex]::Escape($versionPrefix)) {
    Write-Host "Installing Python $targetVer via pyenv-win..." -ForegroundColor Yellow
    & $pyenv install $targetVer -q
} else {
    Write-Host "Python $targetVer already installed via pyenv." -ForegroundColor Green
}

$currentGlobal = ((& $pyenv global 2>&1) | Out-String).Trim()
if ($currentGlobal -notmatch [regex]::Escape($versionPrefix)) {
    & $pyenv global $targetVer
    Write-Host "pyenv-win global version set to $targetVer" -ForegroundColor Green
} else {
    Write-Host "pyenv-win global already set to $currentGlobal" -ForegroundColor Green
}

Write-Host "=== Bootstrap complete ===" -ForegroundColor Cyan
