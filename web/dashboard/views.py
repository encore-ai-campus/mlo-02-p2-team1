from django.shortcuts import render

from .models import GoldSnapshot


def decision_board(request):
    snapshot = GoldSnapshot.objects.first()  # 가장 최근 Gold (계산은 build_gold 명령에서)
    if snapshot is None:
        return render(request, "dashboard/empty.html", status=503)
    return render(request, "dashboard/decision_board.html", {"snapshot": snapshot, "payload": snapshot.payload})
