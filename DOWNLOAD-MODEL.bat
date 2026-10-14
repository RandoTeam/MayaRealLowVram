@echo off
rem =========================================================================
rem MayaRealLowVram - Скрипт загрузки модели GLM-5.3-Flash
rem =========================================================================
setlocal
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

rem Если аргументы не переданы, выводим подсказку и запускаем интерактивно
if "%~1"=="" (
    echo.
    echo =========================================================================
    echo  MayaRealLowVram: Менеджер загрузки модели GLM-5.3-Flash
    echo =========================================================================
    echo  [1] Проверить доступность ссылок и место на диске (Dry-Run, безопасно)
    echo  [2] Скачать рекомендуемую модель Maya-S24 (~95 GB) + DFlash2 драфтер (~0.7 GB)
    echo  [3] Скачать рекомендуемую модель Maya-S24 (~95 GB) без драфтера
    echo  [4] Скачать базовую модель Maya-S-v2 (~96 GB)
    echo  [5] Проверить целостность (SHA256) уже скачанных файлов
    echo  [6] Выход
    echo =========================================================================
    set /p CHOICE=" Выберите действие [1-6]: "
    
    if "%CHOICE%"=="1" goto dryrun
    if "%CHOICE%"=="2" goto download_s24_dflash
    if "%CHOICE%"=="3" goto download_s24
    if "%CHOICE%"=="4" goto download_s
    if "%CHOICE%"=="5" goto verify
    if "%CHOICE%"=="6" goto exit
    goto exit

    :dryrun
    %PY% download_model.py --model Maya-S24 --with-dflash --dry-run
    pause
    goto exit

    :download_s24_dflash
    %PY% download_model.py --model Maya-S24 --with-dflash
    pause
    goto exit

    :download_s24
    %PY% download_model.py --model Maya-S24
    pause
    goto exit

    :download_s
    %PY% download_model.py --model Maya-S-v2-IQ2_XXS
    pause
    goto exit

    :verify
    %PY% download_model.py --model Maya-S24 --verify-checksums
    pause
    goto exit

    :exit
    exit /b 0
)

rem Если аргументы переданы через командную строку (например: DOWNLOAD-MODEL.bat --dry-run)
%PY% download_model.py %*
if errorlevel 1 pause
exit /b %errorlevel%
