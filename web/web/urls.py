from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("data/", include("viewer.urls")),   # 적재 테이블 조회
    path("", include("dashboard.urls")),     # Decision Board (Gold)
]
