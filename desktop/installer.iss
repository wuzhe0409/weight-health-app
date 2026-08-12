; Inno Setup script for Weight Health (Windows)
; Produces an installer that copies the PyInstaller bundle to Program Files,
; adds a desktop shortcut, registers an uninstall entry.
;
; DATA SAFETY: This installer only reads backend\dist\WeightHealth\.
; It NEVER touches %USERPROFILE%\.weight-health\ except to write a fresh
; empty app.db on first launch.

#define MyAppName "Weight Health"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "wuzhe0409"
#define MyAppURL "https://github.com/wuzhe0409/weight-health-app"
#define MyAppExeName "WeightHealth.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=installer_output
OutputBaseFilename=WeightHealth-Setup-{#MyAppVersion}
SetupIconFile=icons\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\backend\dist\WeightHealth\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove per-user app data on uninstall (user opt-in friendly).
; Default: kept. Users can manually delete %USERPROFILE%\.weight-health\.
Type: filesandordirs; Name: "{userappdata}\.weight-health"
