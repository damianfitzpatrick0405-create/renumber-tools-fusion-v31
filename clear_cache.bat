@echo off
echo Clearing Fusion 360 add-in Python cache...

set ADDIN_PATH=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\renumber-tools-fusion

if not exist "%ADDIN_PATH%" (
    echo Add-in folder not found at: %ADDIN_PATH%
    pause
    exit /b 1
)

:: Delete all .pyc compiled cache files
for /r "%ADDIN_PATH%" %%f in (*.pyc) do del /f /q "%%f"

:: Delete all __pycache__ folders
for /d /r "%ADDIN_PATH%" %%d in (__pycache__) do rd /s /q "%%d"

echo Done! Now:
echo  1. Stop the add-in in Fusion (Utilities ^> ADD-INS ^> Stop)
echo  2. Copy the new files into: %ADDIN_PATH%
echo  3. Run the add-in again
pause
