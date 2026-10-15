from django.urls import path

from . import views

urlpatterns = [
    path("", views.table_list, name="table_list"),
    path("table/<str:name>/", views.table_detail, name="table_detail"),
]
