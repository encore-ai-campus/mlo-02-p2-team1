# F1 AI 데이터 표준사전

진단 결과, 원본 데이터 명세서, `F1_P2_Spec.md`를 기준으로 작성한 표준사전입니다. 원천별 명세는 `../schema/F1_데이터_명세서.md`에 있습니다. 원본 값은 문자열로 보존하고, 계산·검증 시에만 도메인 규칙에 따라 숫자나 날짜시간으로 해석합니다.

## 구성

- `standard_words.csv`: 표준 단어와 정의
- `standard_terms.csv`: 표준 용어, 용어 조합, 식별자 규칙
- `domains.csv`: 데이터 타입, 길이, 단위, 결측 허용, 검증 규칙
- `codes.csv`: 허용 코드와 코드 설명
- `column_dictionary.csv`: 원천 11종(오염 정제 6종 + 신규 5종)의 컬럼별 표준 정의
- `race_points_rules.csv`: 연도별 본경기 기본 배점(1~10위 25-18-15-12-10-8-6-4-2-1, 최속 랩 보너스·Sprint 제외)
- `validation_checks.csv`: 정제 후 검증 항목 VC01~VC71 (`pipeline/validate_cleaned.py`, `sql/03_validate_cleaned.sql` 공용)
- `composition_rules.md`: 표준명명·키·타입·검증 조합 규칙
- `diagnostic_codes.csv`: 진단 결과 기반 오염 코드와 기본 처리 규칙

## 진단 결과 반영

- `country_code`는 국가 코드 도메인으로 관리하며 세션 국가 코드와 드라이버 국가 코드를 구분합니다.
- 랩·피트 시간은 초 단위 실수 도메인으로 관리하고, 비정상 임계값은 삭제가 아니라 검토 이슈로 기록합니다.
- `compound`는 허용 코드 목록을 사용하고 결측은 `UNKNOWN`으로 표시합니다.
- 스틴트는 `session_key + driver_number + stint_number`를 기준으로 관리하며 `lap_end < lap_start`와 실제 구간 중첩을 검증합니다.
- `segments_sector_1~3`은 목록 원문을 보존하며 임의로 JSON으로 변환하지 않습니다.
- 진단 코드는 `DQ001~DQ027`로 관리하고, 결함 종류와 복구 상태를 분리합니다. 각 코드는 오류 유형(`error_type`)과 심각도(`severity`)를 가집니다. `pipeline/recovery.py`가 `diagnostic_codes.csv`를 직접 읽습니다.

## 통합 PDF

CSV와 Markdown 내용을 한 번에 확인하려면 [F1 AI 데이터 표준사전 PDF](./F1_AI_data_standard_dictionary.pdf)를 열어보세요.

## 신규 5종 반영

- 격차(`interval`, `gap_to_leader`)는 초 단위 숫자와 `+N LAP(S)` 문자열이 섞이므로 `GAP_TEXT` 도메인으로 관리합니다.
- `starting_grid.session_key`는 Qualifying 키이며 Race 키와 직접 JOIN하지 않습니다(`qualifying_session_key`, `race_session_key` 용어).
- 원천 `session_result.points`는 보존만 하고, 분석에는 `race_base_points`(본경기 기본 포인트)를 씁니다.
