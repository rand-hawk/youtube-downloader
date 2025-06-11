
[Setup]
AppName=YouTube Downloader
AppVersion=1.0
AppPublisher=YouTube Downloader
DefaultDirName=C:\YouTube Downloader
DefaultGroupName=YouTube Downloader
OutputDir=installer
OutputBaseFilename=youtube-downloader-installer
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
Name: "{app}"; Permissions: users-full
Name: "{app}\ffmpeg"; Permissions: users-full

[Files]
Source: "dist\youtube-downloader-v1.0\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "youtube-downloader.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "youtube-downloader-icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\ffmpeg.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "ffmpeg\ffprobe.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion

[Icons]
Name: "{group}\YouTube Downloader"; Filename: "{app}\youtube-downloader-v1.0.exe"; WorkingDir: "{app}"; IconFilename: "{app}\youtube-downloader.ico"
Name: "{commondesktop}\YouTube Downloader"; Filename: "{app}\youtube-downloader-v1.0.exe"; WorkingDir: "{app}"; IconFilename: "{app}\youtube-downloader.ico"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\YouTubeDownloader"; ValueType: string; ValueName: "DisplayName"; ValueData: "YouTube Downloader"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\YouTubeDownloader"; ValueType: string; ValueName: "UninstallString"; ValueData: "{uninstallexe}"

[Run]
Filename: "{app}\youtube-downloader-v1.0.exe"; Description: "{cm:LaunchProgram,YouTube Downloader}"; Flags: nowait postinstall skipifsilent
