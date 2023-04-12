from http import HTTPStatus
from fastapi.testclient import TestClient

from qlapi.app import app

client = TestClient(app)


def test_fail_on_invalid_extension(label_pdf):
    req = client.post("/job", files={"label_file": ("myfile.doc", label_pdf)})

    assert req.status_code == HTTPStatus.BAD_REQUEST
    assert "doc" in req.text


def test_fail_on_png_extension_no_image(label_pdf):
    """
    Checks for the case where a file is sent with an image extension but is not one
    Returns:

    """

    req = client.post("/job", files={"label_file": ("myfile.png", label_pdf)})

    assert req.status_code == HTTPStatus.BAD_REQUEST


def test_fail_on_pdf_extension_no_pdf(label_png):
    """
    Checks for the case where a file is sent with the pdf extension but is not one
    Returns:

    """

    req = client.post("/job", files={"label_file": ("myfile.pdf", label_png)})

    assert req.status_code == HTTPStatus.BAD_REQUEST
