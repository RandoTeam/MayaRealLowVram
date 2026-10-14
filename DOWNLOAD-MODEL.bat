@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if not "%~1"=="" (
    "%PY%" download_model.py %*
    exit /b %errorlevel%
)

:menu
cls
echo =========================================================================
echo  MayaRealLowVram - GLM-5.3-Flash Model Download Manager
echo =========================================================================
echo  [1] Dry-Run: Check URLs and disk space without downloading (safe)
echo  [2] Download Maya-S24 (~95 GB) + DFlash2 Drafter (~0.7 GB) [Recommended]
echo  [3] Download Maya-S24 (~95 GB) without drafter
echo  [4] Download Maya-S-v2-IQ2_XXS (~96 GB)
echo  [5] Verify SHA-256 checksums of downloaded files
echo  [6] Exit
echo =========================================================================
set /p CHOICE=" Select option [1-6]: "

if "%CHOICE%"=="1" goto do_dryrun
if "%CHOICE%"=="2" goto do_s24_dflash
if "%CHOICE%"=="3" goto do_s24
if "%CHOICE%"=="4" goto do_s
if "%CHOICE%"=="5" goto do_verify
if "%CHOICE%"=="6" goto do_exit
goto menu

:do_dryrun
"%PY%" download_model.py --model Maya-S24 --with-dflash --dry-run
pause
goto do_exit

:do_s24_dflash
"%PY%" download_model.py --model Maya-S24 --with-dflash
pause
goto do_exit

:do_s24
"%PY%" download_model.py --model Maya-S24
pause
goto do_exit

:do_s
"%PY%" download_model.py --model Maya-S-v2-IQ2_XXS
pause
goto do_exit

:do_verify
"%PY%" download_model.py --model Maya-S24 --verify-checksums
pause
goto do_exit

:do_exit
exit /b 0
