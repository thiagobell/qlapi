# qlwebapi
A Rest API for Brother Label Printers based on the [brother_ql library](https://github.com/pklaus/brother_ql).
This microservice makes it convenient to abstract away the hardware configuration of your Brother printer.
You can print a label by simply sending a POST request to `/job` with an image or pdf file.

## Getting Started
This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Install uv, then run `./start.sh`
(or `uv run uvicorn qlapi.app:app --reload`) to start the service locally. `uv` will create the virtualenv and
install pinned dependencies from `uv.lock` automatically. To run the tests: `uv run pytest`.

You should provide configuration information as environment variables
- "QL_BACKEND": The backend brother_ql should use, "pyusb")
- "QL_PRINTER_MODEL": The model of your printer. e.g. QL-570
- "QL_PRINTER_DEVICE": The device location of your printer. If using `pyusb`, you may simply set it to `auto`. Otherwise, it should be a device path such as /dev/usb/lp0 
- "QL_TEMPLATES_DIR": Directory where label templates are stored (JSON files). Defaults to `qlapi/data/templates` inside the package. In Docker, set it to a mounted volume path (e.g. `/data/templates`) so templates persist across container recreation.

If running on a docker container, you can use the provided `docker-compose` file. There an example of the use of the 
environment variables listed above is already included.

The API starts fine even if the printer is unplugged/unreachable; `GET /health` reports its reachability and
`POST /job` returns `503` instead of crashing when it can't be reached.

## brother_ql Backends
The brother_ql library supports multiple backend. Here, we support the `linux_kernel` and `pyusb` backends. In a docker
environment, it seems like using the `linux_kernel` backend is the better choice. You can start the container
by mounting exclusively the printer's corresponding device, and avoid running it in privileged mode.

## API documentation
An interactive endpoint documentation can be viewed after deploying under `localhost:8000/docs`

## Endpoints

| Method | Path              | Description                                                           |
|--------|-------------------|------------------------------------------------------------------------|
| GET    | `/`               | Liveness check, returns `{"message": "Hello World"}`                  |
| GET    | `/health`         | Reachability status of each configured printer                        |
| GET    | `/labels`         | Label types supported by the configured printer model                 |
| POST   | `/job`            | Queues a file (`pdf`/`jpg`/`jpeg`/`png`) to print, returns a `job_id`  |
| GET    | `/job/{job_id}`   | Status of a previously submitted print job                            |

See below for details on `/job` and `/health`; full request/response schemas are in `/docs`.

## Printing is queued
`POST /job` validates and decodes the file, then enqueues the print and returns `202` immediately with a
`job_id`. A single background worker thread drains the queue and prints jobs one at a time, so:
- requests never block waiting for the physical print to finish
- concurrent requests can't race on the printer (previously a real risk: FastAPI runs sync endpoints in a
  threadpool, so multiple in-flight `/job` calls could hit the printer at the same time)

Poll `GET /job/{job_id}` for `queued` / `printing` / `done` / `failed` (+ `error` message) status.

The worker starts/stops with the app's startup/shutdown hooks: on shutdown, already-queued jobs are
allowed to finish (so a label isn't cut mid-feed) before the worker thread stops.

Note: job state is kept in memory only and is lost on restart. This is a single small local-network service,
so that's an acceptable ceiling for now; swap in a persistent store (e.g. sqlite) if jobs need to survive restarts.

## Health check
`GET /health` returns a list with the reachability status of each configured printer (currently one),
e.g. `available`, `model`, `backend`, and an `error` message if unreachable. It does not crash the API when
the printer is disconnected.

## TODO
- use udev to give a fixed path to the printer under /dev/