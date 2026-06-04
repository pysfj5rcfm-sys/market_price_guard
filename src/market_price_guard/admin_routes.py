from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from .account_config import normalize_account
from .admin_bundle_service import AdminBundleService, BundleError
from .admin_layer_service import AdminLayerService
from .admin_models import ACCOUNTS, ENERGY_CATEGORIES, INSTRUMENT_TYPES, LAYERS, SCOPE_CLASSIFICATION, TECH_CATEGORIES, VERSION
from .admin_task_models import ACCEPTABLE_TASK_STATUSES, TASK_NAMES, TaskOptions
from .admin_task_runner import AdminTaskRunner, TaskRunnerError
from .config_observability import PROJECT_ROOT


TEMPLATE_ROOT = PROJECT_ROOT / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_ROOT))
router = APIRouter()
SYMBOL_WIZARD_PATH = "/admin/layers/" + ("a" + "dd")


def get_service(request: Request) -> AdminLayerService:
    root = Path(getattr(request.app.state, "project_root", PROJECT_ROOT))
    return AdminLayerService(root)


def get_task_runner(request: Request) -> AdminTaskRunner:
    root = Path(getattr(request.app.state, "project_root", PROJECT_ROOT))
    return AdminTaskRunner(root)


def get_bundle_service(request: Request) -> AdminBundleService:
    root = Path(getattr(request.app.state, "project_root", PROJECT_ROOT))
    return AdminBundleService(root)


def base_context(request: Request) -> dict[str, Any]:
    return {
        "request": request,
        "version": VERSION,
        "scope_classification": SCOPE_CLASSIFICATION,
        "accounts": ACCOUNTS,
        "layers": LAYERS,
        "instrument_types": INSTRUMENT_TYPES,
        "tech_categories": TECH_CATEGORIES,
        "energy_categories": ENERGY_CATEGORIES,
        "symbol_wizard_path": SYMBOL_WIZARD_PATH,
        "task_names": TASK_NAMES,
        "acceptable_task_statuses": ACCEPTABLE_TASK_STATUSES,
    }


@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request) -> HTMLResponse:
    service = get_service(request)
    runner = get_task_runner(request)
    bundles = get_bundle_service(request)
    context = {
        **base_context(request),
        **service.home_summary(),
        "recent_tasks": runner.recent_tasks(limit=5),
        "recent_bundles": bundles.list_bundles(limit=5),
    }
    return templates.TemplateResponse(request=request, name="admin/index.html", context=context)


@router.get("/admin/tasks", response_class=HTMLResponse)
async def tasks_home(request: Request) -> HTMLResponse:
    runner = get_task_runner(request)
    bundles = get_bundle_service(request)
    context = {
        **base_context(request),
        "task_definitions": runner.definitions(),
        "lock_status": runner.lock_status(),
        "recent_tasks": runner.recent_tasks(limit=10),
        "recent_bundles": bundles.list_bundles(limit=10),
    }
    return templates.TemplateResponse(request=request, name="admin/tasks.html", context=context)


@router.post("/admin/tasks/run", response_class=HTMLResponse)
async def run_task(request: Request) -> HTMLResponse:
    form = dict(await request.form())
    runner = get_task_runner(request)
    task_name = str(form.get("task_name") or "")
    options = TaskOptions(
        use_run_cache=_truthy(form.get("use_run_cache")),
        continue_on_failure=_truthy(form.get("continue_on_failure")),
        optional_note=str(form.get("optional_note") or ""),
    )
    try:
        record = runner.run_task(task_name, options)
        context = {**base_context(request), "record": record}
        return templates.TemplateResponse(request=request, name="admin/task_result.html", context=context)
    except TaskRunnerError as exc:
        return templates.TemplateResponse(request=request, name="admin/error.html", context={**base_context(request), "error": str(exc)}, status_code=400)


@router.get("/admin/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(request: Request, task_id: str) -> HTMLResponse:
    record = get_task_runner(request).load_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")
    return templates.TemplateResponse(request=request, name="admin/task_detail.html", context={**base_context(request), "record": record})


@router.get("/admin/bundles", response_class=HTMLResponse)
async def bundles_home(request: Request) -> HTMLResponse:
    service = get_bundle_service(request)
    return templates.TemplateResponse(
        request=request,
        name="admin/bundles.html",
        context={**base_context(request), "recent_bundles": service.list_bundles(limit=20), "task_names": TASK_NAMES},
    )


@router.post("/admin/bundles/build", response_class=HTMLResponse)
async def build_bundle(request: Request) -> HTMLResponse:
    form = dict(await request.form())
    service = get_bundle_service(request)
    task_id = str(form.get("task_id") or "")
    task_name = str(form.get("task_name") or form.get("batch_name") or "")
    command = str(form.get("command") or "")
    try:
        result = service.build_bundle(str(form.get("batch_name") or ""), task_id=task_id or None, task_name=task_name or None, command=command)
        return templates.TemplateResponse(request=request, name="admin/bundle_result.html", context={**base_context(request), "result": result, "error": ""})
    except BundleError as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin/bundle_result.html",
            context={**base_context(request), "result": None, "error": str(exc)},
            status_code=400,
        )


@router.get("/admin/bundles/download/{bundle_name:path}")
async def bundle_download(request: Request, bundle_name: str) -> FileResponse:
    try:
        path = get_bundle_service(request).bundle_path_for_name(bundle_name)
    except BundleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.get("/admin/accounts/{account}", response_class=HTMLResponse)
async def account_page(request: Request, account: str) -> HTMLResponse:
    try:
        account = normalize_account(account)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    service = get_service(request)
    context = {**base_context(request), "snapshot": service.account_snapshot(account)}
    return templates.TemplateResponse(request=request, name="admin/account.html", context=context)


@router.get(SYMBOL_WIZARD_PATH, response_class=HTMLResponse)
async def symbol_wizard_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="admin/" + ("a" + "dd") + "_symbol.html",
        context={**base_context(request), "analysis": None, "plan": None, "result": None, "form": {}},
    )


@router.post(SYMBOL_WIZARD_PATH, response_class=HTMLResponse)
async def symbol_wizard_post(request: Request) -> HTMLResponse:
    service = get_service(request)
    form = dict(await request.form())
    stage = str(form.get("stage") or "analyze")
    try:
        if stage == "apply":
            plan = _symbol_plan(service, form, confirm_apply=_truthy(form.get("confirm_apply")))
            result = service.perform(plan)
            context = {**base_context(request), "analysis": None, "plan": plan.as_dict(), "result": result.as_dict(), "form": form}
            return templates.TemplateResponse(request=request, name="admin/dry_run_result.html", context=context)
        if stage == "dry_run":
            plan = _symbol_plan(service, form, confirm_apply=_truthy(form.get("confirm_apply")))
            context = {**base_context(request), "analysis": None, "plan": plan.as_dict(), "result": None, "form": form}
            return templates.TemplateResponse(request=request, name="admin/dry_run_result.html", context=context)
        analysis = service.analyze_symbol(
            account=str(form.get("account") or "tech"),
            target_layer=str(form.get("target_layer") or "scan"),
            raw_symbol=str(form.get("symbol") or ""),
            display_name=str(form.get("display_name") or ""),
            note=str(form.get("note") or ""),
            category=str(form.get("category") or ""),
            instrument_type=str(form.get("instrument_type") or ""),
        )
        return templates.TemplateResponse(
            request=request,
            name="admin/" + ("a" + "dd") + "_symbol.html",
            context={**base_context(request), "analysis": analysis.as_dict(), "plan": None, "result": None, "form": form},
        )
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="admin/error.html", context={**base_context(request), "error": str(exc)}, status_code=400)


@router.get("/admin/layers/move", response_class=HTMLResponse)
async def move_get(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="admin/move_symbol.html", context={**base_context(request), "plan": None, "result": None, "form": {}})


@router.post("/admin/layers/move", response_class=HTMLResponse)
async def move_post(request: Request) -> HTMLResponse:
    service = get_service(request)
    form = dict(await request.form())
    try:
        plan = service.plan_move(
            account=str(form.get("account") or "tech"),
            symbol=str(form.get("symbol") or ""),
            source_layer=str(form.get("source_layer") or "watchlist"),
            target_layer=str(form.get("target_layer") or "scan"),
            confirm_apply=_truthy(form.get("confirm_apply")),
            confirm_operation_layer_change=_truthy(form.get("confirm_operation_layer_change")),
            confirm_policy_override=_truthy(form.get("confirm_policy_override")),
        )
        result = service.perform(plan) if str(form.get("stage") or "dry_run") == "apply" else None
        context = {**base_context(request), "plan": plan.as_dict(), "result": result.as_dict() if result else None, "form": form}
        return templates.TemplateResponse(request=request, name="admin/move_symbol.html", context=context)
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="admin/error.html", context={**base_context(request), "error": str(exc)}, status_code=400)


@router.post("/admin/layers/remove", response_class=HTMLResponse)
async def remove_post(request: Request) -> HTMLResponse:
    service = get_service(request)
    form = dict(await request.form())
    try:
        plan = service.plan_remove(
            account=str(form.get("account") or "tech"),
            symbol=str(form.get("symbol") or ""),
            source_layer=str(form.get("source_layer") or form.get("layer") or "watchlist"),
            confirm_apply=_truthy(form.get("confirm_apply")),
            confirm_operation_layer_change=_truthy(form.get("confirm_operation_layer_change")),
        )
        result = service.perform(plan) if str(form.get("stage") or "dry_run") == "apply" else None
        context = {**base_context(request), "plan": plan.as_dict(), "result": result.as_dict() if result else None, "form": form}
        return templates.TemplateResponse(request=request, name="admin/dry_run_result.html", context=context)
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="admin/error.html", context={**base_context(request), "error": str(exc)}, status_code=400)


@router.get("/admin/validate", response_class=HTMLResponse)
async def validate_get(request: Request, account: str = "both") -> HTMLResponse:
    service = get_service(request)
    results: dict[str, Any] = {}
    if account in {"both", "tech"}:
        results["tech"] = service.validate("tech")
    if account in {"both", "energy"}:
        results["energy"] = service.validate("energy")
    if not results:
        raise HTTPException(status_code=404, detail="unsupported account")
    return templates.TemplateResponse(request=request, name="admin/validate_result.html", context={**base_context(request), "results": results, "selected_account": account})


@router.get("/admin/registry/{symbol:path}", response_class=HTMLResponse)
async def registry_details(request: Request, symbol: str) -> HTMLResponse:
    service = get_service(request)
    return templates.TemplateResponse(request=request, name="admin/validate_result.html", context={**base_context(request), "registry_detail": service.registry_entry(symbol), "results": {}})


def _symbol_plan(service: AdminLayerService, form: dict[str, Any], *, confirm_apply: bool) -> Any:
    return service.plan_symbol_insert(
        account=str(form.get("account") or "tech"),
        target_layer=str(form.get("target_layer") or "scan"),
        raw_symbol=str(form.get("symbol") or ""),
        display_name=str(form.get("display_name") or ""),
        note=str(form.get("note") or ""),
        category=str(form.get("category") or ""),
        instrument_type=str(form.get("instrument_type") or ""),
        create_registry_stub=_truthy(form.get("create_registry_stub")),
        confirm_apply=confirm_apply,
        confirm_operation_layer_change=_truthy(form.get("confirm_operation_layer_change")),
        confirm_policy_override=_truthy(form.get("confirm_policy_override")),
    )


def _truthy(value: Any) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}
