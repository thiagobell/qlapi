"""
Serializes access to the physical printer through a single background
worker thread + queue, and exposes non-throwing reachability checks so a
disconnected/unplugged printer degrades to a clear error instead of
crashing the process (see qlapi.config for why construction itself never
does I/O).
"""
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from PIL import Image
from brother_ql.backends.helpers import discover

from qlapi.config import PrinterSettings
from qlapi.printer import print_label


class JobStatus(str, Enum):
    QUEUED = "queued"
    PRINTING = "printing"
    DONE = "done"
    FAILED = "failed"


class PrinterUnavailableError(Exception):
    """Raised when the printer cannot be reached right now."""


@dataclass
class PrintJob:
    id: str
    status: JobStatus = JobStatus.QUEUED
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class PrinterStatus:
    name: str
    model: str
    backend: str
    configured_device: str
    available: bool
    resolved_device: Optional[str] = None
    error: Optional[str] = None


def _resolve_device(settings: PrinterSettings) -> str:
    """Returns the concrete device identifier to print to.

    Raises PrinterUnavailableError instead of crashing the caller if the
    printer can't currently be found.
    """
    if settings.backend == "pyusb":
        identifiers = [
            f"usb://0x{d['instance'].idVendor:04x}:0x{d['instance'].idProduct:04x}"
            for d in discover(settings.backend)
        ]
        if settings.device == "auto":
            if not identifiers:
                raise PrinterUnavailableError("No USB printer detected")
            settings.device = identifiers[0]  # cache, mirrors previous behavior
            return settings.device
        if settings.device not in identifiers:
            raise PrinterUnavailableError(f"Printer {settings.device} not detected on USB")
        return settings.device

    # ponytail: reachability for non-pyusb backends (e.g. linux_kernel) only
    # checks that the device file exists, not e.g. paper-out/cover-open.
    # Upgrade path: send a brother_ql status request and parse the reply.
    if not os.path.exists(settings.device):
        raise PrinterUnavailableError(f"Device {settings.device} not found")
    return settings.device


class PrinterManager:
    """Owns one printer's settings, a serial print queue, and job tracking."""

    def __init__(self, settings: PrinterSettings, name: str = "default"):
        self.settings = settings
        self.name = name
        self._queue: "queue.Queue" = queue.Queue()
        self._jobs: Dict[str, PrintJob] = {}
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def status(self) -> PrinterStatus:
        try:
            resolved = _resolve_device(self.settings)
            return PrinterStatus(
                name=self.name, model=self.settings.model_id, backend=self.settings.backend,
                configured_device=self.settings.device, available=True, resolved_device=resolved,
            )
        except Exception as exc:
            return PrinterStatus(
                name=self.name, model=self.settings.model_id, backend=self.settings.backend,
                configured_device=self.settings.device, available=False, error=str(exc),
            )

    def submit(self, images: List[Image.Image], rotate: bool, copies: int) -> PrintJob:
        """Queues a print job. Fails fast (raises PrinterUnavailableError)
        instead of queueing a job that's doomed to fail.
        """
        _resolve_device(self.settings)

        job = PrintJob(id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        self._queue.put((job, images, rotate, copies))
        return job

    def get_job(self, job_id: str) -> Optional[PrintJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self):
        while True:
            job, images, rotate, copies = self._queue.get()
            job.status = JobStatus.PRINTING
            try:
                _resolve_device(self.settings)
                print_label(self.settings, images, rotate, copies=copies)
                job.status = JobStatus.DONE
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
            finally:
                self._queue.task_done()
