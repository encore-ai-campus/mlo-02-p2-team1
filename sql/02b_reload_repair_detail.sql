-- [보정] repair_detail.csv 스테이징 재적재 (선택 실행)
-- 02의 repair_detail 적재를 '\r\n'으로 고쳤으므로 현재 02만 실행하면 이 파일은 필요 없다.
-- 예전 02로 적재한 DB(1,335행 → 3행)의 stg_repair_detail만 다시 채울 때 사용한다.
-- 스키마 repair_detail은 04 이후 05가 stg_repair_detail에서 채운다(04 전에 실행해도 실패하지 않음).
SET NAMES utf8mb4;
TRUNCATE TABLE stg_repair_detail;
LOAD DATA LOCAL INFILE 'data/04_reports/quality/repair_detail.csv'
INTO TABLE stg_repair_detail CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(`issue_id`, `diagnostic_code`, `error_type`, `file`, `source_row`, `row_key`, `session_key`, `driver_number`, `field`, `old_value`, `new_value`, `method`, `confidence`, `reason`);
SELECT COUNT(*) staged, MAX(LENGTH(reason)) max_reason_len FROM stg_repair_detail;
