#!/usr/bin/env python3
"""
reaction-bot scheduler
────────────────────────
story_reaction_bot.py'yi HER SAAT çalıştırır ve şu sorunları çözer:

1. Script timeout (630s) sorunu:
   - Her API çağrısına HTTP_TIMEOUT_SECONDS (varsayılan 25s) sınırı konur
   - Tüm iş subprocess.run(timeout=JOB_TIMEOUT_SECONDS) ile sarılır (varsayılan 300s)
   - Zaman aşımı olursa iş sonlandırılır, sonraki saatlik çalışmayı bloklamaz

2. Cron çakışması (abf04916 / b738eb18 aynı saatte -> rate limit):
   - Bu servis TEK bir scheduler döngüsüdür; aynı işin iki kopyasının aynı
     anda çalışmasını önlemek için basit dosya kilidi (lock file) kullanır

3. reaction_onlineisra.py ile aynı saatte çalışmayı da önlemek için farklı
   dakikalarda (xx:00 reaction, xx:07 onlineisra) tetikleme uygulanır.
"""

import os
import subprocess
import threading
import time
from datetime import datetime, timezone

import schedule

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CRON_TRACKING_DIR = "/app/cron_tracking/reaction_bot"
HEARTBEAT_FILE = "/app/cron_tracking/reaction_heartbeat"
LOCK_FILE = "/app/cron_tracking/reaction_bot.lock"
JOB_TIMEOUT = int(os.environ.get("JOB_TIMEOUT_SECONDS", "300"))

os.makedirs(CRON_TRACKING_DIR, exist_ok=True)


def _touch_heartbeat():
    with open(HEARTBEAT_FILE, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def _is_locked() -> bool:
    if not os.path.exists(LOCK_FILE):
        return False
    # 10 dakikadan eski kilit dosyası -> önceki çalışma takılı kalmış, kilidi kaldır
    age = time.time() - os.path.getmtime(LOCK_FILE)
    if age > 600:
        os.remove(LOCK_FILE)
        return False
    return True


def run_reaction_job():
    if _is_locked():
        print("[reaction-scheduler] önceki iş hâlâ kilitli, bu tetikleme atlanıyor (çakışma engeli)")
        return

    open(LOCK_FILE, "w").close()
    log_path = os.path.join(
        CRON_TRACKING_DIR, f"run_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}.log"
    )
    print(f"[{datetime.now(timezone.utc).isoformat()}] story_reaction_bot.py çalıştırılıyor...")
    try:
        result = subprocess.run(
            ["python3", os.path.join(APP_DIR, "story_reaction_bot.py")],
            capture_output=True,
            text=True,
            timeout=JOB_TIMEOUT,
        )
        with open(log_path, "w") as f:
            f.write(result.stdout + "\n--- STDERR ---\n" + result.stderr)
    except subprocess.TimeoutExpired:
        with open(log_path, "w") as f:
            f.write(f"TIMEOUT: {JOB_TIMEOUT} saniyede tamamlanamadı, iş sonlandırıldı")
        print(f"[reaction-scheduler] iş {JOB_TIMEOUT}s içinde tamamlanamadı, sonlandırıldı")
    except Exception as e:
        with open(log_path, "w") as f:
            f.write(f"HATA: {e}")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        _touch_heartbeat()


def scheduler_loop():
    schedule.every().hour.at(":00").do(run_reaction_job)
    _touch_heartbeat()
    while True:
        schedule.run_pending()
        time.sleep(15)


if __name__ == "__main__":
    scheduler_loop()
