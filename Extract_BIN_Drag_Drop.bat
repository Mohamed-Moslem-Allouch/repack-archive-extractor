@echo off
setlocal
title Repack Archive Extractor (FitGirl / DODI)

:: Locate Python script
set "PY_SCRIPT=%~dp0extract_fitgirl_bin.py"
if not exist "!PY_SCRIPT!" (
    set "PY_SCRIPT=C:\Users\SlouMa\Downloads\extract_fitgirl_bin.py"
)

:: If a file was dragged & dropped, pass it
if not "%~1"=="" (
    py "!PY_SCRIPT!" "%~1"
) else (
    py "!PY_SCRIPT!"
)

echo.
pause
