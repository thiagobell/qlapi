import time
from unittest.mock import patch

import pytest

from qlapi.config import PrinterSettings
from qlapi.printer_manager import JobStatus, PrinterManager, PrinterUnavailableError


def test_status_unavailable_when_no_device_discovered(printer_settings: PrinterSettings):
    with patch("qlapi.printer_manager.discover", return_value=[]):
        manager = PrinterManager(printer_settings)
        status = manager.status()
        manager.shutdown()

    assert status.available is False
    assert status.error


def test_submit_fails_fast_without_queueing_when_printer_unavailable(printer_settings: PrinterSettings):
    with patch("qlapi.printer_manager.discover", return_value=[]):
        manager = PrinterManager(printer_settings)
        with pytest.raises(PrinterUnavailableError):
            manager.submit(images=[], rotate=False, copies=1)
        manager.shutdown()

    assert len(manager._jobs) == 0


def test_jobs_are_processed_serially_by_the_background_worker(printer_settings: PrinterSettings):
    fake_device = [{"instance": type("D", (), {"idVendor": 0x04F9, "idProduct": 0x2028})()}]
    calls = []

    def fake_print_label(settings, images, rotate, copies=1):
        calls.append(images)
        time.sleep(0.05)

    with patch("qlapi.printer_manager.discover", return_value=fake_device), \
         patch("qlapi.printer_manager.print_label", side_effect=fake_print_label):
        manager = PrinterManager(printer_settings)
        job1 = manager.submit(images=["a"], rotate=False, copies=1)
        job2 = manager.submit(images=["b"], rotate=False, copies=1)

        manager._queue.join()
        manager.shutdown()

    assert job1.status == JobStatus.DONE
    assert job2.status == JobStatus.DONE
    # processed in submission order, one at a time
    assert calls == [["a"], ["b"]]


def test_failed_job_records_error(printer_settings: PrinterSettings):
    fake_device = [{"instance": type("D", (), {"idVendor": 0x04F9, "idProduct": 0x2028})()}]

    def failing_print_label(settings, images, rotate, copies=1):
        raise RuntimeError("printer jammed")

    with patch("qlapi.printer_manager.discover", return_value=fake_device), \
         patch("qlapi.printer_manager.print_label", side_effect=failing_print_label):
        manager = PrinterManager(printer_settings)
        job = manager.submit(images=["a"], rotate=False, copies=1)
        manager._queue.join()
        manager.shutdown()

    assert job.status == JobStatus.FAILED
    assert "printer jammed" in job.error


def test_shutdown_finishes_queued_job_before_stopping_worker(printer_settings: PrinterSettings):
    """Graceful shutdown: a job queued before shutdown() must still complete,
    it shouldn't be dropped or killed mid-print.
    """
    fake_device = [{"instance": type("D", (), {"idVendor": 0x04F9, "idProduct": 0x2028})()}]

    def slow_print_label(settings, images, rotate, copies=1):
        time.sleep(0.05)

    with patch("qlapi.printer_manager.discover", return_value=fake_device), \
         patch("qlapi.printer_manager.print_label", side_effect=slow_print_label):
        manager = PrinterManager(printer_settings)
        job = manager.submit(images=["a"], rotate=False, copies=1)

        manager.shutdown()  # should block until the queued job above is done

    assert job.status == JobStatus.DONE
    assert not manager._worker.is_alive()
