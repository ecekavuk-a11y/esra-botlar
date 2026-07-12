# ──────────────────────────────────────────────────────────────
# reaction-bot — Python: story_reaction_bot.py saatlik scheduler
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY story_reaction_bot.py scheduler.py ./

RUN mkdir -p /app/cron_tracking && \
    useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

USER botuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "scheduler.py"]
