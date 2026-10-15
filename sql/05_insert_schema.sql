-- =====================================================================
-- 05_insert_schema.sql : 스테이징(stg_*) → TO-BE 스키마 적재 (MySQL 8.0+)
-- 순서: 01_create_staging → 02_load_staging → 03_validate_cleaned(FAIL 0 확인) → 04_create_schema → 05_insert_schema
-- 전체 재적재 방식이다. 다시 실행하면 기존 행을 지우고 같은 결과로 다시 넣는다.
-- 원칙: 형식이 맞지 않는 값은 NULL로 넣고 0으로 바꾸지 않는다(f1_num/f1_int/f1_utc).
--       격리 행(quarantine_flag='Y')도 적재하고 플래그로 분석에서 제외한다.
-- 실행: mysql -u <user> -p <db> < sql/05_insert_schema.sql
-- =====================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE repair_detail;
TRUNCATE TABLE quality_issue;
TRUNCATE TABLE interval_event;
TRUNCATE TABLE race_control_event;
TRUNCATE TABLE position_event;
TRUNCATE TABLE session_result;
TRUNCATE TABLE starting_grid;
TRUNCATE TABLE weather;
TRUNCATE TABLE pit_event;
TRUNCATE TABLE stint;
TRUNCATE TABLE lap;
TRUNCATE TABLE session_driver;
TRUNCATE TABLE driver;
TRUNCATE TABLE session;
TRUNCATE TABLE meeting;
SET FOREIGN_KEY_CHECKS = 1;

START TRANSACTION;

-- 1) 대회: 세션의 장소 정보를 meeting 단위로 정규화
INSERT INTO meeting (meeting_key, year, circuit_key, circuit_short_name, country_key, country_code, country_name, location, gmt_offset)
SELECT f1_int(meeting_key), MIN(f1_int(year)), MIN(f1_int(circuit_key)), MIN(NULLIF(circuit_short_name, '')),
       MIN(f1_int(country_key)), MIN(NULLIF(country_code, '')), MIN(NULLIF(country_name, '')),
       MIN(NULLIF(location, '')), MIN(NULLIF(gmt_offset, ''))
FROM stg_sessions
GROUP BY f1_int(meeting_key);

-- 2) 세션
INSERT INTO session (session_key, meeting_key, session_name, session_type, date_start, date_end, is_cancelled, year,
                     repair_status, quarantine_flag)
SELECT f1_int(session_key), f1_int(meeting_key), session_name, session_type, f1_utc(date_start), f1_utc(date_end),
       f1_bool(is_cancelled), f1_int(year), repair_status, quarantine_flag
FROM stg_sessions;

-- 3) 드라이버 마스터: full_name 기준 1행, 이름 속성은 가장 최근 세션 값
INSERT INTO driver (full_name, first_name, last_name, name_acronym, country_code)
SELECT full_name, first_name, last_name, name_acronym, country_code
FROM (
  SELECT d.full_name, NULLIF(d.first_name, '') first_name, NULLIF(d.last_name, '') last_name,
         NULLIF(d.name_acronym, '') name_acronym,
         FIRST_VALUE(NULLIF(d.country_code, '')) OVER (PARTITION BY d.full_name ORDER BY (d.country_code = ''), s.date_start DESC) country_code,
         ROW_NUMBER() OVER (PARTITION BY d.full_name ORDER BY s.date_start DESC) rn
  FROM stg_drivers d JOIN stg_sessions s ON s.session_key = d.session_key
  WHERE TRIM(d.full_name) <> ''
) x
WHERE rn = 1;

-- 4) 세션 참가자
INSERT INTO session_driver (session_key, driver_number, driver_id, team_name, team_colour, broadcast_name, headshot_url,
                            country_code, repair_status, quarantine_flag)
SELECT f1_int(d.session_key), f1_int(d.driver_number), m.driver_id, NULLIF(d.team_name, ''), NULLIF(d.team_colour, ''),
       NULLIF(d.broadcast_name, ''), NULLIF(d.headshot_url, ''), NULLIF(d.country_code, ''), d.repair_status, d.quarantine_flag
FROM stg_drivers d JOIN driver m ON m.full_name = d.full_name;

-- 5) 랩
INSERT INTO lap (session_key, driver_number, lap_number, date_start, lap_duration, duration_sector_1, duration_sector_2,
                 duration_sector_3, i1_speed, i2_speed, st_speed, is_pit_out_lap, segments_sector_1, segments_sector_2,
                 segments_sector_3, repair_status, repair_method, dq_codes, quarantine_flag)
SELECT f1_int(session_key), f1_int(driver_number), f1_int(lap_number), f1_utc(date_start), f1_num(lap_duration),
       f1_num(duration_sector_1), f1_num(duration_sector_2), f1_num(duration_sector_3),
       f1_num(i1_speed), f1_num(i2_speed), f1_num(st_speed), f1_bool(is_pit_out_lap),
       NULLIF(segments_sector_1, ''), NULLIF(segments_sector_2, ''), NULLIF(segments_sector_3, ''),
       repair_status, NULLIF(repair_method, ''), NULLIF(dq_codes, ''), quarantine_flag
FROM stg_laps;

-- 6) 스틴트 (컴파운드 결측은 파이프라인이 UNKNOWN으로 표시)
INSERT INTO stint (session_key, driver_number, stint_number, compound, lap_start, lap_end, tyre_age_at_start,
                   repair_status, dq_codes, quarantine_flag)
SELECT f1_int(session_key), f1_int(driver_number), f1_int(stint_number), COALESCE(NULLIF(compound, ''), 'UNKNOWN'),
       f1_int(lap_start), f1_int(lap_end), f1_int(tyre_age_at_start), repair_status, NULLIF(dq_codes, ''), quarantine_flag
FROM stg_stints;

-- 7) 피트 (lane_duration·stop_duration 분리, 결측 0 대체 금지)
INSERT INTO pit_event (session_key, driver_number, lap_number, event_date, lane_duration, pit_duration, stop_duration,
                       repair_status, dq_codes, quarantine_flag)
SELECT f1_int(session_key), f1_int(driver_number), f1_int(lap_number), f1_utc(`date`), f1_num(lane_duration),
       f1_num(pit_duration), f1_num(stop_duration), repair_status, NULLIF(dq_codes, ''), quarantine_flag
FROM stg_pit;

-- 8) 기상
INSERT INTO weather (session_key, observed_at, air_temperature, track_temperature, humidity, pressure, rainfall,
                     wind_direction, wind_speed, repair_status, dq_codes, quarantine_flag)
SELECT f1_int(session_key), f1_utc(`date`), f1_num(air_temperature), f1_num(track_temperature), f1_num(humidity),
       f1_num(pressure), f1_int(rainfall), f1_int(wind_direction), f1_num(wind_speed), repair_status, NULLIF(dq_codes, ''),
       quarantine_flag
FROM stg_weather;

-- 9) 출발 그리드: Qualifying 원본 키 보존 + meeting_key로 Race 세션 매핑
INSERT INTO starting_grid (qualifying_session_key, driver_number, meeting_key, race_session_key, grid_position, qualifying_lap_duration)
SELECT f1_int(g.session_key), f1_int(g.driver_number), f1_int(g.meeting_key), r.session_key,
       f1_int(g.position), f1_num(g.lap_duration)
FROM stg_starting_grid g
LEFT JOIN session r ON r.meeting_key = f1_int(g.meeting_key) AND r.session_type = 'Race';

-- 10) 경기 결과 + 본경기 기본 포인트 (25-18-15-12-10-8-6-4-2-1, 최속 랩 보너스·Sprint 제외)
INSERT INTO session_result (session_key, driver_number, finish_position, classification_status, number_of_laps,
                            dnf, dns, dsq, duration, gap_to_leader, gap_to_leader_laps, source_points,
                            race_base_points, scoring_rule_year, points_rule_status)
SELECT f1_int(r.session_key), f1_int(r.driver_number), f1_int(r.position),
       CASE WHEN r.dsq = 'True' THEN 'DSQ' WHEN r.dns = 'True' THEN 'DNS' WHEN r.dnf = 'True' THEN 'DNF'
            WHEN f1_int(r.position) IS NOT NULL THEN 'CLASSIFIED' ELSE 'NOT_CLASSIFIED' END,
       f1_int(r.number_of_laps), f1_bool(r.dnf), f1_bool(r.dns), f1_bool(r.dsq), f1_num(r.duration),
       f1_num(r.gap_to_leader), f1_gap_laps(r.gap_to_leader), f1_num(r.points),
       COALESCE(p.race_base_points, 0), s.year,
       CASE WHEN f1_int(r.position) IS NULL THEN 'NOT_CLASSIFIED' ELSE 'STANDARD' END
FROM stg_session_result r
JOIN session s ON s.session_key = f1_int(r.session_key)
LEFT JOIN ref_race_points_rule p ON p.year = s.year AND p.position = f1_int(r.position);

-- 11) 순위 타임라인 (약 4만 행)
INSERT INTO position_event (session_key, driver_number, recorded_at, position)
SELECT f1_int(session_key), f1_int(driver_number), f1_utc(`date`), f1_int(position)
FROM stg_position;

-- 12) 레이스 컨트롤
INSERT INTO race_control_event (session_key, recorded_at, driver_number, lap_number, category, flag, scope, sector,
                                qualifying_phase, message)
SELECT f1_int(session_key), f1_utc(`date`), f1_int(driver_number), f1_int(lap_number), category, NULLIF(flag, ''),
       NULLIF(scope, ''), f1_int(sector), f1_int(qualifying_phase), message
FROM stg_race_control
ORDER BY f1_utc(`date`);

-- 13) 격차 타임라인 (약 210만 행; 시간이 걸린다)
INSERT INTO interval_event (session_key, driver_number, recorded_at, `interval`, interval_laps, gap_to_leader, gap_to_leader_laps)
SELECT f1_int(session_key), f1_int(driver_number), f1_utc(`date`), f1_num(`interval`), f1_gap_laps(`interval`),
       f1_num(gap_to_leader), f1_gap_laps(gap_to_leader)
FROM stg_intervals;

-- 14) 품질 이력
INSERT INTO quality_issue (issue_id, diagnostic_code, error_type, severity, source_file, row_key, session_key, driver_number,
                           field, observed_value, expected_value, evidence, action, status, confidence)
SELECT issue_id, diagnostic_code, error_type, severity, file, row_key, f1_int(session_key), f1_int(driver_number), field,
       NULLIF(observed_value, ''), NULLIF(expected_value, ''), NULLIF(evidence, ''), action, status, NULLIF(confidence, '')
FROM stg_validation_issues;

INSERT INTO repair_detail (issue_id, source_file, row_key, field, old_value, new_value, method, confidence, reason)
SELECT issue_id, file, row_key, field, old_value, new_value, method, NULLIF(confidence, ''), NULLIF(reason, '')
FROM stg_repair_detail;

COMMIT;

-- 적재 대사: 스테이징 행 수 = 스키마 행 수 (diff가 모두 0이어야 한다)
SELECT t, staged, loaded, loaded - staged AS diff FROM (
  SELECT 'session' t, (SELECT COUNT(*) FROM stg_sessions) staged, (SELECT COUNT(*) FROM session) loaded
  UNION ALL SELECT 'session_driver', (SELECT COUNT(*) FROM stg_drivers), (SELECT COUNT(*) FROM session_driver)
  UNION ALL SELECT 'lap', (SELECT COUNT(*) FROM stg_laps), (SELECT COUNT(*) FROM lap)
  UNION ALL SELECT 'stint', (SELECT COUNT(*) FROM stg_stints), (SELECT COUNT(*) FROM stint)
  UNION ALL SELECT 'pit_event', (SELECT COUNT(*) FROM stg_pit), (SELECT COUNT(*) FROM pit_event)
  UNION ALL SELECT 'weather', (SELECT COUNT(*) FROM stg_weather), (SELECT COUNT(*) FROM weather)
  UNION ALL SELECT 'starting_grid', (SELECT COUNT(*) FROM stg_starting_grid), (SELECT COUNT(*) FROM starting_grid)
  UNION ALL SELECT 'session_result', (SELECT COUNT(*) FROM stg_session_result), (SELECT COUNT(*) FROM session_result)
  UNION ALL SELECT 'position_event', (SELECT COUNT(*) FROM stg_position), (SELECT COUNT(*) FROM position_event)
  UNION ALL SELECT 'race_control_event', (SELECT COUNT(*) FROM stg_race_control), (SELECT COUNT(*) FROM race_control_event)
  UNION ALL SELECT 'interval_event', (SELECT COUNT(*) FROM stg_intervals), (SELECT COUNT(*) FROM interval_event)
  UNION ALL SELECT 'quality_issue', (SELECT COUNT(*) FROM stg_validation_issues), (SELECT COUNT(*) FROM quality_issue)
  UNION ALL SELECT 'repair_detail', (SELECT COUNT(*) FROM stg_repair_detail), (SELECT COUNT(*) FROM repair_detail)
) x;

-- 포인트 점검: 드라이버 합계 = 팀 합계 (시즌별)
SELECT year, SUM(race_base_points) AS driver_sum,
       (SELECT SUM(race_base_points) FROM v_team_race_points t WHERE t.year = o.year) AS team_sum
FROM v_race_outcome o GROUP BY year;
