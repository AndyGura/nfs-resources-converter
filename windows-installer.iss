[Setup]
AppName=NFS Resources Converter
AppVersion={#AppVersion}
DefaultDirName={pf}\NFS Resources Converter
DefaultGroupName=NFS Resources Converter
UninstallDisplayIcon={app}\nfs-resources-converter-{#AppVersion}.exe
SetupIconFile=frontend\dist\gui\favicon.ico
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=nfs-resources-converter-windows-setup-{#AppVersion}
; "ArchitecturesAllowed=x64" specifies that Setup cannot run on
; anything but x64.
ArchitecturesAllowed=x64
; "ArchitecturesInstallIn64BitMode=x64" requests that the install be
; done in "64-bit mode" on x64, meaning it should use the native
; 64-bit Program Files directory and the 64-bit view of the registry.
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\nfs-resources-converter-{#AppVersion}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
; Edge WebView2 Runtime bootstrapper, downloaded by the release workflow. Without the runtime pywebview
; falls back to Internet Explorer 11, which can't run the GUI.
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: not IsWebView2Installed

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Flags: waituntilterminated; Check: not IsWebView2Installed

[Icons]
Name: "{group}\NFS Resources Converter"; Filename: "{app}\nfs-resources-converter-{#AppVersion}.exe"
Name: "{commondesktop}\NFS Resources Converter"; Filename: "{app}\nfs-resources-converter-{#AppVersion}.exe"

[Registry]
; File-type associations are generated from file_associations.py by generate_build_configs.py
#include "windows-installer.filetypes.iss"

[Code]
// Registry keys of the WebView2 Runtime: https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution
function IsWebView2Installed: Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version)
      and (Version <> '') and (Version <> '0.0.0.0'))
    or (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version)
      and (Version <> '') and (Version <> '0.0.0.0'));
end;
