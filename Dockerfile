FROM python:3.11-slim

WORKDIR /workspace

COPY app/backend app/backend
COPY data data
COPY scripts scripts

# The optional postgres extra keeps the default image one install; memory mode
# ignores psycopg entirely. Do not install [dev] in the runtime image.
RUN pip install --no-cache-dir "app/backend[postgres]"

ENV PYTHONPATH=app/backend/src
ENV APP_ENV=production

EXPOSE 8000

CMD ["uvicorn", "delivery_platform.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
