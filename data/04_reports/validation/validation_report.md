# 정제 후 데이터 검증 결과

## 행 수 대사: 원본 = 원본 유지 + 복구 + 격리 + 제거

| 파일 | ① 원본 | ② 원본 유지 | ③ 복구 | ④ 격리 | ⑤ 제거 | 처리 합계 | 차이 | 분석 대상 | 남은 키 중복 | 결과 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| sessions | 87 | 85 | 2 | 0 | 0 | 87 | 0 | 87 | 0 | PASS |
| drivers | 1,771 | 1,047 | 724 | 0 | 0 | 1,771 | 0 | 1,771 | 0 | PASS |
| laps | 97,018 | 96,489 | 527 | 2 | 0 | 97,018 | 0 | 97,016 | 0 | PASS |
| stints | 5,040 | 5,004 | 36 | 0 | 0 | 5,040 | 0 | 5,040 | 0 | PASS |
| weather | 13,928 | 13,923 | 5 | 0 | 0 | 13,928 | 0 | 13,928 | 0 | PASS |
| pit | 3,029 | 3,027 | 0 | 2 | 0 | 3,029 | 0 | 3,027 | 0 | PASS |
| starting_grid | 1,770 | 1,770 | 0 | 0 | 0 | 1,770 | 0 | 1,770 | 0 | PASS |
| session_result | 1,771 | 1,771 | 0 | 0 | 0 | 1,771 | 0 | 1,771 | 0 | PASS |
| position | 42,952 | 42,952 | 0 | 0 | 0 | 42,952 | 0 | 42,952 | 0 | PASS |
| race_control | 9,499 | 9,499 | 0 | 0 | 0 | 9,499 | 0 | 9,499 | 0 | PASS |
| intervals | 2,107,568 | 2,107,568 | 0 | 0 | 0 | 2,107,568 | 0 | 2,107,568 | 0 | PASS |
| 합계(오염 정제 6종) | 120,873 | 119,575 | 1,294 | 4 | 0 | 120,873 | 0 | 120,869 | 0 | PASS |

| 상태 | 건수 |
|---|---:|
| PASS | 127 |
| FAIL | 0 |
| WARN | 7 |
| INFO | 20 |

## 정제 전후 비교

같은 검사를 정제 전 값(`original_*` = 오염 원본)과 정제 후 값에 각각 실행한 결과입니다. 정제 전후 모두 PASS인 항목과 INFO는 뺐습니다.

| 검사 | 대상 | 검사명 | 등급 | 정제 전 위반 | 정제 전 | 정제 후 위반 | 정제 후 |
|---|---|---|---|---:|---|---:|---|
| VC22 | drivers | MEETING_KEY_CONSISTENT | ERROR | 40 | FAIL | 0 | PASS |
| VC22 | laps | MEETING_KEY_CONSISTENT | ERROR | 1,942 | FAIL | 0 | PASS |
| VC22 | stints | MEETING_KEY_CONSISTENT | ERROR | 89 | FAIL | 0 | PASS |
| VC22 | weather | MEETING_KEY_CONSISTENT | ERROR | 307 | FAIL | 0 | PASS |
| VC22 | pit | MEETING_KEY_CONSISTENT | ERROR | 48 | FAIL | 0 | PASS |
| VC22 | session_result | MEETING_KEY_CONSISTENT | ERROR | 40 | FAIL | 0 | PASS |
| VC22 | position | MEETING_KEY_CONSISTENT | ERROR | 777 | FAIL | 0 | PASS |
| VC22 | race_control | MEETING_KEY_CONSISTENT | ERROR | 91 | FAIL | 0 | PASS |
| VC22 | intervals | MEETING_KEY_CONSISTENT | ERROR | 45,072 | FAIL | 0 | PASS |
| VC32 | stints | CODE_DOMAIN | ERROR | 7 | FAIL | 0 | PASS |
| VC43 | pit | PIT_DURATION_SPLIT | ERROR | 2 | FAIL | 0 | PASS |
| VC46 | laps | LAP_START_CONSISTENT | ERROR | 116 | FAIL | 0 | PASS |
| VC04 | session_result | UNCLASSIFIED_WITHOUT_STATUS | WARNING | 4 | WARN | 4 | WARN |
| VC24 | starting_grid | GRID_WITHOUT_RESULT | WARNING | 4 | WARN | 2 | WARN |
| VC26 | pit | PIT_LAP_IN_RANGE | WARNING | 1 | WARN | 1 | WARN |
| VC27 | laps | LAP_COVERED_BY_STINT | WARNING | 303 | WARN | 280 | WARN |
| VC40 | drivers | TEAM_DRIVER_COUNT | WARNING | 3 | WARN | 3 | WARN |
| VC42 | laps | SECTOR_SUM | WARNING | 20 | WARN | 20 | WARN |
| VC45 | stints | STINT_OVERLAP | WARNING | 3 | WARN | 3 | WARN |
| VC35 | weather | TRACK_TEMP_SPIKE | WARNING | 5 | WARN | 0 | PASS |
| VC41 | drivers | SEASON_NUMBER_IDENTITY | WARNING | 4 | WARN | 0 | PASS |
| VC47 | drivers | TEAM_SEQUENCE | WARNING | 6 | WARN | 0 | PASS |

## FAIL·WARN 항목

| 검사 | 대상 | 등급 | 위반 | 전체 | 설명 | 비고 |
|---|---|---|---:|---:|---|---|
| VC04 | session_result | WARNING | 4 | 1,771 | session_result 순위 공백인데 dnf·dns·dsq 모두 False |  |
| VC24 | starting_grid | WARNING | 2 | 1,770 | starting_grid(meeting_key+driver_number)가 Race 결과에 없음(예선 후 기권 확인) |  |
| VC26 | pit | WARNING | 1 | 3,029 | 피트 랩이 해당 드라이버 최대 랩보다 큼 |  |
| VC27 | laps | WARNING | 280 | 97,018 | 어느 스틴트 구간에도 속하지 않는 랩 |  |
| VC40 | drivers | WARNING | 3 | 887 | 세션별 팀 소속 드라이버 수가 2가 아님 |  |
| VC42 | laps | WARNING | 20 | 96,597 | 섹터 3개 합과 랩타임 차이 0.5초 초과(잔여 검토) |  |
| VC45 | stints | WARNING | 3 | 5,040 | 다음 스틴트 시작 < 이전 스틴트 종료 |  |

## INFO 항목

| 검사 | 대상 | 건수 | 설명 | 비고 |
|---|---|---:|---|---|
| VC02 | sessions | 0 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | drivers | 186 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | laps | 26,025 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | stints | 6 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | weather | 0 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | pit | 2,026 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | starting_grid | 59 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | session_result | 1,147 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | position | 0 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | race_control | 32,426 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC02 | intervals | 37,023 | 컬럼별 공백 건수(참고용 프로파일; null_profile 출력) | null_profile.csv 참고 |
| VC25 | session_result | 3 | Race 결과에 그리드가 없음(피트레인 출발 등 원천 특성) | 그리드 없는 Race 결과(피트레인 출발 등) |
| VC71 | laps×stints | 305 | 랩이 2개 이상 스틴트 구간에 매칭(경계 랩 공유 → Silver에서 귀속 규칙 필요) | 경계 랩이 앞뒤 스틴트에 모두 속함 |
| VC50 | session_result | 47 | 원천 points와 재계산 race_base_points 차이(최속 랩 보너스·원천 누락 확인용) | -18점 2건, -15점 1건, -12점 1건, -10점 1건, -8점 1건, -6점 1건, -4점 1건, -2점 1건, -1점 1건, +1점 37건 |
| VC61 | sessions | 0 | quarantine_flag=Y 행 수(격리 대상 참고) | quarantine/sessions.csv 0행 |
| VC61 | drivers | 0 | quarantine_flag=Y 행 수(격리 대상 참고) | quarantine/drivers.csv 0행 |
| VC61 | laps | 2 | quarantine_flag=Y 행 수(격리 대상 참고) | quarantine/laps.csv 2행 |
| VC61 | stints | 0 | quarantine_flag=Y 행 수(격리 대상 참고) | quarantine/stints.csv 0행 |
| VC61 | weather | 0 | quarantine_flag=Y 행 수(격리 대상 참고) | quarantine/weather.csv 0행 |
| VC61 | pit | 2 | quarantine_flag=Y 행 수(격리 대상 참고) | quarantine/pit.csv 2행 |
