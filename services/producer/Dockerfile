# Lightweight Python 3.11-slim container for Transaction Replay Simulator
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir requests kafka-python-ng pydantic

COPY data/paysim_sample.csv /app/data/paysim_sample.csv
COPY services/producer/ /app/services/producer/

ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "services.producer.producer"]

