# AI 데이터 표준 조합 규칙

## 명명

- 컬럼명은 영문 소문자 `snake_case`를 사용한다.
- 업무 개념은 단수형을 우선한다. 예: `driver`, `lap`, `stint`.
- 식별자는 개념명 뒤에 `_key`를 붙인다. 예: `session_key`, `meeting_key`.
- 순번은 개념명 뒤에 `_number`를 붙인다. 예: `lap_number`, `stint_number`.
- 시작·종료 경계는 `_start`, `_end`를 붙인다. 예: `lap_start`, `lap_end`.
- 시간 길이는 `_duration`, 시각은 `date` 또는 `date_start`/`date_end`를 사용한다.

## 식별자와 관계

- 기본 세션 연결 키는 `session_key`이다.
- `meeting_key`는 `session_key`와 다른 개념이므로 대체 키로 사용하지 않는다.
- 드라이버 관련 연결은 `session_key + driver_number` 복합키를 사용한다.
- 랩 식별 후보는 `session_key + driver_number + lap_number`이다.
- 스틴트 식별 후보는 `session_key + driver_number + stint_number`이다.
- `drivers`, `laps`, `stints`, `pit`은 `sessions.session_key`로 장소·세션 정보를 결합한다.

## 데이터 타입과 값

- 원본 식별자와 코드값은 문자열로 보존한다.
- 계산 시에만 정수·실수로 변환하며, 변환 실패값은 임의로 0으로 바꾸지 않는다.
- 날짜시간은 UTC 오프셋을 포함한 ISO 8601 문자열을 권장한다.
- `segments_sector_1~3`은 목록 형태 원문을 보존하며 표준 JSON으로 강제 변환하지 않는다.
- 결측 타이어 컴파운드는 `UNKNOWN`으로 표시한다.
- `lap_end < lap_start`는 오류이며, 스틴트 겹침은 `next.lap_start < previous.lap_end`일 때 검출한다.
- `lap_duration > 300`초와 `pit_duration > 180`초는 자동 삭제하지 않고 검토 이슈로 기록한다.

## 복구 관리 컬럼

복구 결과에는 `original_*`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`을 유지한다. 원본값은 덮어쓰지 않으며, 추정값은 직접 조인값과 구분한다.

## 오염코드 적용 규칙

- 하나의 결함은 `diagnostic_code` 하나로 기록하고, 한 행에 여러 결함이 있으면 진단 상세 테이블에 별도 행으로 기록한다.
- `MISSING_*`는 결측 자체를 의미하며, 복구 성공 여부는 `diagnostic_status`로 분리한다.
- `LONG_*`, `INVALID_*`, `OVERLAPPING_*`은 자동으로 정상값으로 바꾸지 않고 검토 이슈로 남긴다.
- `DQ001` 국가 코드 결측은 같은 드라이버(`full_name`)의 다른 세션 국가 코드로 복구한다. 세션(개최국) 국가 코드는 드라이버 국적이 아니므로 사용하지 않는다.
- 통계값(중앙값 등)으로 결측을 채우지 않는다(F1_P2_Spec.md 5.1). `DQ003` 속도 결측은 원천 결측으로 허용하고, `DQ004` 섹터 결측은 1개만 비었을 때 `랩타임 - 나머지 두 섹터`로 역산한다.
- 진단 결과에는 `error_type`(MISSING·INVALID·OUTLIER·INCONSISTENT·SWAP·SCHEMA·TYPE·REFERENTIAL·DUPLICATE·OVERLAP), `severity`, `action`(AUTO_FIX·REVIEW·ACCEPT·QUARANTINE), `status`를 함께 기록한다.
- `DQ008` 컴파운드 결측은 실제 타이어 종류를 추정하지 않고 `UNKNOWN`으로 표시한다.
- `DQ010`은 `lap_end < lap_start`, `DQ011`은 `next lap_start < previous lap_end`일 때 발생한다. `lap_end = lap_start - 1`인 빈 스틴트는 원천 특성으로 `ACCEPTED` 처리한다.
- 진단 상태는 `OPEN`(미처리), `REPAIRED`(복구 완료), `ACCEPTED`(오염을 업무상 허용), `WAIVED`(검토 후 제외)로 통제한다.
