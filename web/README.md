# F1 Data — Django (MySQL 조회 화면)

## 바로 실행
저장소 루트에서 `run_web.bat` 더블클릭 → 브라우저에서
- http://127.0.0.1:8000 — **Decision Board** (현재 디자인 시안, 데이터 스냅샷 기반)
- http://127.0.0.1:8000/gold/ — 이전 C 시안 (Gold 기반)
- http://127.0.0.1:8000/data/ — 적재 테이블 조회
- http://127.0.0.1:8000/ops/ — **데이터 파이프라인 관리자** (staff 계정 로그인 필요)

`run_web.bat`은 서버를 띄우기 전에 `data/f1_extra_data.zip`이 안 풀려 있으면 `data/f1_extra_data/`로 자동 압축 해제한다 (`python -m pipeline.extra_data`). 실패해도(압축 손상·파일 누락·디스크 부족 등) 사유를 출력하고 웹은 그대로 실행한다.

터미널에서 실행하려면:
```bash
venv\Scripts\python.exe web\manage.py runserver 127.0.0.1:8000
```

## 구성
- 프로젝트 `web/`
- 앱 `dashboard/`: Decision Board 화면
  - `/`: 현재 Decision Board 시안. 화면은 `templates/dashboard/decision_board.html` + `static/dashboard/board/board.{css,js}`, 데이터는 `snapshot/decision_board.json`을 그대로 쓴다. DB·Gold 연결은 아직 안 함
  - 화면을 고칠 때는 위 템플릿·정적 파일을 직접 수정한다 (원래 시안 폴더 `audit/`는 반영 후 삭제, git 기록에 남아 있음)
  - `/gold/`: 이전 C 시안. `gold_snapshot`의 최신 Gold를 읽기만 한다
- 앱 `viewer/`: 테이블 목록 → 클릭하면 50행씩 조회
- 앱 `ops/`: 데이터 파이프라인 관리자 (`/ops/`, 같은 서버·같은 포트)
  - 실행: 정제·검증 / DB 적재(sql 01~05) / Gold 갱신 / 전체, 또는 단계 하나. 웹 요청과 분리된 실행기(`manage.py run_pipeline <id>`)가 단계를 순서대로 돌리고 실패하면 멈춘다. 동시에 하나만, 중지 가능
  - 수행 결과: 단계별 상태·소요·종료 코드·마지막 출력, 실시간 로그, 실행 이력 (로그 `outputs/ops_runs/`, git 제외)
  - 오류 분석: 오류 유형·진단코드·파일별 탐지/복구/허용/미해결/격리, 미해결 이슈 샘플, 실패한 실행의 오류 줄
  - 데이터 정합성: pandas·MySQL 검증(VC01~VC71)과 두 결과 비교, 행 수 대사, 적재 대사(스테이징=스키마), 포인트 점검
  - 처음 한 번 관리자 계정 생성: `venv\Scripts\python.exe web\manage.py createsuperuser`
  - mysql 클라이언트는 PATH 또는 `C:\Program Files\MySQL\MySQL Server *in`에서 찾고, 다른 위치면 `.env`에 `MYSQL_BIN=` 지정
- Gold 갱신: MySQL 데이터가 바뀌면 `venv\Scripts\python.exe web\manage.py build_gold` (약 30초)
  - 결과 테이블: `gold_driver_profile`, `gold_team_profile`, `gold_snapshot`
  - 계산 규칙: `web/dashboard/gold.py` (tools/f1_report 분석 스크립트와 같은 규칙, 원천만 MySQL)
- DB 접속 정보는 저장소 루트 `.env`에서 읽음 (git 제외). 항목: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- MySQL 8.4 로컬, DB 이름·계정은 `.env` 기준 (이 PC: `f1_pipeline`)

## 처음부터 다시 만들 때 (다른 PC)
1. `python -m venv venv` → `venv\Scripts\pip install -r requirements.txt`
2. MySQL root로 DB·계정 생성, `SET PERSIST local_infile = 1;`, `SET PERSIST log_bin_trust_function_creators = 1;`
3. `.env` 작성 (위 항목)
4. 저장소 루트에서 순서대로:
   `sql/01_create_staging.sql` → `sql/02_load_staging.sql` → `sql/02b_reload_repair_detail.sql`
   → `sql/03_validate_cleaned.mysql84.sql` → `sql/04_create_schema.sql` → `sql/05_insert_schema.sql` (intervals 변환에 약 20분)
   - `02b`: repair_detail.csv가 CRLF + 마지막 칸 따옴표라 예전 02로는 1,335행 중 3행만 들어갔음 → 02를 `\r\n`으로 고쳐 지금은 선택 실행(스테이징만 재적재, 실행해도 무해)
   - `03 ... mysql84`: 원본 03이 MySQL 8.4에서 ERROR 1292(빈 값 CAST, STRICT 모드)·ERROR 1137(TEMPORARY 테이블 중복 참조)로 실패해 수정한 사본
   - 실행 예: `mysql --local-infile=1 -u f1user -p f1_db < sql/01_create_staging.sql`
   - 4번은 `/ops/`의 'DB 적재'로 대신 실행할 수 있다
5. `venv\Scripts\python.exe web\manage.py migrate`
6. `venv\Scripts\python.exe web\manage.py build_gold` (또는 `/ops/`의 'Gold 갱신')
7. `venv\Scripts\python.exe web\manage.py createsuperuser` (`/ops/` 로그인용)

## 같은 네트워크의 다른 PC에서 접속
- `run_web_lan.bat` 실행 (0.0.0.0:8000), 접속 주소 `http://이PC의IP:8000`
- `.env`의 `DJANGO_ALLOWED_HOSTS`에 이 PC의 IP를 쉼표로 추가 (예: `192.168.0.100,192.168.0.22`)
- 개발 서버(DEBUG)이므로 내부 네트워크 시연용으로만 사용
