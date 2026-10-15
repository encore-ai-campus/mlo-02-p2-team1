-- =====================================================================
-- 01_create_staging.sql : 정제 후 데이터 검증용 스테이징 테이블 (MySQL 8.0+)
-- 정제 결과(repaired/ 6종)와 추가 데이터 5종을 원문 문자열 그대로 적재한다.
-- 타입 변환은 검증 쿼리(03)에서 형식 확인 후에만 수행한다(변환 실패를 0으로 바꾸지 않음).
-- 실행: mysql --local-infile=1 -u <user> -p <db> < sql/01_create_staging.sql
-- 04 스키마가 ref_* 를 FK로 참조하므로 재실행할 때를 위해 FK 검사를 잠시 끈다.
-- =====================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS stg_sessions;
CREATE TABLE stg_sessions (
  `circuit_key` VARCHAR(255) NULL,
  `circuit_short_name` VARCHAR(255) NULL,
  `country_code` VARCHAR(255) NULL,
  `country_key` VARCHAR(255) NULL,
  `country_name` VARCHAR(255) NULL,
  `date_end` VARCHAR(64) NULL,
  `date_start` VARCHAR(64) NULL,
  `gmt_offset` VARCHAR(255) NULL,
  `is_cancelled` VARCHAR(255) NULL,
  `location` VARCHAR(255) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  `session_name` VARCHAR(255) NULL,
  `session_type` VARCHAR(255) NULL,
  `year` VARCHAR(255) NULL,
  `original_circuit_key` VARCHAR(255) NULL,
  `original_circuit_short_name` VARCHAR(255) NULL,
  `original_country_code` VARCHAR(255) NULL,
  `original_country_key` VARCHAR(255) NULL,
  `original_country_name` VARCHAR(255) NULL,
  `original_date_end` VARCHAR(255) NULL,
  `original_date_start` VARCHAR(255) NULL,
  `original_gmt_offset` VARCHAR(255) NULL,
  `original_is_cancelled` VARCHAR(255) NULL,
  `original_location` VARCHAR(255) NULL,
  `original_meeting_key` VARCHAR(255) NULL,
  `original_session_key` VARCHAR(255) NULL,
  `original_session_name` VARCHAR(255) NULL,
  `original_session_type` VARCHAR(255) NULL,
  `original_year` VARCHAR(255) NULL,
  `source_file` VARCHAR(255) NULL,
  `repair_status` VARCHAR(255) NULL,
  `repair_method` TEXT NULL,
  `repair_confidence` VARCHAR(255) NULL,
  `repair_reason` TEXT NULL,
  `dq_codes` TEXT NULL,
  `quarantine_flag` VARCHAR(255) NULL,
  INDEX ix_sessions_pk (`session_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_drivers;
CREATE TABLE stg_drivers (
  `broadcast_name` VARCHAR(255) NULL,
  `country_code` VARCHAR(255) NULL,
  `driver_number` VARCHAR(64) NULL,
  `first_name` VARCHAR(255) NULL,
  `full_name` VARCHAR(255) NULL,
  `headshot_url` VARCHAR(255) NULL,
  `last_name` VARCHAR(255) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `name_acronym` VARCHAR(255) NULL,
  `session_key` VARCHAR(64) NULL,
  `team_colour` VARCHAR(255) NULL,
  `team_name` VARCHAR(255) NULL,
  `original_broadcast_name` VARCHAR(255) NULL,
  `original_country_code` VARCHAR(255) NULL,
  `original_driver_number` VARCHAR(255) NULL,
  `original_first_name` VARCHAR(255) NULL,
  `original_full_name` VARCHAR(255) NULL,
  `original_headshot_url` VARCHAR(255) NULL,
  `original_last_name` VARCHAR(255) NULL,
  `original_meeting_key` VARCHAR(255) NULL,
  `original_name_acronym` VARCHAR(255) NULL,
  `original_session_key` VARCHAR(255) NULL,
  `original_team_colour` VARCHAR(255) NULL,
  `original_team_name` VARCHAR(255) NULL,
  `source_file` VARCHAR(255) NULL,
  `repair_status` VARCHAR(255) NULL,
  `repair_method` TEXT NULL,
  `repair_confidence` VARCHAR(255) NULL,
  `repair_reason` TEXT NULL,
  `dq_codes` TEXT NULL,
  `quarantine_flag` VARCHAR(255) NULL,
  INDEX ix_drivers_k (`session_key`, `driver_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_laps;
CREATE TABLE stg_laps (
  `date_start` VARCHAR(64) NULL,
  `driver_number` VARCHAR(64) NULL,
  `duration_sector_1` VARCHAR(255) NULL,
  `duration_sector_2` VARCHAR(255) NULL,
  `duration_sector_3` VARCHAR(255) NULL,
  `i1_speed` VARCHAR(255) NULL,
  `i2_speed` VARCHAR(255) NULL,
  `is_pit_out_lap` VARCHAR(255) NULL,
  `lap_duration` VARCHAR(255) NULL,
  `lap_number` VARCHAR(64) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `segments_sector_1` TEXT NULL,
  `segments_sector_2` TEXT NULL,
  `segments_sector_3` TEXT NULL,
  `session_key` VARCHAR(64) NULL,
  `st_speed` VARCHAR(255) NULL,
  `original_date_start` VARCHAR(255) NULL,
  `original_driver_number` VARCHAR(255) NULL,
  `original_duration_sector_1` VARCHAR(255) NULL,
  `original_duration_sector_2` VARCHAR(255) NULL,
  `original_duration_sector_3` VARCHAR(255) NULL,
  `original_i1_speed` VARCHAR(255) NULL,
  `original_i2_speed` VARCHAR(255) NULL,
  `original_is_pit_out_lap` VARCHAR(255) NULL,
  `original_lap_duration` VARCHAR(255) NULL,
  `original_lap_number` VARCHAR(255) NULL,
  `original_meeting_key` VARCHAR(255) NULL,
  `original_segments_sector_1` TEXT NULL,
  `original_segments_sector_2` TEXT NULL,
  `original_segments_sector_3` TEXT NULL,
  `original_session_key` VARCHAR(255) NULL,
  `original_st_speed` VARCHAR(255) NULL,
  `source_file` VARCHAR(255) NULL,
  `repair_status` VARCHAR(255) NULL,
  `repair_method` TEXT NULL,
  `repair_confidence` VARCHAR(255) NULL,
  `repair_reason` TEXT NULL,
  `dq_codes` TEXT NULL,
  `quarantine_flag` VARCHAR(255) NULL,
  INDEX ix_laps_k (`session_key`, `driver_number`, `lap_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_stints;
CREATE TABLE stg_stints (
  `compound` VARCHAR(255) NULL,
  `driver_number` VARCHAR(64) NULL,
  `lap_end` VARCHAR(255) NULL,
  `lap_start` VARCHAR(255) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  `stint_number` VARCHAR(64) NULL,
  `tyre_age_at_start` VARCHAR(255) NULL,
  `original_compound` VARCHAR(255) NULL,
  `original_driver_number` VARCHAR(255) NULL,
  `original_lap_end` VARCHAR(255) NULL,
  `original_lap_start` VARCHAR(255) NULL,
  `original_meeting_key` VARCHAR(255) NULL,
  `original_session_key` VARCHAR(255) NULL,
  `original_stint_number` VARCHAR(255) NULL,
  `original_tyre_age_at_start` VARCHAR(255) NULL,
  `source_file` VARCHAR(255) NULL,
  `repair_status` VARCHAR(255) NULL,
  `repair_method` TEXT NULL,
  `repair_confidence` VARCHAR(255) NULL,
  `repair_reason` TEXT NULL,
  `dq_codes` TEXT NULL,
  `quarantine_flag` VARCHAR(255) NULL,
  INDEX ix_stints_k (`session_key`, `driver_number`, `stint_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_weather;
CREATE TABLE stg_weather (
  `air_temperature` VARCHAR(255) NULL,
  `date` VARCHAR(64) NULL,
  `humidity` VARCHAR(255) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `pressure` VARCHAR(255) NULL,
  `rainfall` VARCHAR(255) NULL,
  `session_key` VARCHAR(64) NULL,
  `track_temperature` VARCHAR(255) NULL,
  `wind_direction` VARCHAR(255) NULL,
  `wind_speed` VARCHAR(255) NULL,
  `original_air_temperature` VARCHAR(255) NULL,
  `original_date` VARCHAR(255) NULL,
  `original_humidity` VARCHAR(255) NULL,
  `original_meeting_key` VARCHAR(255) NULL,
  `original_pressure` VARCHAR(255) NULL,
  `original_rainfall` VARCHAR(255) NULL,
  `original_session_key` VARCHAR(255) NULL,
  `original_track_temperature` VARCHAR(255) NULL,
  `original_wind_direction` VARCHAR(255) NULL,
  `original_wind_speed` VARCHAR(255) NULL,
  `source_file` VARCHAR(255) NULL,
  `repair_status` VARCHAR(255) NULL,
  `repair_method` TEXT NULL,
  `repair_confidence` VARCHAR(255) NULL,
  `repair_reason` TEXT NULL,
  `dq_codes` TEXT NULL,
  `quarantine_flag` VARCHAR(255) NULL,
  INDEX ix_weather_k (`session_key`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_pit;
CREATE TABLE stg_pit (
  `date` VARCHAR(64) NULL,
  `driver_number` VARCHAR(64) NULL,
  `lane_duration` VARCHAR(255) NULL,
  `lap_number` VARCHAR(64) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `pit_duration` VARCHAR(255) NULL,
  `session_key` VARCHAR(64) NULL,
  `stop_duration` VARCHAR(255) NULL,
  `original_date` VARCHAR(255) NULL,
  `original_driver_number` VARCHAR(255) NULL,
  `original_lane_duration` VARCHAR(255) NULL,
  `original_lap_number` VARCHAR(255) NULL,
  `original_meeting_key` VARCHAR(255) NULL,
  `original_pit_duration` VARCHAR(255) NULL,
  `original_session_key` VARCHAR(255) NULL,
  `original_stop_duration` VARCHAR(255) NULL,
  `source_file` VARCHAR(255) NULL,
  `repair_status` VARCHAR(255) NULL,
  `repair_method` TEXT NULL,
  `repair_confidence` VARCHAR(255) NULL,
  `repair_reason` TEXT NULL,
  `dq_codes` TEXT NULL,
  `quarantine_flag` VARCHAR(255) NULL,
  INDEX ix_pit_k (`session_key`, `driver_number`, `lap_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_starting_grid;
CREATE TABLE stg_starting_grid (
  `position` VARCHAR(64) NULL,
  `driver_number` VARCHAR(64) NULL,
  `lap_duration` VARCHAR(255) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  INDEX ix_starting_grid_k (`session_key`, `driver_number`),
  INDEX ix_starting_grid_m (`meeting_key`, `driver_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_session_result;
CREATE TABLE stg_session_result (
  `position` VARCHAR(64) NULL,
  `driver_number` VARCHAR(64) NULL,
  `number_of_laps` VARCHAR(255) NULL,
  `points` VARCHAR(255) NULL,
  `dnf` VARCHAR(255) NULL,
  `dns` VARCHAR(255) NULL,
  `dsq` VARCHAR(255) NULL,
  `duration` VARCHAR(255) NULL,
  `gap_to_leader` VARCHAR(255) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  INDEX ix_session_result_k (`session_key`, `driver_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_position;
CREATE TABLE stg_position (
  `date` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `driver_number` VARCHAR(64) NULL,
  `position` VARCHAR(64) NULL,
  INDEX ix_position_k (`session_key`, `driver_number`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_race_control;
CREATE TABLE stg_race_control (
  `meeting_key` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  `date` VARCHAR(64) NULL,
  `driver_number` VARCHAR(64) NULL,
  `lap_number` VARCHAR(64) NULL,
  `category` VARCHAR(255) NULL,
  `flag` VARCHAR(255) NULL,
  `scope` VARCHAR(255) NULL,
  `sector` VARCHAR(255) NULL,
  `qualifying_phase` VARCHAR(255) NULL,
  `message` TEXT NULL,
  INDEX ix_race_control_k (`session_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

DROP TABLE IF EXISTS stg_intervals;
CREATE TABLE stg_intervals (
  `date` VARCHAR(64) NULL,
  `session_key` VARCHAR(64) NULL,
  `meeting_key` VARCHAR(64) NULL,
  `interval` VARCHAR(255) NULL,
  `driver_number` VARCHAR(64) NULL,
  `gap_to_leader` VARCHAR(255) NULL,
  INDEX ix_intervals_k (`session_key`, `driver_number`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- 기준 테이블: 검증 항목 카탈로그, 본경기 기본 배점표, Bronze 매니페스트
DROP TABLE IF EXISTS ref_validation_check;
CREATE TABLE ref_validation_check (
  check_id VARCHAR(8) PRIMARY KEY, category VARCHAR(32), korean_category VARCHAR(32),
  check_name VARCHAR(64), description VARCHAR(500), severity VARCHAR(16), expected VARCHAR(8), spec_ref VARCHAR(32)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS ref_race_points_rule;
CREATE TABLE ref_race_points_rule (
  year SMALLINT NOT NULL, position SMALLINT NOT NULL, race_base_points DECIMAL(5,1) NOT NULL,
  fastest_lap_bonus_in_source CHAR(1), note VARCHAR(200), PRIMARY KEY (year, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS ref_diagnostic;
CREATE TABLE ref_diagnostic (
  diagnostic_code VARCHAR(8) PRIMARY KEY, diagnostic_name VARCHAR(64), korean_name VARCHAR(64), error_type VARCHAR(16),
  error_type_korean VARCHAR(32), severity VARCHAR(16), applies_to VARCHAR(255), `condition` VARCHAR(500),
  default_action VARCHAR(500), default_confidence VARCHAR(16), active CHAR(1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS ref_code;
CREATE TABLE ref_code (
  code_group VARCHAR(32), code VARCHAR(64), code_name VARCHAR(64), korean_name VARCHAR(64),
  description VARCHAR(500), active CHAR(1), PRIMARY KEY (code_group, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 파이프라인 리포트(복구 이력) 스테이징
DROP TABLE IF EXISTS stg_validation_issues;
CREATE TABLE stg_validation_issues (
  issue_id VARCHAR(255), diagnostic_code VARCHAR(8), diagnostic_name VARCHAR(64), korean_name VARCHAR(64),
  error_type VARCHAR(16), error_type_korean VARCHAR(32), severity VARCHAR(16), file VARCHAR(64), source_row VARCHAR(16),
  row_key VARCHAR(255), session_key VARCHAR(64), driver_number VARCHAR(64), field VARCHAR(64), observed_value TEXT,
  expected_value TEXT, evidence TEXT, action VARCHAR(16), status VARCHAR(16), confidence VARCHAR(16)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS stg_repair_detail;
CREATE TABLE stg_repair_detail (
  issue_id VARCHAR(255), diagnostic_code VARCHAR(8), error_type VARCHAR(16), file VARCHAR(64), source_row VARCHAR(16),
  row_key VARCHAR(255), session_key VARCHAR(64), driver_number VARCHAR(64), field VARCHAR(64), old_value TEXT,
  new_value TEXT, method VARCHAR(64), confidence VARCHAR(16), reason TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS stg_bronze_manifest;
CREATE TABLE stg_bronze_manifest (
  file VARCHAR(64), `rows` BIGINT, `columns` INT, spec_rows VARCHAR(16), spec_columns VARCHAR(16),
  spec_row_count VARCHAR(16), `schema` VARCHAR(16), column_order VARCHAR(16), checksum VARCHAR(16),
  encoding VARCHAR(16), bytes BIGINT, sha256 VARCHAR(64), sha256_expected VARCHAR(64)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
