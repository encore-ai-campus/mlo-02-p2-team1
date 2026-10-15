@echo off
REM F1 Data 조회 화면 실행 (더블클릭 또는 터미널에서 run_web.bat)
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo [오류] venv가 없습니다. 먼저: python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
echo 브라우저에서 http://127.0.0.1:8000 을 여세요. 종료는 Ctrl+C
venv\Scripts\python.exe web\manage.py runserver 127.0.0.1:8000
