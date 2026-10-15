# F1 오염 데이터 검증·복구 리포트

파이프라인 0.2.0 · 입력 `data\01_raw\F1_distribution.zip` · run_id `3d8d8eebc0fc`  
전체 샘플과 원자료: [quality_report.html](./quality_report.html) (내려받아 브라우저로 열기) · `validation_issues.csv` · `repair_detail.csv`

| 탐지 | 자동 복구 | 허용(원천 특성) | 검토 필요 | 격리 행 |
|---:|---:|---:|---:|---:|
| 28,052 | 1,335 | 24,824 | 1,893 | 2 |

## 1. Bronze 매니페스트

원본 파일이 배포본 그대로인지(체크섬)와 명세서의 행·컬럼 구성과 같은지 확인한다. 판정 컬럼(spec_row_count·schema·column_order·checksum)이 모두 MATCH/OK이면 정상이다.

| file | rows | columns | spec_rows | spec_columns | spec_row_count | schema | column_order | checksum | encoding | bytes |
|---|---|---|---|---|---|---|---|---|---|---|
| sessions.csv | 87 | 15 | 87 | 15 | MATCH | OK | OK | MATCH | utf-8 | 11,673 |
| drivers.csv | 1,771 | 12 | 1,771 | 12 | MATCH | OK | OK | MATCH | utf-8 | 382,185 |
| laps.csv | 97,018 | 16 | 97,018 | 16 | MATCH | OK | OK | MATCH | utf-8 | 23,304,903 |
| stints.csv | 5,040 | 8 | 5,040 | 8 | MATCH | OK | OK | MATCH | utf-8 | 150,297 |
| weather.csv | 13,928 | 10 | 13,928 | 10 | MATCH | OK | OK | MATCH | utf-8 | 1,053,799 |
| pit.csv | 3,029 | 8 | 3,029 | 8 | MATCH | OK | OK | MATCH | utf-8 | 192,135 |

## 2. 파일별 처리 결과

| file | rows | issue_count | repaired_cells | repaired_rows | open_issues | quarantined_rows | status |
|---|---|---|---|---|---|---|---|
| sessions.csv | 87 | 2 | 2 | 2 | 0 | 0 | PASS |
| drivers.csv | 1,771 | 928 | 742 | 724 | 137 | 0 | REVIEW |
| laps.csv | 97,018 | 26,814 | 527 | 525 | 1,523 | 0 | REVIEW |
| stints.csv | 5,040 | 79 | 59 | 36 | 9 | 0 | REVIEW |
| weather.csv | 13,928 | 5 | 5 | 5 | 0 | 0 | PASS |
| pit.csv | 3,029 | 224 | 0 | 0 | 224 | 2 | REVIEW |

## 3. 오류 유형별 집계

| error_type | error_type_korean | detected | repaired | accepted | open | quarantined_rows |
|---|---|---|---|---|---|---|
| INCONSISTENT | 파일 간 불일치 | 2 | 2 | 0 | 0 | 0 |
| INCONSISTENT | 파일 내 불일치 | 22 | 0 | 0 | 22 | 2 |
| INVALID | 값 오류 | 99 | 41 | 11 | 47 | 0 |
| MISSING | 결측 | 27,485 | 1,268 | 24,813 | 1,404 | 0 |
| OUTLIER | 이상치 | 416 | 0 | 0 | 416 | 0 |
| OVERLAP | 구간 중첩 | 3 | 0 | 0 | 3 | 0 |
| REFERENTIAL | 참조 무결성 | 1 | 0 | 0 | 1 | 0 |
| SWAP | 값 뒤바뀜 | 24 | 24 | 0 | 0 | 0 |

## 4. 진단코드별 집계

residual_after_repair: 복구 후 같은 규칙으로 다시 검사했을 때 남은 건수 (= accepted + open 이어야 함)

| file | diagnostic_code | diagnostic_name | korean_name | error_type | error_type_korean | severity | detected | repaired | accepted | open | quarantined_rows | residual_after_repair |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| drivers.csv | DQ001 | MISSING_COUNTRY_CODE | 국가 코드 결측 | MISSING | 결측 | WARNING | 853 | 716 | 0 | 137 | 0 | 137 |
| drivers.csv | DQ016 | DRIVER_IDENTITY_SWAP | 드라이버 신원 뒤바뀜 | SWAP | 값 뒤바뀜 | ERROR | 20 | 20 | 0 | 0 | 0 | 0 |
| drivers.csv | DQ017 | TEAM_NAME_MISMATCH | 소속 팀 불일치 | SWAP | 값 뒤바뀜 | ERROR | 4 | 4 | 0 | 0 | 0 | 0 |
| drivers.csv | DQ024 | MISSING_HEADSHOT_URL | 프로필 사진 주소 결측 | MISSING | 결측 | INFO | 51 | 2 | 49 | 0 | 0 | 49 |
| laps.csv | DQ002 | MISSING_LAP_DATE_START | 랩 시작 시각 결측 | MISSING | 결측 | WARNING | 55 | 0 | 55 | 0 | 0 | 55 |
| laps.csv | DQ003 | MISSING_SPEED | 속도 측정값 결측 | MISSING | 결측 | INFO | 24,101 | 0 | 24,101 | 0 | 0 | 24,101 |
| laps.csv | DQ004 | MISSING_SECTOR_DURATION | 섹터 소요시간 결측 | MISSING | 결측 | WARNING | 1,489 | 489 | 0 | 1,000 | 0 | 1,000 |
| laps.csv | DQ005 | MISSING_SEGMENT_STATUS | 미니 섹터 상태 결측 | MISSING | 결측 | INFO | 498 | 0 | 498 | 0 | 0 | 498 |
| laps.csv | DQ006 | LONG_LAP_DURATION | 비정상 장시간 랩 | OUTLIER | 이상치 | WARNING | 195 | 0 | 0 | 195 | 0 | 195 |
| laps.csv | DQ018 | MISSING_LAP_DURATION | 랩 소요시간 결측 | MISSING | 결측 | WARNING | 373 | 2 | 110 | 261 | 0 | 371 |
| laps.csv | DQ019 | LAP_DATE_INCONSISTENT | 랩 시작 시각 불일치 | INVALID | 값 오류 | ERROR | 83 | 36 | 0 | 47 | 0 | 47 |
| laps.csv | DQ020 | SECTOR_SUM_MISMATCH | 섹터 합계 불일치 | INCONSISTENT | 파일 내 불일치 | WARNING | 20 | 0 | 0 | 20 | 0 | 20 |
| pit.csv | DQ007 | LONG_PIT_DURATION | 비정상 장시간 피트 | OUTLIER | 이상치 | WARNING | 164 | 0 | 0 | 164 | 0 | 164 |
| pit.csv | DQ021 | PIT_DURATION_CONFLICT | 피트 시간 컬럼 충돌 | INCONSISTENT | 파일 내 불일치 | ERROR | 2 | 0 | 0 | 2 | 2 | 2 |
| pit.csv | DQ022 | LONG_STOP_DURATION | 비정상 장시간 정지 | OUTLIER | 이상치 | INFO | 57 | 0 | 0 | 57 | 0 | 57 |
| pit.csv | DQ025 | PIT_LAP_OUT_OF_RANGE | 피트 랩 범위 초과 | REFERENTIAL | 참조 무결성 | WARNING | 1 | 0 | 0 | 1 | 0 | 1 |
| sessions.csv | DQ015 | MEETING_KEY_MISMATCH | 대회 식별자 불일치 | INCONSISTENT | 파일 간 불일치 | ERROR | 2 | 2 | 0 | 0 | 0 | 0 |
| stints.csv | DQ008 | MISSING_COMPOUND | 컴파운드 결측 | MISSING | 결측 | WARNING | 7 | 7 | 0 | 0 | 0 | 0 |
| stints.csv | DQ009 | MISSING_STINT_BOUNDARY | 스틴트 경계 결측 | MISSING | 결측 | WARNING | 58 | 52 | 0 | 6 | 0 | 6 |
| stints.csv | DQ010 | INVALID_STINT_RANGE | 스틴트 종료 범위 오류 | INVALID | 값 오류 | ERROR | 11 | 0 | 11 | 0 | 0 | 11 |
| stints.csv | DQ011 | OVERLAPPING_STINT | 스틴트 구간 중첩 | OVERLAP | 구간 중첩 | WARNING | 3 | 0 | 0 | 3 | 0 | 3 |
| weather.csv | DQ023 | INVALID_WEATHER_VALUE | 기상 측정값 오류 | INVALID | 값 오류 | WARNING | 5 | 5 | 0 | 0 | 0 | 0 |

## 5. 진단코드별 상세 샘플 (허용 제외, 코드당 5건)

#### DQ001 국가 코드 결측 (853건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | drivers.csv | 9693\|1 | country_code |  | NED | 같은 드라이버의 다른 46개 세션 값이 모두 NED | AUTO_FIX | REPAIRED |
| WARNING | drivers.csv | 9693\|4 | country_code |  | GBR | 같은 드라이버의 다른 46개 세션 값이 모두 GBR | AUTO_FIX | REPAIRED |
| WARNING | drivers.csv | 9693\|5 | country_code |  |  | 같은 드라이버의 다른 세션 값 없음 | REVIEW | OPEN |
| WARNING | drivers.csv | 9693\|6 | country_code |  |  | 같은 드라이버의 다른 세션 값 없음 | REVIEW | OPEN |
| WARNING | drivers.csv | 9693\|7 | country_code |  | AUS | 같은 드라이버의 다른 1개 세션 값이 모두 AUS | AUTO_FIX | REPAIRED |

_853건 중 5건 표시_

#### DQ004 섹터 소요시간 결측 (1,489건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | laps.csv | 7953\|81\|14 | duration_sector_1 |  |  | 결측 섹터가 2개 이상이거나 원본 랩타임 없음 | REVIEW | OPEN |
| WARNING | laps.csv | 7953\|21\|20 | duration_sector_1 |  | 31.442 | 랩타임 - 나머지 두 섹터 (원본 랩의 99%에서 섹터 합 = 랩타임) | AUTO_FIX | REPAIRED |
| WARNING | laps.csv | 7953\|1\|25 | duration_sector_1 |  | 31.145 | 랩타임 - 나머지 두 섹터 (원본 랩의 99%에서 섹터 합 = 랩타임) | AUTO_FIX | REPAIRED |
| WARNING | laps.csv | 7953\|16\|37 | duration_sector_1 |  | 31.07 | 랩타임 - 나머지 두 섹터 (원본 랩의 99%에서 섹터 합 = 랩타임) | AUTO_FIX | REPAIRED |
| WARNING | laps.csv | 7953\|31\|42 | duration_sector_1 |  |  | 결측 섹터가 2개 이상이거나 원본 랩타임 없음 | REVIEW | OPEN |

_1,489건 중 5건 표시_

#### DQ006 비정상 장시간 랩 (195건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | laps.csv | 7787\|1\|8 | lap_duration | 1080.581 |  | 300초 초과(적기·세이프티카 가능) | REVIEW | OPEN |
| WARNING | laps.csv | 7787\|14\|8 | lap_duration | 1082.497 |  | 300초 초과(적기·세이프티카 가능) | REVIEW | OPEN |
| WARNING | laps.csv | 7787\|18\|8 | lap_duration | 1080.934 |  | 300초 초과(적기·세이프티카 가능) | REVIEW | OPEN |
| WARNING | laps.csv | 7787\|10\|8 | lap_duration | 1083.17 |  | 300초 초과(적기·세이프티카 가능) | REVIEW | OPEN |
| WARNING | laps.csv | 7787\|27\|8 | lap_duration | 1081.953 |  | 300초 초과(적기·세이프티카 가능) | REVIEW | OPEN |

_195건 중 5건 표시_

#### DQ007 비정상 장시간 피트 (164건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | pit.csv | 9149\|11\|63 | pit_duration | 2461.6 |  | 180초 초과 | REVIEW | OPEN |
| WARNING | pit.csv | 9149\|4\|63 | pit_duration | 2443.2 |  | 180초 초과 | REVIEW | OPEN |
| WARNING | pit.csv | 9149\|63\|63 | pit_duration | 2446.2 |  | 180초 초과 | REVIEW | OPEN |
| WARNING | pit.csv | 9149\|23\|63 | pit_duration | 2443.4 |  | 180초 초과 | REVIEW | OPEN |
| WARNING | pit.csv | 9149\|81\|63 | pit_duration | 2434.6 |  | 180초 초과 | REVIEW | OPEN |

_164건 중 5건 표시_

#### DQ008 컴파운드 결측 (7건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | stints.csv | 11234\|31\|1 | compound |  | UNKNOWN | 원본 타이어 정보가 없어 UNKNOWN으로 명시 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 11234\|10\|1 | compound |  | UNKNOWN | 원본 타이어 정보가 없어 UNKNOWN으로 명시 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 11234\|30\|1 | compound |  | UNKNOWN | 원본 타이어 정보가 없어 UNKNOWN으로 명시 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 11234\|63\|1 | compound |  | UNKNOWN | 원본 타이어 정보가 없어 UNKNOWN으로 명시 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 11234\|23\|1 | compound |  | UNKNOWN | 원본 타이어 정보가 없어 UNKNOWN으로 명시 | AUTO_FIX | REPAIRED |

_7건 중 5건 표시_

#### DQ009 스틴트 경계 결측 (58건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | stints.csv | 10022\|10\|1 | lap_start |  | 1 | 첫 스틴트는 1랩에서 시작 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 10022\|10\|1 | lap_end |  | 1 | 마지막 스틴트: laps.csv의 해당 드라이버 최대 랩 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 7787\|16\|1 | lap_start |  | 1 | 첫 스틴트는 1랩에서 시작 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 7787\|16\|1 | lap_end |  | 1 | 마지막 스틴트: laps.csv의 해당 드라이버 최대 랩 | AUTO_FIX | REPAIRED |
| WARNING | stints.csv | 9141\|81\|1 | lap_start |  | 1 | 첫 스틴트는 1랩에서 시작 | AUTO_FIX | REPAIRED |

_58건 중 5건 표시_

#### DQ011 스틴트 구간 중첩 (3건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | stints.csv | 9558\|24\|4 | lap_start | 20 |  | 이전 스틴트 종료 37 이후에 시작해야 함 | REVIEW | OPEN |
| WARNING | stints.csv | 9558\|31\|4 | lap_start | 22 |  | 이전 스틴트 종료 38 이후에 시작해야 함 | REVIEW | OPEN |
| WARNING | stints.csv | 9590\|18\|3 | lap_start | 20 |  | 이전 스틴트 종료 50 이후에 시작해야 함 | REVIEW | OPEN |

#### DQ015 대회 식별자 불일치 (2건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| ERROR | sessions.csv | 9126 | meeting_key | 1218 | 1214 | 하위 5개 파일이 모두 meeting_key=1214로 일치 | AUTO_FIX | REPAIRED |
| ERROR | sessions.csv | 9157 | meeting_key | 1214 | 1218 | 하위 5개 파일이 모두 meeting_key=1218로 일치 | AUTO_FIX | REPAIRED |

#### DQ016 드라이버 신원 뒤바뀜 (20건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| ERROR | drivers.csv | 9523\|1 | full_name | Pierre GASLY | Max VERSTAPPEN | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9523\|1 | first_name | Pierre | Max | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9523\|1 | last_name | Gasly | Verstappen | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9523\|1 | broadcast_name | P GASLY | M VERSTAPPEN | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9523\|1 | name_acronym | GAS | VER | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 | AUTO_FIX | REPAIRED |

_20건 중 5건 표시_

#### DQ017 소속 팀 불일치 (4건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| ERROR | drivers.csv | 9523\|23 | team_name | Aston Martin | Williams | 앞뒤 세션 소속 Williams, 팀 색상 64C4FF도 Williams와 일치 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9606\|63 | team_name | Haas F1 Team | Mercedes | 앞뒤 세션 소속 Mercedes, 팀 색상 27F4D2도 Mercedes와 일치 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9606\|20 | team_name | Mercedes | Haas F1 Team | 앞뒤 세션 소속 Haas F1 Team, 팀 색상 B6BABD도 Haas F1 Team와 일치 | AUTO_FIX | REPAIRED |
| ERROR | drivers.csv | 9523\|18 | team_name | Williams | Aston Martin | 앞뒤 세션 소속 Aston Martin, 팀 색상 229971도 Aston Martin와 일치 | AUTO_FIX | REPAIRED |

#### DQ018 랩 소요시간 결측 (263건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | laps.csv | 10014\|55\|46 | lap_duration |  |  | 드라이버의 마지막 랩(완주·리타이어)이라 다음 랩 없음 | REVIEW | OPEN |
| WARNING | laps.csv | 10022\|22\|2 | lap_duration |  |  | 드라이버의 마지막 랩(완주·리타이어)이라 다음 랩 없음 | REVIEW | OPEN |
| WARNING | laps.csv | 10033\|30\|37 | lap_duration |  |  | 드라이버의 마지막 랩(완주·리타이어)이라 다음 랩 없음 | REVIEW | OPEN |
| WARNING | laps.csv | 10033\|5\|31 | lap_duration |  |  | 드라이버의 마지막 랩(완주·리타이어)이라 다음 랩 없음 | REVIEW | OPEN |
| WARNING | laps.csv | 10033\|87\|28 | lap_duration |  |  | 드라이버의 마지막 랩(완주·리타이어)이라 다음 랩 없음 | REVIEW | OPEN |

_263건 중 5건 표시_

#### DQ019 랩 시작 시각 불일치 (83건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| ERROR | laps.csv | 10014\|14\|22 | date_start | 2025-04-13 15:39:12.402000+00:00 | 2025-04-13 15:39:14.348000+00:00 | 앞 랩 기준 예상과 -1.946초 차이(적기·세이프티카·체커 이후 등 원천 특성 가능, 근거 부족으로 미수정) | REVIEW | OPEN |
| ERROR | laps.csv | 10014\|22\|2 | date_start | 2025-04-13 15:07:13.477000+00:00 | 2025-04-13 15:05:34.495000+00:00 | 다음 랩과 시작 시각이 서로 바뀜(교환 시 앞뒤 랩타임과 일치) | AUTO_FIX | REPAIRED |
| ERROR | laps.csv | 10014\|22\|3 | date_start | 2025-04-13 15:05:34.495000+00:00 | 2025-04-13 15:07:13.477000+00:00 | 이전 랩과 시작 시각이 서로 바뀜(교환 시 앞뒤 랩타임과 일치) | AUTO_FIX | REPAIRED |
| ERROR | laps.csv | 10014\|63\|7 | date_start | 2025-04-13 15:15:19.418000+00:00 | 2025-04-13 15:13:40.701000+00:00 | 다음 랩과 시작 시각이 서로 바뀜(교환 시 앞뒤 랩타임과 일치) | AUTO_FIX | REPAIRED |
| ERROR | laps.csv | 10014\|63\|8 | date_start | 2025-04-13 15:13:40.701000+00:00 | 2025-04-13 15:15:19.418000+00:00 | 이전 랩과 시작 시각이 서로 바뀜(교환 시 앞뒤 랩타임과 일치) | AUTO_FIX | REPAIRED |

_83건 중 5건 표시_

#### DQ020 섹터 합계 불일치 (20건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | laps.csv | 9644\|77\|38 | lap_duration | 97.092 | 96.584 | 섹터 합 - 랩타임 = -0.508초 | REVIEW | OPEN |
| WARNING | laps.csv | 9644\|63\|39 | lap_duration | 96.275 | 95.766 | 섹터 합 - 랩타임 = -0.509초 | REVIEW | OPEN |
| WARNING | laps.csv | 9644\|77\|40 | lap_duration | 99.608 | 99.099 | 섹터 합 - 랩타임 = -0.509초 | REVIEW | OPEN |
| WARNING | laps.csv | 9644\|63\|41 | lap_duration | 96.559 | 96.05 | 섹터 합 - 랩타임 = -0.509초 | REVIEW | OPEN |
| WARNING | laps.csv | 9644\|81\|41 | lap_duration | 97.188 | 96.676 | 섹터 합 - 랩타임 = -0.512초 | REVIEW | OPEN |

_20건 중 5건 표시_

#### DQ021 피트 시간 컬럼 충돌 (2건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| ERROR | pit.csv | 9157\|2\|14 | pit_duration | 24.7 | 29.3 | 원천에서 두 컬럼이 동일(99.93%)한데 이 행만 다름 | QUARANTINE | OPEN |
| ERROR | pit.csv | 9157\|18\|20 | pit_duration | 25.6 | 32.4 | 원천에서 두 컬럼이 동일(99.93%)한데 이 행만 다름 | QUARANTINE | OPEN |

#### DQ022 비정상 장시간 정지 (57건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| INFO | pit.csv | 9126\|81\|29 | stop_duration | 15.3 |  | 10초 초과 정지(수리·페널티 가능) | REVIEW | OPEN |
| INFO | pit.csv | 9617\|23\|3 | stop_duration | 12.5 |  | 10초 초과 정지(수리·페널티 가능) | REVIEW | OPEN |
| INFO | pit.csv | 9625\|1\|26 | stop_duration | 24.0 |  | 10초 초과 정지(수리·페널티 가능) | REVIEW | OPEN |
| INFO | pit.csv | 9625\|30\|65 | stop_duration | 10.4 |  | 10초 초과 정지(수리·페널티 가능) | REVIEW | OPEN |
| INFO | pit.csv | 9636\|27\|27 | stop_duration | 36.0 |  | 10초 초과 정지(수리·페널티 가능) | REVIEW | OPEN |

_57건 중 5건 표시_

#### DQ023 기상 측정값 오류 (5건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | weather.csv | 11377\|2026-09-26 10:11:59.518000+00:00 | track_temperature | 0.0 | 47.0 | 앞뒤 측정 46.6, 47.3과 10도 이상 차이 나는 단일값 | AUTO_FIX | REPAIRED |
| WARNING | weather.csv | 11377\|2026-09-26 12:46:00.023000+00:00 | track_temperature | 0.0 | 40.0 | 앞뒤 측정 39.8, 40.1과 10도 이상 차이 나는 단일값 | AUTO_FIX | REPAIRED |
| WARNING | weather.csv | 11388\|2026-10-11 11:32:56.866000+00:00 | track_temperature | 0.0 | 43.2 | 앞뒤 측정 43.1, 43.4과 10도 이상 차이 나는 단일값 | AUTO_FIX | REPAIRED |
| WARNING | weather.csv | 11731\|2026-10-04 07:20:57.704000+00:00 | track_temperature | 0.0 | 34.7 | 앞뒤 측정 34.7, 34.7과 10도 이상 차이 나는 단일값 | AUTO_FIX | REPAIRED |
| WARNING | weather.csv | 11731\|2026-10-04 08:43:58.024000+00:00 | track_temperature | 0.0 | 33.6 | 앞뒤 측정 33.7, 33.5과 10도 이상 차이 나는 단일값 | AUTO_FIX | REPAIRED |

#### DQ024 프로필 사진 주소 결측 (2건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| INFO | drivers.csv | 11361\|22 | headshot_url |  | https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/Y/YUKTSU01_Yuki_Tsunoda/yuktsu01.png.transform/1col/image.png | 같은 드라이버·시즌의 유일한 주소 | AUTO_FIX | REPAIRED |
| INFO | drivers.csv | 11369\|22 | headshot_url |  | https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/Y/YUKTSU01_Yuki_Tsunoda/yuktsu01.png.transform/1col/image.png | 같은 드라이버·시즌의 유일한 주소 | AUTO_FIX | REPAIRED |

#### DQ025 피트 랩 범위 초과 (1건)

| severity | file | row_key | field | observed_value | expected_value | evidence | action | status |
|---|---|---|---|---|---|---|---|---|
| WARNING | pit.csv | 11234\|18\|46 | lap_number | 46 | 43 | 해당 드라이버 최대 랩보다 큼 | REVIEW | OPEN |

## 6. 복구 이력 샘플

| diagnostic_code | file | row_key | field | old_value | new_value | method | confidence | reason |
|---|---|---|---|---|---|---|---|---|
| DQ015 | sessions.csv | 9126 | meeting_key | 1218 | 1214 | child_file_consensus | HIGH | 하위 5개 파일이 모두 meeting_key=1214로 일치 |
| DQ015 | sessions.csv | 9157 | meeting_key | 1214 | 1218 | child_file_consensus | HIGH | 하위 5개 파일이 모두 meeting_key=1218로 일치 |
| DQ016 | drivers.csv | 9523\|1 | full_name | Pierre GASLY | Max VERSTAPPEN | season_number_consensus_swap | HIGH | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|1 | first_name | Pierre | Max | season_number_consensus_swap | HIGH | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|1 | last_name | Gasly | Verstappen | season_number_consensus_swap | HIGH | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|1 | broadcast_name | P GASLY | M VERSTAPPEN | season_number_consensus_swap | HIGH | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|1 | name_acronym | GAS | VER | season_number_consensus_swap | HIGH | 2024 시즌 #1의 신원 합의값, 같은 세션 #10 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|10 | full_name | Max VERSTAPPEN | Pierre GASLY | season_number_consensus_swap | HIGH | 2024 시즌 #10의 신원 합의값, 같은 세션 #1 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|10 | first_name | Max | Pierre | season_number_consensus_swap | HIGH | 2024 시즌 #10의 신원 합의값, 같은 세션 #1 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|10 | last_name | Verstappen | Gasly | season_number_consensus_swap | HIGH | 2024 시즌 #10의 신원 합의값, 같은 세션 #1 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|10 | broadcast_name | M VERSTAPPEN | P GASLY | season_number_consensus_swap | HIGH | 2024 시즌 #10의 신원 합의값, 같은 세션 #1 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|10 | name_acronym | VER | GAS | season_number_consensus_swap | HIGH | 2024 시즌 #10의 신원 합의값, 같은 세션 #1 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|16 | full_name | Carlos SAINZ | Charles LECLERC | season_number_consensus_swap | HIGH | 2024 시즌 #16의 신원 합의값, 같은 세션 #55 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|16 | first_name | Carlos | Charles | season_number_consensus_swap | HIGH | 2024 시즌 #16의 신원 합의값, 같은 세션 #55 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|16 | last_name | Sainz | Leclerc | season_number_consensus_swap | HIGH | 2024 시즌 #16의 신원 합의값, 같은 세션 #55 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|16 | broadcast_name | C SAINZ | C LECLERC | season_number_consensus_swap | HIGH | 2024 시즌 #16의 신원 합의값, 같은 세션 #55 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|16 | name_acronym | SAI | LEC | season_number_consensus_swap | HIGH | 2024 시즌 #16의 신원 합의값, 같은 세션 #55 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|55 | full_name | Charles LECLERC | Carlos SAINZ | season_number_consensus_swap | HIGH | 2024 시즌 #55의 신원 합의값, 같은 세션 #16 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|55 | first_name | Charles | Carlos | season_number_consensus_swap | HIGH | 2024 시즌 #55의 신원 합의값, 같은 세션 #16 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|55 | last_name | Leclerc | Sainz | season_number_consensus_swap | HIGH | 2024 시즌 #55의 신원 합의값, 같은 세션 #16 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|55 | broadcast_name | C LECLERC | C SAINZ | season_number_consensus_swap | HIGH | 2024 시즌 #55의 신원 합의값, 같은 세션 #16 행과 교환됨 |
| DQ016 | drivers.csv | 9523\|55 | name_acronym | LEC | SAI | season_number_consensus_swap | HIGH | 2024 시즌 #55의 신원 합의값, 같은 세션 #16 행과 교환됨 |
| DQ017 | drivers.csv | 9523\|23 | team_name | Aston Martin | Williams | adjacent_session_team | HIGH | 앞뒤 세션 소속 Williams, 팀 색상 64C4FF도 Williams와 일치 |
| DQ017 | drivers.csv | 9606\|63 | team_name | Haas F1 Team | Mercedes | adjacent_session_team | HIGH | 앞뒤 세션 소속 Mercedes, 팀 색상 27F4D2도 Mercedes와 일치 |
| DQ017 | drivers.csv | 9606\|20 | team_name | Mercedes | Haas F1 Team | adjacent_session_team | HIGH | 앞뒤 세션 소속 Haas F1 Team, 팀 색상 B6BABD도 Haas F1 Team와 일치 |
| DQ017 | drivers.csv | 9523\|18 | team_name | Williams | Aston Martin | adjacent_session_team | HIGH | 앞뒤 세션 소속 Aston Martin, 팀 색상 229971도 Aston Martin와 일치 |
| DQ001 | drivers.csv | 9693\|1 | country_code |  | NED | driver_consensus | HIGH | 같은 드라이버의 다른 46개 세션 값이 모두 NED |
| DQ001 | drivers.csv | 9693\|4 | country_code |  | GBR | driver_consensus | HIGH | 같은 드라이버의 다른 46개 세션 값이 모두 GBR |
| DQ001 | drivers.csv | 9693\|7 | country_code |  | AUS | driver_consensus | HIGH | 같은 드라이버의 다른 1개 세션 값이 모두 AUS |
| DQ001 | drivers.csv | 9693\|10 | country_code |  | FRA | driver_consensus | HIGH | 같은 드라이버의 다른 46개 세션 값이 모두 FRA |

_1,335건 중 30건 표시_
