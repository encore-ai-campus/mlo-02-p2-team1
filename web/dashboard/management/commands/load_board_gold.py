"""Decision Board Gold 적재: data/05_gold/decision_board.json → MySQL gold_board_* (테이블은 sql/06이 만든다).

    venv\\Scripts\\python.exe web\\manage.py load_board_gold [--source 파일]

적재 후 DB에서 다시 읽어 원천 파일과 값이 같은지 확인하고, 다르면 실패로 끝난다.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dashboard import board_gold


class Command(BaseCommand):
    help = "Decision Board 데이터를 MySQL gold_board_* 테이블에 적재하고 검증"

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(board_gold.SNAPSHOT))

    def handle(self, *args, source, **opts):
        path = Path(source)
        if not path.exists():
            raise CommandError(f"원천 파일 없음: {path}")
        try:
            counts = board_gold.load_board(path)
        except (board_gold.BoardNotLoaded, ValueError) as e:
            raise CommandError(str(e))
        for name, n in counts.items():
            self.stdout.write(f"{board_gold.P}{name:<16} {n:>8,}행")
        diffs = board_gold.diff_against(path)
        if diffs:
            raise CommandError("DB에서 읽은 값이 원천과 다름:\n" + "\n".join(diffs))
        self.stdout.write(self.style.SUCCESS("적재·검증 완료: DB에서 읽은 화면 데이터 = 원천 파일"))
