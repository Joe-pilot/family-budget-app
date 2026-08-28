FROM python:3.14-alpine

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN apk upgrade --no-cache \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall --yes pip setuptools wheel \
    && addgroup -g 10001 appuser \
    && adduser -D -u 10001 -G appuser appuser
COPY --chown=appuser:appuser bot.py .

USER 10001:10001
CMD ["python", "bot.py"]
