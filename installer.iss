; YouTube Indirici - Inno Setup Scripti
; Bu script GitHub Actions tarafından otomatik çalıştırılır.

#define AppName "YouTube Indirici"
#define AppVersion "1.0"
#define AppPublisher "YouTube Indirici"
#define AppExeName "YouTube Indirici.exe"

[Setup]
AppId={{B8F2A3C1-4D5E-4F6A-8B9C-0D1E2F3A4B5C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=setup_output
OutputBaseFilename=YouTube_Indirici_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Masaüstü kısayolu sor
DisableProgramGroupPage=yes
; UAC - yönetici gerektirme (kullanıcı klasörüne kurulum)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek görevler:"; Flags: checkedonce

[Files]
; Tüm PyInstaller çıktısını kopyala
Source: "dist\YouTube Indirici\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Başlat menüsü
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName}'i Kaldır"; Filename: "{uninstallexe}"
; Masaüstü (görev seçildiyse)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Kurulum bittikten sonra uygulamayı başlat (opsiyonel)
Filename: "{app}\{#AppExeName}"; Description: "Uygulamayı şimdi başlat"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
