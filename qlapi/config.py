import os

from brother_ql.backends.helpers import discover


class NoDeviceFoundError(Exception):
    """Raised if tried to find printers in the system but did not find any"""

class InvalidSettingsError(Exception):
    pass


class PrinterSettings:

    def __init__(self):
        self.default_label = "62"
        self.backend = os.getenv("QL_BACKEND", "pyusb")
        self.model_id = os.getenv("QL_PRINTER_MODEL", "QL-570")

        self.device = os.getenv("QL_PRINTER_DEVICE", "auto")
        """The file system device where the printer is reachable. format depends on the backend.
        If using pyusb, can set this environment variable to auto and the printer will be 
        automatically detected
        """

        if self.device == "auto":
            if self.backend != "pyusb":
                raise InvalidSettingsError("'auto' option for QL_PRINTER_DEVICE is "
                                           "only supported with the 'pyusb' backend")

            devices = discover(self.backend)
            if len(devices) == 0:
                raise NoDeviceFoundError
            device_identifier = devices[0]['instance']
            self.device = f"usb://0x{device_identifier.idVendor:04x}:0x{device_identifier.idProduct:04x}"
            print(f"device is {self.device}")

