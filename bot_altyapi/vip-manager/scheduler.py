#!/usr/bin/env python3
"""
vip-manager scheduler
────────────────────────
vip_erisim_yonetici.py'yi HER GÜN 06:00 UTC (09:00 İstanbul) çalıştırır.
Supabase'deki members tablosunu tarar, süresi dolanları çıkarır,
yaklaşanları uyarır, admin'e özet rapor gönderir.
"""

import os
import subprocess
import time
from datetime import datetime, timezone

import schedule

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CRON_TRACKING_DIR = "/app/cron_tracking/vip_yonetici"
HEARTBEAT_FILE = "/app/cron_tracking/vip_heartbeat"
JOB_TIMEOUT = int(os.environ.get("JOB_TIMEOUT_SECONDS", "300"))

os.makedirs(CRON_TRACKING_DIR, exist_ok=True)


def _touch_heartbeat():
    with open(HEARTBEAT_FILE, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def run_vip_job():
    print(f"[{datetime.now(timezone.utc).isoformat()}] vip_erisim_yonetici.py çalıştırılıyor...")
    log_path = os.path.join(
        CRON_TRACKING_DIR, f"run_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
    )
    try:
        result = subprocess.run(
            ["python3", os.path.join(APP_DIR, "vip_erisim_yonetici.py")],
            capture_output=True,
            text=True,
            timeout=JOB_TIMEOUT,
        )
        with open(log_path, "w") as f:
            f.write(result.stdout + "\n--- STDERR ---\n" + result.stderr)
    except subprocess.TimeoutExpired:
        with open(log_path, "w") as f:
            f.write(f"TIMEOUT: {JOB_TIMEOUT} saniyede tamamlanamadı")
    except Exception as e:
        with open(log_path, "w") as f:
            f.write(f"HATA: {e}")
    finally:
        _touch_heartbeat()


def scheduler_loop():
    schedule.every().day.at("06:00").do(run_vip_job)
    _touch_heartbeat()
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    scheduler_loop()
