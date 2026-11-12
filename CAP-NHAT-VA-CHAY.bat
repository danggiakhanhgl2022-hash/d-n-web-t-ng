@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Dang cap nhat va khoi dong ung dung...
".venv\Scripts\python.exe" scripts\manage.py update
if errorlevel 1 (
  echo Cap nhat that bai. Xem thong bao phia tren.
  pause
  exit /b 1
)
start "" http://127.0.0.1:3100
echo Da mo http://127.0.0.1:3100
pause
