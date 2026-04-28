FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY data ./data
COPY frontend ./frontend
COPY training ./training
COPY serving ./serving

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
