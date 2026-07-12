# ──────────────────────────────────────────────────────────────
# arsiv-bot — Python: arsiv_paylasim_cron.py + arsiv_bot.py scheduler
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget curl tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY arsiv_bot.py arsiv_paylasim_cron.py caption_motor.py scheduler.py ./

RUN mkdir -p /app/cron_tracking && \
    useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

USER botuser

EXPOSE 3002

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "scheduler.py"]
