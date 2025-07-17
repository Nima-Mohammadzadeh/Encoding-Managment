@echo off
echo Creating desktop shortcut for Encoding Manager...

set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=Encoding Manager.lnk
set EXECUTABLE=%SCRIPT_DIR%encoding_manager.exe
set DESKTOP=%USERPROFILE%\Desktop

echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%DESKTOP%\%SHORTCUT_NAME%" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%EXECUTABLE%" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> CreateShortcut.vbs
echo oLink.Description = "Encoding Manager Application" >> CreateShortcut.vbs
echo oLink.IconLocation = "%EXECUTABLE%,0" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo Desktop shortcut created successfully!
echo.
pause 