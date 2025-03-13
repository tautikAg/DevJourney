@echo off
REM Cursor Chat History Exporter and Analyzer - Windows Batch File

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is required but not found.
    echo Please install Python and try again.
    exit /b 1
)

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Check if the --analyze flag is present
set ANALYZE=0
set ANALYZE_ARGS=
set EXPORT_ARGS=

:parse_args
if "%~1"=="" goto run_scripts
if /i "%~1"=="--analyze" (
    set ANALYZE=1
    shift
    goto parse_args
)
if /i "%~1"=="--search" (
    set ANALYZE=1
    set "ANALYZE_ARGS=%ANALYZE_ARGS% --search %~2"
    shift
    shift
    goto parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% %~1"
shift
goto parse_args

:run_scripts
REM Run the Python export script with arguments
echo Running Cursor data export...
python "%SCRIPT_DIR%export_cursor_data.py"%EXPORT_ARGS%

REM Check if the script executed successfully
if %ERRORLEVEL% neq 0 (
    echo ❌ Error occurred during export. Please check the output above for details.
    exit /b 1
)

echo ✅ Cursor data export completed successfully!

REM If analyze flag is set, run the analyzer script
if %ANALYZE% equ 1 (
    echo.
    echo Running Cursor data analyzer...
    
    REM Find the most recent export directory
    for /f "tokens=*" %%a in ('dir /b /ad /o-d "%SCRIPT_DIR%cursor_data_export_*" 2^>nul') do (
        set "LATEST_EXPORT=%%a"
        goto found_export
    )
    
    :found_export
    if not defined LATEST_EXPORT (
        echo No export directory found. Please specify a directory to analyze.
        exit /b 1
    )
    
    echo Analyzing: %LATEST_EXPORT%
    python "%SCRIPT_DIR%analyze_cursor_data.py" "%SCRIPT_DIR%%LATEST_EXPORT%"%ANALYZE_ARGS%
    
    if %ERRORLEVEL% equ 0 (
        echo ✅ Cursor data analysis completed successfully!
    ) else (
        echo ❌ Error occurred during analysis. Please check the output above for details.
        exit /b 1
    )
)

echo.
echo All operations completed.
pause 