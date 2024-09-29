REM Copy the config.json file, add the different models, and batch process them like this.
REM If you are gathering performance metrics to see which model works best, ensure the 
REM OnlyGatherMetrics key is set to true in each json file you process.
python main.py config-3.0-Haiku.json
python main.py config-3.0-Opus.json
python main.py config-3.5-Sonnet.json

REM Run this script to compare the results against metrics-groundtruth.csv to see which
REM model most-closely detects SPAM according to your hand-edited groundtruth file. 
print Update your metrics-groundtruth.csv first and then press enter to continue
pause 
cd output
python analyze_metrics.py > metrics_results.txt
cd ..
