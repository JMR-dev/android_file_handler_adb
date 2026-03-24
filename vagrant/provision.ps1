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

# --- Allow script execution (required for test suite) ---
# Write the LocalMachine execution policy directly via the registry instead of using
# Set-ExecutionPolicy.  Vagrant runs provision.ps1 under "powershell -ExecutionPolicy Bypass",
# which sets a Process-scope policy.  When a Process-scope policy is active,
# Set-ExecutionPolicy -Scope LocalMachine throws a terminating SecurityException
# ("overridden by a policy defined at a more specific scope") that cannot be suppressed
# with -ErrorAction.  Writing the registry key bypasses that cmdlet restriction entirely.
# The value takes effect in all subsequent WinRM PSSessions (which have no Process-scope
# override) — exactly the sessions that run the test suite.
$psMachinePolicyPath = 'HKLM:\SOFTWARE\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell'
Set-ItemProperty -Path $psMachinePolicyPath -Name 'ExecutionPolicy' -Value 'Unrestricted' -Force
Write-Host "  Execution policy set to Unrestricted (LocalMachine)." -ForegroundColor DarkGray

# --- Install Chocolatey (package manager) ---
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# --- Configure HTTPS WinRM listener ---
# HTTP WinRM (plaintext) causes PowerShell PSSession to reject unencrypted
# traffic. A self-signed cert on port 5986 satisfies WinRM's security policy
# without needing a domain CA. The 10-year expiry covers long-lived test boxes.
Write-Host "Configuring HTTPS WinRM listener..." -ForegroundColor Yellow

# Ensure network is Private so WinRM HTTPS works correctly
Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private

# Allow local accounts to perform administrative tasks via WinRM
# (Required for the 'vagrant' user to have full admin rights over PSSession)
$policyPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
Set-ItemProperty -Path $policyPath -Name LocalAccountTokenFilterPolicy -Value 1 -Force

# Create certificate for HTTPS listener
$cert = New-SelfSignedCertificate `
    -DnsName "afh-test", "localhost" `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -NotAfter (Get-Date).AddYears(10)

# Check if an HTTPS listener already exists
$listeners = winrm enumerate winrm/config/listener
$hasHttps = $listeners -match "Transport = HTTPS"

if ($hasHttps) {
    # If the thumbprint matches, we're already good
    if ($listeners -match $cert.Thumbprint) {
        Write-Host "  HTTPS listener already correctly configured." -ForegroundColor Green
    } else {
        Write-Host "  Updating existing HTTPS listener with new certificate..." -ForegroundColor Gray
        winrm delete winrm/config/Listener?Address=*+Transport=HTTPS
        winrm create winrm/config/Listener?Address=*+Transport=HTTPS `
            "@{Hostname=`"afh-test`";CertificateThumbprint=`"$($cert.Thumbprint)`"}"
    }
} else {
    Write-Host "  Creating new HTTPS listener..." -ForegroundColor Gray
    winrm create winrm/config/Listener?Address=*+Transport=HTTPS `
        "@{Hostname=`"afh-test`";CertificateThumbprint=`"$($cert.Thumbprint)`"}"
}

winrm set winrm/config/service/Auth '@{Basic="true"}'

netsh advfirewall firewall add rule `
    name="WinRM HTTPS" protocol=TCP dir=in localport=5986 action=allow profile=any | Out-Null

Write-Host "  HTTPS WinRM listener ready on port 5986" -ForegroundColor Green

# --- Install nircmd for screenshot capture ---
Write-Host "Installing nircmd for screenshot capture..." -ForegroundColor Yellow
choco install nircmd -y --no-progress

# --- Install Inno Setup 6.7.1 (pinned) ---
Write-Host "Installing Inno Setup 6.7.1..." -ForegroundColor Yellow
choco install innosetup --version 6.7.1 -y --no-progress

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "=== Provisioning complete ===" -ForegroundColor Green
