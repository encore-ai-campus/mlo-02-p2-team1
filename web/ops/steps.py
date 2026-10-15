"""파이프라인 단계 정의와 실행 (관리자 페이지 → run_pipeline 명령이 사용).

단계는 모두 저장소 루트에서 별도 프로세스로 실행한다.
- 정제·검증: pipeline 패키지 (python -m pipeline.*)
- DB 적재: mysql 클라이언트로 sql/01~05 실행 (접속 정보는 Django DB 설정과 같음)
- Gold: sql/06 → manage.py load_board_gold → manage.py build_gold
"""
from __future__ import annotations

import glob, os, shutil, subprocess, sys, tempfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

ROOT = Path(settings.BASE_DIR).parent
LOG_DIR = ROOT / "logs" / "ops_runs"
PY = sys.executable


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    group: str
    command: tuple = ()      # python 단계
    sql: str = ""            # mysql 단계 (sql/ 파일명)


STEPS = [
    Step("extract", "추가 데이터 압축 해제", "정제·검증", command=("-m", "pipeline.extra_data")),
    Step("recovery", "오염 6종 진단·복구", "정제·검증", command=("-m", "pipeline.recovery")),
    Step("validate", "정제 후 검증 VC01~VC71 (pandas)", "정제·검증", command=("-m", "pipeline.validate_cleaned")),
    Step("sql01", "스테이징 테이블 생성 (sql/01)", "DB 적재", sql="01_create_staging.sql"),
    Step("sql02", "정제 결과·추가 데이터 CSV를 스테이징에 적재 (sql/02)", "DB 적재", sql="02_load_staging.sql"),
    Step("sql03", "적재 데이터 검증 VC01~VC71 (sql/03)", "DB 적재", sql="03_validate_cleaned.mysql84.sql"),
    Step("sql04", "정규화 스키마 생성 (sql/04)", "DB 적재", sql="04_create_schema.sql"),
    Step("sql05", "스키마 적재·행 수 대사, 약 20분 (sql/05)", "DB 적재", sql="05_insert_schema.sql"),
    # 02가 수정 이력 CSV를 1,335행 모두 적재하도록 고쳐져 평소에는 필요 없음. 예전 방식으로 적재한 DB 보정용
    Step("sql02b", "[보정용] 수정 이력(repair_detail)만 스테이징에 다시 적재 (sql/02b)", "DB 적재", sql="02b_reload_repair_detail.sql"),
    Step("sql06", "Decision Board Gold 테이블 생성 (sql/06)", "Gold", sql="06_create_gold_board.sql"),
    Step("board", "Decision Board Gold 적재·검증 (gold_board_*)", "Gold", command=("web/manage.py", "load_board_gold")),
    Step("gold", "이전 시안용 Gold 계산 (gold_driver/team_profile)", "Gold", command=("web/manage.py", "build_gold")),
]
STEP_BY_KEY = {s.key: s for s in STEPS}

PRESETS = {
    "clean": ("정제·검증", ["extract", "recovery", "validate"]),
    "load": ("DB 적재", ["extract", "sql01", "sql02", "sql03", "sql04", "sql05"]),
    "gold": ("Gold 갱신", ["sql06", "board", "gold"]),
    "all": ("전체 실행", ["extract", "recovery", "validate", "sql01", "sql02", "sql03", "sql04", "sql05", "sql06", "board", "gold"]),
}


def mysql_bin() -> str | None:
    """MYSQL_BIN 환경변수 → PATH → 기본 설치 경로 순으로 찾는다."""
    if os.environ.get("MYSQL_BIN") and Path(os.environ["MYSQL_BIN"]).exists():
        return os.environ["MYSQL_BIN"]
    found = shutil.which("mysql")
    if found:
        return found
    candidates = sorted(glob.glob(r"C:\Program Files\MySQL\MySQL Server *\bin\mysql.exe"), reverse=True)
    return candidates[0] if candidates else None


def _child_env():
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")  # 자식 출력은 UTF-8로 통일
    return env


def run_step(step: Step, log) -> int:
    """단계 하나를 실행하고 종료 코드를 반환한다. 출력은 log(파일 객체)에 그대로 쓴다."""
    if step.sql:
        return _run_sql(step, log)
    return _stream([PY, *step.command], log)


def _stream(cmd, log, stdin=None) -> int:
    proc = subprocess.Popen(cmd, cwd=ROOT, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=_child_env(), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for raw in proc.stdout:
        log.write(raw.decode("utf-8", errors="replace").rstrip("\r\n") + "\n")
        log.flush()
    return proc.wait()


def _run_sql(step: Step, log) -> int:
    binary = mysql_bin()
    if not binary:
        log.write("[오류] mysql 클라이언트를 찾을 수 없습니다. .env에 MYSQL_BIN=mysql.exe 경로를 넣으세요.\n")
        return 127
    sql_path = ROOT / "sql" / step.sql
    if not sql_path.exists():
        log.write(f"[오류] SQL 파일 없음: {sql_path}\n")
        return 2
    db = settings.DATABASES["default"]
    # 비밀번호가 명령줄·로그에 남지 않도록 임시 옵션 파일로 넘기고 바로 지운다
    fd, cnf = tempfile.mkstemp(suffix=".cnf", prefix="ops_mysql_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("[client]\n")
            f.write(f"user={db['USER']}\npassword=\"{db['PASSWORD']}\"\n")
            f.write(f"host={db['HOST'] or '127.0.0.1'}\nport={db['PORT'] or 3306}\n")
        cmd = [binary, f"--defaults-extra-file={cnf}", "--local-infile=1", "--default-character-set=utf8mb4",
               "--show-warnings", "--table", db["NAME"]]
        with open(sql_path, "rb") as stdin:
            return _stream(cmd, log, stdin=stdin)
    finally:
        try:
            os.remove(cnf)
        except OSError:
            pass
