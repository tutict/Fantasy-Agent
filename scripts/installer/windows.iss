; Inno Setup script for the 灵构工坊 Windows installer.
;
; Compiled by scripts/package_desktop.py, which passes everything it knows in as
; /D defines -- SourceDir, AppVersion, AppName, OutputDir, OutputBase. Nothing
; here is hardcoded, because a second copy of the version string is how an
; installer ends up named after a release that never existed.
;
; This script does not sign anything. Signing belongs in the release workflow
; (see .github/workflows/release.yml), where a certificate and its password can
; be supplied as secrets -- never in a file that lives in the repository.

#ifndef AppVersion
  #error Compile through scripts/package_desktop.py, or pass /DAppVersion=<version>
#endif
#ifndef SourceDir
  #error Compile through scripts/package_desktop.py, or pass /DSourceDir=<path>
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif
#ifndef OutputBase
  #define OutputBase "linggou-studio-setup"
#endif
#ifndef AppName
  #define AppName "灵构工坊"
#endif

[Setup]
; AppId must stay constant across releases or Windows treats each version as a
; separate product and leaves the old one installed.
AppId={{7C1E5F3A-2B4D-4E88-9A61-5D0F3B7E1C42}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Fantasy Agent
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBase}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; The shell writes a WebView2 profile under generated/ and a log under %TEMP%;
; neither needs admin, so the installer should not ask for it either.
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayName={#AppName}

[Languages]
Name: "chinese"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; Flags: unchecked

[Files]
; The payload is copied wholesale; the directory bundle is the thing that was
; tested, so the installer does not selectively re-arrange it.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.bat"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.bat"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.bat"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
