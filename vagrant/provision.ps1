# provision.ps1 — Vagrant provisioning script for Windows 11 test VM.
# Installs prerequisites needed to test the Android File Handler installer.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== Provisioning Android File Handler test VM ===" -ForegroundColor Cyan

# --- Enable auto-logon so GUI tests work after reboot ---
$RegPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $RegPath -Name AutoAdminLogon -Value "1"
Set-ItemProperty -Path $RegPath -Name DefaultUserName -Value "vagrant"
Set-ItemProperty -Path $RegPath -Name DefaultPassword -Value "vagrant"

# --- Install Chocolatey (package manager) ---
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# --- Install nircmd for screenshot capture ---
Write-Host "Installing nircmd for screenshot capture..." -ForegroundColor Yellow
choco install nircmd -y --no-progress

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "=== Provisioning complete ===" -ForegroundColor Green
