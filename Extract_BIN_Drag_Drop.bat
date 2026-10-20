@echo off
setlocal
title Repack Archive Extractor (FitGirl / DODI)

:: Set python script path
set "PY_SCRIPT=%~dp0extract_fitgirl_bin.py"
if not exist "!PY_SCRIPT!" (
    set "PY_SCRIPT=C:\Users\SlouMa\Downloads\extract_fitgirl_bin.py"
)

:: If double-clicked without dropping a file, launch the UI
if "%~1"=="" (
    start "" py "%PY_SCRIPT%"
    exit /b
)

:: If a file was dragged & dropped, pass it to the Python UI
start "" py "%PY_SCRIPT%" "%~1"
exit /b
