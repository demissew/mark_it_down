FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir .

COPY app.py /app/

RUN useradd -m -u 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 29999
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:29999", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
