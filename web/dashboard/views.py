from django.shortcuts import render
from sqlalchemy.exc import SQLAlchemyError

from . import board_gold
from .models import GoldSnapshot


def decision_board(request):
    # MySQL gold_board_* 테이블에서 읽는다 (적재: sql/06 → manage.py load_board_gold)
    try:
        board = board_gold.read_board()
    except (board_gold.BoardNotLoaded, SQLAlchemyError) as e:
        return render(request, "dashboard/empty.html", {"reason": str(e).splitlines()[0][:200], "board": True}, status=503)
    return render(request, "dashboard/decision_board.html", {"snapshot_json": board["json"]})


def decision_board_gold(request):
    snapshot = GoldSnapshot.objects.first()  # 가장 최근 Gold (계산은 build_gold 명령에서)
    if snapshot is None:
        return render(request, "dashboard/empty.html", status=503)
    return render(request, "dashboard/decision_board_gold.html", {"snapshot": snapshot, "payload": snapshot.payload})
