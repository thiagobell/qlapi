from datetime import datetime, timezone
from typing import List
from http import HTTPStatus
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, Request, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from brother_ql.labels import ALL_LABELS, Label as QLLabel
from qlapi.config import PrinterSettings
from qlapi.models import JobAccepted, JobStatusResponse, LabelSpecs, PrinterHealth, Template, TemplateMeta, TemplateSave
from qlapi.pdf import pdf2im, CouldNotLoadPDFError
from qlapi.printer_manager import PrinterManager, PrinterUnavailableError
from qlapi import templates as templates_store

# Settings construction does no I/O (see qlapi.config), so a disconnected
# printer never prevents startup.
_printer_settings = PrinterSettings()

app = FastAPI()

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ponytail: fastapi~=0.79.0 (pinned for pydantic v1 compat) predates the
# `lifespan=` context-manager parameter -- passing it is silently swallowed
# into **extra and never runs. on_event is the real startup/shutdown hook on
# this version. Upgrade path: switch to `lifespan=` once fastapi/pydantic
# are bumped to v2-compatible versions.
@app.on_event("startup")
async def _start_printer_manager():
    # The manager owns a background thread that serializes prints through a
    # queue, so concurrent /job requests can't race on the physical printer
    # and don't block the request-handling threadpool while a print is in
    # progress. Started/stopped with the app instead of at import time so it
    # has a real (graceful) shutdown: already-queued jobs finish before the
    # worker thread stops, instead of being killed mid-print on exit.
    app.state.printer_manager = PrinterManager(_printer_settings)


@app.on_event("shutdown")
async def _stop_printer_manager():
    app.state.printer_manager.shutdown()


def get_printer_settings() -> PrinterSettings:
    return _printer_settings


def get_printer_manager(request: Request) -> PrinterManager:
    return request.app.state.printer_manager


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/editor")
async def editor():
    """Serves the in-browser label editor, a single static page."""
    return FileResponse(_STATIC_DIR / "editor.html")


@app.get("/health")
async def health(printer_manager: PrinterManager = Depends(get_printer_manager)) -> List[PrinterHealth]:
    """Lists reachability status for each configured printer (currently one)."""
    status = printer_manager.status()
    return [PrinterHealth(
        name=status.name,
        model=status.model,
        backend=status.backend,
        available=status.available,
        error=status.error,
    )]


@app.get("/labels")
async def labels(printer_settings: PrinterSettings = Depends(get_printer_settings)) -> List[LabelSpecs]:
    # Filter out labels which are supported by printer

    __available_labels: List[QLLabel] = [
        label for label in ALL_LABELS
        if len(label.restricted_to_models) == 0
        or printer_settings.model_id in label.restricted_to_models
    ]

    labels_dict = [LabelSpecs(
        name=label.name,
        identifier=label.identifier,
        form_factor=label.form_factor,
        tape_size=label.tape_size,
        dots_total=label.dots_total,
        dots_printable=label.dots_printable,
        is_default=label.identifier == printer_settings.default_label
    ) for label in __available_labels]
    return labels_dict


@app.post("/job", status_code=HTTPStatus.ACCEPTED)
def print_job(label_file: UploadFile,
              rotate: bool = False,
              copies: int = 1,
              printer_manager: PrinterManager = Depends(get_printer_manager)) -> JobAccepted:
    """
    Queues the provided file to be printed and returns immediately with a job id.
    Printing itself happens serially on a background worker (see printer_manager),
    so this never blocks on the physical printer and concurrent requests can't
    race on it.
    Args:
        label_file:
        rotate:
        copies:

    Returns: the queued job id and its initial status. Poll GET /job/{job_id} for progress.

    """

    # check the format of image_file
    ext = label_file.filename.lower().split(".")[-1]

    allowed_extensions = ["pdf", "jpg", "jpeg", "png"]

    if copies < 1:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                            detail=f"Invalid number of copies")

    if ext not in allowed_extensions:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                            detail=f"({ext}) is not a valid extension."
                                   f"Formats accepted: {allowed_extensions}")
    if ext in ["pdf"]:
        try:
            # convert pdf into images
            images = pdf2im(label_file.file)
        except CouldNotLoadPDFError:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                                detail=f"The file provided has a PDF extension "
                                       f"but could not opened. Is it an actual PDF?"
                                       f"Formats accepted: {allowed_extensions}")

    else:
        try:
            images = [
                Image.open(label_file.file)
            ]
        except UnidentifiedImageError:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                                detail=f"The file provided has an image extension "
                                       f"but is not a (supported) image"
                                       f"Formats accepted: {allowed_extensions}")
    try:
        job = printer_manager.submit(images, rotate, copies)
    except PrinterUnavailableError as exc:
        raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=str(exc))

    return JobAccepted(job_id=job.id, status=job.status)


@app.get("/job/{job_id}")
def get_job_status(job_id: str,
                    printer_manager: PrinterManager = Depends(get_printer_manager)) -> JobStatusResponse:
    job = printer_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unknown job id")
    return JobStatusResponse(job_id=job.id, status=job.status, error=job.error)


@app.get("/templates")
def list_templates() -> List[TemplateMeta]:
    return [TemplateMeta(**meta) for meta in templates_store.list_templates()]


@app.get("/templates/{template_id}")
def get_template(template_id: str) -> Template:
    try:
        return Template(**templates_store.get_template(template_id))
    except FileNotFoundError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unknown template id")


@app.post("/templates", status_code=HTTPStatus.OK)
def create_template(body: TemplateSave) -> Template:
    template_id = templates_store.new_id()
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "name": body.name,
        "label_identifier": body.label_identifier,
        "created_at": now,
        "updated_at": now,
        "canvas": body.canvas,
    }
    return Template(**templates_store.save_template(template_id, data))


@app.post("/templates/{template_id}")
def update_template(template_id: str, body: TemplateSave) -> Template:
    try:
        existing = templates_store.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unknown template id")
    data = {
        "name": body.name,
        "label_identifier": body.label_identifier,
        "created_at": existing["created_at"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "canvas": body.canvas,
    }
    return Template(**templates_store.save_template(template_id, data))


@app.delete("/templates/{template_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_template(template_id: str):
    if not templates_store.delete_template(template_id):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unknown template id")

