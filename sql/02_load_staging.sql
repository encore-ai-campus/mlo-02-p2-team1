-- =====================================================================
-- 02_load_staging.sql : 정제 결과·추가 데이터·기준표 적재
-- 저장소 루트에서 실행한다(LOCAL INFILE 경로는 mysql 클라이언트 실행 위치 기준).
--   mysql --local-infile=1 -u <user> -p <db> < sql/02_load_staging.sql
-- 서버에 SET GLOBAL local_infile = 1; 이 필요하다.
-- 정제 결과 경로가 다르면 아래 'data/03_cleaned/'·'data/04_reports/quality/' 를 바꾼다.
-- data/01_raw/f1_extra_data.zip 은 먼저 data/01_raw/f1_extra_data/ 로 압축 해제한다 (run_web.bat·python -m pipeline.extra_data가 자동 처리).
-- CSV는 UTF-8(BOM 포함 가능)이며 헤더 1행은 건너뛴다. CRLF 파일도 마지막 컬럼의 \r을 제거한다.
-- 04 스키마가 ref_* 를 FK로 참조하므로 재적재(TRUNCATE) 동안 FK 검사를 잠시 끈다.
-- =====================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE stg_sessions;
LOAD DATA LOCAL INFILE 'data/03_cleaned/repaired/sessions.csv'
INTO TABLE stg_sessions CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`circuit_key`, `circuit_short_name`, `country_code`, `country_key`, `country_name`, `date_end`, `date_start`, `gmt_offset`, `is_cancelled`, `location`, `meeting_key`, `session_key`, `session_name`, `session_type`, `year`, `original_circuit_key`, `original_circuit_short_name`, `original_country_code`, `original_country_key`, `original_country_name`, `original_date_end`, `original_date_start`, `original_gmt_offset`, `original_is_cancelled`, `original_location`, `original_meeting_key`, `original_session_key`, `original_session_name`, `original_session_type`, `original_year`, `source_file`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`, `dq_codes`, @last_col)
SET `quarantine_flag` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_drivers;
LOAD DATA LOCAL INFILE 'data/03_cleaned/repaired/drivers.csv'
INTO TABLE stg_drivers CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`broadcast_name`, `country_code`, `driver_number`, `first_name`, `full_name`, `headshot_url`, `last_name`, `meeting_key`, `name_acronym`, `session_key`, `team_colour`, `team_name`, `original_broadcast_name`, `original_country_code`, `original_driver_number`, `original_first_name`, `original_full_name`, `original_headshot_url`, `original_last_name`, `original_meeting_key`, `original_name_acronym`, `original_session_key`, `original_team_colour`, `original_team_name`, `source_file`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`, `dq_codes`, @last_col)
SET `quarantine_flag` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_laps;
LOAD DATA LOCAL INFILE 'data/03_cleaned/repaired/laps.csv'
INTO TABLE stg_laps CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`date_start`, `driver_number`, `duration_sector_1`, `duration_sector_2`, `duration_sector_3`, `i1_speed`, `i2_speed`, `is_pit_out_lap`, `lap_duration`, `lap_number`, `meeting_key`, `segments_sector_1`, `segments_sector_2`, `segments_sector_3`, `session_key`, `st_speed`, `original_date_start`, `original_driver_number`, `original_duration_sector_1`, `original_duration_sector_2`, `original_duration_sector_3`, `original_i1_speed`, `original_i2_speed`, `original_is_pit_out_lap`, `original_lap_duration`, `original_lap_number`, `original_meeting_key`, `original_segments_sector_1`, `original_segments_sector_2`, `original_segments_sector_3`, `original_session_key`, `original_st_speed`, `source_file`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`, `dq_codes`, @last_col)
SET `quarantine_flag` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_stints;
LOAD DATA LOCAL INFILE 'data/03_cleaned/repaired/stints.csv'
INTO TABLE stg_stints CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`compound`, `driver_number`, `lap_end`, `lap_start`, `meeting_key`, `session_key`, `stint_number`, `tyre_age_at_start`, `original_compound`, `original_driver_number`, `original_lap_end`, `original_lap_start`, `original_meeting_key`, `original_session_key`, `original_stint_number`, `original_tyre_age_at_start`, `source_file`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`, `dq_codes`, @last_col)
SET `quarantine_flag` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_weather;
LOAD DATA LOCAL INFILE 'data/03_cleaned/repaired/weather.csv'
INTO TABLE stg_weather CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`air_temperature`, `date`, `humidity`, `meeting_key`, `pressure`, `rainfall`, `session_key`, `track_temperature`, `wind_direction`, `wind_speed`, `original_air_temperature`, `original_date`, `original_humidity`, `original_meeting_key`, `original_pressure`, `original_rainfall`, `original_session_key`, `original_track_temperature`, `original_wind_direction`, `original_wind_speed`, `source_file`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`, `dq_codes`, @last_col)
SET `quarantine_flag` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_pit;
LOAD DATA LOCAL INFILE 'data/03_cleaned/repaired/pit.csv'
INTO TABLE stg_pit CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`date`, `driver_number`, `lane_duration`, `lap_number`, `meeting_key`, `pit_duration`, `session_key`, `stop_duration`, `original_date`, `original_driver_number`, `original_lane_duration`, `original_lap_number`, `original_meeting_key`, `original_pit_duration`, `original_session_key`, `original_stop_duration`, `source_file`, `repair_status`, `repair_method`, `repair_confidence`, `repair_reason`, `dq_codes`, @last_col)
SET `quarantine_flag` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_starting_grid;
LOAD DATA LOCAL INFILE 'data/01_raw/f1_extra_data/starting_grid.csv'
INTO TABLE stg_starting_grid CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`position`, `driver_number`, `lap_duration`, `meeting_key`, @last_col)
SET `session_key` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_session_result;
LOAD DATA LOCAL INFILE 'data/01_raw/f1_extra_data/session_result.csv'
INTO TABLE stg_session_result CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`position`, `driver_number`, `number_of_laps`, `points`, `dnf`, `dns`, `dsq`, `duration`, `gap_to_leader`, `meeting_key`, @last_col)
SET `session_key` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_position;
LOAD DATA LOCAL INFILE 'data/01_raw/f1_extra_data/position.csv'
INTO TABLE stg_position CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`date`, `session_key`, `meeting_key`, `driver_number`, @last_col)
SET `position` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_race_control;
LOAD DATA LOCAL INFILE 'data/01_raw/f1_extra_data/race_control.csv'
INTO TABLE stg_race_control CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`meeting_key`, `session_key`, `date`, `driver_number`, `lap_number`, `category`, `flag`, `scope`, `sector`, `qualifying_phase`, @last_col)
SET `message` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_intervals;
LOAD DATA LOCAL INFILE 'data/01_raw/f1_extra_data/intervals.csv'
INTO TABLE stg_intervals CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`date`, `session_key`, `meeting_key`, `interval`, `driver_number`, @last_col)
SET `gap_to_leader` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE ref_validation_check;
LOAD DATA LOCAL INFILE 'data/02_reference/standard_dictionary/validation_checks.csv'
INTO TABLE ref_validation_check CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`check_id`, `category`, `korean_category`, `check_name`, `description`, `severity`, `expected`, @last_col)
SET `spec_ref` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE ref_race_points_rule;
LOAD DATA LOCAL INFILE 'data/02_reference/standard_dictionary/race_points_rules.csv'
INTO TABLE ref_race_points_rule CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`year`, `position`, `race_base_points`, `fastest_lap_bonus_in_source`, @last_col)
SET `note` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE ref_diagnostic;
LOAD DATA LOCAL INFILE 'data/02_reference/standard_dictionary/diagnostic_codes.csv'
INTO TABLE ref_diagnostic CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`diagnostic_code`, `diagnostic_name`, `korean_name`, `error_type`, `error_type_korean`, `severity`, `applies_to`, `condition`, `default_action`, `default_confidence`, @last_col)
SET `active` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE ref_code;
LOAD DATA LOCAL INFILE 'data/02_reference/standard_dictionary/codes.csv'
INTO TABLE ref_code CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`code_group`, `code`, `code_name`, `korean_name`, `description`, @last_col)
SET `active` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_validation_issues;
LOAD DATA LOCAL INFILE 'data/04_reports/quality/validation_issues.csv'
INTO TABLE stg_validation_issues CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`issue_id`, `diagnostic_code`, `diagnostic_name`, `korean_name`, `error_type`, `error_type_korean`, `severity`, `file`, `source_row`, `row_key`, `session_key`, `driver_number`, `field`, `observed_value`, `expected_value`, `evidence`, `action`, `status`, @last_col)
SET `confidence` = TRIM(TRAILING '\r' FROM @last_col);

TRUNCATE TABLE stg_repair_detail;
LOAD DATA LOCAL INFILE 'data/04_reports/quality/repair_detail.csv'
INTO TABLE stg_repair_detail CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
-- CRLF + 마지막 칸 따옴표라 '\n'으로는 1,335행 중 3행만 들어감 → 줄 끝을 '\r\n'으로 지정
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(`issue_id`, `diagnostic_code`, `error_type`, `file`, `source_row`, `row_key`, `session_key`, `driver_number`, `field`, `old_value`, `new_value`, `method`, `confidence`, `reason`);

TRUNCATE TABLE stg_bronze_manifest;
LOAD DATA LOCAL INFILE 'data/04_reports/quality/bronze_manifest.csv'
INTO TABLE stg_bronze_manifest CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(`file`, `rows`, `columns`, `spec_rows`, `spec_columns`, `spec_row_count`, `schema`, `column_order`, `checksum`, `encoding`, `bytes`, `sha256`, @last_col)
SET `sha256_expected` = TRIM(TRAILING '\r' FROM @last_col);

SET FOREIGN_KEY_CHECKS = 1;

-- 적재 행 수 확인
SELECT 'sessions' t, COUNT(*) n FROM stg_sessions UNION ALL SELECT 'drivers', COUNT(*) FROM stg_drivers
UNION ALL SELECT 'laps', COUNT(*) FROM stg_laps UNION ALL SELECT 'stints', COUNT(*) FROM stg_stints
UNION ALL SELECT 'weather', COUNT(*) FROM stg_weather UNION ALL SELECT 'pit', COUNT(*) FROM stg_pit
UNION ALL SELECT 'starting_grid', COUNT(*) FROM stg_starting_grid UNION ALL SELECT 'session_result', COUNT(*) FROM stg_session_result
UNION ALL SELECT 'position', COUNT(*) FROM stg_position UNION ALL SELECT 'race_control', COUNT(*) FROM stg_race_control
UNION ALL SELECT 'intervals', COUNT(*) FROM stg_intervals;
