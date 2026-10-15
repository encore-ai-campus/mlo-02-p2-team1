@echo off
REM 같은 네트워크의 다른 PC에서도 접속 가능하게 실행 (0.0.0.0:8000)
REM 접속 주소: http://이PC의IP:8000  (예: http://192.168.0.100:8000)
REM 허용 IP는 .env 의 DJANGO_ALLOWED_HOSTS 에 있어야 합니다.
cd /d "%~dp0"
echo 다른 PC에서: http://192.168.0.100:8000  또는  http://192.168.0.22:8000
echo 이 PC에서:   http://127.0.0.1:8000      종료는 Ctrl+C
venv\Scripts\python.exe web\manage.py runserver 0.0.0.0:8000
