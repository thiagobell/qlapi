FROM python:3.10-bullseye

WORKDIR /app
RUN apt-get update && apt-get install -y libusb-1.0-0

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
COPY qlapi qlapi

CMD ["uvicorn", "qlapi.app:app", "--host", "0.0.0.0", "--port", "80"]