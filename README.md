# F1 오염 데이터 복구 및 품질 검증 파이프라인

F1 경기 데이터 아카이브를 원본 명세서와 비교하고, 결측·오염 데이터를 근거에 따라 복구한 뒤 Django에서 사용할 수 있는 CSV와 HTML 품질 리포트를 생성합니다.

## 입력 데이터

설정한 압축파일은 `00. 데이터_명세서.md`와 `all_years/` 아래의 `sessions.csv`, `drivers.csv`, `laps.csv`, `stints.csv`, `weather.csv`, `pit.csv`를 포함해야 합니다. 원본 CSV는 직접 수정하거나 덮어쓰지 않습니다.

## 설정

`config.example.json`을 복사해 `config.json`을 만들고 경로를 입력합니다.

```json
{
  "input_archive": "D:/data/F1_distribution.압축",
  "output_directory": "D:/data/f1_recovery_output"
}
```

경로는 코드에 하드코딩하지 않습니다.

## 실행

```powershell
python run_pipeline.py --config config.json
```

파이프라인은 명세서 컬럼 구조를 확인하고, `session_key`와 `driver_number`를 기준으로 테이블을 연결합니다. 세션으로 확인 가능한 결측값은 조인으로 복구하고, 랩 수치 결측값은 동일 세션·드라이버 중앙값을 우선 사용합니다. 근거가 부족한 타이어 정보는 `UNKNOWN`으로 표시합니다.

복구 후 자료형·범위·비정상적으로 긴 랩/피트 시간·스틴트 구간을 재검증합니다.

## 출력

`output_directory` 아래에 다음 결과가 생성됩니다.

```text
repaired/{sessions,drivers,laps,stints,weather,pit}.csv
reports/quality_report.html
reports/repair_detail.csv
reports/repair_summary.csv
reports/validation_issues.csv
reports/run_result.json
```

복구 CSV에는 다음 관리 컬럼이 포함됩니다.

- `original_*`: 복구 전 원본값
- `repair_status`: `UNCHANGED` 또는 `REPAIRED`
- `repair_method`: 복구 방법
- `repair_confidence`: `HIGH`, `MEDIUM`, `LOW`
- `repair_reason`: 복구 판단 근거

`quality_report.html`에는 파일별 행·컬럼 검증 결과, 복구 전후 값, 복구 근거, 검증 이슈가 포함됩니다. `validation_issues.csv`와 `reports/*.csv`는 Django 관리자 화면이나 API의 품질 이력 데이터로 사용할 수 있습니다.

## Django 연동

`repaired/*.csv`를 적재 테이블의 원천으로 사용하고 `repair_status`, `repair_confidence`로 원본 유지값·직접 복구값·통계 추정값을 구분할 수 있습니다.

## AI 데이터 표준사전

진단 결과를 반영한 표준사전은 `data/standard_dictionary/`에 있습니다. 표준단어·표준용어·도메인·허용코드·컬럼별 타입과 길이·조합 규칙을 각각 CSV와 Markdown으로 관리합니다.

## 의존성

Pandas를 사용합니다.

```powershell
pip install -r requirements.txt
```

CSV 읽기·결측 복구·그룹별 중앙값 계산·검증 집계는 Pandas DataFrame으로 처리하고, 결과 리포트는 HTML 표와 CSV·JSON 파일로 생성합니다.
