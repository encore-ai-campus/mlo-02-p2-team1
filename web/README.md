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

## 관리자 계정 (`/ops/`·`/admin/` 로그인)
기본 계정은 없다. 비밀번호를 저장소에 남기지 않도록 **PC마다 각자 한 번 만든다.**

```bash
venv\Scripts\python.exe web\manage.py createsuperuser
```
- 저장소 루트에서 실행. 사용자 이름 → 이메일(비워도 됨) → 비밀번호를 차례로 입력
- 만든 계정으로 http://127.0.0.1:8000/ops/ (파이프라인 관리자)와 http://127.0.0.1:8000/admin/ 에 로그인
- 비밀번호 변경: `venv\Scripts\python.exe web\manage.py changepassword <사용자이름>`
- 다른 사람에게 관리자 권한을 줄 때: `/admin/` → 사용자 → 추가 후 **스태프 권한**(staff status) 체크
- 계정은 `.env`의 DB(`auth_user` 테이블)에 저장되므로 DB를 새로 만들면 다시 생성한다. 계정·비밀번호를 README나 코드에 적지 않는다

## 구성
- 프로젝트 `web/`
- 앱 `dashboard/`: Decision Board 화면
  - `/`: 현재 Decision Board. 화면은 `templates/dashboard/decision_board.html` + `static/dashboard/board/board.{css,js}`, **데이터는 MySQL `gold_board_*` 테이블에서 읽는다** (`dashboard/board_gold.py`)
    - 테이블 생성: `sql/06_create_gold_board.sql` / 적재·검증: `venv\Scripts\python.exe web\manage.py load_board_gold` (적재 후 DB에서 다시 읽어 원천과 값이 같은지 확인)
    - 적재 원천: `snapshot/decision_board.json` (분석 결과 내보내기 파일. 이 수치를 계산한 분석 코드는 저장소에 없어 재계산 대신 결과를 정규화해 적재)
    - 테이블이 없거나 비어 있으면 안내 화면(503)을 보여 준다
  - 화면을 고칠 때는 위 템플릿·정적 파일을 직접 수정한다 (원래 시안 폴더 `audit/`는 반영 후 삭제, git 기록에 남아 있음)
  - `/gold/`: 이전 C 시안. `gold_snapshot`의 최신 Gold를 읽기만 한다
- 앱 `viewer/`: 테이블 목록 → 클릭하면 50행씩 조회
- 앱 `ops/`: 데이터 파이프라인 관리자 (`/ops/`, 같은 서버·같은 포트)
  - 실행: 정제·검증 / DB 적재(sql 01~05) / Gold 갱신(sql 06 → load_board_gold → build_gold) / 전체, 또는 단계 하나. 웹 요청과 분리된 실행기(`manage.py run_pipeline <id>`)가 단계를 순서대로 돌리고 실패하면 멈춘다. 동시에 하나만, 중지 가능
  - 수행 결과: 단계별 상태·소요·종료 코드·마지막 출력, 실시간 로그, 실행 이력 (로그 `outputs/ops_runs/`, git 제외)
  - 오류 분석: 오류 유형·진단코드·파일별 탐지/복구/허용/미해결/격리, 미해결 이슈 샘플, 실패한 실행의 오류 줄
  - 데이터 정합성: pandas·MySQL 검증(VC01~VC71)과 두 결과 비교, 행 수 대사, 적재 대사(스테이징=스키마), 포인트 점검
  - 처음 한 번 관리자 계정 생성: `venv\Scripts\python.exe web\manage.py createsuperuser`
  - mysql 클라이언트는 PATH 또는 MySQL 기본 설치 폴더(`C:\Program Files\MySQL\MySQL Server 버전\bin`)에서 찾고, 다른 위치면 `.env`에 `MYSQL_BIN=` 지정
- Decision Board Gold(`gold_board_*`, 11개 테이블): 06으로 만들고 `load_board_gold`로 채움 — 테이블별 의미는 `sql/06_create_gold_board.sql` 주석
- 이전 시안(`/gold/`)용 Gold: MySQL 데이터가 바뀌면 `venv\Scripts\python.exe web\manage.py build_gold` (약 30초)
  - 결과 테이블: `gold_driver_profile`, `gold_team_profile`, `gold_snapshot`
  - 계산 규칙: `web/dashboard/gold.py` (tools/f1_report 분석 스크립트와 같은 규칙, 원천만 MySQL)
- DB 접속 정보는 저장소 루트 `.env`에서 읽음 (git 제외). 항목: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- MySQL 8.4 로컬, DB 이름·계정은 `.env` 기준 (이 PC: `f1_pipeline`)

## 처음부터 다시 만들 때 (다른 PC)
1. `python -m venv venv` → `venv\Scripts\pip install -r requirements.txt`
2. MySQL root로 DB·계정 생성, `SET PERSIST local_infile = 1;`, `SET PERSIST log_bin_trust_function_creators = 1;`
3. `.env` 작성 (위 항목)
4. 저장소 루트에서 순서대로:
   `sql/01_create_staging.sql` → `sql/02_load_staging.sql` → `sql/03_validate_cleaned.mysql84.sql`
   → `sql/04_create_schema.sql` → `sql/05_insert_schema.sql` (intervals 변환에 약 20분) → `sql/06_create_gold_board.sql`
   - `sql/02b_reload_repair_detail.sql`은 **보정용, 평소에는 실행하지 않음**. 수정 이력(repair_detail.csv, 1,335행)을 스테이징에 다시 넣는 파일이다. 예전 02가 이 CSV(CRLF + 마지막 칸 따옴표)를 `\n` 기준으로 읽어 3행만 들어가던 문제를 보정하려고 만들었는데, 02를 `\r\n`으로 고쳐 지금은 02만으로 전부 들어간다. 예전 방식으로 적재한 DB를 고칠 때만 02 뒤에 실행 (실행해도 무해)
   - `03 ... mysql84`: 원본 03이 MySQL 8.4에서 ERROR 1292(빈 값 CAST, STRICT 모드)·ERROR 1137(TEMPORARY 테이블 중복 참조)로 실패해 수정한 사본
   - 실행 예: `mysql --local-infile=1 -u f1user -p f1_db < sql/01_create_staging.sql`
   - 4번은 `/ops/`의 'DB 적재'(01~05)와 'Gold 갱신'(06)으로 대신 실행할 수 있다
5. `venv\Scripts\python.exe web\manage.py migrate`
6. `venv\Scripts\python.exe web\manage.py load_board_gold` → `venv\Scripts\python.exe web\manage.py build_gold` (또는 `/ops/`의 'Gold 갱신')
7. `venv\Scripts\python.exe web\manage.py createsuperuser` (`/ops/` 로그인용)

## 같은 네트워크의 다른 PC에서 접속
- `run_web_lan.bat` 실행 (0.0.0.0:8000), 접속 주소 `http://이PC의IP:8000`
- `.env`의 `DJANGO_ALLOWED_HOSTS`에 이 PC의 IP를 쉼표로 추가 (예: `192.168.0.100,192.168.0.22`)
- 개발 서버(DEBUG)이므로 내부 네트워크 시연용으로만 사용
