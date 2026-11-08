; Script for the DocInBox Windows x64 installer.
; Build the application first with:
;   python -m PyInstaller --noconfirm DocInBox.spec
; Then compile this script with Inno Setup Compiler (ISCC.exe).

#define AppName "DocInBox"
#define AppVersion "1.0.0"
#define AppExeName "DocInBox.exe"

[Setup]
AppId={{67728158-593a-51f4-b936-123dc1f0bbd4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=DocInBox
AppComments=Recepcion y administracion de documentos en red local.
DefaultDirName={autopf}\DocInBox
DisableDirPage=yes
DefaultGroupName=DocInBox
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=assets\icon.ico
OutputDir=Output
OutputBaseFilename=DocInBox_Setup_{#AppVersion}
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
MinVersion=10.0
WizardStyle=modern
Compression=lzma2/fast
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
RestartApplications=no
Uninstallable=yes
VersionInfoVersion=1.0.0.0
VersionInfoCompany=DocInBox
VersionInfoDescription=DocInBox Setup
VersionInfoProductName=DocInBox
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; Solo se instala el bundle generado por PyInstaller. No se incluyen fuentes,
; pruebas, .git, entornos virtuales, caches ni archivos temporales.
Source: "dist\DocInBox\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\DocInBox"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\DocInBox"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Description: "Iniciar DocInBox"; Flags: postinstall nowait skipifsilent runasoriginaluser

; El desinstalador elimina los binarios instalados, pero no elimina los datos
; del usuario almacenados por la aplicación en %LOCALAPPDATA%\DocInBox.
