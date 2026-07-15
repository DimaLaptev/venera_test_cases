FROM python:3.8-slim

ARG UID=1000
ARG GID=1000

RUN groupadd -g ${GID} app && useradd -m -u ${UID} -g ${GID} app \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -U "pip<25" \
    && pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY --chown=app:app . .

RUN mkdir -p tmp/mail_mock \
    && chown -R app:app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src \
    REPORTS_DEPO_DIRECTORY=/mnt/share/

USER app

ENTRYPOINT ["python", "/app/scripts/mail_poller.py"]
