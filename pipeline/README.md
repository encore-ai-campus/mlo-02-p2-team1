# pipeline — F1 오염 데이터 검증·복구 패키지

프로젝트 개요와 진행 현황은 [저장소 README](../README.md)에 있습니다. 이 문서는 정제·검증 패키지의 실행 안내입니다.

F1 경기 데이터 배포본(CSV 6종)을 데이터 명세서와 비교하고, 진단코드(DQ001~DQ027)별로 오염을 탐지·복구·격리한 뒤 복구 CSV와 품질 리포트를 생성합니다. 원본 CSV는 수정하지 않습니다. 기준 문서는 [`F1_P2_Spec.md`](../F1_P2_Spec.md) 5.1절(Silver 정제 규칙)과 11장(품질 검수 체크리스트)입니다. 정제 결과와 미오염 추가 데이터 5종(`data/01_raw/f1_extra_data`)을 함께 검증하고 MySQL에 적재하는 SQL도 포함합니다.

## 입력 데이터

`data/01_raw/F1_distribution.zip`(풀린 폴더) 또는 같은 구성의 zip을 입력으로 씁니다. `all_years/` 아래 `sessions.csv`, `drivers.csv`, `laps.csv`, `stints.csv`, `weather.csv`, `pit.csv`가 있어야 하며, `SHA256SUMS.txt`와 `00. 데이터_명세서.md`가 있으면 체크섬·행 수·컬럼 순서를 함께 검증합니다.

## 설정

`pipeline/config.json`에 경로를 입력합니다. 상대 경로는 저장소 루트 기준입니다. `input_path`는 폴더와 zip 모두 받습니다(이전 키 `input_archive`도 동작).

```json
{
  "input_path": "data/01_raw/F1_distribution.zip",
  "output_directory": "data/03_cleaned"
}
```

## 실행

```powershell
python -m pipeline.recovery                       # 기본 설정 pipeline/config.json
python -m unittest discover -s tests -v   # 결과·리포트 로직 검증 (약 1~2분)
```

## 처리 원칙

- 모든 값을 문자열로 읽고, 검사할 때만 숫자·일시로 해석합니다.
- 근거가 있는 규칙으로만 복구합니다. 중앙값 같은 통계값으로 결측을 채우지 않습니다(F1_P2_Spec.md 5.1).
- 원천 특성으로 판단되는 항목(1랩 랩타임·시작 시각 결측, 속도 결측, 빈 스틴트 등)은 `ACCEPTED`로 남깁니다.
- 근거가 부족한 결함은 `OPEN`(검토)으로, 분석을 왜곡하는 미해결 결함은 `quarantine/`으로 격리합니다.
- 복구 후 같은 규칙으로 다시 검사해 잔여 건수(`residual_after_repair`)를 리포트에 남깁니다.

주요 탐지·복구 규칙

| 코드 | 내용 | 조치 |
|---|---|---|
| DQ015 | 파일 간 `meeting_key` 불일치 | 하위 5개 파일 합의값으로 sessions 복구 |
| DQ016 | 드라이버 신원(이름·약어) 행 간 뒤바뀜 | 시즌 차량번호 합의값으로 교환 |
| DQ017 | 소속팀 뒤바뀜 | 앞뒤 세션 소속팀 + 팀 색상 근거로 복구 |
| DQ001 | 국가 코드 결측 | 같은 드라이버의 다른 세션 값 |
| DQ019 | 랩 시작 시각 불일치(인접 랩 교환 등) | 인접 교환 또는 앞뒤 랩 기준 복구 |
| DQ002·DQ018·DQ004 | 시작 시각·랩타임·섹터 결측 | 다음 랩 시각, 섹터 역산으로 복구 |
| DQ021 | `lane_duration`≠`pit_duration` | 격리 |
| DQ023 | 노면온도 단일 튐값 | 앞뒤 측정 평균 |

전체 목록과 오류 유형·심각도는 `data/02_reference/standard_dictionary/diagnostic_codes.csv`에 있고, 파이프라인이 이 파일을 직접 읽습니다.

## 출력

```text
repaired/{sessions,drivers,laps,stints,weather,pit}.csv   전체 행 + 관리 컬럼
quarantine/{...}.csv                                      격리 대상 행
reports/bronze_manifest.csv   파일별 SHA256·행·열·명세서 일치 여부
reports/validation_issues.csv 진단 이슈 전체 (코드·오류유형·심각도·조치·상태·근거)
reports/repair_detail.csv     값 변경 이력 (issue_id로 이슈와 연결)
reports/dq_summary.csv        파일×진단코드별 탐지/복구/허용/미해결/격리/잔여
reports/repair_summary.csv    파일별 요약
reports/quality_report.md     위 내용을 묶은 리포트 (GitHub에서 표로 보임, 샘플 축약)
reports/quality_report.html   같은 리포트의 HTML판 (전체 샘플)
reports/run_result.json       실행 요약 (run_id는 입력 체크섬+버전 기반, 재실행 시 동일)
```

복구 CSV 관리 컬럼: `original_*`, `repair_status`, `repair_method`(코드:컬럼 목록), `repair_confidence`(행 내 최저), `repair_reason`, `dq_codes`, `quarantine_flag`.

## 정제 후 검증

파이프라인 실행 뒤 정제 결과와 추가 데이터 5종을 결측·중복·참조·범위·정합성·포인트·대사·JOIN 행 증폭 기준으로 검사합니다. 검사 정의는 `data/02_reference/standard_dictionary/validation_checks.csv`(VC01~VC71)이고 pandas와 SQL이 같은 ID·규칙을 씁니다.

```powershell
python -m pipeline.validate_cleaned               # 기본: data/03_cleaned + data/01_raw/f1_extra_data(없으면 zip)
python -m pipeline.validate_cleaned --extra data/01_raw/f1_extra_data.zip
```

출력은 `data/04_reports/validation/`의 `validation_report.html`(첫 표가 행 수 대사: 원본 = 원본 유지 + 복구 + 격리 + 제거), `row_reconciliation.csv`, `validation_result.csv`, `validation_samples.csv`, `null_profile.csv`, `validation_report.md`입니다. ERROR 등급 위반이 있으면 종료 코드 1을 반환합니다.

## MySQL 적재 (sql/)

저장소 루트에서 순서대로 실행합니다. `data/01_raw/f1_extra_data.zip`은 먼저 `data/01_raw/f1_extra_data/`로 압축 해제하고, 서버에 `SET GLOBAL local_infile = 1;`이 필요합니다.

```powershell
mysql --local-infile=1 -u <user> -p <db> < sql/01_create_staging.sql   # 문자열 스테이징·기준표 테이블
mysql --local-infile=1 -u <user> -p <db> < sql/02_load_staging.sql     # CSV·리포트·기준표 적재
mysql -u <user> -p <db> < sql/03_validate_cleaned.sql                   # 정제 후 검증 (FAIL 0 확인)
mysql -u <user> -p <db> < sql/04_create_schema.sql                      # TO-BE 정규화 스키마·변환 함수·뷰
mysql -u <user> -p <db> < sql/05_insert_schema.sql                      # 스테이징 → 스키마 INSERT, 행 수 대사
mysql -u <user> -p <db> < sql/06_create_gold_board.sql                  # Decision Board Gold 테이블 (적재: manage.py load_board_gold)
```

`04`에서 변환 함수 생성 권한 오류가 나면 `SET GLOBAL log_bin_trust_function_creators = 1;` 후 다시 실행합니다. 설계 설명은 `data/02_reference/schema/TO_BE_model_design.md`, 원천 11종 명세는 `data/02_reference/schema/F1_데이터_명세서.md`에 있습니다.

## Django 연동

`sql/04_create_schema.sql`로 만든 스키마를 `python manage.py inspectdb`로 모델화하거나 `managed = False` 모델로 연결합니다. `repaired/*.csv`와 추가 데이터 5종이 적재 원천이고, `validation_issues.csv`·`repair_detail.csv`는 `quality_issue`·`repair_detail` 테이블 원천입니다.

## AI 데이터 표준사전

`data/02_reference/standard_dictionary/`에 표준단어·용어·도메인·코드·컬럼사전·진단코드·조합 규칙이 있습니다.

## 의존성

```powershell
pip install -r requirements.txt
```
