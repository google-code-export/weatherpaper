;NSIS Modern User Interface
;Welcome/Finish Page Example Script
;Written by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  ;Name and file
  Name "WeatherPaper"
  OutFile "WeatherInstall.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\WeatherPaper"

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !insertmacro MUI_PAGE_WELCOME
  #!insertmacro MUI_PAGE_LICENSE "${NSISDIR}\Docs\Modern UI\License.txt"
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_PAGE_FINISH

  !insertmacro MUI_UNPAGE_WELCOME
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !insertmacro MUI_UNPAGE_FINISH

;--------------------------------
;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "WeatherPaper" SecDummy

  SetOutPath "$INSTDIR"
  ;ADD YOUR OWN FILES HERE...
  File weatherpaper.exe
  
  SetOutPath "$APPDATA\WeatherPaper\"
  File settings.cfg
  File tango.zip
  
  ;Add shortcut to the startup folder
  CreateShortCut "$SMSTARTUP\WeatherPaper.lnk" "$INSTDIR\Weatherpaper.exe"

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ;Add entry to Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WeatherPaper" "DisplayName"\
  "WeatherPaper (remove only)"

  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WeatherPaper" "UninstallString" \
  "$INSTDIR\Uninstall.exe"

SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecDummy ${LANG_ENGLISH} "A test section."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDummy} $(DESC_SecDummy)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;ADD YOUR OWN FILES HERE...
  
  Delete "$INSTDIR\Uninstall.exe"
  
  RMDir /r "$INSTDIR"
  RMDir /r "$APPDATA\WeatherPaper\"
  
  ;Remove shortcut from the startup folder
  delete "$SMSTARTUP\WeatherPaper.lnk"
  
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WeatherPaper"

SectionEnd
