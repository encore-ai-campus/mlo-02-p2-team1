from django.contrib import admin

from .models import PipelineRun


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "requested_by", "created_at", "finished_at")
    list_filter = ("status",)
    readonly_fields = [f.name for f in PipelineRun._meta.fields] + ["steps", "results"]
