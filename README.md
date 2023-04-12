# qlwebapi
A Rest API for Brother Label Printers based on the [brother_ql library](https://github.com/pklaus/brother_ql).
This microservice makes it convenient to abstract away the hardware configuration of your Brother printer.
You can print a label by simply sending a POST request to `/job` with an image or pdf file.

## Getting Started
You can start the service locally by calling the `start.sh`. You should provide configuration information as
environment variables
- "QL_BACKEND": The backend brother_ql should use, "pyusb")
- "QL_PRINTER_MODEL": The model of your printer. e.g. QL-570
- "QL_PRINTER_DEVICE": The device location of your printer. If using `pyusb`, you may simply set it to `auto`. Otherwise, it should be a device path such as /dev/usb/lp0 

If running on a docker container, you can use the provided `docker-compose` file. There an example of the use of the 
environment variables listed above is already included.

## brother_ql Backends
The brother_ql library supports multiple backend. Here, we support the `linux_kernel` and `pyusb` backends. In a docker
environment, it seems like using the `linux_kernel` backend is the better choice. You can start the container
by mounting exclusively the printer's corresponding device, and avoid running it in privileged mode.

## API documentation
An interactive endpoint documentation can be viewed after deploying under `localhost:8000/docs`

## Remarks on concurrency
The printer is a shared resource, and as such access to it must be serial.
If more than one worker is used on the server, there will be no guarantee that 
this constraint will be respected. Therefore, only one worker should be instantiated.

The easiest way to solve this issue is to implement a queue with a print worker.
This was postponed since this microservice handles only print requests and, therefore,
concurrency in request handling is not needed. 

## TODO
- Handle resource locking of the printer when needed
- use udev to give a fixed path to the printer under /dev/