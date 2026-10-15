-- [MySQL 8.4 호환 수정본] 원본: sql/03_validate_cleaned.sql
-- 1) MySQL은 TEMPORARY TABLE을 한 쿼리에서 두 번 참조할 수 없어(ERROR 1137) 작업 테이블 t_*를 일반 테이블로 바꿈
-- 2) 28행 빈 position의 CAST가 STRICT 모드에서 오류(ERROR 1292)라 CASE로 감쌈
-- =====================================================================
-- 03_validate_cleaned.sql : 정제 후 데이터 검증 쿼리 (MySQL 8.0+)
-- 검사 ID는 data/02_reference/standard_dictionary/validation_checks.csv (VC01~VC71)와 같고,
-- pipeline/validate_cleaned.py(pandas)와 같은 규칙이다.
-- 결과: vc_result (검사 × 대상별 위반 건수) → 마지막 SELECT가 PASS/FAIL/WARN/INFO를 붙여 보여준다.
-- 각 블록 아래 '상세 조회' 주석의 쿼리로 위반 행을 직접 볼 수 있다.
-- 실행: mysql -u <user> -p <db> < sql/03_validate_cleaned.sql
-- =====================================================================
SET NAMES utf8mb4;
SET SESSION group_concat_max_len = 100000;

DROP TABLE IF EXISTS vc_result;
CREATE TABLE vc_result (
  id INT AUTO_INCREMENT PRIMARY KEY,
  check_id VARCHAR(8) NOT NULL,
  target VARCHAR(64) NOT NULL,
  fail_count BIGINT NOT NULL,
  total_count BIGINT NOT NULL,
  note VARCHAR(500) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Race 세션과 기본 포인트 (VC23~VC25, VC50~VC53에서 사용)
DROP TABLE IF EXISTS t_race;
CREATE TABLE t_race (INDEX (meeting_key), INDEX (session_key)) AS
SELECT session_key, meeting_key, year FROM stg_sessions WHERE session_type = 'Race';

DROP TABLE IF EXISTS t_result_points;
CREATE TABLE t_result_points (INDEX (session_key, driver_number)) AS
SELECT r.session_key, r.driver_number, r.position, r.points, s.year,
       COALESCE(p.race_base_points, 0) AS race_base_points
FROM stg_session_result r
JOIN t_race s ON s.session_key = r.session_key
LEFT JOIN ref_race_points_rule p
       ON p.year = CAST(s.year AS UNSIGNED)
      AND p.position = CAST(CASE WHEN r.position REGEXP '^[0-9]+$' THEN r.position END AS UNSIGNED);

-- 드라이버별 최대 랩 (VC26, VC44)
DROP TABLE IF EXISTS t_max_lap;
CREATE TABLE t_max_lap (PRIMARY KEY (session_key, driver_number)) AS
SELECT session_key, driver_number, MAX((CASE WHEN TRIM(lap_number) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(lap_number) AS DECIMAL(18,6)) END)) AS max_lap
FROM stg_laps GROUP BY session_key, driver_number;

-- ===================== 결측 =====================
-- VC01 식별키·meeting_key 공백
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'sessions', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_sessions;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'drivers', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_drivers;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'laps', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`lap_number`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'stints', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`stint_number`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_stints;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'weather', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`date`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_weather;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'pit', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`lap_number`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_pit;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'starting_grid', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_starting_grid;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'session_result', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_session_result;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'position', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`date`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_position;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'race_control', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`date`,'')) = '') OR (TRIM(COALESCE(`category`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_race_control;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC01', 'intervals', SUM((TRIM(COALESCE(`session_key`,'')) = '') OR (TRIM(COALESCE(`driver_number`,'')) = '') OR (TRIM(COALESCE(`date`,'')) = '') OR (TRIM(COALESCE(`meeting_key`,'')) = '')), COUNT(*), NULL FROM stg_intervals;

-- VC02 컬럼별 공백 프로파일 (INFO) : 테이블별 공백 셀 합계를 기록하고, 컬럼별 상세는 vc_null_profile에 남긴다.
DROP TABLE IF EXISTS vc_null_profile;
CREATE TABLE vc_null_profile (table_name VARCHAR(64), column_name VARCHAR(64), `rows` BIGINT, blank BIGINT,
  blank_rate DECIMAL(9,6)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT INTO vc_null_profile
SELECT 'sessions', 'circuit_key', COUNT(*), SUM((TRIM(COALESCE(`circuit_key`,'')) = '')), SUM((TRIM(COALESCE(`circuit_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'circuit_short_name', COUNT(*), SUM((TRIM(COALESCE(`circuit_short_name`,'')) = '')), SUM((TRIM(COALESCE(`circuit_short_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'country_code', COUNT(*), SUM((TRIM(COALESCE(`country_code`,'')) = '')), SUM((TRIM(COALESCE(`country_code`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'country_key', COUNT(*), SUM((TRIM(COALESCE(`country_key`,'')) = '')), SUM((TRIM(COALESCE(`country_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'country_name', COUNT(*), SUM((TRIM(COALESCE(`country_name`,'')) = '')), SUM((TRIM(COALESCE(`country_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'date_end', COUNT(*), SUM((TRIM(COALESCE(`date_end`,'')) = '')), SUM((TRIM(COALESCE(`date_end`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'date_start', COUNT(*), SUM((TRIM(COALESCE(`date_start`,'')) = '')), SUM((TRIM(COALESCE(`date_start`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'gmt_offset', COUNT(*), SUM((TRIM(COALESCE(`gmt_offset`,'')) = '')), SUM((TRIM(COALESCE(`gmt_offset`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'is_cancelled', COUNT(*), SUM((TRIM(COALESCE(`is_cancelled`,'')) = '')), SUM((TRIM(COALESCE(`is_cancelled`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'location', COUNT(*), SUM((TRIM(COALESCE(`location`,'')) = '')), SUM((TRIM(COALESCE(`location`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'session_name', COUNT(*), SUM((TRIM(COALESCE(`session_name`,'')) = '')), SUM((TRIM(COALESCE(`session_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'session_type', COUNT(*), SUM((TRIM(COALESCE(`session_type`,'')) = '')), SUM((TRIM(COALESCE(`session_type`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions
UNION ALL SELECT 'sessions', 'year', COUNT(*), SUM((TRIM(COALESCE(`year`,'')) = '')), SUM((TRIM(COALESCE(`year`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_sessions;
INSERT INTO vc_null_profile
SELECT 'drivers', 'broadcast_name', COUNT(*), SUM((TRIM(COALESCE(`broadcast_name`,'')) = '')), SUM((TRIM(COALESCE(`broadcast_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'country_code', COUNT(*), SUM((TRIM(COALESCE(`country_code`,'')) = '')), SUM((TRIM(COALESCE(`country_code`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'first_name', COUNT(*), SUM((TRIM(COALESCE(`first_name`,'')) = '')), SUM((TRIM(COALESCE(`first_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'full_name', COUNT(*), SUM((TRIM(COALESCE(`full_name`,'')) = '')), SUM((TRIM(COALESCE(`full_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'headshot_url', COUNT(*), SUM((TRIM(COALESCE(`headshot_url`,'')) = '')), SUM((TRIM(COALESCE(`headshot_url`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'last_name', COUNT(*), SUM((TRIM(COALESCE(`last_name`,'')) = '')), SUM((TRIM(COALESCE(`last_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'name_acronym', COUNT(*), SUM((TRIM(COALESCE(`name_acronym`,'')) = '')), SUM((TRIM(COALESCE(`name_acronym`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'team_colour', COUNT(*), SUM((TRIM(COALESCE(`team_colour`,'')) = '')), SUM((TRIM(COALESCE(`team_colour`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers
UNION ALL SELECT 'drivers', 'team_name', COUNT(*), SUM((TRIM(COALESCE(`team_name`,'')) = '')), SUM((TRIM(COALESCE(`team_name`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_drivers;
INSERT INTO vc_null_profile
SELECT 'laps', 'date_start', COUNT(*), SUM((TRIM(COALESCE(`date_start`,'')) = '')), SUM((TRIM(COALESCE(`date_start`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'duration_sector_1', COUNT(*), SUM((TRIM(COALESCE(`duration_sector_1`,'')) = '')), SUM((TRIM(COALESCE(`duration_sector_1`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'duration_sector_2', COUNT(*), SUM((TRIM(COALESCE(`duration_sector_2`,'')) = '')), SUM((TRIM(COALESCE(`duration_sector_2`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'duration_sector_3', COUNT(*), SUM((TRIM(COALESCE(`duration_sector_3`,'')) = '')), SUM((TRIM(COALESCE(`duration_sector_3`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'i1_speed', COUNT(*), SUM((TRIM(COALESCE(`i1_speed`,'')) = '')), SUM((TRIM(COALESCE(`i1_speed`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'i2_speed', COUNT(*), SUM((TRIM(COALESCE(`i2_speed`,'')) = '')), SUM((TRIM(COALESCE(`i2_speed`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'is_pit_out_lap', COUNT(*), SUM((TRIM(COALESCE(`is_pit_out_lap`,'')) = '')), SUM((TRIM(COALESCE(`is_pit_out_lap`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'lap_duration', COUNT(*), SUM((TRIM(COALESCE(`lap_duration`,'')) = '')), SUM((TRIM(COALESCE(`lap_duration`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'lap_number', COUNT(*), SUM((TRIM(COALESCE(`lap_number`,'')) = '')), SUM((TRIM(COALESCE(`lap_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'segments_sector_1', COUNT(*), SUM((TRIM(COALESCE(`segments_sector_1`,'')) = '')), SUM((TRIM(COALESCE(`segments_sector_1`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'segments_sector_2', COUNT(*), SUM((TRIM(COALESCE(`segments_sector_2`,'')) = '')), SUM((TRIM(COALESCE(`segments_sector_2`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'segments_sector_3', COUNT(*), SUM((TRIM(COALESCE(`segments_sector_3`,'')) = '')), SUM((TRIM(COALESCE(`segments_sector_3`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps
UNION ALL SELECT 'laps', 'st_speed', COUNT(*), SUM((TRIM(COALESCE(`st_speed`,'')) = '')), SUM((TRIM(COALESCE(`st_speed`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_laps;
INSERT INTO vc_null_profile
SELECT 'stints', 'compound', COUNT(*), SUM((TRIM(COALESCE(`compound`,'')) = '')), SUM((TRIM(COALESCE(`compound`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'lap_end', COUNT(*), SUM((TRIM(COALESCE(`lap_end`,'')) = '')), SUM((TRIM(COALESCE(`lap_end`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'lap_start', COUNT(*), SUM((TRIM(COALESCE(`lap_start`,'')) = '')), SUM((TRIM(COALESCE(`lap_start`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'stint_number', COUNT(*), SUM((TRIM(COALESCE(`stint_number`,'')) = '')), SUM((TRIM(COALESCE(`stint_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints
UNION ALL SELECT 'stints', 'tyre_age_at_start', COUNT(*), SUM((TRIM(COALESCE(`tyre_age_at_start`,'')) = '')), SUM((TRIM(COALESCE(`tyre_age_at_start`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_stints;
INSERT INTO vc_null_profile
SELECT 'weather', 'air_temperature', COUNT(*), SUM((TRIM(COALESCE(`air_temperature`,'')) = '')), SUM((TRIM(COALESCE(`air_temperature`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'date', COUNT(*), SUM((TRIM(COALESCE(`date`,'')) = '')), SUM((TRIM(COALESCE(`date`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'humidity', COUNT(*), SUM((TRIM(COALESCE(`humidity`,'')) = '')), SUM((TRIM(COALESCE(`humidity`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'pressure', COUNT(*), SUM((TRIM(COALESCE(`pressure`,'')) = '')), SUM((TRIM(COALESCE(`pressure`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'rainfall', COUNT(*), SUM((TRIM(COALESCE(`rainfall`,'')) = '')), SUM((TRIM(COALESCE(`rainfall`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'track_temperature', COUNT(*), SUM((TRIM(COALESCE(`track_temperature`,'')) = '')), SUM((TRIM(COALESCE(`track_temperature`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'wind_direction', COUNT(*), SUM((TRIM(COALESCE(`wind_direction`,'')) = '')), SUM((TRIM(COALESCE(`wind_direction`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather
UNION ALL SELECT 'weather', 'wind_speed', COUNT(*), SUM((TRIM(COALESCE(`wind_speed`,'')) = '')), SUM((TRIM(COALESCE(`wind_speed`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_weather;
INSERT INTO vc_null_profile
SELECT 'pit', 'date', COUNT(*), SUM((TRIM(COALESCE(`date`,'')) = '')), SUM((TRIM(COALESCE(`date`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'lane_duration', COUNT(*), SUM((TRIM(COALESCE(`lane_duration`,'')) = '')), SUM((TRIM(COALESCE(`lane_duration`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'lap_number', COUNT(*), SUM((TRIM(COALESCE(`lap_number`,'')) = '')), SUM((TRIM(COALESCE(`lap_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'pit_duration', COUNT(*), SUM((TRIM(COALESCE(`pit_duration`,'')) = '')), SUM((TRIM(COALESCE(`pit_duration`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit
UNION ALL SELECT 'pit', 'stop_duration', COUNT(*), SUM((TRIM(COALESCE(`stop_duration`,'')) = '')), SUM((TRIM(COALESCE(`stop_duration`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_pit;
INSERT INTO vc_null_profile
SELECT 'starting_grid', 'position', COUNT(*), SUM((TRIM(COALESCE(`position`,'')) = '')), SUM((TRIM(COALESCE(`position`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_starting_grid
UNION ALL SELECT 'starting_grid', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_starting_grid
UNION ALL SELECT 'starting_grid', 'lap_duration', COUNT(*), SUM((TRIM(COALESCE(`lap_duration`,'')) = '')), SUM((TRIM(COALESCE(`lap_duration`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_starting_grid
UNION ALL SELECT 'starting_grid', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_starting_grid
UNION ALL SELECT 'starting_grid', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_starting_grid;
INSERT INTO vc_null_profile
SELECT 'session_result', 'position', COUNT(*), SUM((TRIM(COALESCE(`position`,'')) = '')), SUM((TRIM(COALESCE(`position`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'number_of_laps', COUNT(*), SUM((TRIM(COALESCE(`number_of_laps`,'')) = '')), SUM((TRIM(COALESCE(`number_of_laps`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'points', COUNT(*), SUM((TRIM(COALESCE(`points`,'')) = '')), SUM((TRIM(COALESCE(`points`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'dnf', COUNT(*), SUM((TRIM(COALESCE(`dnf`,'')) = '')), SUM((TRIM(COALESCE(`dnf`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'dns', COUNT(*), SUM((TRIM(COALESCE(`dns`,'')) = '')), SUM((TRIM(COALESCE(`dns`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'dsq', COUNT(*), SUM((TRIM(COALESCE(`dsq`,'')) = '')), SUM((TRIM(COALESCE(`dsq`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'duration', COUNT(*), SUM((TRIM(COALESCE(`duration`,'')) = '')), SUM((TRIM(COALESCE(`duration`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'gap_to_leader', COUNT(*), SUM((TRIM(COALESCE(`gap_to_leader`,'')) = '')), SUM((TRIM(COALESCE(`gap_to_leader`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result
UNION ALL SELECT 'session_result', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_session_result;
INSERT INTO vc_null_profile
SELECT 'position', 'date', COUNT(*), SUM((TRIM(COALESCE(`date`,'')) = '')), SUM((TRIM(COALESCE(`date`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_position
UNION ALL SELECT 'position', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_position
UNION ALL SELECT 'position', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_position
UNION ALL SELECT 'position', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_position
UNION ALL SELECT 'position', 'position', COUNT(*), SUM((TRIM(COALESCE(`position`,'')) = '')), SUM((TRIM(COALESCE(`position`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_position;
INSERT INTO vc_null_profile
SELECT 'race_control', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'date', COUNT(*), SUM((TRIM(COALESCE(`date`,'')) = '')), SUM((TRIM(COALESCE(`date`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'lap_number', COUNT(*), SUM((TRIM(COALESCE(`lap_number`,'')) = '')), SUM((TRIM(COALESCE(`lap_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'category', COUNT(*), SUM((TRIM(COALESCE(`category`,'')) = '')), SUM((TRIM(COALESCE(`category`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'flag', COUNT(*), SUM((TRIM(COALESCE(`flag`,'')) = '')), SUM((TRIM(COALESCE(`flag`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'scope', COUNT(*), SUM((TRIM(COALESCE(`scope`,'')) = '')), SUM((TRIM(COALESCE(`scope`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'sector', COUNT(*), SUM((TRIM(COALESCE(`sector`,'')) = '')), SUM((TRIM(COALESCE(`sector`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'qualifying_phase', COUNT(*), SUM((TRIM(COALESCE(`qualifying_phase`,'')) = '')), SUM((TRIM(COALESCE(`qualifying_phase`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control
UNION ALL SELECT 'race_control', 'message', COUNT(*), SUM((TRIM(COALESCE(`message`,'')) = '')), SUM((TRIM(COALESCE(`message`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_race_control;
INSERT INTO vc_null_profile
SELECT 'intervals', 'date', COUNT(*), SUM((TRIM(COALESCE(`date`,'')) = '')), SUM((TRIM(COALESCE(`date`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_intervals
UNION ALL SELECT 'intervals', 'session_key', COUNT(*), SUM((TRIM(COALESCE(`session_key`,'')) = '')), SUM((TRIM(COALESCE(`session_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_intervals
UNION ALL SELECT 'intervals', 'meeting_key', COUNT(*), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')), SUM((TRIM(COALESCE(`meeting_key`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_intervals
UNION ALL SELECT 'intervals', 'interval', COUNT(*), SUM((TRIM(COALESCE(`interval`,'')) = '')), SUM((TRIM(COALESCE(`interval`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_intervals
UNION ALL SELECT 'intervals', 'driver_number', COUNT(*), SUM((TRIM(COALESCE(`driver_number`,'')) = '')), SUM((TRIM(COALESCE(`driver_number`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_intervals
UNION ALL SELECT 'intervals', 'gap_to_leader', COUNT(*), SUM((TRIM(COALESCE(`gap_to_leader`,'')) = '')), SUM((TRIM(COALESCE(`gap_to_leader`,'')) = '')) / NULLIF(COUNT(*),0) FROM stg_intervals;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC02', table_name, SUM(blank), SUM(`rows`), 'vc_null_profile 참고' FROM vc_null_profile GROUP BY table_name;

-- VC03 원본 공백인데 정제 후 0으로 채워진 시간·속도 값
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC03', 'laps', COALESCE(SUM(((TRIM(COALESCE(`original_lap_duration`,'')) = '') AND (CASE WHEN TRIM(`lap_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_duration`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_duration_sector_1`,'')) = '') AND (CASE WHEN TRIM(`duration_sector_1`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration_sector_1`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_duration_sector_2`,'')) = '') AND (CASE WHEN TRIM(`duration_sector_2`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration_sector_2`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_duration_sector_3`,'')) = '') AND (CASE WHEN TRIM(`duration_sector_3`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration_sector_3`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_i1_speed`,'')) = '') AND (CASE WHEN TRIM(`i1_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`i1_speed`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_i2_speed`,'')) = '') AND (CASE WHEN TRIM(`i2_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`i2_speed`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_st_speed`,'')) = '') AND (CASE WHEN TRIM(`st_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`st_speed`) AS DECIMAL(18,6)) END) = 0)),0), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC03', 'pit', COALESCE(SUM(((TRIM(COALESCE(`original_lane_duration`,'')) = '') AND (CASE WHEN TRIM(`lane_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lane_duration`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_pit_duration`,'')) = '') AND (CASE WHEN TRIM(`pit_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`pit_duration`) AS DECIMAL(18,6)) END) = 0) OR ((TRIM(COALESCE(`original_stop_duration`,'')) = '') AND (CASE WHEN TRIM(`stop_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`stop_duration`) AS DECIMAL(18,6)) END) = 0)),0), COUNT(*), NULL FROM stg_pit;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC03', 'stints', COALESCE(SUM(((TRIM(COALESCE(`original_tyre_age_at_start`,'')) = '') AND (CASE WHEN TRIM(`tyre_age_at_start`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`tyre_age_at_start`) AS DECIMAL(18,6)) END) = 0)),0), COUNT(*), NULL FROM stg_stints;

-- VC04 순위 공백인데 dnf·dns·dsq 모두 False
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC04', 'session_result',
       SUM(TRIM(position) = '' AND dnf <> 'True' AND dns <> 'True' AND dsq <> 'True'), COUNT(*), NULL
FROM stg_session_result;
-- 상세 조회: SELECT * FROM stg_session_result WHERE TRIM(position)='' AND dnf<>'True' AND dns<>'True' AND dsq<>'True';

-- ===================== 중복 =====================
-- VC10 자연키 중복 (초과 행 수)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'sessions', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_sessions), NULL
FROM (SELECT COUNT(*) n FROM stg_sessions GROUP BY `session_key` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'drivers', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_drivers), NULL
FROM (SELECT COUNT(*) n FROM stg_drivers GROUP BY `session_key`, `driver_number` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'laps', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_laps), NULL
FROM (SELECT COUNT(*) n FROM stg_laps GROUP BY `session_key`, `driver_number`, `lap_number` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'stints', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_stints), NULL
FROM (SELECT COUNT(*) n FROM stg_stints GROUP BY `session_key`, `driver_number`, `stint_number` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'weather', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_weather), NULL
FROM (SELECT COUNT(*) n FROM stg_weather GROUP BY `session_key`, `date` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'pit', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_pit), NULL
FROM (SELECT COUNT(*) n FROM stg_pit GROUP BY `session_key`, `driver_number`, `lap_number` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'starting_grid', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_starting_grid), NULL
FROM (SELECT COUNT(*) n FROM stg_starting_grid GROUP BY `session_key`, `driver_number` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'session_result', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_session_result), NULL
FROM (SELECT COUNT(*) n FROM stg_session_result GROUP BY `session_key`, `driver_number` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'position', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_position), NULL
FROM (SELECT COUNT(*) n FROM stg_position GROUP BY `session_key`, `driver_number`, `date` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC10', 'intervals', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_intervals), NULL
FROM (SELECT COUNT(*) n FROM stg_intervals GROUP BY `session_key`, `driver_number`, `date` HAVING COUNT(*) > 1) d;

-- 상세 조회 예: SELECT session_key, driver_number, lap_number, COUNT(*) FROM stg_laps GROUP BY 1,2,3 HAVING COUNT(*) > 1;
-- VC11 모든 업무 컬럼이 같은 완전 중복 행
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'sessions', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_sessions), NULL
FROM (SELECT COUNT(*) n FROM stg_sessions GROUP BY `circuit_key`, `circuit_short_name`, `country_code`, `country_key`, `country_name`, `date_end`, `date_start`, `gmt_offset`, `is_cancelled`, `location`, `meeting_key`, `session_key`, `session_name`, `session_type`, `year` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'drivers', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_drivers), NULL
FROM (SELECT COUNT(*) n FROM stg_drivers GROUP BY `broadcast_name`, `country_code`, `driver_number`, `first_name`, `full_name`, `headshot_url`, `last_name`, `meeting_key`, `name_acronym`, `session_key`, `team_colour`, `team_name` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'laps', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_laps), NULL
FROM (SELECT COUNT(*) n FROM stg_laps GROUP BY `date_start`, `driver_number`, `duration_sector_1`, `duration_sector_2`, `duration_sector_3`, `i1_speed`, `i2_speed`, `is_pit_out_lap`, `lap_duration`, `lap_number`, `meeting_key`, `segments_sector_1`, `segments_sector_2`, `segments_sector_3`, `session_key`, `st_speed` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'stints', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_stints), NULL
FROM (SELECT COUNT(*) n FROM stg_stints GROUP BY `compound`, `driver_number`, `lap_end`, `lap_start`, `meeting_key`, `session_key`, `stint_number`, `tyre_age_at_start` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'weather', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_weather), NULL
FROM (SELECT COUNT(*) n FROM stg_weather GROUP BY `air_temperature`, `date`, `humidity`, `meeting_key`, `pressure`, `rainfall`, `session_key`, `track_temperature`, `wind_direction`, `wind_speed` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'pit', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_pit), NULL
FROM (SELECT COUNT(*) n FROM stg_pit GROUP BY `date`, `driver_number`, `lane_duration`, `lap_number`, `meeting_key`, `pit_duration`, `session_key`, `stop_duration` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'starting_grid', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_starting_grid), NULL
FROM (SELECT COUNT(*) n FROM stg_starting_grid GROUP BY `position`, `driver_number`, `lap_duration`, `meeting_key`, `session_key` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'session_result', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_session_result), NULL
FROM (SELECT COUNT(*) n FROM stg_session_result GROUP BY `position`, `driver_number`, `number_of_laps`, `points`, `dnf`, `dns`, `dsq`, `duration`, `gap_to_leader`, `meeting_key`, `session_key` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'position', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_position), NULL
FROM (SELECT COUNT(*) n FROM stg_position GROUP BY `date`, `session_key`, `meeting_key`, `driver_number`, `position` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'race_control', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_race_control), NULL
FROM (SELECT COUNT(*) n FROM stg_race_control GROUP BY `meeting_key`, `session_key`, `date`, `driver_number`, `lap_number`, `category`, `flag`, `scope`, `sector`, `qualifying_phase`, `message` HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC11', 'intervals', COALESCE(SUM(n - 1),0), (SELECT COUNT(*) FROM stg_intervals), NULL
FROM (SELECT COUNT(*) n FROM stg_intervals GROUP BY `date`, `session_key`, `meeting_key`, `interval`, `driver_number`, `gap_to_leader` HAVING COUNT(*) > 1) d;

-- VC12 같은 세션 안 순위 중복
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC12', 'session_result', COALESCE(SUM(n - 1),0),
       (SELECT COUNT(*) FROM stg_session_result WHERE TRIM(position) <> ''), NULL
FROM (SELECT COUNT(*) n FROM stg_session_result WHERE TRIM(position) <> '' GROUP BY session_key, position HAVING COUNT(*) > 1) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC12', 'starting_grid', COALESCE(SUM(n - 1),0),
       (SELECT COUNT(*) FROM stg_starting_grid WHERE TRIM(position) <> ''), NULL
FROM (SELECT COUNT(*) n FROM stg_starting_grid WHERE TRIM(position) <> '' GROUP BY session_key, position HAVING COUNT(*) > 1) d;

-- VC13 같은 세션에서 한 이름·약어가 여러 차량 번호에 등장
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC13', 'drivers.full_name', COALESCE(SUM(n > 1),0), COUNT(*), NULL
FROM (SELECT session_key, full_name, COUNT(DISTINCT driver_number) n FROM stg_drivers
      WHERE TRIM(full_name) <> '' GROUP BY session_key, full_name) d;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC13', 'drivers.name_acronym', COALESCE(SUM(n > 1),0), COUNT(*), NULL
FROM (SELECT session_key, name_acronym, COUNT(DISTINCT driver_number) n FROM stg_drivers
      WHERE TRIM(name_acronym) <> '' GROUP BY session_key, name_acronym) d;

-- ===================== 참조 무결성 =====================
-- VC20 sessions에 없는 session_key
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'drivers', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_drivers c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'laps', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_laps c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'stints', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_stints c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'weather', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_weather c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'pit', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_pit c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'session_result', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_session_result c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'position', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_position c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'race_control', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_race_control c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC20', 'intervals', SUM(s.session_key IS NULL), COUNT(*), NULL
FROM stg_intervals c LEFT JOIN stg_sessions s ON s.session_key = c.session_key;

-- VC21 drivers에 없는 session_key + driver_number
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'laps', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_laps c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'stints', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_stints c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'pit', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_pit c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'session_result', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_session_result c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'position', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_position c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'race_control', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_race_control c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number WHERE TRIM(c.driver_number) <> '';

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC21', 'intervals', SUM(d.session_key IS NULL), COUNT(*), NULL
FROM stg_intervals c LEFT JOIN stg_drivers d ON d.session_key = c.session_key AND d.driver_number = c.driver_number;

-- 상세 조회: SELECT DISTINCT c.session_key, c.driver_number FROM stg_laps c LEFT JOIN stg_drivers d USING (session_key, driver_number) WHERE d.session_key IS NULL;
-- VC22 같은 session_key인데 meeting_key가 sessions와 다름
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'drivers', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_drivers c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'laps', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_laps c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'stints', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_stints c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'weather', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_weather c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'pit', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_pit c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'session_result', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_session_result c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'position', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_position c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'race_control', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_race_control c JOIN stg_sessions s ON s.session_key = c.session_key;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC22', 'intervals', COALESCE(SUM(c.meeting_key <> s.meeting_key),0), COUNT(*), NULL
FROM stg_intervals c JOIN stg_sessions s ON s.session_key = c.session_key;

-- VC23 starting_grid: Race session_key 직접 사용 금지, meeting_key당 Race 1개·그리드 세션 1개
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC23', 'starting_grid',
       SUM(g.session_key IN (SELECT session_key FROM t_race) OR COALESCE(r.n_race,0) <> 1 OR gs.n_grid_session <> 1),
       COUNT(*), 'Qualifying session_key → meeting_key → Race session_key'
FROM stg_starting_grid g
LEFT JOIN (SELECT meeting_key, COUNT(*) n_race FROM t_race GROUP BY meeting_key) r ON r.meeting_key = g.meeting_key
JOIN (SELECT meeting_key, COUNT(DISTINCT session_key) n_grid_session FROM stg_starting_grid GROUP BY meeting_key) gs
  ON gs.meeting_key = g.meeting_key;

-- VC24 그리드(meeting_key+driver_number)가 Race 결과에 없음 (예선 후 기권 등)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC24', 'starting_grid', SUM(res.session_key IS NULL), COUNT(*), NULL
FROM stg_starting_grid g
JOIN t_race r ON r.meeting_key = g.meeting_key
LEFT JOIN stg_session_result res ON res.session_key = r.session_key AND res.driver_number = g.driver_number;
-- 상세 조회:
-- SELECT g.meeting_key, g.session_key AS qualifying_session_key, r.session_key AS race_session_key, g.driver_number
-- FROM stg_starting_grid g JOIN t_race r ON r.meeting_key = g.meeting_key
-- LEFT JOIN stg_session_result res ON res.session_key = r.session_key AND res.driver_number = g.driver_number
-- WHERE res.session_key IS NULL;

-- VC25 Race 결과에 그리드가 없음 (피트레인 출발 등, INFO)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC25', 'session_result', SUM(g.driver_number IS NULL), COUNT(*), '그리드 없는 Race 결과(피트레인 출발 등)'
FROM stg_session_result res
JOIN t_race r ON r.session_key = res.session_key
LEFT JOIN stg_starting_grid g ON g.meeting_key = r.meeting_key AND g.driver_number = res.driver_number;

-- VC26 피트 랩이 드라이버 최대 랩보다 큼
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC26', 'pit', COALESCE(SUM((CASE WHEN TRIM(p.lap_number) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(p.lap_number) AS DECIMAL(18,6)) END) > m.max_lap),0), COUNT(*), NULL
FROM stg_pit p LEFT JOIN t_max_lap m ON m.session_key = p.session_key AND m.driver_number = p.driver_number;

-- VC27 / VC71 랩 ↔ 스틴트 범위 JOIN 매칭 수 (0건 = 미포함, 2건 이상 = 행 증폭)
DROP TABLE IF EXISTS t_lap_stint;
CREATE TABLE t_lap_stint AS
SELECT l.session_key, l.driver_number, l.lap_number,
       SUM((CASE WHEN TRIM(l.lap_number) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(l.lap_number) AS DECIMAL(18,6)) END) BETWEEN (CASE WHEN TRIM(s.lap_start) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(s.lap_start) AS DECIMAL(18,6)) END) AND (CASE WHEN TRIM(s.lap_end) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(s.lap_end) AS DECIMAL(18,6)) END)) AS matches
FROM stg_laps l
LEFT JOIN stg_stints s ON s.session_key = l.session_key AND s.driver_number = l.driver_number
GROUP BY l.session_key, l.driver_number, l.lap_number;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC27', 'laps', SUM(COALESCE(matches,0) = 0), COUNT(*), NULL FROM t_lap_stint;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC71', 'laps×stints', SUM(matches > 1), COUNT(*), '경계 랩이 앞뒤 스틴트에 모두 속함' FROM t_lap_stint;

-- ===================== 범위·형식 =====================
-- VC30 숫자 변환 실패 (격차 컬럼의 +N LAP(S)는 허용)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'sessions', SUM(TRIM(`circuit_key`) <> '' AND TRIM(`circuit_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`country_key`) <> '' AND TRIM(`country_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`year`) <> '' AND TRIM(`year`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_sessions;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'drivers', SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_drivers;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'laps', SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`duration_sector_1`) <> '' AND TRIM(`duration_sector_1`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`duration_sector_2`) <> '' AND TRIM(`duration_sector_2`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`duration_sector_3`) <> '' AND TRIM(`duration_sector_3`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`i1_speed`) <> '' AND TRIM(`i1_speed`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`i2_speed`) <> '' AND TRIM(`i2_speed`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`st_speed`) <> '' AND TRIM(`st_speed`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_duration`) <> '' AND TRIM(`lap_duration`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_number`) <> '' AND TRIM(`lap_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'stints', SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_end`) <> '' AND TRIM(`lap_end`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_start`) <> '' AND TRIM(`lap_start`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`stint_number`) <> '' AND TRIM(`stint_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`tyre_age_at_start`) <> '' AND TRIM(`tyre_age_at_start`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_stints;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'weather', SUM(TRIM(`air_temperature`) <> '' AND TRIM(`air_temperature`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`humidity`) <> '' AND TRIM(`humidity`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`pressure`) <> '' AND TRIM(`pressure`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`track_temperature`) <> '' AND TRIM(`track_temperature`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`wind_direction`) <> '' AND TRIM(`wind_direction`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`wind_speed`) <> '' AND TRIM(`wind_speed`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_weather;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'pit', SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lane_duration`) <> '' AND TRIM(`lane_duration`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_number`) <> '' AND TRIM(`lap_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`pit_duration`) <> '' AND TRIM(`pit_duration`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`stop_duration`) <> '' AND TRIM(`stop_duration`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_pit;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'starting_grid', SUM(TRIM(`position`) <> '' AND TRIM(`position`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_duration`) <> '' AND TRIM(`lap_duration`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_starting_grid;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'session_result', SUM(TRIM(`position`) <> '' AND TRIM(`position`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`number_of_laps`) <> '' AND TRIM(`number_of_laps`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`points`) <> '' AND TRIM(`points`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`duration`) <> '' AND TRIM(`duration`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`gap_to_leader`) <> '' AND TRIM(`gap_to_leader`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' AND TRIM(`gap_to_leader`) NOT REGEXP '^[+][0-9]+ LAPS?$'), COUNT(*), NULL FROM stg_session_result;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'position', SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`position`) <> '' AND TRIM(`position`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_position;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'race_control', SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`lap_number`) <> '' AND TRIM(`lap_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`sector`) <> '' AND TRIM(`sector`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`qualifying_phase`) <> '' AND TRIM(`qualifying_phase`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$'), COUNT(*), NULL FROM stg_race_control;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC30', 'intervals', SUM(TRIM(`session_key`) <> '' AND TRIM(`session_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`meeting_key`) <> '' AND TRIM(`meeting_key`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`driver_number`) <> '' AND TRIM(`driver_number`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$') + SUM(TRIM(`interval`) <> '' AND TRIM(`interval`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' AND TRIM(`interval`) NOT REGEXP '^[+][0-9]+ LAPS?$') + SUM(TRIM(`gap_to_leader`) <> '' AND TRIM(`gap_to_leader`) NOT REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' AND TRIM(`gap_to_leader`) NOT REGEXP '^[+][0-9]+ LAPS?$'), COUNT(*), NULL FROM stg_intervals;

-- VC31 허용 범위 위반
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'sessions', COALESCE(SUM((CASE WHEN TRIM(`year`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`year`) AS DECIMAL(18,6)) END) < 2023 OR (CASE WHEN TRIM(`year`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`year`) AS DECIMAL(18,6)) END) > 2026),0), COUNT(*), NULL FROM stg_sessions;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'laps', COALESCE(SUM((CASE WHEN TRIM(`lap_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_duration`) AS DECIMAL(18,6)) END) <= 0),0) + COALESCE(SUM((CASE WHEN TRIM(`duration_sector_1`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration_sector_1`) AS DECIMAL(18,6)) END) <= 0),0) + COALESCE(SUM((CASE WHEN TRIM(`duration_sector_2`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration_sector_2`) AS DECIMAL(18,6)) END) <= 0),0) + COALESCE(SUM((CASE WHEN TRIM(`duration_sector_3`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration_sector_3`) AS DECIMAL(18,6)) END) <= 0),0) + COALESCE(SUM((CASE WHEN TRIM(`i1_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`i1_speed`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`i2_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`i2_speed`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`st_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`st_speed`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`lap_number`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_number`) AS DECIMAL(18,6)) END) < 1),0), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'stints', COALESCE(SUM((CASE WHEN TRIM(`stint_number`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`stint_number`) AS DECIMAL(18,6)) END) < 1),0) + COALESCE(SUM((CASE WHEN TRIM(`lap_start`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_start`) AS DECIMAL(18,6)) END) < 1),0) + COALESCE(SUM((CASE WHEN TRIM(`lap_end`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_end`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`tyre_age_at_start`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`tyre_age_at_start`) AS DECIMAL(18,6)) END) < 0),0), COUNT(*), NULL FROM stg_stints;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'pit', COALESCE(SUM((CASE WHEN TRIM(`lane_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lane_duration`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`pit_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`pit_duration`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`stop_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`stop_duration`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`lap_number`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_number`) AS DECIMAL(18,6)) END) < 1),0), COUNT(*), NULL FROM stg_pit;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'weather', COALESCE(SUM((CASE WHEN TRIM(`humidity`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`humidity`) AS DECIMAL(18,6)) END) < 0 OR (CASE WHEN TRIM(`humidity`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`humidity`) AS DECIMAL(18,6)) END) > 100),0) + COALESCE(SUM((CASE WHEN TRIM(`wind_direction`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`wind_direction`) AS DECIMAL(18,6)) END) < 0 OR (CASE WHEN TRIM(`wind_direction`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`wind_direction`) AS DECIMAL(18,6)) END) > 360),0) + COALESCE(SUM((CASE WHEN TRIM(`wind_speed`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`wind_speed`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`pressure`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`pressure`) AS DECIMAL(18,6)) END) <= 0),0) + COALESCE(SUM((CASE WHEN TRIM(`air_temperature`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`air_temperature`) AS DECIMAL(18,6)) END) < -20 OR (CASE WHEN TRIM(`air_temperature`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`air_temperature`) AS DECIMAL(18,6)) END) > 60),0) + COALESCE(SUM((CASE WHEN TRIM(`track_temperature`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`track_temperature`) AS DECIMAL(18,6)) END) < -20 OR (CASE WHEN TRIM(`track_temperature`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`track_temperature`) AS DECIMAL(18,6)) END) > 80),0), COUNT(*), NULL FROM stg_weather;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'starting_grid', COALESCE(SUM((CASE WHEN TRIM(`position`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`position`) AS DECIMAL(18,6)) END) < 1 OR (CASE WHEN TRIM(`position`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`position`) AS DECIMAL(18,6)) END) > 30),0) + COALESCE(SUM((CASE WHEN TRIM(`lap_duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_duration`) AS DECIMAL(18,6)) END) <= 0),0), COUNT(*), NULL FROM stg_starting_grid;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'session_result', COALESCE(SUM((CASE WHEN TRIM(`position`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`position`) AS DECIMAL(18,6)) END) < 1 OR (CASE WHEN TRIM(`position`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`position`) AS DECIMAL(18,6)) END) > 30),0) + COALESCE(SUM((CASE WHEN TRIM(`number_of_laps`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`number_of_laps`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`points`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`points`) AS DECIMAL(18,6)) END) < 0 OR (CASE WHEN TRIM(`points`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`points`) AS DECIMAL(18,6)) END) > 26),0) + COALESCE(SUM((CASE WHEN TRIM(`duration`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`duration`) AS DECIMAL(18,6)) END) < 0),0), COUNT(*), NULL FROM stg_session_result;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'position', COALESCE(SUM((CASE WHEN TRIM(`position`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`position`) AS DECIMAL(18,6)) END) < 1 OR (CASE WHEN TRIM(`position`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`position`) AS DECIMAL(18,6)) END) > 30),0), COUNT(*), NULL FROM stg_position;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'race_control', COALESCE(SUM((CASE WHEN TRIM(`lap_number`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`lap_number`) AS DECIMAL(18,6)) END) < 0),0) + COALESCE(SUM((CASE WHEN TRIM(`sector`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`sector`) AS DECIMAL(18,6)) END) < 1),0), COUNT(*), NULL FROM stg_race_control;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'session_result.gap_to_leader', COALESCE(SUM((CASE WHEN TRIM(`gap_to_leader`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`gap_to_leader`) AS DECIMAL(18,6)) END) < 0),0), COUNT(*), NULL FROM stg_session_result;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'intervals.interval', COALESCE(SUM((CASE WHEN TRIM(`interval`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`interval`) AS DECIMAL(18,6)) END) < 0),0), COUNT(*), NULL FROM stg_intervals;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC31', 'intervals.gap_to_leader', COALESCE(SUM((CASE WHEN TRIM(`gap_to_leader`) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(`gap_to_leader`) AS DECIMAL(18,6)) END) < 0),0), COUNT(*), NULL FROM stg_intervals;

-- VC32 허용 코드 위반
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC32', 'sessions',
       SUM(session_type NOT IN ('Race','Sprint','Qualifying','Practice')) + SUM(is_cancelled NOT IN ('True','False')), COUNT(*), NULL
FROM stg_sessions;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC32', 'laps', SUM(TRIM(is_pit_out_lap) <> '' AND is_pit_out_lap NOT IN ('True','False')), COUNT(*), NULL
FROM stg_laps;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC32', 'weather', SUM(TRIM(rainfall) <> '' AND rainfall NOT IN ('0','1')), COUNT(*), NULL
FROM stg_weather;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC32', 'stints', SUM(compound NOT IN ('SOFT','MEDIUM','HARD','INTERMEDIATE','WET','UNKNOWN')), COUNT(*), NULL
FROM stg_stints;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC32', 'session_result',
       SUM(dnf NOT IN ('True','False')) + SUM(dns NOT IN ('True','False')) + SUM(dsq NOT IN ('True','False')), COUNT(*), NULL
FROM stg_session_result;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC32', 'race_control',
       SUM(category NOT IN ('Flag','Other','SafetyCar','SessionStatus','Drs','CarEvent'))
     + SUM(TRIM(flag) <> '' AND flag NOT IN ('GREEN','YELLOW','DOUBLE YELLOW','RED','BLUE','CLEAR','CHEQUERED','BLACK AND WHITE'))
     + SUM(TRIM(scope) <> '' AND scope NOT IN ('Track','Sector','Driver')), COUNT(*), NULL
FROM stg_race_control;
-- VC33 일시 변환 실패, 세션 종료 < 시작
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'sessions', SUM(TRIM(`date_start`) <> '' AND TRIM(`date_start`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$') + SUM(TRIM(`date_end`) <> '' AND TRIM(`date_end`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$') + COALESCE(SUM((CASE WHEN TRIM(date_end) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$' THEN CAST(REPLACE(LEFT(TRIM(date_end),19),'T',' ') AS DATETIME) END) < (CASE WHEN TRIM(date_start) REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$' THEN CAST(REPLACE(LEFT(TRIM(date_start),19),'T',' ') AS DATETIME) END)),0), COUNT(*), NULL FROM stg_sessions;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'laps', SUM(TRIM(`date_start`) <> '' AND TRIM(`date_start`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$'), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'pit', SUM(TRIM(`date`) <> '' AND TRIM(`date`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$'), COUNT(*), NULL FROM stg_pit;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'weather', SUM(TRIM(`date`) <> '' AND TRIM(`date`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$'), COUNT(*), NULL FROM stg_weather;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'position', SUM(TRIM(`date`) <> '' AND TRIM(`date`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$'), COUNT(*), NULL FROM stg_position;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'race_control', SUM(TRIM(`date`) <> '' AND TRIM(`date`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$'), COUNT(*), NULL FROM stg_race_control;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC33', 'intervals', SUM(TRIM(`date`) <> '' AND TRIM(`date`) NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([+-][0-9]{2}:?[0-9]{2}|Z)?$'), COUNT(*), NULL FROM stg_intervals;

-- VC34 dnf·dns·dsq 중 2개 이상 True
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC34', 'session_result',
       SUM((dnf = 'True') + (dns = 'True') + (dsq = 'True') > 1), COUNT(*), NULL FROM stg_session_result;

-- ===================== 정합성 =====================
-- VC40 세션별 팀 소속 드라이버 수가 2가 아님
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC40', 'drivers', SUM(n <> 2), COUNT(*), NULL
FROM (SELECT session_key, team_name, COUNT(DISTINCT driver_number) n FROM stg_drivers
      WHERE TRIM(team_name) <> '' GROUP BY session_key, team_name) d;
-- 상세 조회: SELECT session_key, team_name, GROUP_CONCAT(driver_number) FROM stg_drivers GROUP BY 1,2 HAVING COUNT(DISTINCT driver_number) <> 2;
-- VC41 같은 시즌 driver_number에 full_name이 여러 개
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC41', 'drivers', SUM(n > 1), COUNT(*), NULL
FROM (SELECT s.year, d.driver_number, COUNT(DISTINCT d.full_name) n
      FROM stg_drivers d JOIN stg_sessions s ON s.session_key = d.session_key GROUP BY s.year, d.driver_number) x;
-- VC42 섹터 합과 랩타임 차이 0.5초 초과
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC42', 'laps', COALESCE(SUM(ABS(diff) > 0.5),0), SUM(diff IS NOT NULL), NULL
FROM (SELECT (CASE WHEN TRIM(duration_sector_1) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(duration_sector_1) AS DECIMAL(18,6)) END) + (CASE WHEN TRIM(duration_sector_2) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(duration_sector_2) AS DECIMAL(18,6)) END) + (CASE WHEN TRIM(duration_sector_3) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(duration_sector_3) AS DECIMAL(18,6)) END) - (CASE WHEN TRIM(lap_duration) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(lap_duration) AS DECIMAL(18,6)) END) AS diff FROM stg_laps) x;
-- VC43 lane_duration ≠ pit_duration (격리 행 제외)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC43', 'pit', COALESCE(SUM((CASE WHEN TRIM(lane_duration) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(lane_duration) AS DECIMAL(18,6)) END) <> (CASE WHEN TRIM(pit_duration) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(pit_duration) AS DECIMAL(18,6)) END) AND quarantine_flag <> 'Y'),0), COUNT(*),
       CONCAT('격리 행 ', SUM(quarantine_flag = 'Y'), '건 제외') FROM stg_pit;
-- VC44 결과 완료 랩 수와 laps 최대 랩 차이 1랩 초과
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC44', 'session_result', COALESCE(SUM(ABS((CASE WHEN TRIM(r.number_of_laps) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(r.number_of_laps) AS DECIMAL(18,6)) END) - m.max_lap) > 1),0),
       SUM((CASE WHEN TRIM(r.number_of_laps) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(r.number_of_laps) AS DECIMAL(18,6)) END) IS NOT NULL AND m.max_lap IS NOT NULL), NULL
FROM stg_session_result r LEFT JOIN t_max_lap m ON m.session_key = r.session_key AND m.driver_number = r.driver_number;
-- VC45 다음 스틴트 시작 < 이전 스틴트 종료
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC45', 'stints', COALESCE(SUM(lap_start_n < prev_end),0), COUNT(*), NULL
FROM (SELECT (CASE WHEN TRIM(lap_start) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(lap_start) AS DECIMAL(18,6)) END) AS lap_start_n,
             LAG((CASE WHEN TRIM(lap_end) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(lap_end) AS DECIMAL(18,6)) END)) OVER (PARTITION BY session_key, driver_number ORDER BY (CASE WHEN TRIM(stint_number) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(stint_number) AS DECIMAL(18,6)) END)) AS prev_end
      FROM stg_stints) x;

-- ===================== 포인트 =====================
-- VC50 원천 points와 재계산 race_base_points 차이 (INFO; 2023~2024 최속 랩 +1, 원천 누락 확인용)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC50', 'session_result',
       SUM(COALESCE((CASE WHEN TRIM(points) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(points) AS DECIMAL(18,6)) END), 0) <> race_base_points), COUNT(*),
       (SELECT GROUP_CONCAT(CONCAT(d, '점 ', n, '건') ORDER BY d SEPARATOR ', ')
        FROM (SELECT CAST(COALESCE((CASE WHEN TRIM(points) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(points) AS DECIMAL(18,6)) END),0) - race_base_points AS DECIMAL(6,1)) d, COUNT(*) n
              FROM t_result_points WHERE COALESCE((CASE WHEN TRIM(points) REGEXP '^-?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$' THEN CAST(TRIM(points) AS DECIMAL(18,6)) END),0) <> race_base_points GROUP BY d) b)
FROM t_result_points;
-- 상세 조회: SELECT * FROM t_result_points WHERE CAST(points AS DECIMAL(6,1)) <> race_base_points;

-- VC51 Race별·시즌별 드라이버 기본 포인트 합 = 팀(경기 당시 소속) 기본 포인트 합
DROP TABLE IF EXISTS t_points_team;
CREATE TABLE t_points_team AS
SELECT p.session_key, p.year, p.driver_number, p.race_base_points, d.team_name AS team_at_race
FROM t_result_points p
LEFT JOIN stg_drivers d ON d.session_key = p.session_key AND d.driver_number = p.driver_number;
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC51', 'session_result×drivers',
       (SELECT COUNT(*) FROM (SELECT session_key, SUM(race_base_points) s FROM t_result_points GROUP BY session_key) a
          LEFT JOIN (SELECT session_key, SUM(team_sum) s
                     FROM (SELECT session_key, team_at_race, SUM(race_base_points) team_sum FROM t_points_team
                           GROUP BY session_key, team_at_race) t GROUP BY session_key) b USING (session_key)
         WHERE b.s IS NULL OR a.s <> b.s)
     + (SELECT COUNT(*) FROM (SELECT year, SUM(race_base_points) s FROM t_result_points GROUP BY year) a
          LEFT JOIN (SELECT year, SUM(team_sum) s
                     FROM (SELECT year, team_at_race, SUM(race_base_points) team_sum FROM t_points_team
                           WHERE team_at_race IS NOT NULL GROUP BY year, team_at_race) t GROUP BY year) b USING (year)
         WHERE b.s IS NULL OR a.s <> b.s),
       (SELECT COUNT(DISTINCT session_key) + COUNT(DISTINCT year) FROM t_result_points),
       CONCAT('행 수 ', (SELECT COUNT(*) FROM t_result_points), '→', (SELECT COUNT(*) FROM t_points_team));
-- 상세 조회(팀 시즌 누적·기본 포인트 순위):
-- SELECT year, team_at_race, SUM(race_base_points) AS cumulative_race_base_points,
--        RANK() OVER (PARTITION BY year ORDER BY SUM(race_base_points) DESC) AS race_base_points_team_rank
-- FROM t_points_team GROUP BY year, team_at_race;

-- VC52 Race별 기본 포인트 합계 ≠ 101
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC52', 'session_result', SUM(s <> 101), COUNT(*), NULL
FROM (SELECT session_key, SUM(race_base_points) s FROM t_result_points GROUP BY session_key) x;
-- VC53 포인트 귀속 팀이 공백
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC53', 'session_result×drivers', SUM(team_at_race IS NULL OR TRIM(team_at_race) = ''), COUNT(*), NULL
FROM t_points_team;

-- ===================== 대사 =====================
-- VC60 원본(bronze_manifest) 행 수 = 정제 후 행 수
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC60', 'sessions', ABS(COALESCE(m.`rows`, -1) - c.n), COALESCE(m.`rows`, -1),
       CONCAT('원본 ', COALESCE(m.`rows`, '없음'), ' / 정제 ', c.n)
FROM (SELECT COUNT(*) n FROM stg_sessions) c LEFT JOIN stg_bronze_manifest m ON m.file = 'sessions.csv';

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC60', 'drivers', ABS(COALESCE(m.`rows`, -1) - c.n), COALESCE(m.`rows`, -1),
       CONCAT('원본 ', COALESCE(m.`rows`, '없음'), ' / 정제 ', c.n)
FROM (SELECT COUNT(*) n FROM stg_drivers) c LEFT JOIN stg_bronze_manifest m ON m.file = 'drivers.csv';

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC60', 'laps', ABS(COALESCE(m.`rows`, -1) - c.n), COALESCE(m.`rows`, -1),
       CONCAT('원본 ', COALESCE(m.`rows`, '없음'), ' / 정제 ', c.n)
FROM (SELECT COUNT(*) n FROM stg_laps) c LEFT JOIN stg_bronze_manifest m ON m.file = 'laps.csv';

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC60', 'stints', ABS(COALESCE(m.`rows`, -1) - c.n), COALESCE(m.`rows`, -1),
       CONCAT('원본 ', COALESCE(m.`rows`, '없음'), ' / 정제 ', c.n)
FROM (SELECT COUNT(*) n FROM stg_stints) c LEFT JOIN stg_bronze_manifest m ON m.file = 'stints.csv';

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC60', 'weather', ABS(COALESCE(m.`rows`, -1) - c.n), COALESCE(m.`rows`, -1),
       CONCAT('원본 ', COALESCE(m.`rows`, '없음'), ' / 정제 ', c.n)
FROM (SELECT COUNT(*) n FROM stg_weather) c LEFT JOIN stg_bronze_manifest m ON m.file = 'weather.csv';

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC60', 'pit', ABS(COALESCE(m.`rows`, -1) - c.n), COALESCE(m.`rows`, -1),
       CONCAT('원본 ', COALESCE(m.`rows`, '없음'), ' / 정제 ', c.n)
FROM (SELECT COUNT(*) n FROM stg_pit) c LEFT JOIN stg_bronze_manifest m ON m.file = 'pit.csv';

-- VC61 격리 플래그 행 수 (INFO)
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC61', 'sessions', SUM(quarantine_flag = 'Y'), COUNT(*), NULL FROM stg_sessions;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC61', 'drivers', SUM(quarantine_flag = 'Y'), COUNT(*), NULL FROM stg_drivers;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC61', 'laps', SUM(quarantine_flag = 'Y'), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC61', 'stints', SUM(quarantine_flag = 'Y'), COUNT(*), NULL FROM stg_stints;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC61', 'weather', SUM(quarantine_flag = 'Y'), COUNT(*), NULL FROM stg_weather;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC61', 'pit', SUM(quarantine_flag = 'Y'), COUNT(*), NULL FROM stg_pit;

-- VC62 original_* 와 값이 다른데 복구 기록(REPAIRED + repair_method의 컬럼)이 없음
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC62', 'sessions', SUM(BINARY `circuit_key` <> BINARY `original_circuit_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:circuit_key;%'))
     + SUM(BINARY `circuit_short_name` <> BINARY `original_circuit_short_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:circuit_short_name;%'))
     + SUM(BINARY `country_code` <> BINARY `original_country_code` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:country_code;%'))
     + SUM(BINARY `country_key` <> BINARY `original_country_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:country_key;%'))
     + SUM(BINARY `country_name` <> BINARY `original_country_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:country_name;%'))
     + SUM(BINARY `date_end` <> BINARY `original_date_end` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:date_end;%'))
     + SUM(BINARY `date_start` <> BINARY `original_date_start` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:date_start;%'))
     + SUM(BINARY `gmt_offset` <> BINARY `original_gmt_offset` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:gmt_offset;%'))
     + SUM(BINARY `is_cancelled` <> BINARY `original_is_cancelled` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:is_cancelled;%'))
     + SUM(BINARY `location` <> BINARY `original_location` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:location;%'))
     + SUM(BINARY `meeting_key` <> BINARY `original_meeting_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:meeting_key;%'))
     + SUM(BINARY `session_key` <> BINARY `original_session_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_key;%'))
     + SUM(BINARY `session_name` <> BINARY `original_session_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_name;%'))
     + SUM(BINARY `session_type` <> BINARY `original_session_type` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_type;%'))
     + SUM(BINARY `year` <> BINARY `original_year` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:year;%')), COUNT(*), NULL FROM stg_sessions;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC62', 'drivers', SUM(BINARY `broadcast_name` <> BINARY `original_broadcast_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:broadcast_name;%'))
     + SUM(BINARY `country_code` <> BINARY `original_country_code` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:country_code;%'))
     + SUM(BINARY `driver_number` <> BINARY `original_driver_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:driver_number;%'))
     + SUM(BINARY `first_name` <> BINARY `original_first_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:first_name;%'))
     + SUM(BINARY `full_name` <> BINARY `original_full_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:full_name;%'))
     + SUM(BINARY `headshot_url` <> BINARY `original_headshot_url` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:headshot_url;%'))
     + SUM(BINARY `last_name` <> BINARY `original_last_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:last_name;%'))
     + SUM(BINARY `meeting_key` <> BINARY `original_meeting_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:meeting_key;%'))
     + SUM(BINARY `name_acronym` <> BINARY `original_name_acronym` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:name_acronym;%'))
     + SUM(BINARY `session_key` <> BINARY `original_session_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_key;%'))
     + SUM(BINARY `team_colour` <> BINARY `original_team_colour` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:team_colour;%'))
     + SUM(BINARY `team_name` <> BINARY `original_team_name` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:team_name;%')), COUNT(*), NULL FROM stg_drivers;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC62', 'laps', SUM(BINARY `date_start` <> BINARY `original_date_start` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:date_start;%'))
     + SUM(BINARY `driver_number` <> BINARY `original_driver_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:driver_number;%'))
     + SUM(BINARY `duration_sector_1` <> BINARY `original_duration_sector_1` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:duration_sector_1;%'))
     + SUM(BINARY `duration_sector_2` <> BINARY `original_duration_sector_2` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:duration_sector_2;%'))
     + SUM(BINARY `duration_sector_3` <> BINARY `original_duration_sector_3` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:duration_sector_3;%'))
     + SUM(BINARY `i1_speed` <> BINARY `original_i1_speed` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:i1_speed;%'))
     + SUM(BINARY `i2_speed` <> BINARY `original_i2_speed` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:i2_speed;%'))
     + SUM(BINARY `is_pit_out_lap` <> BINARY `original_is_pit_out_lap` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:is_pit_out_lap;%'))
     + SUM(BINARY `lap_duration` <> BINARY `original_lap_duration` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:lap_duration;%'))
     + SUM(BINARY `lap_number` <> BINARY `original_lap_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:lap_number;%'))
     + SUM(BINARY `meeting_key` <> BINARY `original_meeting_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:meeting_key;%'))
     + SUM(BINARY `segments_sector_1` <> BINARY `original_segments_sector_1` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:segments_sector_1;%'))
     + SUM(BINARY `segments_sector_2` <> BINARY `original_segments_sector_2` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:segments_sector_2;%'))
     + SUM(BINARY `segments_sector_3` <> BINARY `original_segments_sector_3` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:segments_sector_3;%'))
     + SUM(BINARY `session_key` <> BINARY `original_session_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_key;%'))
     + SUM(BINARY `st_speed` <> BINARY `original_st_speed` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:st_speed;%')), COUNT(*), NULL FROM stg_laps;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC62', 'stints', SUM(BINARY `compound` <> BINARY `original_compound` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:compound;%'))
     + SUM(BINARY `driver_number` <> BINARY `original_driver_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:driver_number;%'))
     + SUM(BINARY `lap_end` <> BINARY `original_lap_end` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:lap_end;%'))
     + SUM(BINARY `lap_start` <> BINARY `original_lap_start` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:lap_start;%'))
     + SUM(BINARY `meeting_key` <> BINARY `original_meeting_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:meeting_key;%'))
     + SUM(BINARY `session_key` <> BINARY `original_session_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_key;%'))
     + SUM(BINARY `stint_number` <> BINARY `original_stint_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:stint_number;%'))
     + SUM(BINARY `tyre_age_at_start` <> BINARY `original_tyre_age_at_start` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:tyre_age_at_start;%')), COUNT(*), NULL FROM stg_stints;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC62', 'weather', SUM(BINARY `air_temperature` <> BINARY `original_air_temperature` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:air_temperature;%'))
     + SUM(BINARY `date` <> BINARY `original_date` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:date;%'))
     + SUM(BINARY `humidity` <> BINARY `original_humidity` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:humidity;%'))
     + SUM(BINARY `meeting_key` <> BINARY `original_meeting_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:meeting_key;%'))
     + SUM(BINARY `pressure` <> BINARY `original_pressure` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:pressure;%'))
     + SUM(BINARY `rainfall` <> BINARY `original_rainfall` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:rainfall;%'))
     + SUM(BINARY `session_key` <> BINARY `original_session_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_key;%'))
     + SUM(BINARY `track_temperature` <> BINARY `original_track_temperature` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:track_temperature;%'))
     + SUM(BINARY `wind_direction` <> BINARY `original_wind_direction` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:wind_direction;%'))
     + SUM(BINARY `wind_speed` <> BINARY `original_wind_speed` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:wind_speed;%')), COUNT(*), NULL FROM stg_weather;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC62', 'pit', SUM(BINARY `date` <> BINARY `original_date` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:date;%'))
     + SUM(BINARY `driver_number` <> BINARY `original_driver_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:driver_number;%'))
     + SUM(BINARY `lane_duration` <> BINARY `original_lane_duration` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:lane_duration;%'))
     + SUM(BINARY `lap_number` <> BINARY `original_lap_number` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:lap_number;%'))
     + SUM(BINARY `meeting_key` <> BINARY `original_meeting_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:meeting_key;%'))
     + SUM(BINARY `pit_duration` <> BINARY `original_pit_duration` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:pit_duration;%'))
     + SUM(BINARY `session_key` <> BINARY `original_session_key` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:session_key;%'))
     + SUM(BINARY `stop_duration` <> BINARY `original_stop_duration` AND NOT (repair_status = 'REPAIRED' AND CONCAT(repair_method, ';') LIKE '%:stop_duration;%')), COUNT(*), NULL FROM stg_pit;

-- ===================== JOIN 행 증폭 =====================
-- VC70 drivers와 JOIN한 뒤 행 수 증가
INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC70', 'laps×drivers', j.n - c.n, c.n, CONCAT(c.n, '→', j.n)
FROM (SELECT COUNT(*) n FROM stg_laps) c,
     (SELECT COUNT(*) n FROM stg_laps x LEFT JOIN stg_drivers d
        ON d.session_key = x.session_key AND d.driver_number = x.driver_number) j;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC70', 'stints×drivers', j.n - c.n, c.n, CONCAT(c.n, '→', j.n)
FROM (SELECT COUNT(*) n FROM stg_stints) c,
     (SELECT COUNT(*) n FROM stg_stints x LEFT JOIN stg_drivers d
        ON d.session_key = x.session_key AND d.driver_number = x.driver_number) j;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC70', 'pit×drivers', j.n - c.n, c.n, CONCAT(c.n, '→', j.n)
FROM (SELECT COUNT(*) n FROM stg_pit) c,
     (SELECT COUNT(*) n FROM stg_pit x LEFT JOIN stg_drivers d
        ON d.session_key = x.session_key AND d.driver_number = x.driver_number) j;

INSERT INTO vc_result (check_id, target, fail_count, total_count, note)
SELECT 'VC70', 'session_result×drivers', j.n - c.n, c.n, CONCAT(c.n, '→', j.n)
FROM (SELECT COUNT(*) n FROM stg_session_result) c,
     (SELECT COUNT(*) n FROM stg_session_result x LEFT JOIN stg_drivers d
        ON d.session_key = x.session_key AND d.driver_number = x.driver_number) j;

-- ===================== 행 수 대사 표 =====================
-- 처리 결과를 겹치지 않는 4개 구간으로 나눠 합계가 원본(bronze_manifest) 행 수와 같은지 본다.
--   ② 원본 유지(UNCHANGED, 격리 아님) + ③ 복구(REPAIRED, 격리 아님) + ④ 격리(quarantine_flag='Y') + ⑤ 제거(원본 - 정제 후) = ① 원본
-- 추가 5종은 정제 단계가 없으므로 전부 ② 원본 유지로 센다.
DROP TABLE IF EXISTS vc_row_reconciliation;
CREATE TABLE vc_row_reconciliation AS
SELECT x.file, x.grp, x.raw_rows, x.unchanged_rows, x.repaired_rows, x.quarantined_rows,
       x.raw_rows - x.cleaned_rows AS removed_rows,
       x.unchanged_rows + x.repaired_rows + x.quarantined_rows + (x.raw_rows - x.cleaned_rows) AS processed_sum,
       x.unchanged_rows + x.repaired_rows + x.quarantined_rows + (x.raw_rows - x.cleaned_rows) - x.raw_rows AS difference,
       x.unchanged_rows + x.repaired_rows AS analysis_rows,
       CASE WHEN x.raw_rows IS NOT NULL AND x.raw_rows >= x.cleaned_rows
             AND x.unchanged_rows + x.repaired_rows + x.quarantined_rows = x.cleaned_rows THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
  SELECT 'sessions' file, '오염 정제 6종' grp, (SELECT `rows` FROM stg_bronze_manifest WHERE file = 'sessions.csv') raw_rows, COUNT(*) cleaned_rows,
         SUM(repair_status = 'UNCHANGED' AND quarantine_flag <> 'Y') unchanged_rows,
         SUM(repair_status = 'REPAIRED' AND quarantine_flag <> 'Y') repaired_rows, SUM(quarantine_flag = 'Y') quarantined_rows FROM stg_sessions
UNION ALL   SELECT 'drivers' file, '오염 정제 6종' grp, (SELECT `rows` FROM stg_bronze_manifest WHERE file = 'drivers.csv') raw_rows, COUNT(*) cleaned_rows,
         SUM(repair_status = 'UNCHANGED' AND quarantine_flag <> 'Y') unchanged_rows,
         SUM(repair_status = 'REPAIRED' AND quarantine_flag <> 'Y') repaired_rows, SUM(quarantine_flag = 'Y') quarantined_rows FROM stg_drivers
UNION ALL   SELECT 'laps' file, '오염 정제 6종' grp, (SELECT `rows` FROM stg_bronze_manifest WHERE file = 'laps.csv') raw_rows, COUNT(*) cleaned_rows,
         SUM(repair_status = 'UNCHANGED' AND quarantine_flag <> 'Y') unchanged_rows,
         SUM(repair_status = 'REPAIRED' AND quarantine_flag <> 'Y') repaired_rows, SUM(quarantine_flag = 'Y') quarantined_rows FROM stg_laps
UNION ALL   SELECT 'stints' file, '오염 정제 6종' grp, (SELECT `rows` FROM stg_bronze_manifest WHERE file = 'stints.csv') raw_rows, COUNT(*) cleaned_rows,
         SUM(repair_status = 'UNCHANGED' AND quarantine_flag <> 'Y') unchanged_rows,
         SUM(repair_status = 'REPAIRED' AND quarantine_flag <> 'Y') repaired_rows, SUM(quarantine_flag = 'Y') quarantined_rows FROM stg_stints
UNION ALL   SELECT 'weather' file, '오염 정제 6종' grp, (SELECT `rows` FROM stg_bronze_manifest WHERE file = 'weather.csv') raw_rows, COUNT(*) cleaned_rows,
         SUM(repair_status = 'UNCHANGED' AND quarantine_flag <> 'Y') unchanged_rows,
         SUM(repair_status = 'REPAIRED' AND quarantine_flag <> 'Y') repaired_rows, SUM(quarantine_flag = 'Y') quarantined_rows FROM stg_weather
UNION ALL   SELECT 'pit' file, '오염 정제 6종' grp, (SELECT `rows` FROM stg_bronze_manifest WHERE file = 'pit.csv') raw_rows, COUNT(*) cleaned_rows,
         SUM(repair_status = 'UNCHANGED' AND quarantine_flag <> 'Y') unchanged_rows,
         SUM(repair_status = 'REPAIRED' AND quarantine_flag <> 'Y') repaired_rows, SUM(quarantine_flag = 'Y') quarantined_rows FROM stg_pit
UNION ALL   SELECT 'starting_grid', '추가 5종', COUNT(*), COUNT(*), COUNT(*), 0, 0 FROM stg_starting_grid
UNION ALL   SELECT 'session_result', '추가 5종', COUNT(*), COUNT(*), COUNT(*), 0, 0 FROM stg_session_result
UNION ALL   SELECT 'position', '추가 5종', COUNT(*), COUNT(*), COUNT(*), 0, 0 FROM stg_position
UNION ALL   SELECT 'race_control', '추가 5종', COUNT(*), COUNT(*), COUNT(*), 0, 0 FROM stg_race_control
UNION ALL   SELECT 'intervals', '추가 5종', COUNT(*), COUNT(*), COUNT(*), 0, 0 FROM stg_intervals
) x;
SELECT * FROM vc_row_reconciliation
UNION ALL
SELECT '합계(오염 정제 6종)', '', SUM(raw_rows), SUM(unchanged_rows), SUM(repaired_rows), SUM(quarantined_rows), SUM(removed_rows),
       SUM(processed_sum), SUM(difference), SUM(analysis_rows), MIN(status)
FROM vc_row_reconciliation WHERE grp = '오염 정제 6종';

-- ===================== 결과 =====================
SELECT r.check_id, c.korean_category, c.check_name, r.target, c.severity, r.fail_count, r.total_count,
       CASE WHEN c.severity = 'INFO' THEN 'INFO'
            WHEN r.fail_count = 0 THEN 'PASS'
            WHEN c.severity = 'ERROR' THEN 'FAIL' ELSE 'WARN' END AS status,
       r.note
FROM vc_result r JOIN ref_validation_check c ON c.check_id = r.check_id
ORDER BY r.check_id, r.id;

SELECT CASE WHEN c.severity = 'INFO' THEN 'INFO' WHEN r.fail_count = 0 THEN 'PASS'
            WHEN c.severity = 'ERROR' THEN 'FAIL' ELSE 'WARN' END AS status, COUNT(*) AS checks
FROM vc_result r JOIN ref_validation_check c ON c.check_id = r.check_id
GROUP BY 1 ORDER BY 1;

-- 작업 테이블 정리
DROP TABLE IF EXISTS t_race, t_result_points, t_max_lap, t_lap_stint, t_points_team;
