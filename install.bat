@echo off
REM ============================================================
REM FuturesForged Virtual Office — Windows installer
REM ============================================================
REM Drops vo_client.py into C:\Users\TOM\Desktop\TradingBot\
REM and appends required env vars to its .env (if not already set).
REM
REM Run from inside the unzipped virtual_office folder:
REM     install.bat
REM ============================================================

setlocal enabledelayedexpansion

set "BOT_DIR=C:\Users\TOM\Desktop\TradingBot"
set "SRC=%~dp0client\vo_client.py"
set "DST=%BOT_DIR%\vo_client.py"
set "ENV_FILE=%BOT_DIR%\.env"

echo.
echo ============================================================
echo  FuturesForged Virtual Office installer
echo ============================================================
echo.

if not exist "%BOT_DIR%" (
    echo [ERROR] TradingBot folder not found: %BOT_DIR%
    echo         Edit BOT_DIR at the top of install.bat if needed.
    pause
    exit /b 1
)

if not exist "%SRC%" (
    echo [ERROR] Source not found: %SRC%
    echo         Run this from inside the unzipped virtual_office folder.
    pause
    exit /b 1
)

echo [1/3] Copying vo_client.py to TradingBot folder...
copy /Y "%SRC%" "%DST%" >nul
if errorlevel 1 (
    echo [ERROR] Copy failed. Is the bot running? Stop it and retry.
    pause
    exit /b 1
)
echo       OK -^> %DST%
echo.

echo [2/3] Checking .env for required vars...
if not exist "%ENV_FILE%" (
    echo       .env not found - creating new one.
    type nul > "%ENV_FILE%"
)

call :ensure_env_var SUPABASE_URL          "https://yourproject.supabase.co"
call :ensure_env_var SUPABASE_SERVICE_KEY  "PASTE_SERVICE_ROLE_KEY_HERE"
call :ensure_env_var VO_ENABLED            "1"
echo.

echo [3/3] Done.
echo.
echo ============================================================
echo  Next steps:
echo ============================================================
echo  1. Open %ENV_FILE% and fill in your real Supabase values.
echo  2. Run the Supabase SQL scripts:
echo       - supabase\schema.sql
echo       - supabase\seed_workflow_tree.sql
echo  3. Add the hook lines to bot_engine.py:
echo       import vo_client
echo       vo_client.log_event("bot starting", level="info")
echo     (see HOOK GUIDE at the bottom of vo_client.py for the rest)
echo  4. Push render.yaml + requirements.txt + server/ to GitHub,
echo     then create a Blueprint deployment on Render.
echo  5. Set Render env vars (Supabase + Telegram).
echo ============================================================
echo.
pause
exit /b 0


REM ── helper: append VAR=DEFAULT to .env if VAR is not already present ──
:ensure_env_var
set "VAR=%~1"
set "DEFAULT=%~2"
findstr /B /C:"%VAR%=" "%ENV_FILE%" >nul 2>&1
if errorlevel 1 (
    echo %VAR%=%DEFAULT%>>"%ENV_FILE%"
    echo       Added %VAR% to .env  (placeholder - update it!)
) else (
    echo       %VAR% already in .env - leaving as is.
)
exit /b 0
