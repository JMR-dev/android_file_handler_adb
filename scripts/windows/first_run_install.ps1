param(
    [string]$ExePath = "$PSScriptRoot\..\..\dist\android-file-handler.exe",
    [string]$IconPath = "$PSScriptRoot\..\..\assets\icons\android-file-handler.ico",
    [string]$AppName = "Android File Handler"
)

function Ensure-Elevated {
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        # Relaunch the script with elevation
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "powershell.exe"
        $psi.Arguments = "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
        $psi.Verb = "runas"
        try {
            [System.Diagnostics.Process]::Start($psi) | Out-Null
            Exit 0
        } catch {
            Write-Error "Elevation required to install to Program Files."
            Exit 1
        }
    }
}

Ensure-Elevated

$destDir = Join-Path ${env:ProgramFiles} $AppName
if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }

$resolvedExe = Resolve-Path -Path $ExePath -ErrorAction SilentlyContinue
if (-not $resolvedExe) {
    Write-Error "Application executable not found at $ExePath"
    Exit 1
}

Copy-Item -Path $resolvedExe -Destination (Join-Path $destDir (Split-Path $resolvedExe -Leaf)) -Force

# Create Start Menu shortcut
$programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$appFolder = Join-Path $programs $AppName
if (-not (Test-Path $appFolder)) { New-Item -ItemType Directory -Path $appFolder | Out-Null }

$shortcutPath = Join-Path $appFolder "$AppName.lnk"
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = (Join-Path $destDir (Split-Path $resolvedExe -Leaf))
$sc.WorkingDirectory = $destDir
if (Test-Path $IconPath) { $sc.IconLocation = Resolve-Path $IconPath }
$sc.Save()

Write-Output "Installed $AppName to $destDir and created Start Menu shortcut."
Exit 0
