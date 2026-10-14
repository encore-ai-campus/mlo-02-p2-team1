# F1 AI 데이터 표준사전

진단 결과와 원본 데이터 명세서를 기준으로 작성한 표준사전입니다. 원본 값은 문자열로 보존하고, 계산·검증 시에만 도메인 규칙에 따라 숫자나 날짜시간으로 해석합니다.

## 구성

- `standard_words.csv`: 표준 단어와 정의
- `standard_terms.csv`: 표준 용어, 용어 조합, 식별자 규칙
- `domains.csv`: 데이터 타입, 길이, 단위, 결측 허용, 검증 규칙
- `codes.csv`: 허용 코드와 코드 설명
- `column_dictionary.csv`: 6개 원천 테이블의 컬럼별 표준 정의
- `composition_rules.md`: 표준명명·키·타입·검증 조합 규칙

## 진단 결과 반영

- `country_code`는 국가 코드 도메인으로 관리하며 세션 국가 코드와 드라이버 국가 코드를 구분합니다.
- 랩·피트 시간은 초 단위 실수 도메인으로 관리하고, 비정상 임계값은 삭제가 아니라 검토 이슈로 기록합니다.
- `compound`는 허용 코드 목록을 사용하고 결측은 `UNKNOWN`으로 표시합니다.
- 스틴트는 `session_key + driver_number + stint_number`를 기준으로 관리하며 `lap_end < lap_start`와 실제 구간 중첩을 검증합니다.
- `segments_sector_1~3`은 목록 원문을 보존하며 임의로 JSON으로 변환하지 않습니다.
