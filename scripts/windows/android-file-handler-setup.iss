; Inno Setup script for Android File Handler
; Compiles a Windows installer from the PyInstaller one-file executable.
;
; Usage (CI):
;   iscc scripts\windows\android-file-handler-setup.iss /DMyAppVersion=1.2.3
;
; Usage (local, from repo root):
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" scripts\windows\android-file-handler-setup.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.1.1"
#endif

#define MyAppName      "Android File Handler"
#define MyAppPublisher "Jason Ross"
#define MyAppURL       "https://github.com/JMR-dev/android-file-handler"
#define MyAppExeName   "android-file-handler-windows.exe"

[Setup]
AppId={{8F2B3A7E-4D1C-4E8F-9A2B-6C7D8E9F0A1B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
; AppVerName controls the registry DisplayName value. Without it Inno Setup
; defaults to "AppName version AppVersion" which breaks exact-name lookups.
; Windows convention: DisplayName = product name, DisplayVersion = version.
AppVerName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=..\..\LICENSE.txt
OutputDir=..\..\dist
OutputBaseFilename=android-file-handler-setup
SetupIconFile=..\..\icon_media\robot_files_256.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/normal
LZMADictionarySize=16384
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
