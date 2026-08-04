[Setup]
AppName=YouTube Downloader
AppVersion=2.2
AppPublisher=YouTube Downloader Team
AppPublisherURL=https://github.com/rand-hawk/youtube-downloader
AppSupportURL=https://github.com/rand-hawk/youtube-downloader/issues
AppUpdatesURL=https://github.com/rand-hawk/youtube-downloader/releases
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
DefaultDirName=C:\YouTube Downloader
DefaultGroupName=YouTube Downloader
OutputDir=installer
OutputBaseFilename=youtube-downloader-installer
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayName=YouTube Downloader v2.2
UninstallDisplayIcon={app}\youtube-downloader.ico
VersionInfoVersion=2.2.0.0
VersionInfoCompany=YouTube Downloader Team
VersionInfoDescription=Professional YouTube Video Downloader with Modern UI
VersionInfoCopyright=Copyright (C) 2025 YouTube Downloader Team

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
Name: "{app}"; Permissions: users-full
Name: "{app}\ffmpeg"; Permissions: users-full

[Files]
Source: "dist\youtube-downloader-v2.2-portable.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "youtube-downloader.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "youtube-downloader-icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\ffmpeg.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "ffmpeg\ffprobe.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion

[Icons]
Name: "{group}\YouTube Downloader"; Filename: "{app}\youtube-downloader-v2.2-portable.exe"; WorkingDir: "{app}"; IconFilename: "{app}\youtube-downloader.ico"
Name: "{commondesktop}\YouTube Downloader"; Filename: "{app}\youtube-downloader-v2.2-portable.exe"; WorkingDir: "{app}"; IconFilename: "{app}\youtube-downloader.ico"; Tasks: desktopicon



[Run]
Filename: "{app}\youtube-downloader-v2.2-portable.exe"; Description: "{cm:LaunchProgram,YouTube Downloader}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: string;
  ConfigContent: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Update config.json with correct FFmpeg path
    ConfigPath := ExpandConstant('{app}\config.json');
    ConfigContent := '{' + #13#10 +
      '    "output_dir": "' + ExpandConstant('{userdocs}') + '\YouTube Downloads",' + #13#10 +
      '    "ffmpeg_path": "' + ExpandConstant('{app}') + '\ffmpeg",' + #13#10 +
      '    "clipboard_monitoring": true,' + #13#10 +
      '    "max_concurrent_downloads": 2,' + #13#10 +
      '    "download_speed_limit": null,' + #13#10 +
      '    "download_queue": []' + #13#10 +
      '}';
    SaveStringToFile(ConfigPath, ConfigContent, False);
  end;
end;