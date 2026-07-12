#!/usr/bin/env python3
"""
arsiv-bot scheduler
────────────────────
Docker konteyneri içinde çalışan giriş noktası:
  1. Flask ile /health endpoint sunar (Docker healthcheck için)
  2. `schedule` kütüphanesi ile arsiv_paylasim_cron.py'yi günde 3 kez çalıştırır
     (09:00, 15:00, 21:00 İstanbul saati -> 06:00, 12:00, 18:00 UTC)
  3. Her çalışmadan sonra heartbeat dosyasını günceller
     (health-checker servisi bu dosyayı 2 saatten eski mi diye kontrol eder)

video_arsiv.json tükenme riskine karşı: paylaşımdan önce arşivdeki
kullanılabilir video sayısını kontrol eder, azsa admin'e uyarı gönderir.
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone

import schedule
from flask import Flask, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CRON_TRACKING_DIR = "/app/cron_tracking/arsiv_bot"
HEARTBEAT_FILE = "/app/cron_tracking/arsiv_heartbeat"
VIDEO_ARSIV_PATH = "/app/video_arsiv.json"
ADMIN_ID = os.environ.get("ADMIN_ID", "5019918710")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MIN_VIDEO_ESIK = int(os.environ.get("MIN_VIDEO_ESIK", "5"))

os.makedirs(CRON_TRACKING_DIR, exist_ok=True)

app = Flask(__name__)


def _touch_heartbeat():
    with open(HEARTBEAT_FILE, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def _send_admin_alert(text: str):
    if not BOT_TOKEN:
        return
    try:
        import requests

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[arsiv-scheduler] admin uyarı gönderilemedi: {e}")


def _check_video_stock():
    """9 videoluk arşiv hızla tükeniyor sorunu için erken uyarı."""
    try:
        with open(VIDEO_ARSIV_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        videos = data if isinstance(data, list) else data.get("videos", [])
        kalan = len(videos)
        if kalan <= MIN_VIDEO_ESIK:
            _send_admin_alert(
                f"⚠️ <b>Arşiv Stok Uyarısı</b>\n"
                f"Arşivde sadece {kalan} video kaldı (eşik: {MIN_VIDEO_ESIK}).\n"
                f"Yeni video eklenmezse paylaşım döngüsü kısa süre içinde tükenecek."
            )
    except Exception as e:
        print(f"[arsiv-scheduler] video stok kontrolü başarısız: {e}")


def run_paylasim_job():
    print(f"[{datetime.now(timezone.utc).isoformat()}] arsiv_paylasim_cron.py çalıştırılıyor...")
    _check_video_stock()
    log_path = os.path.join(
        CRON_TRACKING_DIR, f"run_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}.log"
    )
    try:
        result = subprocess.run(
            ["python3", os.path.join(APP_DIR, "arsiv_paylasim_cron.py")],
            capture_output=True,
            text=True,
            timeout=280,  # script timeout sorununa karşı sert sınır
        )
        with open(log_path, "w") as f:
            f.write(result.stdout + "\n--- STDERR ---\n" + result.stderr)
        if result.returncode != 0:
            _send_admin_alert(
                f"🔴 <b>arsiv_paylasim_cron.py hata ile bitti</b>\nreturncode={result.returncode}"
            )
    except subprocess.TimeoutExpired:
        with open(log_path, "w") as f:
            f.write("TIMEOUT: 280 saniyede tamamlanamadı")
        _send_admin_alert("🔴 <b>arsiv_paylasim_cron.py zaman aşımına uğradı</b> (280s)")
    except Exception as e:
        _send_admin_alert(f"🔴 <b>arsiv_paylasim_cron.py çalıştırma hatası</b>\n{e}")
    finally:
        _touch_heartbeat()


def scheduler_loop():
    # 06:00, 12:00, 18:00 UTC = 09:00, 15:00, 21:00 İstanbul
    schedule.every().day.at("06:00").do(run_paylasim_job)
    schedule.every().day.at("12:00").do(run_paylasim_job)
    schedule.every().day.at("18:00").do(run_paylasim_job)
    _touch_heartbeat()
    while True:
        schedule.run_pending()
        time.sleep(30)


@app.route("/health")
def health():
    return jsonify(status="ok", service="arsiv-bot", ts=datetime.now(timezone.utc).isoformat())


@app.route("/webhook/arsiv", methods=["POST"])
def webhook_arsiv():
    """esra_arsiv_bot Telegram webhook giriş noktası (admin video yükleme vb.)."""
    from flask import request

    update = request.get_json(silent=True) or {}
    print(f"[arsiv-webhook] update_id={update.get('update_id')}")
    # arsiv_bot.py içindeki güncelleme işleme mantığı buraya entegre edilebilir.
    return jsonify(ok=True)


if __name__ == "__main__":
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3002)))
