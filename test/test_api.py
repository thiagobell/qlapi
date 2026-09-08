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


def test_health_lists_printer_status():
    req = client.get("/health")

    assert req.status_code == HTTPStatus.OK
    body = req.json()
    assert isinstance(body, list) and len(body) == 1
    assert set(body[0].keys()) >= {"name", "model", "backend", "available", "error"}


def test_job_returns_503_when_printer_unavailable(label_png):
    """
    In this test environment no printer is connected, so submitting a valid
    image must fail gracefully instead of crashing the request.
    """
    req = client.post("/job", files={"label_file": ("myfile.png", label_png)})

    assert req.status_code == HTTPStatus.SERVICE_UNAVAILABLE


def test_unknown_job_id_returns_404():
    req = client.get("/job/does-not-exist")

    assert req.status_code == HTTPStatus.NOT_FOUND
