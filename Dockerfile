FROM python:3.11-slim

WORKDIR /workspace

COPY app/backend app/backend
COPY data data

RUN pip install --no-cache-dir -e "app/backend[dev]"

ENV PYTHONPATH=app/backend/src

EXPOSE 8000
