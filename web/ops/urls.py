from django.urls import path

from . import views

app_name = "ops"
urlpatterns = [
    path("", views.console, name="console"),
    path("run/", views.start, name="start"),
    path("runs/<int:pk>/cancel/", views.cancel, name="cancel"),
    path("runs/<int:pk>/status/", views.status, name="status"),
    path("runs/<int:pk>/log/", views.log, name="log"),
    path("report/<str:name>/", views.report, name="report"),
]
