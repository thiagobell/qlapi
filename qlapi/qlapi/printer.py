from typing import List, Optional

from PIL import Image
from brother_ql import BrotherQLRaster
from brother_ql.backends.helpers import send
from brother_ql.conversion import convert

from qlapi.config import PrinterSettings


def print_label(
    printer_settings: PrinterSettings,
    images: List[Image.Image],
    rotate: bool,
    copies: int = 1,
    label: Optional[str] = None
):
    """
    Prints a label.
    Image will be printed with its height axis along the label feed unless the `rotate` arg is set to true
    Args:
        printer_settings: the settings to use for printing
        images: a list of images to print, as bytes or as Pillow's Image instance
        rotate: rotates the label as described in method documentation.
        copies: the number of copies to print
        label: the label to use. If none uses the default.

    Returns:

    """
    # adapted from https://github.com/pklaus/brother_ql/blob/master/brother_ql/cli.py#L134

    qlr = BrotherQLRaster(printer_settings.model_id)
    qlr.exception_on_warning = True

    instructions = convert(
        qlr=qlr,
        images=images,
        label=label if label is not None else printer_settings.default_label,
        cut=True,
        dither=True,
        compress=False,  # not needed
        rotate=90 if rotate else 0,
    )
    for i in range(copies):
        send(
            instructions=instructions,
            printer_identifier=printer_settings.device,
            backend_identifier=printer_settings.backend,
            blocking=True
        )
