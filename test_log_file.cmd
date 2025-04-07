@echo off
chcp 65001
REM Test script to verify log file configuration works

if not exist ".\output" mkdir ".\output"

REM Get log file name from config using helper script
for /f "tokens=*" %%a in ('python get_log_filename.py config-3.0-Haiku.json') do (
    set LOG_FILE=%%a
)

echo Using log file: .\output\%LOG_FILE%

echo. >> ".\output\%LOG_FILE%"
echo %date% %time% >> ".\output\%LOG_FILE%"
echo ------------------- >> ".\output\%LOG_FILE%"
echo This is a test entry to verify the log file configuration works. >> ".\output\%LOG_FILE%"
echo ------------------- >> ".\output\%LOG_FILE%"

echo Test completed. Check .\output\%LOG_FILE% to verify the log entry.
