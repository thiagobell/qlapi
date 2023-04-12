from typing import BinaryIO
import os
from pytest import fixture

from qlapi.config import PrinterSettings


__data_path = os.path.join(os.path.dirname(__file__), "data")


@fixture()
def printer_settings() -> PrinterSettings:
    yield PrinterSettings()


@fixture()
def label_png() -> BinaryIO:
    with open(os.path.join(__data_path, "testlabel.png"), "rb") as f:
        yield f


@fixture()
def label_pdf() -> BinaryIO:
    with open(os.path.join(__data_path, "test.pdf"), "rb") as f:
        yield f
