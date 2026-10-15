"""추가 데이터 5종 압축 해제 (data/01_raw/f1_extra_data.zip → data/01_raw/f1_extra_data/).

서비스 시작(run_web.bat) 때 자동으로 실행된다. 이미 풀려 있으면 건너뛴다.

실행(저장소 루트): python -m pipeline.extra_data [--force]
종료 코드: 0 = 준비됨(이미 있음·해제 완료), 1 = 실패(사유 출력, 기존 파일은 그대로 둠)
"""
from __future__ import annotations

import argparse, shutil, sys, tempfile, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "01_raw" / "f1_extra_data.zip"
DEST = ROOT / "data" / "01_raw" / "f1_extra_data"
FILES = ["starting_grid.csv", "session_result.csv", "position.csv", "race_control.csv", "intervals.csv"]


class ExtraDataError(Exception):
    """압축 해제를 진행할 수 없는 상태."""


def _members(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """필요한 CSV 5종의 압축 항목. 폴더 한 단계 아래에 있어도 찾고, 경로 탈출 항목은 거부한다."""
    found = {}
    for info in zf.infolist():
        if info.is_dir():
            continue
        path = PurePosixPath(info.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ExtraDataError(f"허용되지 않는 압축 경로: {info.filename}")
        if path.name in FILES:
            if path.name in found:
                raise ExtraDataError(f"같은 파일이 압축 안에 두 번 있음: {path.name}")
            found[path.name] = info
    missing = [f for f in FILES if f not in found]
    if missing:
        raise ExtraDataError(f"압축 안에 없는 파일: {', '.join(missing)}")
    return found


def _is_ready(dest: Path, members: dict[str, zipfile.ZipInfo] | None = None) -> bool:
    """5종이 모두 있고, 압축 정보가 있으면 크기까지 같은지."""
    for name in FILES:
        path = dest / name
        if not path.is_file():
            return False
        if members is not None and path.stat().st_size != members[name].file_size:
            return False
    return True


def ensure_extra_data(archive: Path = ARCHIVE, dest: Path = DEST, force: bool = False) -> str:
    """필요할 때만 압축을 풀고 결과 문구를 반환한다. 실패하면 ExtraDataError."""
    if not archive.exists():
        if _is_ready(dest):
            return f"압축 파일은 없지만 {dest.name}/ 에 5종이 이미 있음"
        raise ExtraDataError(f"압축 파일이 없고 {dest} 도 비어 있음: {archive}")

    try:
        with zipfile.ZipFile(archive) as zf:
            members = _members(zf)
            if not force and _is_ready(dest, members):
                return f"이미 압축 해제됨: {dest}"

            need = sum(m.file_size for m in members.values())
            free = shutil.disk_usage(dest.parent).free
            if free < need * 1.1:
                raise ExtraDataError(f"디스크 공간 부족: 필요 {need / 1e6:,.0f}MB, 남은 공간 {free / 1e6:,.0f}MB")

            # 임시 폴더에 먼저 풀고 CRC 확인 뒤 옮긴다. 중간에 실패해도 기존 파일은 그대로.
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".f1_extra_", dir=dest.parent) as tmp:
                for name, info in members.items():
                    with zf.open(info) as src, open(Path(tmp) / name, "wb") as out:
                        shutil.copyfileobj(src, out, 1024 * 1024)  # CRC 불일치는 BadZipFile로 올라온다
                dest.mkdir(exist_ok=True)
                for name in FILES:
                    shutil.move(str(Path(tmp) / name), str(dest / name))
    except zipfile.BadZipFile as e:
        raise ExtraDataError(f"압축 파일이 손상됨: {archive} ({e})") from e
    except PermissionError as e:
        raise ExtraDataError(f"파일 권한 오류(다른 프로그램이 CSV를 열고 있는지 확인): {e.filename}") from e
    except OSError as e:
        raise ExtraDataError(f"압축 해제 중 파일 오류: {e}") from e

    return f"압축 해제 완료: {archive.name} → {dest} ({len(FILES)}개, {need / 1e6:,.0f}MB)"


def main() -> int:
    parser = argparse.ArgumentParser(description="추가 데이터 5종 압축 해제")
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.add_argument("--force", action="store_true", help="이미 있어도 다시 풀기")
    args = parser.parse_args()
    try:
        print(f"[추가 데이터] {ensure_extra_data(args.archive, args.dest, args.force)}")
        return 0
    except ExtraDataError as e:
        print(f"[추가 데이터][오류] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
