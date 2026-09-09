from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from qlapi.app import app


@pytest.fixture()
def client():
    # Using the context-manager form triggers the app's lifespan
    # (startup/shutdown), which is what starts the printer_manager.
    with TestClient(app) as c:
        yield c


def test_fail_on_invalid_extension(client, label_pdf):
    req = client.post("/job", files={"label_file": ("myfile.doc", label_pdf)})

    assert req.status_code == HTTPStatus.BAD_REQUEST
    assert "doc" in req.text


def test_fail_on_png_extension_no_image(client, label_pdf):
    """
    Checks for the case where a file is sent with an image extension but is not one
    Returns:

    """

    req = client.post("/job", files={"label_file": ("myfile.png", label_pdf)})

    assert req.status_code == HTTPStatus.BAD_REQUEST


def test_fail_on_pdf_extension_no_pdf(client, label_png):
    """
    Checks for the case where a file is sent with the pdf extension but is not one
    Returns:

    """

    req = client.post("/job", files={"label_file": ("myfile.pdf", label_png)})

    assert req.status_code == HTTPStatus.BAD_REQUEST


def test_health_lists_printer_status(client):
    req = client.get("/health")

    assert req.status_code == HTTPStatus.OK
    body = req.json()
    assert isinstance(body, list) and len(body) == 1
    assert set(body[0].keys()) >= {"name", "model", "backend", "available", "error"}


def test_job_returns_503_when_printer_unavailable(client, label_png):
    """
    In this test environment no printer is connected, so submitting a valid
    image must fail gracefully instead of crashing the request.
    """
    req = client.post("/job", files={"label_file": ("myfile.png", label_png)})

    assert req.status_code == HTTPStatus.SERVICE_UNAVAILABLE


def test_unknown_job_id_returns_404(client):
    req = client.get("/job/does-not-exist")

    assert req.status_code == HTTPStatus.NOT_FOUND
