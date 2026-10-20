@echo off
setlocal
title Repack Extractor (FitGirl / DODI)

:: If double-clicked without dropping a file, open the GUI window
if "%~1"=="" (
    echo [i] No file dropped. Opening GUI...
    start "" py "%~dp0repack_extractor.py"
    exit /b
)

:: A file was dragged & dropped onto this batch file
echo =======================================================
echo       Repack Extractor - Drag and Drop (FitGirl / DODI)
echo =======================================================
echo.
echo [*] Dropped File: "%~1"
echo.

py "%~dp0repack_extractor.py" "%~1"

echo.
echo =======================================================
echo  Finished.
echo =======================================================
echo.
pause
