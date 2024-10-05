@echo off
REM Copy the config.json file, add the specific model you want, and process nightly like this.
REM Append all console output to ./output/log.txt with a timestamp
if not exist ".\output" mkdir ".\output"
echo. >> ".\output\log.txt"
echo %date% %time% >> ".\output\log.txt"
echo ------------------- >> ".\output\log.txt"
python main.py config-3.0-Haiku.json >> ".\output\log.txt" 2>&1
echo ------------------- >> ".\output\log.txt"