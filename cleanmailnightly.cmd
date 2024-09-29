REM @echo off
REM Copy the config.json file, add the specific model you want, and process nightly like this.
REM Redirect all console output to ./output/log.txt
if not exist ".\output" mkdir ".\output"
python main.py config-3.0-Haiku.json > ".\output\log.txt" 2>&1