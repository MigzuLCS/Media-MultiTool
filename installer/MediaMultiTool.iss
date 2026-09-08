; Script do Inno Setup para o Media MultiTool
; Permite gerar um instalador modular no Windows (Setup.exe) com seleção de ferramentas

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

[Types]
Name: "full"; Description: "Instalação Completa (Todos os módulos e ferramentas)"
Name: "compact"; Description: "Instalação Mínima (Apenas núcleo e analisador leve)"
Name: "custom"; Description: "Instalação Personalizada (Escolher ferramentas manualmente)"; Flags: iscustom

[Components]
Name: "core"; Description: "Núcleo do Aplicativo & Configurações (Obrigatório)"; Types: full compact custom; Flags: fixed
Name: "tools"; Description: "Módulos de Ferramentas"; Types: full compact custom
Name: "tools\downloader"; Description: "Download de Mídia (Web & YouTube via yt-dlp)"; Types: full custom
Name: "tools\converter"; Description: "Conversor de Formatos (GIF, MP3, WAV, etc.)"; Types: full custom
Name: "tools\compressor"; Description: "Compressor de Vídeo (Presets Web, Discord, WhatsApp)"; Types: full custom
Name: "tools\trim"; Description: "Corte Rápido (Modo Lossless instantâneo)"; Types: full custom
Name: "tools\analyzer"; Description: "Analisador de Disco (Armazenamento & Duplicados)"; Types: full compact custom
Name: "engine_ffmpeg"; Description: "Motor FFmpeg (~80 MB - Necessário para Conversão/Compressão/Corte)"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copia os arquivos do aplicativo principal (excluindo a pasta bin se houver selecao especifica)
Source: "..\dist\Media MultiTool\*"; DestDir: "{app}"; Excludes: "bin\*,_internal\bin\*"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copia os binarios do FFmpeg quando selecionados pelo usuario (da pasta dist ou da raiz bin do repo)
Source: "..\bin\*"; DestDir: "{app}\bin"; Components: engine_ffmpeg; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\Media MultiTool\bin\*"; DestDir: "{app}\bin"; Components: engine_ffmpeg; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Grava o arquivo modules.json na pasta de instalacao apos a conclusao da copia
procedure CurStepChanged(CurStep: TSetupStep);
var
  JsonContent: String;
  ManifestFile: String;
begin
  if CurStep = ssPostInstall then
  begin
    ManifestFile := ExpandConstant('{app}\modules.json');
    JsonContent := '{' + #13#10 +
                   '  "version": "1.0",' + #13#10 +
                   '  "enabled_modules": [' + #13#10 +
                   '    "settings"';

    if WizardIsComponentSelected('tools\downloader') then
      JsonContent := JsonContent + ',' + #13#10 + '    "youtube"';

    if WizardIsComponentSelected('tools\converter') then
      JsonContent := JsonContent + ',' + #13#10 + '    "convert"';

    if WizardIsComponentSelected('tools\compressor') then
      JsonContent := JsonContent + ',' + #13#10 + '    "compress"';

    if WizardIsComponentSelected('tools\trim') then
      JsonContent := JsonContent + ',' + #13#10 + '    "trim"';

    if WizardIsComponentSelected('tools\analyzer') then
      JsonContent := JsonContent + ',' + #13#10 + '    "disk_analyzer"';

    JsonContent := JsonContent + #13#10 + '  ]' + #13#10 + '}';

    SaveStringToFile(ManifestFile, JsonContent, False);
  end;
end;
