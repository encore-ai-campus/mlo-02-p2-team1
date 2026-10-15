"""파이프라인 실행 기록 (관리자 페이지에서 요청 → run_pipeline 명령이 갱신)."""
import os

from django.db import models


class PipelineRun(models.Model):
    QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED = "queued", "running", "success", "failed", "cancelled"
    STATUS = [(QUEUED, "대기"), (RUNNING, "실행 중"), (SUCCESS, "성공"), (FAILED, "실패"), (CANCELLED, "중지")]
    ACTIVE = (QUEUED, RUNNING)

    title = models.CharField(max_length=64)
    steps = models.JSONField(default=list, help_text="실행할 단계 key 목록")
    results = models.JSONField(default=list, help_text="단계별 {key, status, started, finished, rc, tail}")
    status = models.CharField(max_length=16, choices=STATUS, default=QUEUED)
    current_step = models.CharField(max_length=32, blank=True)
    error = models.TextField(blank=True)
    pid = models.IntegerField(null=True, blank=True)
    requested_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ops_pipeline_run"
        ordering = ["-id"]

    def __str__(self):
        return f"#{self.pk} {self.title} ({self.get_status_display()})"

    @property
    def log_path(self):
        from .steps import LOG_DIR
        return LOG_DIR / f"run_{self.pk}.log"

    @property
    def duration_s(self):
        if not self.started_at:
            return None
        from django.utils import timezone
        return ((self.finished_at or timezone.now()) - self.started_at).total_seconds()

    def process_alive(self) -> bool:
        return bool(self.pid) and pid_alive(self.pid)


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(handle, ctypes.byref(code))
        k32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
