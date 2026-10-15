-- [보정] repair_detail.csv 재적재 (02 실행 후)
-- 02의 LINES TERMINATED BY '\n'로는 따옴표 뒤 \r 때문에 한 칸에 뒷줄이 합쳐짐(1,335행 → 3행).
-- 줄 끝을 '\r\n'으로 지정해 스테이징과 스키마의 repair_detail만 다시 적재한다.
SET NAMES utf8mb4;
TRUNCATE TABLE stg_repair_detail;
LOAD DATA LOCAL INFILE 'outputs/f1_recovery/reports/repair_detail.csv'
INTO TABLE stg_repair_detail CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\r\n' IGNORE 1 LINES
(`issue_id`, `diagnostic_code`, `error_type`, `file`, `source_row`, `row_key`, `session_key`, `driver_number`, `field`, `old_value`, `new_value`, `method`, `confidence`, `reason`);
TRUNCATE TABLE repair_detail;
INSERT INTO repair_detail (issue_id, source_file, row_key, field, old_value, new_value, method, confidence, reason)
SELECT issue_id, file, row_key, field, old_value, new_value, method, NULLIF(confidence, ''), NULLIF(reason, '')
FROM stg_repair_detail;
SELECT (SELECT COUNT(*) FROM stg_repair_detail) staged, (SELECT COUNT(*) FROM repair_detail) loaded,
       (SELECT MAX(LENGTH(reason)) FROM stg_repair_detail) max_reason_len;
