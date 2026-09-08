import os


class InvalidSettingsError(Exception):
    pass


class PrinterSettings:
    """Printer configuration read from environment variables.

    Construction is cheap and does no I/O: actual device discovery and
    reachability checks happen lazily (see qlapi.printer_manager), so a
    disconnected printer never prevents the API from starting up.
    """

    def __init__(self):
        self.default_label = "62"
        self.backend = os.getenv("QL_BACKEND", "pyusb")
        self.model_id = os.getenv("QL_PRINTER_MODEL", "QL-570")

        self.device = os.getenv("QL_PRINTER_DEVICE", "auto")
        """The file system device where the printer is reachable. format depends on the backend.
        If using pyusb, can set this environment variable to auto and the printer will be 
        automatically detected
        """

        if self.device == "auto" and self.backend != "pyusb":
            raise InvalidSettingsError("'auto' option for QL_PRINTER_DEVICE is "
                                       "only supported with the 'pyusb' backend")

