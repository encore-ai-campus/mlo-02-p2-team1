# F1 오염 데이터 복구 프로젝트

오염된 F1 CSV 배포본을 원본 명세서와 관계 규칙에 따라 점검하고, 복구본과 HTML 리포트를 생성합니다.

## 실행

```powershell
python run_pipeline.py --input "C:\Users\Playdata\Downloads\F1_distribution.압축"
```

기본 출력은 `outputs/f1_recovery/`에 생성됩니다.

## 출력

- `repaired/*.csv`: 복구된 CSV
- `reports/repair_summary.csv`: 컬럼별 복구 요약
- `reports/repair_detail.csv`: 행 단위 복구 근거
- `reports/quality_report.html`: Django에 연결 가능한 상세 HTML 리포트

원본값은 `original_*` 컬럼으로 보존하고, 복구값은 원래 컬럼에 기록합니다. 모든 복구에는 `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`을 남깁니다.
