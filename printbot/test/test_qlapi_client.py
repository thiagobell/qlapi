import httpx
import pytest

from printbot.qlapi_client import QlapiClient, QlapiError


def make_client(handler) -> QlapiClient:
    client = QlapiClient("http://qlapi:80")
    # swap in a mock transport so no real network call happens
    client._client = httpx.AsyncClient(
        base_url="http://qlapi:80", transport=httpx.MockTransport(handler)
    )
    return client


async def test_submit_job_returns_job_id_on_202():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/job"
        assert request.url.params["rotate"] == "false"
        assert request.url.params["copies"] == "2"
        return httpx.Response(202, json={"job_id": "abc-123", "status": "queued"})

    client = make_client(handler)

    job_id = await client.submit_job("photo.jpg", b"fake-bytes", rotate=False, copies=2)

    assert job_id == "abc-123"


async def test_submit_job_accepts_bytearray_content():
    """bot.py gets a bytearray back from Telegram's download_as_bytearray().
    httpx's multipart encoder only special-cases str/bytes and calls .read()
    on anything else, so passing a raw bytearray through would break every
    real print. Pin the conversion here, since test_bot.py mocks submit_job
    and never exercises this seam.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"job_id": "abc-123", "status": "queued"})

    client = make_client(handler)

    job_id = await client.submit_job("photo.jpg", bytes(bytearray(b"fake-bytes")))

    assert job_id == "abc-123"


async def test_submit_job_wraps_transport_errors():
    """qlapi down entirely (connection refused / DNS / timeout) must surface
    as QlapiError, not a raw httpx exception escaping the handler.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[Errno 111] Connection refused")

    client = make_client(handler)

    with pytest.raises(QlapiError) as exc_info:
        await client.submit_job("photo.jpg", b"fake-bytes")

    assert exc_info.value.status_code == 0
    assert "unreachable" in exc_info.value.detail


async def test_submit_job_raises_qlapi_error_with_detail_on_503():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "No USB printer detected"})

    client = make_client(handler)

    with pytest.raises(QlapiError) as exc_info:
        await client.submit_job("photo.jpg", b"fake-bytes")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "No USB printer detected"


async def test_get_job_status_returns_parsed_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/job/abc-123"
        return httpx.Response(200, json={"job_id": "abc-123", "status": "done", "error": None})

    client = make_client(handler)

    status = await client.get_job_status("abc-123")

    assert status == {"job_id": "abc-123", "status": "done", "error": None}


async def test_get_job_status_raises_on_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Unknown job id"})

    client = make_client(handler)

    with pytest.raises(QlapiError) as exc_info:
        await client.get_job_status("does-not-exist")

    assert exc_info.value.status_code == 404
