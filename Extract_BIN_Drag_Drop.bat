@echo off
setlocal enabledelayedexpansion
title Repack Archive Extractor (FitGirl / DODI)

:: Locate Python script
set "PY_SCRIPT=%~dp0extract_fitgirl_bin.py"
if not exist "!PY_SCRIPT!" (
    set "PY_SCRIPT=extract_fitgirl_bin.py"
)

:: Prefer 32-bit Python launcher for unarc.dll native compatibility
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py -3-32"
) else (
    set "PY_CMD=python"
)

:: If a file was dragged & dropped, pass it directly
if not "%~1"=="" (
    %PY_CMD% "!PY_SCRIPT!" "%~1"
) else (
    %PY_CMD% "!PY_SCRIPT!"
)

echo.
pause
