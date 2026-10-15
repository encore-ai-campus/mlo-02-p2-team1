import json
from pathlib import Path

from django.shortcuts import render

from .models import GoldSnapshot

# Decision Board 데이터 스냅샷(디자인 시안 검증 때 만든 data.json 사본).
# DB·Gold 연결 검증 전까지는 이 파일을 그대로 화면에 넣는다.
BOARD_SNAPSHOT = Path(__file__).resolve().parent / "snapshot" / "decision_board.json"
_cache = {"mtime": None, "text": ""}


def _board_snapshot_json():
    mtime = BOARD_SNAPSHOT.stat().st_mtime
    if _cache["mtime"] != mtime:
        data = json.loads(BOARD_SNAPSHOT.read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        _cache.update(mtime=mtime, text=text.replace("<", "\\u003c"))  # </script> 방지
    return _cache["text"]


def decision_board(request):
    return render(request, "dashboard/decision_board.html", {"snapshot_json": _board_snapshot_json()})


def decision_board_gold(request):
    snapshot = GoldSnapshot.objects.first()  # 가장 최근 Gold (계산은 build_gold 명령에서)
    if snapshot is None:
        return render(request, "dashboard/empty.html", status=503)
    return render(request, "dashboard/decision_board_gold.html", {"snapshot": snapshot, "payload": snapshot.payload})
