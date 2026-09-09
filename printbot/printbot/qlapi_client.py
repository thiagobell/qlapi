"""Thin async client for the qlapi print service."""
import httpx


class QlapiError(Exception):
    """Raised for any non-2xx response from qlapi."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"qlapi returned {status_code}: {detail}")


def _detail_from_response(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except ValueError:
        pass
    # Truncated: this ends up in a Telegram message, which caps at 4096 chars,
    # and an HTML error page from a proxy would blow past that.
    return (resp.text or resp.reason_phrase)[:500]


class QlapiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def submit_job(
        self, filename: str, content: bytes, rotate: bool = False, copies: int = 1
    ) -> str:
        """POSTs the file to /job. Returns the job_id. Raises QlapiError on failure
        (e.g. 400 bad file, 503 printer unavailable).
        """
        try:
            resp = await self._client.post(
                "/job",
                params={"rotate": rotate, "copies": copies},
                files={"label_file": (filename, content)},
            )
        except httpx.HTTPError as exc:
            # qlapi down/unreachable (connect refused, DNS, timeout). Funnel
            # into QlapiError so callers only handle one exception type.
            raise QlapiError(0, f"qlapi unreachable: {exc}") from exc

        if resp.status_code != httpx.codes.ACCEPTED:
            raise QlapiError(resp.status_code, _detail_from_response(resp))
        return resp.json()["job_id"]

    async def get_job_status(self, job_id: str) -> dict:
        """GETs /job/{job_id}. Returns the parsed {"status": ..., "error": ...} body."""
        try:
            resp = await self._client.get(f"/job/{job_id}")
        except httpx.HTTPError as exc:
            raise QlapiError(0, f"qlapi unreachable: {exc}") from exc

        if resp.status_code != httpx.codes.OK:
            raise QlapiError(resp.status_code, _detail_from_response(resp))
        return resp.json()
