FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so editing a handler does not reinstall aiogram.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The bot writes nothing but its database, and it does that in /data.
RUN useradd --create-home --uid 10001 bot \
 && mkdir -p /data \
 && chown -R bot:bot /data /app
USER bot

ENV DB_PATH=/data/bot.db \
    HEARTBEAT_FILE=/data/heartbeat

# A polling bot serves no port, so liveness is judged by whether it is still
# doing its rounds: the cancellation check touches the heartbeat file every
# CHECK_INTERVAL_MINUTES. Three missed rounds and the container is unhealthy.
# Never probe getUpdates here — a second poller would fight the real one.
HEALTHCHECK --interval=5m --timeout=10s --start-period=3m --retries=2 \
    CMD ["python", "tools/healthcheck.py"]

CMD ["python", "main.py"]
