"""데이터 파이프라인 관리자 페이지 (/ops/). staff 계정만 접근한다."""
import os, subprocess, sys
from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import reports
from .models import PipelineRun
from .steps import PRESETS, ROOT, STEP_BY_KEY, STEPS, mysql_bin

REPORT_FILES = {"quality": reports.REPORTS / "quality_report.html",
                "validation": reports.VALIDATION / "validation_report.html"}


def _reap_stale():
    """프로세스가 사라졌는데 실행 중으로 남은 기록을 실패로 정리한다."""
    for run in PipelineRun.objects.filter(status__in=PipelineRun.ACTIVE):
        if run.status == PipelineRun.RUNNING and not run.process_alive():
            _finish(run, PipelineRun.FAILED, "실행 프로세스가 비정상 종료됨 (서버 재시작·PC 종료 등)")
        elif run.status == PipelineRun.QUEUED and run.created_at < timezone.now() - timedelta(minutes=2):
            _finish(run, PipelineRun.FAILED, "실행기가 시작되지 않음")


def _finish(run, status, error):
    for r in run.results:
        if r.get("status") == "running":
            r["status"] = "cancelled" if status == PipelineRun.CANCELLED else "failed"
        elif r.get("status") == "pending":
            r["status"] = "skipped"
    run.status, run.error, run.current_step, run.finished_at = status, error, "", timezone.now()
    run.save()


def _run_json(run):
    return {"id": run.pk, "title": run.title, "status": run.status, "status_label": run.get_status_display(),
            "current_step": run.current_step, "error": run.error, "duration_s": run.duration_s,
            "results": [{**r, "label": STEP_BY_KEY[r["key"]].label} for r in run.results]
            or [{"key": k, "status": "pending", "label": STEP_BY_KEY[k].label} for k in run.steps]}


@staff_member_required
def console(request):
    _reap_stale()
    runs = list(PipelineRun.objects.all()[:20])
    active = next((r for r in runs if r.status in PipelineRun.ACTIVE), None)
    selected = None
    if request.GET.get("run"):
        selected = PipelineRun.objects.filter(pk=request.GET["run"]).first()
    selected = selected or active or (runs[0] if runs else None)

    pandas_v = reports.pandas_validation()
    mysql_v = reports.mysql_integrity()
    return render(request, "ops/console.html", {
        "presets": [(k, label, [STEP_BY_KEY[s].label for s in keys]) for k, (label, keys) in PRESETS.items()],
        "steps": STEPS, "runs": runs, "active": active, "selected": selected,
        "selected_json": _run_json(selected) if selected else None,
        "selected_errors": reports.log_errors(selected) if selected and selected.status == PipelineRun.FAILED else [],
        "log_tail": reports.log_tail(selected) if selected else "",
        "recovery": reports.recovery_summary(), "errors": reports.error_analysis(),
        "pandas_v": pandas_v, "mysql_v": mysql_v, "compare": reports.compare_validation(pandas_v, mysql_v),
        "mysql_bin": mysql_bin(), "report_files": {k: p.exists() for k, p in REPORT_FILES.items()},
    })


@staff_member_required
@require_POST
def start(request):
    preset, step = request.POST.get("preset"), request.POST.get("step")
    if preset in PRESETS:
        title, keys = PRESETS[preset]
    elif step in STEP_BY_KEY:
        title, keys = f"단계: {STEP_BY_KEY[step].label}", [step]
    else:
        messages.error(request, "실행할 단계를 선택하세요.")
        return redirect("ops:console")
    if any(STEP_BY_KEY[k].sql for k in keys) and not mysql_bin():
        messages.error(request, "mysql 클라이언트를 찾지 못해 DB 적재를 실행할 수 없습니다. .env에 MYSQL_BIN을 지정하세요.")
        return redirect("ops:console")

    _reap_stale()
    with transaction.atomic():
        if PipelineRun.objects.select_for_update().filter(status__in=PipelineRun.ACTIVE).exists():
            messages.error(request, "이미 실행 중인 작업이 있습니다. 끝난 뒤 다시 실행하세요.")
            return redirect("ops:console")
        run = PipelineRun.objects.create(title=title, steps=keys, requested_by=request.user.get_username())

    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    try:  # 웹 요청과 분리된 프로세스로 실행 (SQL 05는 약 20분)
        subprocess.Popen([sys.executable, str(ROOT / "web" / "manage.py"), "run_pipeline", str(run.pk)],
                         cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         close_fds=True, creationflags=flags, start_new_session=os.name != "nt")
    except OSError as e:
        _finish(run, PipelineRun.FAILED, f"실행기 시작 실패: {e}")
        messages.error(request, f"실행기 시작 실패: {e}")
    else:
        messages.success(request, f"#{run.pk} {title} 실행을 시작했습니다.")
    return redirect(f"/ops/?run={run.pk}")


@staff_member_required
@require_POST
def cancel(request, pk):
    run = get_object_or_404(PipelineRun, pk=pk)
    if run.status not in PipelineRun.ACTIVE:
        messages.info(request, "이미 끝난 실행입니다.")
    else:
        if run.pid and run.process_alive():
            if os.name == "nt":  # 실행기와 그 아래 mysql·python 프로세스까지 종료
                subprocess.run(["taskkill", "/PID", str(run.pid), "/T", "/F"], capture_output=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                import signal
                os.killpg(run.pid, signal.SIGTERM)
        _finish(run, PipelineRun.CANCELLED, "사용자가 중지함 — 중간에 멈춘 단계의 결과는 불완전할 수 있으니 다시 실행하세요.")
        messages.warning(request, f"#{run.pk} 실행을 중지했습니다.")
    return redirect(f"/ops/?run={run.pk}")


@staff_member_required
def status(request, pk):
    run = get_object_or_404(PipelineRun, pk=pk)
    if run.status == PipelineRun.RUNNING and not run.process_alive():
        _reap_stale()
        run.refresh_from_db()
    return JsonResponse({**_run_json(run), "log": reports.log_tail(run, 120)})


@staff_member_required
def log(request, pk):
    run = get_object_or_404(PipelineRun, pk=pk)
    if not run.log_path.exists():
        raise Http404("로그 없음")
    return FileResponse(open(run.log_path, "rb"), content_type="text/plain; charset=utf-8")


@staff_member_required
def report(request, name):
    path = REPORT_FILES.get(name)
    if not path or not path.exists():
        raise Http404("리포트 없음 — 해당 단계를 먼저 실행하세요.")
    return FileResponse(open(path, "rb"), content_type="text/html; charset=utf-8")
