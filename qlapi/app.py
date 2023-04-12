from typing import List
from http import HTTPStatus

from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, UploadFile, HTTPException, Depends

from brother_ql.labels import ALL_LABELS, Label as QLLabel
from qlapi.config import PrinterSettings
from qlapi.models import LabelSpecs
from qlapi.pdf import pdf2im, CouldNotLoadPDFError
from qlapi.printer import print_label

# Checks configuration:
PrinterSettings()


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/labels")
async def labels(printer_settings: PrinterSettings = Depends(PrinterSettings)) -> List[LabelSpecs]:
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


@app.post("/job")
def print_job(label_file: UploadFile,
              rotate: bool = False,
              copies: int = 1,
              printer_settings: PrinterSettings = Depends(PrinterSettings)):
    """
    Prints the provided file. Made this function non async on purpose to try and avoid
    race conditions on the printer.
    Args:
        printer_settings:
        label_file:
        rotate:
        copies:

    Returns:

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
    print_label(
        printer_settings,
        images,
        rotate,
        copies=copies,
    )
