@echo off
REM F1 Data 조회 화면 실행 (더블클릭 또는 터미널에서 run_web.bat)
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo [오류] venv가 없습니다. 먼저: python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
echo 브라우저에서 http://127.0.0.1:8000 을 여세요. 종료는 Ctrl+C
REM 추가 데이터 5종(data/01_raw/f1_extra_data.zip)이 아직 안 풀려 있으면 압축 해제. 실패해도 웹은 실행
venv\Scripts\python.exe -m pipeline.extra_data
if errorlevel 1 echo [경고] 추가 데이터 압축 해제 실패 - 위 사유 확인. SQL 적재(sql/02)에 필요하며 웹 화면은 그대로 실행합니다.
venv\Scripts\python.exe web\manage.py runserver 127.0.0.1:8000
