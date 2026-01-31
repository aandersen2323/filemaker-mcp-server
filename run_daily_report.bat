@echo off
REM FileMaker Daily Report - Run via Task Scheduler
REM This script auto-opens FileMaker and generates reports

echo ========================================
echo FileMaker Daily Report
echo %date% %time%
echo ========================================

cd /d "C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test"

"C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test\venv32\Scripts\python.exe" "C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test\run_reports.py"

echo.
echo Report completed at %time%
echo ========================================
