"""관리자 페이지가 띄우는 파이프라인 실행기. 단계를 순서대로 실행하고 실행 기록을 갱신한다.

    venv\\Scripts\\python.exe web\\manage.py run_pipeline <run_id>

단계가 실패하면 그 자리에서 멈춘다(뒤 단계는 skipped). 로그는 logs/ops_runs/run_<id>.log.
"""
import os, traceback

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ops.models import PipelineRun
from ops.steps import LOG_DIR, STEP_BY_KEY, run_step


def tail(path, start, lines=6):
    """이 단계가 쓴 로그 부분의 마지막 몇 줄 (요약 표시용)."""
    with open(path, "rb") as f:
        f.seek(start)
        text = f.read().decode("utf-8", errors="replace")
    rows = [r for r in text.splitlines() if r.strip() and not set(r.strip()) <= set("+-|")]
    return "\n".join(rows[-lines:])


class Command(BaseCommand):
    help = "파이프라인 실행 기록(PipelineRun)의 단계를 순서대로 실행"

    def add_arguments(self, parser):
        parser.add_argument("run_id", type=int)

    def handle(self, *args, run_id, **opts):
        try:
            run = PipelineRun.objects.get(pk=run_id)
        except PipelineRun.DoesNotExist:
            raise CommandError(f"실행 기록 없음: {run_id}")
        if run.status != PipelineRun.QUEUED:
            raise CommandError(f"대기 상태가 아님: #{run_id} {run.status}")

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        run.status, run.pid, run.started_at = PipelineRun.RUNNING, os.getpid(), timezone.now()
        run.results = [{"key": k, "status": "pending"} for k in run.steps]
        run.save()

        failed = None
        with open(run.log_path, "a", encoding="utf-8") as log:
            for i, key in enumerate(run.steps):
                run.refresh_from_db(fields=["status"])
                if run.status == PipelineRun.CANCELLED:
                    failed = "사용자가 중지함"
                    break
                step = STEP_BY_KEY[key]
                started = timezone.now()
                run.current_step = key
                run.results[i].update(status="running", started=started.isoformat())
                run.save(update_fields=["current_step", "results"])

                log.write(f"\n===== [{i + 1}/{len(run.steps)}] {step.label} ({key}) · {started:%Y-%m-%d %H:%M:%S} =====\n")
                log.flush()
                offset = log.tell()
                try:
                    rc = run_step(step, log)
                except Exception:  # 실행 자체가 실패해도 기록은 남긴다
                    log.write(traceback.format_exc())
                    rc = -1
                log.flush()
                summary = tail(run.log_path, offset)
                log.write(f"----- 종료 코드 {rc} -----\n")
                log.flush()

                finished = timezone.now()
                run.results[i].update(status="success" if rc == 0 else "failed", rc=rc,
                                      finished=finished.isoformat(), seconds=round((finished - started).total_seconds(), 1),
                                      tail=summary)
                run.save(update_fields=["results"])
                if rc != 0:
                    failed = f"{step.label} 단계 실패 (종료 코드 {rc})"
                    if key == "validate" and rc == 1:
                        failed += " — ERROR 등급 검증 위반이 있습니다"
                    break

        for r in run.results:
            if r["status"] == "pending":
                r["status"] = "skipped"
        run.refresh_from_db(fields=["status"])
        if run.status != PipelineRun.CANCELLED:
            run.status = PipelineRun.FAILED if failed else PipelineRun.SUCCESS
        run.error = failed or ""
        run.current_step = ""
        run.finished_at = timezone.now()
        run.save()
        self.stdout.write(f"#{run.pk} {run.status} {run.error}")
