[Setup]
AppName=NFS Resources Converter
AppVersion={#AppVersion}
DefaultDirName={pf}\NFS Resources Converter
DefaultGroupName=NFS Resources Converter
UninstallDisplayIcon={app}\nfs-resources-converter-{#AppVersion}.exe
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
; .fsh
Root: HKCR; Subkey: ".fsh"; ValueType: string; ValueName: ""; ValueData: "NFSResourcesConverter.fsh"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "NFSResourcesConverter.fsh"; ValueType: string; ValueName: ""; ValueData: "FSH Image File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "NFSResourcesConverter.fsh\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\nfs-resources-converter-{#AppVersion}.exe,0"
Root: HKCR; Subkey: "NFSResourcesConverter.fsh\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\nfs-resources-converter-{#AppVersion}.exe"" ""%1"""

; .fam
Root: HKCR; Subkey: ".fam"; ValueType: string; ValueName: ""; ValueData: "NFSResourcesConverter.fam"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "NFSResourcesConverter.fam"; ValueType: string; ValueName: ""; ValueData: "FAM Archive File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "NFSResourcesConverter.fam\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\nfs-resources-converter-{#AppVersion}.exe,0"
Root: HKCR; Subkey: "NFSResourcesConverter.fam\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\nfs-resources-converter-{#AppVersion}.exe"" ""%1"""

; .qfs
Root: HKCR; Subkey: ".qfs"; ValueType: string; ValueName: ""; ValueData: "NFSResourcesConverter.qfs"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "NFSResourcesConverter.qfs"; ValueType: string; ValueName: ""; ValueData: "QFS Compressed File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "NFSResourcesConverter.qfs\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\nfs-resources-converter-{#AppVersion}.exe,0"
Root: HKCR; Subkey: "NFSResourcesConverter.qfs\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\nfs-resources-converter-{#AppVersion}.exe"" ""%1"""

; .tri
Root: HKCR; Subkey: ".tri"; ValueType: string; ValueName: ""; ValueData: "NFSResourcesConverter.tri"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "NFSResourcesConverter.tri"; ValueType: string; ValueName: ""; ValueData: "TRI Track File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "NFSResourcesConverter.tri\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\nfs-resources-converter-{#AppVersion}.exe,0"
Root: HKCR; Subkey: "NFSResourcesConverter.tri\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\nfs-resources-converter-{#AppVersion}.exe"" ""%1"""
