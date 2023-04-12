from typing import BinaryIO

from unittest.mock import MagicMock
from PIL import Image

from qlapi import printer
from qlapi.config import PrinterSettings


def test_print_label_count(
    printer_settings: PrinterSettings,
    label_png: BinaryIO
):
    send_mock = MagicMock()
    copies = 3
    printer.send = send_mock
    printer.print_label(
        printer_settings,
        [Image.open(label_png)],
        rotate=False,
        copies=copies
    )

    assert send_mock.call_count == copies
