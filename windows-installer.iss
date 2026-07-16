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

[Icons]
Name: "{group}\NFS Resources Converter"; Filename: "{app}\nfs-resources-converter-{#AppVersion}.exe"
Name: "{commondesktop}\NFS Resources Converter"; Filename: "{app}\nfs-resources-converter-{#AppVersion}.exe"

[Registry]
; File-type associations are generated from file_associations.py by generate_build_configs.py
#include "windows-installer.filetypes.iss"
