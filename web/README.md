# F1 Data — Django (MySQL 조회 화면)

## 바로 실행
저장소 루트에서 `run_web.bat` 더블클릭 → 브라우저에서
- http://127.0.0.1:8000 — **Decision Board** (C 시안, Gold 기반)
- http://127.0.0.1:8000/data/ — 적재 테이블 조회

터미널에서 실행하려면:
```bash
venv\Scripts\python.exe web\manage.py runserver 127.0.0.1:8000
```

## 구성
- 프로젝트 `web/`
- 앱 `dashboard/`: Decision Board 화면. `gold_snapshot`의 최신 Gold를 읽기만 한다
- 앱 `viewer/`: 테이블 목록 → 클릭하면 50행씩 조회
- Gold 갱신: MySQL 데이터가 바뀌면 `venv\Scripts\python.exe web\manage.py build_gold` (약 30초)
  - 결과 테이블: `gold_driver_profile`, `gold_team_profile`, `gold_snapshot`
  - 계산 규칙: `web/dashboard/gold.py` (tools/f1_report 분석 스크립트와 같은 규칙, 원천만 MySQL)
- DB 접속 정보는 저장소 루트 `.env`에서 읽음 (git 제외). 항목: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- MySQL 8.4 로컬, DB `f1_db`, 계정 `f1user`

## 처음부터 다시 만들 때 (다른 PC)
1. `python -m venv venv` → `venv\Scripts\pip install -r requirements.txt`
2. MySQL root로 DB·계정 생성, `SET PERSIST local_infile = 1;`, `SET PERSIST log_bin_trust_function_creators = 1;`
3. `.env` 작성 (위 항목)
4. 저장소 루트에서 순서대로:
   `sql/01_create_staging.sql` → `sql/02_load_staging.sql` → `sql/02b_reload_repair_detail.sql`
   → `sql/03_validate_cleaned.mysql84.sql` → `sql/04_create_schema.sql` → `sql/05_insert_schema.sql` (intervals 변환에 약 20분)
   - `02b`: repair_detail.csv가 CRLF + 마지막 칸 따옴표라 02로는 1,335행 중 3행만 들어감 → 줄 끝 `\r\n`으로 재적재
   - `03 ... mysql84`: 원본 03이 MySQL 8.4에서 ERROR 1292(빈 값 CAST, STRICT 모드)·ERROR 1137(TEMPORARY 테이블 중복 참조)로 실패해 수정한 사본
   - 실행 예: `mysql --local-infile=1 -u f1user -p f1_db < sql/01_create_staging.sql`
5. `venv\Scripts\python.exe web\manage.py migrate`
6. `venv\Scripts\python.exe web\manage.py build_gold`

## 같은 네트워크의 다른 PC에서 접속
- `run_web_lan.bat` 실행 (0.0.0.0:8000), 접속 주소 `http://이PC의IP:8000`
- `.env`의 `DJANGO_ALLOWED_HOSTS`에 이 PC의 IP를 쉼표로 추가 (예: `192.168.0.100,192.168.0.22`)
- 개발 서버(DEBUG)이므로 내부 네트워크 시연용으로만 사용
