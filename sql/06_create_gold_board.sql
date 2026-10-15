-- 06. Decision Board Gold 테이블 생성 (gold_board_*)
-- 화면(/)이 읽는 Gold 테이블이다. 기획서 Gold 9개 마트와의 대응은 각 테이블 주석과 web/dashboard/board_gold.py 참고.
-- 실행: 05 이후 저장소 루트에서
--   mysql --default-character-set=utf8mb4 -u <user> -p <db> < sql/06_create_gold_board.sql
--   venv\Scripts\python.exe web\manage.py load_board_gold      # 데이터 적재 (data/05_gold/decision_board.json → 이 테이블)
-- 관리자 화면(/ops/)의 'Gold 갱신'은 06 → 적재 → build_gold를 차례로 실행한다.
-- 아직 별도 테이블이 없는 마트: 2 tyre_performance(스틴트 단위), 4 pit_strategy(피트 이벤트 단위) — 팀 단위 집계는 team_profile에 있음.
SET NAMES utf8mb4;

DROP TABLE IF EXISTS gold_board_meta, gold_board_driver_profile, gold_board_team_profile, gold_board_team_race, gold_board_race_outcome, gold_board_driver_team_fit, gold_board_fit_race, gold_board_fit_scenario, gold_board_data_quality, gold_board_coverage, gold_board_source;

-- 기준일·조건·임계값·방법론·요약 (1행). 적재 원천 파일과 해시를 함께 기록
CREATE TABLE gold_board_meta (
  `seq` INT NOT NULL,
  `created` VARCHAR(32),
  `cutoff` VARCHAR(32),
  `years` JSON,
  `variants` JSON,
  `thresholds` JSON,
  `summary` JSON,
  `methodology` JSON,
  `source_file` VARCHAR(255),
  `source_sha256` CHAR(64),
  `loaded_at` VARCHAR(32),
  PRIMARY KEY (`seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Gold 1·5 드라이버 프로필: 시즌 × 드라이버 소속 구간 (상대 페이스·동료 대비·일관성·타이어·포인트·상위 %)
CREATE TABLE gold_board_driver_profile (
  `seq` INT NOT NULL,
  `year` INT,
  `full_name` VARCHAR(64),
  `team_name` VARCHAR(64),
  `membership_id` VARCHAR(96),
  `valid_races` INT,
  `valid_laps` INT,
  `relative_pace_pct` DOUBLE,
  `raw_iqr_sec` DOUBLE,
  `adjusted_iqr_sec` DOUBLE,
  `eligible` BOOLEAN,
  `teammate_races` DOUBLE,
  `paired_laps` DOUBLE,
  `teammate_delta_sec` DOUBLE,
  `tyre_races` INT,
  `tyre_stints` INT,
  `tyre_slope_sec_per_lap` DOUBLE,
  `raw_tyre_slope_sec_per_lap` DOUBLE,
  `relative_pace_pct_top_pct` DOUBLE,
  `adjusted_iqr_sec_top_pct` DOUBLE,
  `teammate_delta_sec_top_pct` DOUBLE,
  `tyre_slope_sec_per_lap_top_pct` DOUBLE,
  `sector_1_relative_pct` DOUBLE,
  `sector_2_relative_pct` DOUBLE,
  `sector_3_relative_pct` DOUBLE,
  `race_entries` INT,
  `race_base_points` DOUBLE,
  `unknown_point_rows` INT,
  `finished_races` INT,
  `started_races` INT,
  `pit_count_races` INT,
  `finish_rate_pct` DOUBLE,
  `finish_rate_definition` VARCHAR(255),
  `current_segment` BOOLEAN,
  `own_low` DOUBLE,
  `own_high` DOUBLE,
  `own_races` INT,
  PRIMARY KEY (`seq`),
  KEY `ix_driver_profile_year` (`year`),
  KEY `ix_driver_profile_team_name` (`team_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Gold 6·7 팀 프로필 + 피트 벤치마크: 시즌 × 팀
CREATE TABLE gold_board_team_profile (
  `seq` INT NOT NULL,
  `year` INT,
  `team_name` VARCHAR(64),
  `relative_pace_pct` DOUBLE,
  `adjusted_iqr_sec` DOUBLE,
  `valid_races` INT,
  `valid_laps` INT,
  `one_driver_races` INT,
  `pace_top_pct` DOUBLE,
  `race_base_points` DOUBLE,
  `result_rows` INT,
  `unknown_point_rows` INT,
  `race_base_points_team_rank` DOUBLE,
  `pit_count_driver_races` INT,
  `pit_event_mean` DOUBLE,
  `zero_event_driver_races` INT,
  `pit_event_mean_finished_only` DOUBLE,
  `median_observed_stint_laps` DOUBLE,
  `tyre_slope_sec_per_lap` DOUBLE,
  `valid_stints` INT,
  `lane_sec_races` INT,
  `lane_sec_median` DOUBLE,
  `lane_sec_relative` DOUBLE,
  `stop_sec_races` DOUBLE,
  `stop_sec_median` DOUBLE,
  `stop_sec_relative` DOUBLE,
  `eligible` BOOLEAN,
  `pit_denominator` INT,
  `pit_zero_count` INT,
  `pit_1` INT,
  `pit_2` INT,
  `pit_3plus` INT,
  `grid_change_mean` DOUBLE,
  `grid_change_rows` INT,
  `tyre_valid_races` INT,
  `source_races` INT,
  `source_driver_rows` INT,
  `source_started` INT,
  `classification_unknown` INT,
  `slow_events` INT,
  `pit_comparable_events` INT,
  `slow_pit_pct` DOUBLE,
  PRIMARY KEY (`seq`),
  KEY `ix_team_profile_year` (`year`),
  KEY `ix_team_profile_team_name` (`team_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 팀 × 경기 상대 페이스 (팀 프로필의 경기 단위 근거)
CREATE TABLE gold_board_team_race (
  `seq` INT NOT NULL,
  `year` INT,
  `session_key` VARCHAR(16),
  `team_name` VARCHAR(64),
  `relative_pace_pct` DOUBLE,
  `adjusted_iqr_sec` DOUBLE,
  `valid_drivers` INT,
  `valid_laps` INT,
  PRIMARY KEY (`seq`),
  KEY `ix_team_race_year` (`year`),
  KEY `ix_team_race_session_key` (`session_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Gold 3 경기 결과: 경기 × 드라이버, 본경기 기본 포인트
CREATE TABLE gold_board_race_outcome (
  `seq` INT NOT NULL,
  `session_key` VARCHAR(16),
  `driver_number` INT,
  `full_name` VARCHAR(64),
  `team_name` VARCHAR(64),
  `year` INT,
  `finish_position` DOUBLE,
  `grid_position` DOUBLE,
  `race_base_points` DOUBLE,
  `classification_status` VARCHAR(24),
  `points_rule_status` VARCHAR(255),
  `grid_change` DOUBLE,
  PRIMARY KEY (`seq`),
  KEY `ix_race_outcome_session_key` (`session_key`),
  KEY `ix_race_outcome_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Gold 8 팀 자리 × 타 팀 후보 판정 (case_id = 기준 자리>>후보)
CREATE TABLE gold_board_driver_team_fit (
  `seq` INT NOT NULL,
  `case_id` VARCHAR(160),
  `year` INT,
  `seat` VARCHAR(72),
  `candidate` VARCHAR(72),
  `status` VARCHAR(24),
  `delta` DOUBLE,
  `low` DOUBLE,
  `high` DOUBLE,
  `common_races` INT,
  `faster` INT,
  `missing` INT,
  `own_negative` INT,
  `own_missing` INT,
  `first` DOUBLE,
  `second` DOUBLE,
  `loo_min` DOUBLE,
  `loo_max` DOUBLE,
  `tyre_races` INT,
  `tyre_delta` DOUBLE,
  `tyre_low` DOUBLE,
  `tyre_high` DOUBLE,
  `iqr_delta` DOUBLE,
  `iqr_low` DOUBLE,
  `iqr_high` DOUBLE,
  `reasons` JSON,
  PRIMARY KEY (`seq`),
  KEY `ix_driver_team_fit_case_id` (`case_id`),
  KEY `ix_driver_team_fit_seat` (`seat`),
  KEY `ix_driver_team_fit_year` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 후보 판정의 공통 경기별 상대 페이스 차이 (후보 − 기준 = delta_pct)
CREATE TABLE gold_board_fit_race (
  `case_id` VARCHAR(160) NOT NULL,
  `seq` INT NOT NULL,
  `session_key` VARCHAR(16),
  `delta_pct` DOUBLE,
  `candidate_rel_pct` DOUBLE,
  `seat_rel_pct` DOUBLE,
  PRIMARY KEY (`case_id`, `seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 후보 판정의 정제 조건 11가지별 결과
CREATE TABLE gold_board_fit_scenario (
  `case_id` VARCHAR(160) NOT NULL,
  `seq` INT NOT NULL,
  `variant` VARCHAR(48),
  `delta_pct` DOUBLE,
  `common_races` INT,
  `own_teammate_delta_sec` DOUBLE,
  `own_faster` BOOLEAN,
  PRIMARY KEY (`case_id`, `seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Gold 9 데이터 품질: 원천 × 규칙별 탐지·잔여
CREATE TABLE gold_board_data_quality (
  `seq` INT NOT NULL,
  `run_id` VARCHAR(32),
  `source` VARCHAR(32),
  `rule` VARCHAR(96),
  `detected` INT,
  `remaining` INT,
  `status` VARCHAR(24),
  PRIMARY KEY (`seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 경기별 원천 11종 커버리지
CREATE TABLE gold_board_coverage (
  `seq` INT NOT NULL,
  `session_key` VARCHAR(16),
  `meeting_key` INT,
  `year` INT,
  `circuit_short_name` VARCHAR(48),
  `date_start` VARCHAR(32),
  `date_end` VARCHAR(32),
  `sessions_rows` INT,
  `drivers_rows` INT,
  `laps_rows` INT,
  `stints_rows` INT,
  `weather_rows` INT,
  `pit_rows` INT,
  `session_result_rows` INT,
  `position_rows` INT,
  `race_control_rows` INT,
  `intervals_rows` INT,
  `stop_available_rows` INT,
  `pit_source_present` BOOLEAN,
  `special_strategy` BOOLEAN,
  PRIMARY KEY (`seq`),
  KEY `ix_coverage_session_key` (`session_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 원천 11종 매니페스트 (행 수·해시·수집 상태)
CREATE TABLE gold_board_source (
  `seq` INT NOT NULL,
  `source` VARCHAR(32),
  `rows` INT,
  `session_count` INT,
  `sha256` VARCHAR(64),
  `http_status` VARCHAR(32),
  `collected_at` VARCHAR(32),
  `original_json` VARCHAR(32),
  `source_form` VARCHAR(24),
  PRIMARY KEY (`seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
