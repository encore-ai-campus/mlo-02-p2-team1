@echo off
REM 같은 네트워크의 다른 PC에서도 접속 가능하게 실행 (0.0.0.0:8000)
REM 접속 주소: http://이PC의IP:8000  (이 PC의 IP는 명령 프롬프트에서 ipconfig로 확인)
REM 허용 IP는 .env 의 DJANGO_ALLOWED_HOSTS 에 있어야 합니다.
cd /d "%~dp0"
echo 이 PC에서:   http://127.0.0.1:8000      종료는 Ctrl+C
REM 추가 데이터 5종(data/01_raw/f1_extra_data.zip)이 아직 안 풀려 있으면 압축 해제. 실패해도 웹은 실행
venv\Scripts\python.exe -m pipeline.extra_data
if errorlevel 1 echo [경고] 추가 데이터 압축 해제 실패 - 위 사유 확인. SQL 적재(sql/02)에 필요하며 웹 화면은 그대로 실행합니다.
venv\Scripts\python.exe web\manage.py runserver 0.0.0.0:8000
