; Script do Inno Setup para o Media MultiTool
; Permite gerar um instalador profissional no Windows (Setup.exe)

#define MyAppName "Media MultiTool"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MigzuLCS"
#define MyAppURL "https://github.com/MigzuLCS/Media-MultiTool"
#define MyAppExeName "Media MultiTool.exe"

[Setup]
AppId={{C8E28B93-14A2-4B17-91A2-D467F5B63189}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Media MultiTool
DisableProgramGroupPage=yes
; Nao exige privilegios de administrador para instalar
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Media-MultiTool-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Media MultiTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
