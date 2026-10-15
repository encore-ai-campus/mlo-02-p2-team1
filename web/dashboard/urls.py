from django.urls import path

from . import views

urlpatterns = [
    path("", views.decision_board, name="decision_board"),
    path("gold/", views.decision_board_gold, name="decision_board_gold"),  # 이전 C 시안 (Gold 기반)
]
