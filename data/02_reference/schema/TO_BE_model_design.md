# F1 MySQL TO-BE 데이터베이스 설계도

## 1. 설계 목적

AS-IS 프로파일링 결과와 AI 데이터 표준사전을 적용해 F1 데이터 11종(오염 정제 6종 + 신규 5종)을 MySQL 8.0+에서 관리하기 위한 목표 스키마를 정의한다. 기준 기획서는 `F1_P2_Spec.md`이고, 원천별 컬럼 명세는 `F1_데이터_명세서.md`에 있다. 실행 DDL은 `sql/04_create_schema.sql`, 적재는 `sql/05_insert_schema.sql`이다.

설계 원칙:

- 원본 식별자와 코드값은 문자열 의미를 보존한다.
- `session_key`와 `meeting_key`를 구분한다.
- `driver_number`는 영구 드라이버 ID가 아니므로 세션 참가 맥락에서 식별한다.
- 장소 정보는 대회·세션 테이블에 두고 하위 사실 테이블에 중복 저장하지 않는다.
- 오염 진단과 복구 이력을 원천 업무 데이터와 분리한다.
- Gold 형태의 조회용 중복은 허용하되 정합성 기준은 정규화 모델로 한다.

## 2. 개념 ERD

```mermaid
erDiagram
    MEETING ||--o{ SESSION : contains
    SESSION ||--o{ SESSION_DRIVER : registers
    DRIVER ||--o{ SESSION_DRIVER : participates
    SESSION_DRIVER ||--o{ LAP : records
    SESSION_DRIVER ||--o{ STINT : uses
    SESSION_DRIVER ||--o{ PIT_EVENT : performs
    SESSION ||--o{ WEATHER_OBSERVATION : measures
    SESSION ||--o{ QUALITY_ISSUE : produces
    QUALITY_ISSUE ||--o{ REPAIR_DETAIL : explains
    MEETING ||--o{ STARTING_GRID : "qualifying grid"
    SESSION ||--o{ STARTING_GRID : "race_session_key"
    SESSION_DRIVER ||--o| SESSION_RESULT : finishes
    SESSION_DRIVER ||--o{ POSITION_EVENT : ranks
    SESSION_DRIVER ||--o{ INTERVAL_EVENT : gaps
    SESSION ||--o{ RACE_CONTROL_EVENT : announces
    REF_RACE_POINTS_RULE ||--o{ SESSION_RESULT : scores
```

업무 객체:

- `MEETING`: 대회, 개최지, 국가, 서킷
- `SESSION`: Race, Sprint, Qualifying, Practice 등 주행 세션
- `DRIVER`: 드라이버 기본 정보
- `SESSION_DRIVER`: 특정 세션의 참가자와 차량 번호
- `LAP`: 세션·드라이버별 랩 기록
- `STINT`: 세션·드라이버별 타이어 사용 구간
- `PIT_EVENT`: 세션·드라이버별 피트 이벤트
- `WEATHER_OBSERVATION`: 세션 시각별 기상 측정
- `QUALITY_ISSUE`: DQ 진단 결과
- `REPAIR_DETAIL`: 복구 전후 값과 근거
- `STARTING_GRID`: 예선 결과로 정해진 출발 순위 (Qualifying 키 보존, Race로 매핑)
- `SESSION_RESULT`: Race 최종 분류와 본경기 기본 포인트
- `POSITION_EVENT`, `INTERVAL_EVENT`: 경기 중 순위·격차 시계열
- `RACE_CONTROL_EVENT`: SC/VSC·깃발·사고 등 관제 메시지

## 3. 논리 ERD

```mermaid
erDiagram
    MEETING ||--o{ SESSION : has
    SESSION ||--o{ SESSION_DRIVER : has
    DRIVER ||--o{ SESSION_DRIVER : enters
    SESSION_DRIVER ||--o{ LAP : has
    SESSION_DRIVER ||--o{ STINT : has
    SESSION_DRIVER ||--o{ PIT_EVENT : has
    SESSION ||--o{ WEATHER : has
    SESSION ||--o{ QUALITY_ISSUE : has

    MEETING {
        varchar meeting_key PK
        varchar circuit_key
        varchar country_key
        varchar country_code
        varchar country_name
        varchar location
    }
    SESSION {
        varchar session_key PK
        varchar meeting_key FK
        varchar session_type_code FK
        varchar session_name
        datetime date_start
        datetime date_end
        smallint year
    }
    DRIVER {
        bigint driver_id PK
        varchar full_name
        varchar country_code
    }
    SESSION_DRIVER {
        varchar session_key PK,FK
        varchar driver_number PK,FK
        bigint driver_id FK
        varchar team_name
    }
    LAP {
        varchar session_key PK,FK
        varchar driver_number PK,FK
        int lap_number PK
        decimal lap_duration
        decimal i1_speed
        decimal i2_speed
        decimal st_speed
    }
    STINT {
        varchar session_key PK,FK
        varchar driver_number PK,FK
        int stint_number PK
        varchar compound_code FK
        int lap_start
        int lap_end
    }
    PIT_EVENT {
        varchar session_key PK,FK
        varchar driver_number PK,FK
        int lap_number PK
        datetime event_date
        decimal pit_duration
    }
    WEATHER {
        varchar session_key PK,FK
        datetime observed_at PK
        decimal air_temperature
        decimal humidity
    }
```

## 4. 테이블 및 식별키

| 테이블 | 업무 의미 | 기본키 | 주요 외래키 |
|---|---|---|---|
| `meeting` | 대회·개최지 | `meeting_key` | 없음 |
| `session` | 세션 | `session_key` | `meeting_key`, `session_type_code` |
| `driver` | 드라이버 마스터 | `driver_id` | 없음 |
| `session_driver` | 세션별 참가자 | `session_key + driver_number` | `session_key`, `driver_id` |
| `lap` | 랩 기록 | `session_key + driver_number + lap_number` | `session_driver` |
| `stint` | 타이어 스틴트 | `session_key + driver_number + stint_number` | `session_driver`, `compound_code` |
| `pit_event` | 피트 이벤트 | `session_key + driver_number + lap_number` | `session_driver` |
| `weather` | 기상 측정 | `session_key + observed_at` | `session_key` |
| `quality_issue` | 진단 결과 | `quality_issue_id` | `session_key`, `diagnostic_code` |
| `repair_detail` | 복구 이력 | `repair_detail_id` | `issue_id` |
| `starting_grid` | 출발 그리드 | `qualifying_session_key + driver_number` | `meeting_key`, `race_session_key` |
| `session_result` | Race 결과·기본 포인트 | `session_key + driver_number` | `session_driver`, `ref_race_points_rule`(연도·순위) |
| `position_event` | 순위 시계열 | `position_event_id` (유일: `session_key + driver_number + recorded_at`) | `session_driver` |
| `interval_event` | 격차 시계열 | `interval_event_id` (유일: `session_key + driver_number + recorded_at`) | `session_driver` |
| `race_control_event` | 관제 메시지 | `race_control_event_id` | `session`, `session_driver`(드라이버 대상일 때) |

`driver_number`는 시즌·세션 간 재사용될 수 있으므로 `driver` 테이블의 단독 식별키로 사용하지 않는다. 화면과 사실 테이블에서는 반드시 `session_key + driver_number`를 함께 사용한다.

## 5. 물리 모델 정의

### 5.1 공통 타입 기준

| 표준 도메인 | MySQL 타입 | 길이·정밀도 | NULL | 적용 예 |
|---|---|---:|---|---|
| 식별자 | `VARCHAR` | 64 | N | `session_key`, `meeting_key` |
| 짧은 코드 | `VARCHAR` | 16~32 | Y/N | `compound_code`, `session_type_code` |
| 정수 문자열 | `VARCHAR` | 16 | Y | `driver_number`, `lap_number` 원문 |
| 정수 계산값 | `INT` | - | Y | `lap_number`, `lap_start`, `lap_end` |
| 시간 | `DATETIME(6)` | - | Y | `date_start`, `event_date` |
| 초 단위 실수 | `DECIMAL` | 12,6 | Y | `lap_duration`, `pit_duration` |
| 속도 | `DECIMAL` | 12,3 | Y | `i1_speed`, `st_speed` |
| 온도·기압 | `DECIMAL` | 12,3 | Y | `air_temperature`, `pressure` |
| 불리언 | `BOOLEAN` | - | Y | `is_cancelled`, `is_pit_out_lap` |
| 목록 원문 | `TEXT` | 가변 | Y | `segments_sector_1~3` |
| 설명 | `VARCHAR` | 1000 | Y | `repair_reason`, `issue_message` |

### 5.2 코드 테이블

| 코드 테이블 | 주요 코드 |
|---|---|
| `ref_compound` | `SOFT`, `MEDIUM`, `HARD`, `INTERMEDIATE`, `WET`, `UNKNOWN` |
| `ref_session_type` | `Race`, `Sprint`, `Qualifying`, `Practice` |
| `ref_diagnostic` | `DQ001`~`DQ027` (오류 유형·심각도 포함, `diagnostic_codes.csv`) |
| `ref_error_type` | `MISSING`, `INVALID`, `OUTLIER`, `INCONSISTENT`, `SWAP`, `SCHEMA`, `TYPE`, `REFERENTIAL`, `DUPLICATE`, `OVERLAP` |
| `ref_issue_action` | `AUTO_FIX`, `REVIEW`, `ACCEPT`, `QUARANTINE` |
| `ref_diagnostic_status` | `OPEN`, `REPAIRED`, `ACCEPTED`, `WAIVED` |
| `ref_repair_status` | `UNCHANGED`, `REPAIRED` |
| `ref_repair_confidence` | `HIGH`, `MEDIUM`, `LOW` |
| `ref_repair_method` | `codes.csv`의 `REPAIR_METHOD` 그룹 (중앙값 추정은 폐기) |
| `ref_race_points_rule` | 연도 × 1~10위 기본 배점 (`race_points_rules.csv`) |
| `ref_validation_check` | 정제 후 검증 항목 VC01~VC71 (`validation_checks.csv`) |
| 기타 코드 | `RACE_CONTROL_CATEGORY`, `RACE_CONTROL_FLAG`, `RACE_CONTROL_SCOPE`, `CLASSIFICATION_STATUS`, `POINTS_RULE_STATUS`, `VALIDATION_STATUS` |

실행 DDL에서는 코드 테이블을 `ref_code(code_group, code)` 하나로 적재하고 `ref_diagnostic`, `ref_race_points_rule`, `ref_validation_check`만 별도 테이블로 둔다.

### 5.3 핵심 제약조건

```sql
-- MySQL 8.0 기준 설계 예시이며 실행 스크립트가 아님
CHECK (lap_start IS NULL OR lap_end IS NULL OR lap_end >= lap_start)
CHECK (lap_duration IS NULL OR lap_duration >= 0)
CHECK (pit_duration IS NULL OR pit_duration >= 0)
CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100)
CHECK (wind_direction IS NULL OR wind_direction BETWEEN 0 AND 360)
```

스틴트 중첩은 행 간 비교이므로 CHECK 제약만으로 처리하지 않고 검증 쿼리로 관리한다.

```sql
SELECT a.session_key, a.driver_number, a.stint_number, b.stint_number
FROM stint a
JOIN stint b
  ON a.session_key = b.session_key
 AND a.driver_number = b.driver_number
 AND a.stint_number < b.stint_number
WHERE a.lap_end IS NOT NULL
  AND b.lap_start IS NOT NULL
  AND b.lap_start < a.lap_end;
```

## 6. 정규화

### 1NF

- 반복되는 랩·스틴트·피트 데이터를 하나의 컬럼에 배열로 저장하지 않는다.
- `segments_sector_1~3`은 원본 호환을 위해 문자열로 보존하되, 미니 섹터 분석이 필요하면 `lap_segment`를 별도 테이블로 분리한다.

### 2NF

- 세션에 종속되는 장소 정보는 `meeting`, `session`에 둔다.
- 세션 참가자에 종속되는 팀·프로필 정보는 `session_driver`에 둔다.
- 랩 속성은 `session_key + driver_number + lap_number` 전체에 종속된다.
- 스틴트 속성은 `session_key + driver_number + stint_number` 전체에 종속된다.

### 3NF

- 코드값은 코드 테이블로 분리한다.
- 품질 진단과 복구 이력은 업무 사실 테이블에서 분리한다.
- 장소·세션·드라이버의 설명 속성을 랩·피트·기상 테이블에 중복 저장하지 않는다.

## 7. 관계 및 인덱스

- `session.meeting_key`에 인덱스를 둔다.
- `session_driver(session_key, driver_number)`를 유일키로 둔다.
- `lap(session_key, driver_number, lap_number)`를 기본키로 사용한다.
- `stint(session_key, driver_number, lap_start, lap_end)`에 구간 검색 인덱스를 둔다.
- `pit_event(session_key, driver_number, lap_number)`에 조회 인덱스를 둔다.
- `weather(session_key, observed_at)`를 기본키로 사용한다.
- `quality_issue(source_file, diagnostic_code, session_key)`에 복합 인덱스를 둔다.

## 8. 진단 결과 반영

- `DQ001`: `drivers.country_code` 결측
- `DQ003`: `laps.i1_speed`, `i2_speed`, `st_speed` 결측
- `DQ004`: 섹터 소요시간 결측
- `DQ006`: `lap_duration > 300`
- `DQ007`: `pit_duration > 180`
- `DQ008`: `stints.compound` 결측은 `UNKNOWN`
- `DQ009`: 스틴트 시작·종료 랩 결측
- `DQ010`: `lap_end < lap_start`
- `DQ011`: 스틴트 구간 중첩
- `DQ013`~`DQ027`: 구조·형식, 파일 간 `meeting_key` 불일치, 드라이버 신원·소속팀 뒤바뀜, 랩 시각 불일치, 섹터 합계, 피트 시간 충돌, 기상값 오류, 중복키, 참조 무결성 (전체 목록은 `diagnostic_codes.csv`)

모든 진단 이슈는 `quality_issue`에 기록하고, 복구가 발생한 행은 `repair_detail`에 원본값·복구값·방법·신뢰도·근거를 기록한다.

## 9. 신규 5종과 포인트 설계

- **출발 그리드 매핑:** `starting_grid`의 원본 `session_key`는 Qualifying 키다. `qualifying_session_key`로 보존하고, 같은 `meeting_key`의 Race 세션을 찾아 `race_session_key`에 저장한다. Qualifying/Race `session_key`를 직접 JOIN하지 않는다.
- **결과 분류:** `classification_status` = `DSQ`/`DNS`/`DNF`(플래그 우선) → 순위 있으면 `CLASSIFIED` → 나머지 `NOT_CLASSIFIED`. `DNF`라도 순위가 있으면 그 순위로 배점한다.
- **본경기 기본 포인트:** `race_base_points = ref_race_points_rule(year, finish_position)`, 11위 이하·미분류 0점. 원천 `points`는 `source_points`로만 보존한다(최속 랩 보너스·원천 누락 포함). 단축·중단 경기는 `points_rule_status = EXCLUDED_NONSTANDARD`로 표시한다.
- **팀 귀속:** `session_driver.team_name`(경기 당시 소속팀)으로 합산한다. 뷰 `v_race_outcome`, `v_team_race_points`가 `gold_race_outcome`·`gold_team_profile`의 기초다.
- **시계열:** `position_event`, `interval_event`, `race_control_event`는 랩당 1행이 아니므로 대리키를 쓰고, 랩·피트와는 시각 기준 as-of JOIN 또는 랩 단위 집계 후 결합한다. 격차의 `+N LAP(S)`는 `*_laps` 컬럼으로 분리하고 초 컬럼은 NULL로 둔다.

## 10. Gold 9개 마트 대응

| Gold 마트 | 주 원천 테이블 |
|---|---|
| `gold_driver_performance` | `lap`, `stint`, `session_driver`, `race_control_event`(SC/VSC 제외) |
| `gold_tyre_performance` | `stint`, `lap` |
| `gold_race_outcome` | `session_result`, `starting_grid`, `v_race_outcome` |
| `gold_pit_strategy` | `pit_event`, `position_event`, `interval_event`, `race_control_event` |
| `gold_driver_profile` | 위 드라이버 마트 + `session_result` 누적 기본 포인트 |
| `gold_team_profile` | `v_team_race_points`, `pit_event`, `stint` |
| `gold_team_pit_benchmark` | `pit_event` (`lane_duration`·`stop_duration` 분리, 격리 행 제외) |
| `gold_driver_team_fit` | 드라이버·팀 프로필 마트 |
| `gold_data_quality` | `quality_issue`, `repair_detail`, 정제 후 검증 결과(`vc_result`) |

## 11. 확정 사항과 남은 결정

1. 드라이버 동일인 기준은 `full_name`(정제 후 29명, 국적·약어 충돌 없음). `driver_id`는 대체키로 발급한다.
2. 일시는 모두 UTC로 변환해 `DATETIME(6)`에 저장한다(원본 오프셋은 전부 `+00:00`).
3. 피트 키 `session_key + driver_number + lap_number`는 현재 데이터에서 유일하다. 같은 랩 다중 피트가 생기면 `pit_event_number`를 추가한다.
4. 격리 행도 적재하고 `quarantine_flag`로 분석에서 제외한다.
5. 남은 결정: 운영 DB 이름·계정, Django 모델 연결 방식(`inspectdb`로 생성하거나 `managed = False` 모델로 이 스키마를 사용).
