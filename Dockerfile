FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-rus \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY bot ./bot
COPY welcome.md .

ENV HF_HOME=/app/hf_cache \
    DATA_DIR=/app/data \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
