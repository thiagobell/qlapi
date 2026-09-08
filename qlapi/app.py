from typing import List
from http import HTTPStatus

from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, UploadFile, HTTPException, Depends

from brother_ql.labels import ALL_LABELS, Label as QLLabel
from qlapi.config import PrinterSettings
from qlapi.models import JobAccepted, JobStatusResponse, LabelSpecs, PrinterHealth
from qlapi.pdf import pdf2im, CouldNotLoadPDFError
from qlapi.printer_manager import PrinterManager, PrinterUnavailableError

app = FastAPI()

# Single shared settings/manager instance: construction does no I/O (see
# qlapi.config), so a disconnected printer never prevents startup. The
# manager owns a background thread that serializes prints through a queue,
# so concurrent /job requests can't race on the physical printer and don't
# block the request-handling threadpool while a print is in progress.
_printer_settings = PrinterSettings()
printer_manager = PrinterManager(_printer_settings)


def get_printer_settings() -> PrinterSettings:
    return _printer_settings


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health() -> List[PrinterHealth]:
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
              copies: int = 1) -> JobAccepted:
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
def get_job_status(job_id: str) -> JobStatusResponse:
    job = printer_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unknown job id")
    return JobStatusResponse(job_id=job.id, status=job.status, error=job.error)
