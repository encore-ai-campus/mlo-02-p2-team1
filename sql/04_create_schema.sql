-- =====================================================================
-- 04_create_schema.sql : F1 TO-BE 정규화 스키마 (MySQL 8.0+)
-- 기준: data/schema/TO_BE_model_design.md, data/02_reference/standard_dictionary/column_dictionary.csv, F1_P2_Spec.md
-- 원천 11종(오염 정제 6종 + 추가 5종)과 품질 이력(quality_issue, repair_detail)을 담는다.
-- 데이터 적재는 05_insert_schema.sql(스테이징 → 이 스키마)에서 한다.
-- 선행: 01_create_staging.sql, 02_load_staging.sql (ref_* 기준표를 FK로 참조)
-- 실행: mysql -u <user> -p <db> < sql/04_create_schema.sql   (기존 데이터는 삭제됨)
-- =====================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS v_race_outcome;
DROP VIEW IF EXISTS v_team_race_points;
DROP TABLE IF EXISTS repair_detail, quality_issue,
  interval_event, race_control_event, position_event, session_result, starting_grid,
  weather, pit_event, stint, lap, session_driver, driver, session, meeting;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- 문자열 → 타입 변환 함수 (형식이 맞지 않으면 NULL, 0으로 바꾸지 않는다)
-- 바이너리 로그가 켜진 서버에서 권한 오류가 나면: SET GLOBAL log_bin_trust_function_creators = 1;
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS f1_num;
DROP FUNCTION IF EXISTS f1_int;
DROP FUNCTION IF EXISTS f1_bool;
DROP FUNCTION IF EXISTS f1_utc;
DROP FUNCTION IF EXISTS f1_gap_laps;
DELIMITER //
CREATE FUNCTION f1_num(v VARCHAR(255)) RETURNS DECIMAL(18,6) DETERMINISTIC NO SQL
  RETURN CASE WHEN TRIM(v) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(v) AS DECIMAL(18,6)) END //
CREATE FUNCTION f1_int(v VARCHAR(255)) RETURNS INT DETERMINISTIC NO SQL
  RETURN CASE WHEN TRIM(v) REGEXP '^-?[0-9]+([.]0+)?$' THEN CAST(CAST(TRIM(v) AS DECIMAL(18,0)) AS SIGNED) END //
CREATE FUNCTION f1_bool(v VARCHAR(255)) RETURNS TINYINT DETERMINISTIC NO SQL
  RETURN CASE TRIM(v) WHEN 'True' THEN 1 WHEN 'False' THEN 0 WHEN '1' THEN 1 WHEN '0' THEN 0 END //
-- ISO 8601(공백 또는 T 구분, 오프셋 포함 가능) → UTC DATETIME(6)
CREATE FUNCTION f1_utc(v VARCHAR(64)) RETURNS DATETIME(6) DETERMINISTIC NO SQL
  RETURN CASE WHEN TRIM(v) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:[0-9]{2}|Z)?$'
    THEN CONVERT_TZ(
           CAST(REPLACE(REGEXP_REPLACE(TRIM(v), '([+-][0-9]{2}:[0-9]{2}|Z)$', ''), 'T', ' ') AS DATETIME(6)),
           CASE WHEN TRIM(v) REGEXP '[+-][0-9]{2}:[0-9]{2}$' THEN RIGHT(TRIM(v), 6) ELSE '+00:00' END,
           '+00:00') END //
-- '+N LAP(S)' → N (숫자 격차면 NULL)
CREATE FUNCTION f1_gap_laps(v VARCHAR(255)) RETURNS SMALLINT DETERMINISTIC NO SQL
  RETURN CASE WHEN TRIM(v) REGEXP '^[+][0-9]+ LAPS?$' THEN CAST(REGEXP_SUBSTR(v, '[0-9]+') AS UNSIGNED) END //
DELIMITER ;

-- ---------------------------------------------------------------------
-- 대회·세션·드라이버
-- ---------------------------------------------------------------------
CREATE TABLE meeting (
  meeting_key         INT          NOT NULL,
  year                SMALLINT     NOT NULL,
  circuit_key         INT          NULL,
  circuit_short_name  VARCHAR(64)  NULL,
  country_key         INT          NULL,
  country_code        VARCHAR(3)   NULL,
  country_name        VARCHAR(64)  NULL,
  location            VARCHAR(128) NULL,
  gmt_offset          VARCHAR(16)  NULL,
  PRIMARY KEY (meeting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='대회·개최지';

CREATE TABLE session (
  session_key       INT          NOT NULL,
  meeting_key       INT          NOT NULL,
  session_name      VARCHAR(32)  NOT NULL,
  session_type      VARCHAR(32)  NOT NULL COMMENT 'ref_code SESSION_TYPE',
  date_start        DATETIME(6)  NOT NULL COMMENT 'UTC',
  date_end          DATETIME(6)  NOT NULL COMMENT 'UTC',
  is_cancelled      TINYINT(1)   NOT NULL,
  year              SMALLINT     NOT NULL,
  repair_status     VARCHAR(16)  NOT NULL DEFAULT 'UNCHANGED',
  quarantine_flag   CHAR(1)      NOT NULL DEFAULT 'N',
  PRIMARY KEY (session_key),
  KEY ix_session_meeting (meeting_key),
  CONSTRAINT fk_session_meeting FOREIGN KEY (meeting_key) REFERENCES meeting (meeting_key),
  CONSTRAINT ck_session_dates CHECK (date_end >= date_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Race 세션 (Qualifying은 starting_grid 원본 키로만 보존)';

CREATE TABLE driver (
  driver_id      INT          NOT NULL AUTO_INCREMENT,
  full_name      VARCHAR(128) NOT NULL,
  first_name     VARCHAR(64)  NULL,
  last_name      VARCHAR(64)  NULL,
  name_acronym   VARCHAR(3)   NULL,
  country_code   VARCHAR(3)   NULL COMMENT '드라이버 국적 (개최국 코드와 다름)',
  PRIMARY KEY (driver_id),
  UNIQUE KEY uk_driver_full_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='드라이버 마스터 (동일인 기준: full_name)';

CREATE TABLE session_driver (
  session_key      INT          NOT NULL,
  driver_number    SMALLINT     NOT NULL,
  driver_id        INT          NOT NULL,
  team_name        VARCHAR(128) NULL COMMENT '경기 당시 소속팀 (team_at_race)',
  team_colour      VARCHAR(8)   NULL,
  broadcast_name   VARCHAR(128) NULL,
  headshot_url     VARCHAR(512) NULL,
  country_code     VARCHAR(3)   NULL,
  repair_status    VARCHAR(16)  NOT NULL DEFAULT 'UNCHANGED',
  quarantine_flag  CHAR(1)      NOT NULL DEFAULT 'N',
  PRIMARY KEY (session_key, driver_number),
  KEY ix_session_driver_driver (driver_id),
  KEY ix_session_driver_team (session_key, team_name),
  CONSTRAINT fk_sd_session FOREIGN KEY (session_key) REFERENCES session (session_key),
  CONSTRAINT fk_sd_driver  FOREIGN KEY (driver_id)   REFERENCES driver (driver_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='세션별 참가자 (driver_number는 세션 맥락에서만 식별)';

-- ---------------------------------------------------------------------
-- 랩·스틴트·피트·기상 (정제 6종)
-- ---------------------------------------------------------------------
CREATE TABLE lap (
  session_key        INT           NOT NULL,
  driver_number      SMALLINT      NOT NULL,
  lap_number         SMALLINT      NOT NULL,
  date_start         DATETIME(6)   NULL COMMENT 'UTC',
  lap_duration       DECIMAL(10,3) NULL COMMENT '초',
  duration_sector_1  DECIMAL(10,3) NULL,
  duration_sector_2  DECIMAL(10,3) NULL,
  duration_sector_3  DECIMAL(10,3) NULL,
  i1_speed           DECIMAL(7,1)  NULL,
  i2_speed           DECIMAL(7,1)  NULL,
  st_speed           DECIMAL(7,1)  NULL,
  is_pit_out_lap     TINYINT(1)    NULL,
  segments_sector_1  TEXT          NULL COMMENT '목록 원문 보존',
  segments_sector_2  TEXT          NULL,
  segments_sector_3  TEXT          NULL,
  repair_status      VARCHAR(16)   NOT NULL DEFAULT 'UNCHANGED',
  repair_method      VARCHAR(255)  NULL,
  dq_codes           VARCHAR(255)  NULL,
  quarantine_flag    CHAR(1)       NOT NULL DEFAULT 'N',
  PRIMARY KEY (session_key, driver_number, lap_number),
  CONSTRAINT fk_lap_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number),
  CONSTRAINT ck_lap_duration CHECK (lap_duration IS NULL OR lap_duration > 0),
  CONSTRAINT ck_lap_number CHECK (lap_number >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stint (
  session_key        INT         NOT NULL,
  driver_number      SMALLINT    NOT NULL,
  stint_number       SMALLINT    NOT NULL,
  compound           VARCHAR(16) NOT NULL COMMENT 'ref_code COMPOUND, 결측은 UNKNOWN',
  lap_start          SMALLINT    NULL,
  lap_end            SMALLINT    NULL,
  tyre_age_at_start  SMALLINT    NULL,
  repair_status      VARCHAR(16) NOT NULL DEFAULT 'UNCHANGED',
  dq_codes           VARCHAR(255) NULL,
  quarantine_flag    CHAR(1)     NOT NULL DEFAULT 'N',
  PRIMARY KEY (session_key, driver_number, stint_number),
  KEY ix_stint_range (session_key, driver_number, lap_start, lap_end),
  CONSTRAINT fk_stint_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number),
  CONSTRAINT ck_stint_range CHECK (lap_start IS NULL OR lap_end IS NULL OR lap_end >= lap_start - 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='lap_end = lap_start - 1 빈 스틴트는 원천 특성으로 허용(DQ010)';

CREATE TABLE pit_event (
  session_key      INT           NOT NULL,
  driver_number    SMALLINT      NOT NULL,
  lap_number       SMALLINT      NOT NULL,
  event_date       DATETIME(6)   NOT NULL COMMENT 'UTC',
  lane_duration    DECIMAL(10,3) NULL COMMENT '피트레인 소요시간(초)',
  pit_duration     DECIMAL(10,3) NULL,
  stop_duration    DECIMAL(10,3) NULL COMMENT '정차시간(초), NULL을 0으로 대체 금지',
  repair_status    VARCHAR(16)   NOT NULL DEFAULT 'UNCHANGED',
  dq_codes         VARCHAR(255)  NULL,
  quarantine_flag  CHAR(1)       NOT NULL DEFAULT 'N',
  PRIMARY KEY (session_key, driver_number, lap_number),
  CONSTRAINT fk_pit_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number),
  CONSTRAINT ck_pit_nonneg CHECK ((lane_duration IS NULL OR lane_duration >= 0) AND (stop_duration IS NULL OR stop_duration >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE weather (
  session_key        INT           NOT NULL,
  observed_at        DATETIME(6)   NOT NULL COMMENT 'UTC',
  air_temperature    DECIMAL(6,2)  NULL,
  track_temperature  DECIMAL(6,2)  NULL,
  humidity           DECIMAL(6,2)  NULL,
  pressure           DECIMAL(8,2)  NULL,
  rainfall           TINYINT       NULL,
  wind_direction     SMALLINT      NULL,
  wind_speed         DECIMAL(6,2)  NULL,
  repair_status      VARCHAR(16)   NOT NULL DEFAULT 'UNCHANGED',
  dq_codes           VARCHAR(255)  NULL,
  quarantine_flag    CHAR(1)       NOT NULL DEFAULT 'N',
  PRIMARY KEY (session_key, observed_at),
  CONSTRAINT fk_weather_session FOREIGN KEY (session_key) REFERENCES session (session_key),
  CONSTRAINT ck_weather_range CHECK ((humidity IS NULL OR humidity BETWEEN 0 AND 100)
                                 AND (wind_direction IS NULL OR wind_direction BETWEEN 0 AND 360))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 추가 수집 5종
-- ---------------------------------------------------------------------
CREATE TABLE starting_grid (
  qualifying_session_key  INT           NOT NULL COMMENT '원본 session_key (Qualifying)',
  driver_number           SMALLINT      NOT NULL,
  meeting_key             INT           NOT NULL,
  race_session_key        INT           NULL COMMENT 'meeting_key로 찾은 Race session_key',
  grid_position           SMALLINT      NOT NULL,
  qualifying_lap_duration DECIMAL(10,3) NULL,
  PRIMARY KEY (qualifying_session_key, driver_number),
  UNIQUE KEY uk_grid_position (qualifying_session_key, grid_position),
  KEY ix_grid_race (race_session_key, driver_number),
  CONSTRAINT fk_grid_meeting FOREIGN KEY (meeting_key) REFERENCES meeting (meeting_key),
  CONSTRAINT fk_grid_race FOREIGN KEY (race_session_key) REFERENCES session (session_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Qualifying↔Race는 session_key 직접 JOIN 금지, meeting_key로 매핑';

CREATE TABLE session_result (
  session_key            INT           NOT NULL,
  driver_number          SMALLINT      NOT NULL,
  finish_position        SMALLINT      NULL COMMENT '미분류는 NULL',
  classification_status  VARCHAR(16)   NOT NULL COMMENT 'ref_code CLASSIFICATION_STATUS',
  number_of_laps         SMALLINT      NULL,
  dnf                    TINYINT(1)    NOT NULL,
  dns                    TINYINT(1)    NOT NULL,
  dsq                    TINYINT(1)    NOT NULL,
  duration               DECIMAL(10,3) NULL COMMENT '초',
  gap_to_leader          DECIMAL(10,3) NULL COMMENT '초',
  gap_to_leader_laps     SMALLINT      NULL COMMENT '+N LAP(S)의 N',
  source_points          DECIMAL(4,1)  NULL COMMENT '원천 points (최속 랩 보너스 포함, 분석 미사용)',
  race_base_points       DECIMAL(4,1)  NOT NULL COMMENT '본경기 기본 포인트 재계산값',
  scoring_rule_year      SMALLINT      NOT NULL,
  points_rule_status     VARCHAR(24)   NOT NULL COMMENT 'STANDARD|EXCLUDED_NONSTANDARD|NOT_CLASSIFIED',
  PRIMARY KEY (session_key, driver_number),
  UNIQUE KEY uk_result_position (session_key, finish_position),
  CONSTRAINT fk_result_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number),
  CONSTRAINT ck_result_status CHECK (dnf + dns + dsq <= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE position_event (
  position_event_id  BIGINT      NOT NULL AUTO_INCREMENT,
  session_key        INT         NOT NULL,
  driver_number      SMALLINT    NOT NULL,
  recorded_at        DATETIME(6) NOT NULL COMMENT 'UTC',
  position           SMALLINT    NOT NULL,
  PRIMARY KEY (position_event_id),
  UNIQUE KEY uk_position_event (session_key, driver_number, recorded_at),
  CONSTRAINT fk_position_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='시계열 이벤트 (랩당 1행 아님)';

CREATE TABLE race_control_event (
  race_control_event_id  BIGINT       NOT NULL AUTO_INCREMENT,
  session_key            INT          NOT NULL,
  recorded_at            DATETIME(6)  NOT NULL COMMENT 'UTC',
  driver_number          SMALLINT     NULL,
  lap_number             SMALLINT     NULL,
  category               VARCHAR(32)  NOT NULL COMMENT 'ref_code RACE_CONTROL_CATEGORY',
  flag                   VARCHAR(32)  NULL,
  scope                  VARCHAR(16)  NULL,
  sector                 SMALLINT     NULL,
  qualifying_phase       SMALLINT     NULL,
  message                VARCHAR(1000) NOT NULL,
  PRIMARY KEY (race_control_event_id),
  KEY ix_rc_session_time (session_key, recorded_at),
  KEY ix_rc_session_lap (session_key, lap_number),
  CONSTRAINT fk_rc_session FOREIGN KEY (session_key) REFERENCES session (session_key),
  CONSTRAINT fk_rc_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE interval_event (
  interval_event_id   BIGINT        NOT NULL AUTO_INCREMENT,
  session_key         INT           NOT NULL,
  driver_number       SMALLINT      NOT NULL,
  recorded_at         DATETIME(6)   NOT NULL COMMENT 'UTC',
  `interval`          DECIMAL(10,3) NULL COMMENT '앞차와 격차(초)',
  interval_laps       SMALLINT      NULL COMMENT '+N LAP(S)의 N',
  gap_to_leader       DECIMAL(10,3) NULL,
  gap_to_leader_laps  SMALLINT      NULL,
  PRIMARY KEY (interval_event_id),
  UNIQUE KEY uk_interval_event (session_key, driver_number, recorded_at),
  CONSTRAINT fk_interval_sd FOREIGN KEY (session_key, driver_number) REFERENCES session_driver (session_key, driver_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='시계열 이벤트 (약 210만 행)';

-- ---------------------------------------------------------------------
-- 품질 이력 (파이프라인 reports/)
-- ---------------------------------------------------------------------
CREATE TABLE quality_issue (
  issue_id         VARCHAR(255) NOT NULL COMMENT 'code:file:row_key:field',
  diagnostic_code  VARCHAR(8)   NOT NULL,
  error_type       VARCHAR(16)  NOT NULL,
  severity         VARCHAR(16)  NOT NULL,
  source_file      VARCHAR(64)  NOT NULL,
  row_key          VARCHAR(255) NOT NULL,
  session_key      INT          NULL,
  driver_number    SMALLINT     NULL,
  field            VARCHAR(64)  NOT NULL,
  observed_value   TEXT         NULL,
  expected_value   TEXT         NULL,
  evidence         TEXT         NULL,
  action           VARCHAR(16)  NOT NULL COMMENT 'AUTO_FIX|REVIEW|ACCEPT|QUARANTINE',
  status           VARCHAR(16)  NOT NULL COMMENT 'REPAIRED|OPEN|ACCEPTED|WAIVED',
  confidence       VARCHAR(16)  NULL,
  PRIMARY KEY (issue_id),
  KEY ix_issue_file_code (source_file, diagnostic_code, session_key),
  KEY ix_issue_status (status, severity),
  CONSTRAINT fk_issue_diagnostic FOREIGN KEY (diagnostic_code) REFERENCES ref_diagnostic (diagnostic_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE repair_detail (
  repair_detail_id  BIGINT       NOT NULL AUTO_INCREMENT,
  issue_id          VARCHAR(255) NOT NULL,
  source_file       VARCHAR(64)  NOT NULL,
  row_key           VARCHAR(255) NOT NULL,
  field             VARCHAR(64)  NOT NULL,
  old_value         TEXT         NULL,
  new_value         TEXT         NULL,
  method            VARCHAR(64)  NOT NULL COMMENT 'ref_code REPAIR_METHOD',
  confidence        VARCHAR(16)  NULL,
  reason            TEXT         NULL,
  PRIMARY KEY (repair_detail_id),
  UNIQUE KEY uk_repair_issue (issue_id),
  CONSTRAINT fk_repair_issue FOREIGN KEY (issue_id) REFERENCES quality_issue (issue_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 조회 뷰: gold_race_outcome·gold_team_profile 의 기초
-- ---------------------------------------------------------------------
CREATE VIEW v_race_outcome AS
SELECT s.year, s.meeting_key, r.session_key, r.driver_number, d.full_name, sd.team_name AS team_at_race,
       g.grid_position, r.finish_position, r.classification_status,
       r.race_base_points, r.scoring_rule_year, r.points_rule_status
FROM session_result r
JOIN session s         ON s.session_key = r.session_key
JOIN session_driver sd ON sd.session_key = r.session_key AND sd.driver_number = r.driver_number
JOIN driver d          ON d.driver_id = sd.driver_id
LEFT JOIN starting_grid g ON g.race_session_key = r.session_key AND g.driver_number = r.driver_number;

CREATE VIEW v_team_race_points AS
SELECT year, session_key, team_at_race, SUM(race_base_points) AS race_base_points
FROM v_race_outcome
GROUP BY year, session_key, team_at_race;
