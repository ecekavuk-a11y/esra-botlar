#!/usr/bin/env python3
"""
health_checker.py — Malatya Esra Bot Sistemi Sağlık Denetleyicisi
====================================================================

Her CHECK_INTERVAL_SECONDS (varsayılan 300s = 5 dakika) şu kontrolleri yapar:

  1. Her bot için Telegram getWebhookInfo çağrısı:
       - pending_update_count > 10 ise UYARI
       - last_error_message doluysa UYARI
       - webhook URL beklenenden farklıysa UYARI (çift webhook tespiti)
       - iki botun webhook URL'i AYNI ise KRİTİK UYARI (kök sorun #1)
  2. Cron son çalışma zamanı kontrolü (heartbeat dosyaları):
       - /home/user/workspace/cron_tracking altındaki ilgili dosyalar
       - 2 saatten eskiyse UYARI
  3. Sorun tespit edilirse admin'e Telegram DM gönderir (rate-limited:
     aynı sorun için 30 dakikada bir defadan fazla mesaj göndermez)
  4. Tüm sonuçları /home/user/workspace/cron_tracking/health_status.json'a yazar

Ortam değişkenleri (.env üzerinden):
  ODEME_BOT_TOKEN, VIP_BOT_TOKEN, ARSIV_BOT_TOKEN, REACT_BOT_TOKEN, CICI_BOT_TOKEN
  ADMIN_ID
  CHECK_INTERVAL_SECONDS (varsayılan 300)
"""

import json
import os
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ── Yapılandırma ────────────────────────────────────────────────────────────
ADMIN_ID = os.environ.get("ADMIN_ID", "5019918710")
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))
PENDING_UPDATE_ESIK = int(os.environ.get("PENDING_UPDATE_ESIK", "10"))
CRON_STALE_HOURS = int(os.environ.get("CRON_STALE_HOURS", "2"))
ALERT_COOLDOWN_SECONDS = int(os.environ.get("ALERT_COOLDOWN_SECONDS", "1800"))  # 30 dk

# Alarm göndermek için kullanılacak "kanal" botu — health-checker'ın kendi
# token'ı olmayabilir; ADMIN_ALERT_BOT_TOKEN env'i yoksa odeme_bot token'ı kullanılır.
ALERT_BOT_TOKEN = os.environ.get("ADMIN_ALERT_BOT_TOKEN") or os.environ.get("ODEME_BOT_TOKEN", "")

# İzlenecek botlar: (isim, token_env_adı, beklenen_webhook_url_env_adı)
BOTS = [
    {
        "name": "odeme_bot",
        "token_env": "ODEME_BOT_TOKEN",
        "expected_webhook_env": "ODEME_BOT_WEBHOOK_URL",
    },
    {
        "name": "Vip_iesrabot",
        "token_env": "VIP_BOT_TOKEN",
        "expected_webhook_env": "VIP_BOT_WEBHOOK_URL",
    },
    {
        "name": "esra_arsiv_bot",
        "token_env": "ARSIV_BOT_TOKEN",
        "expected_webhook_env": "ARSIV_BOT_WEBHOOK_URL",
    },
    {
        "name": "react_bot",
        "token_env": "REACT_BOT_TOKEN",
        "expected_webhook_env": None,  # bilinen şekilde ölü / polling yok
    },
    {
        "name": "Cicisinibot",
        "token_env": "CICI_BOT_TOKEN",
        "expected_webhook_env": "CICI_BOT_WEBHOOK_URL",
    },
]

# Heartbeat dosyaları (docker-compose volume: cron-tracking paylaşılan)
CRON_TRACKING_DIR = Path("/app/cron_tracking")
HEARTBEAT_FILES = {
    "reaction-bot (saatlik)": CRON_TRACKING_DIR / "reaction_heartbeat",
    "arsiv-bot (günde 3x)": CRON_TRACKING_DIR / "arsiv_heartbeat",
    "vip-manager (günlük)": CRON_TRACKING_DIR / "vip_heartbeat",
}

STATUS_FILE = CRON_TRACKING_DIR / "health_status.json"
ALERT_STATE_FILE = CRON_TRACKING_DIR / "health_alert_state.json"
HEALTH_HEARTBEAT_FILE = CRON_TRACKING_DIR / "health_heartbeat"

CRON_TRACKING_DIR.mkdir(parents=True, exist_ok=True)


# ── Yardımcı fonksiyonlar ───────────────────────────────────────────────────
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_webhook_info(token: str) -> dict:
    """Telegram getWebhookInfo çağrısı yapar. Hata durumunda ok=False döner."""
    if not token:
        return {"ok": False, "error": "token tanımlı değil"}
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10
        )
        data = resp.json()
        if not data.get("ok"):
            return {"ok": False, "error": data.get("description", "bilinmeyen hata")}
        return {"ok": True, "result": data["result"]}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"istek hatası: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"beklenmeyen hata: {e}"}


def get_pending_update_count_via_getupdates(token: str) -> dict:
    """
    Webhook'u olmayan botlar (react_bot gibi) için getUpdates ile
    bekleyen mesaj sayısını tahmin eder. NOT: Eğer webhook AKTİFSE bu
    çağrı 409 Conflict döner — bu bilerek webhook durumunu ikinci kez
    doğrulamak için kullanılır (yildiz_filtre_bot 409 sorunuyla aynı desen).
    """
    if not token:
        return {"ok": False, "error": "token tanımlı değil"}
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"timeout": 0, "limit": 1},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            if "Conflict" in str(data.get("description", "")):
                return {"ok": False, "conflict": True, "error": data.get("description")}
            return {"ok": False, "error": data.get("description", "bilinmeyen hata")}
        return {"ok": True, "result": data["result"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_alert_state() -> dict:
    if ALERT_STATE_FILE.exists():
        try:
            return json.loads(ALERT_STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_alert_state(state: dict):
    ALERT_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def send_admin_alert(message: str, alert_key: str, alert_state: dict) -> bool:
    """
    Rate-limited admin uyarısı. Aynı alert_key için ALERT_COOLDOWN_SECONDS
    içinde tekrar mesaj göndermez. Gönderilirse True döner.
    """
    last_sent = alert_state.get(alert_key, 0)
    if time.time() - last_sent < ALERT_COOLDOWN_SECONDS:
        return False

    if not ALERT_BOT_TOKEN:
        print(f"[health-checker] UYARI (bot token yok, konsola yazılıyor): {message}")
        alert_state[alert_key] = time.time()
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{ALERT_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        ok = resp.json().get("ok", False)
        if ok:
            alert_state[alert_key] = time.time()
        return ok
    except Exception as e:
        print(f"[health-checker] admin uyarısı gönderilemedi: {e}")
        return False


# ── Ana kontrol döngüsü ─────────────────────────────────────────────────────
def check_bots(alert_state: dict) -> dict:
    results = {}
    webhook_urls_seen = {}  # url -> [bot_name, ...]  (çift webhook tespiti)

    for bot in BOTS:
        name = bot["name"]
        token = os.environ.get(bot["token_env"], "")
        expected_url = os.environ.get(bot["expected_webhook_env"] or "", "")

        info = get_webhook_info(token)
        entry = {"checked_at": _now_iso(), "ok": info.get("ok", False)}

        if not info.get("ok"):
            entry["error"] = info.get("error")
            msg = f"🔴 <b>{name}</b>: getWebhookInfo başarısız — {info.get('error')}"
            send_admin_alert(msg, f"webhook_fail:{name}", alert_state)
            results[name] = entry
            continue

        wh = info["result"]
        url = wh.get("url", "")
        pending = wh.get("pending_update_count", 0)
        last_error = wh.get("last_error_message")
        last_error_date = wh.get("last_error_date")

        entry.update(
            {
                "url": url,
                "pending_update_count": pending,
                "last_error_message": last_error,
                "last_error_date": last_error_date,
            }
        )

        # react_bot özel durumu: webhook YOK + polling YOK -> ölü bot
        if bot["expected_webhook_env"] is None and not url:
            getupdates = get_pending_update_count_via_getupdates(token)
            entry["polling_check"] = getupdates
            msg = (
                f"⚠️ <b>{name}</b>: webhook yok, polling da yapılmıyor — bot ÖLÜ durumda.\n"
                f"Bu botu yeniden aktive etmek veya devre dışı bırakmak gerekiyor."
            )
            send_admin_alert(msg, f"dead_bot:{name}", alert_state)

        # pending update eşiği
        if pending > PENDING_UPDATE_ESIK:
            msg = (
                f"⚠️ <b>{name}</b>: {pending} bekleyen güncelleme var "
                f"(eşik: {PENDING_UPDATE_ESIK}). Bot mesajları işleyemiyor olabilir."
            )
            send_admin_alert(msg, f"pending:{name}", alert_state)

        # last_error_message kontrolü
        if last_error:
            msg = f"🔴 <b>{name}</b>: Telegram webhook hatası bildiriyor: {last_error}"
            send_admin_alert(msg, f"last_error:{name}", alert_state)

        # 409 Conflict deseni: webhook aktifken getUpdates çağrılıyor mu?
        # (yildiz_filtre_bot sorunuyla aynı desen — burada pasif olarak izleniyor)
        if url:
            getupdates = get_pending_update_count_via_getupdates(token)
            if getupdates.get("conflict"):
                entry["getupdates_conflict"] = True
                msg = (
                    f"⚠️ <b>{name}</b>: webhook aktifken ayrıca getUpdates çağrılıyor "
                    f"(409 Conflict deseni — yildiz_filtre_bot sorunuyla aynı). "
                    f"Polling kodu kapatılmalı."
                )
                send_admin_alert(msg, f"conflict:{name}", alert_state)

        # Çift webhook tespiti
        if url:
            webhook_urls_seen.setdefault(url, []).append(name)

        # Beklenen URL karşılaştırması
        if expected_url and url and url != expected_url:
            entry["url_mismatch"] = True
            msg = (
                f"⚠️ <b>{name}</b>: webhook URL beklenenden farklı.\n"
                f"Beklenen: {expected_url}\nGerçek: {url}"
            )
            send_admin_alert(msg, f"url_mismatch:{name}", alert_state)

        results[name] = entry

    # Çift/çakışan webhook kontrolü (kök sorun #1)
    for url, bots_on_url in webhook_urls_seen.items():
        if len(bots_on_url) > 1:
            msg = (
                f"🔴 <b>ÇİFT WEBHOOK ÇAKIŞMASI</b>\n"
                f"Şu botlar AYNI URL'e point ediyor: {', '.join(bots_on_url)}\n"
                f"URL: {url}\n"
                f"Bu durumda mesajlar birbirine karışır — her botun kendi path'i olmalı."
            )
            send_admin_alert(msg, f"dup_webhook:{url}", alert_state)

    return results


def check_cron_heartbeats(alert_state: dict) -> dict:
    results = {}
    now = time.time()
    stale_seconds = CRON_STALE_HOURS * 3600

    for label, path in HEARTBEAT_FILES.items():
        if not path.exists():
            results[label] = {"ok": False, "error": "heartbeat dosyası hiç oluşmadı"}
            msg = f"⚠️ <b>{label}</b>: heartbeat dosyası bulunamadı — servis hiç çalışmamış olabilir."
            send_admin_alert(msg, f"no_heartbeat:{label}", alert_state)
            continue

        age = now - path.stat().st_mtime
        last_run = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        is_stale = age > stale_seconds

        results[label] = {
            "ok": not is_stale,
            "last_run": last_run,
            "age_hours": round(age / 3600, 2),
        }

        if is_stale:
            msg = (
                f"⚠️ <b>{label}</b>: son çalışma {round(age / 3600, 1)} saat önce "
                f"(eşik: {CRON_STALE_HOURS} saat). Cron takılmış olabilir."
            )
            send_admin_alert(msg, f"stale_cron:{label}", alert_state)

    return results


def run_check_cycle():
    alert_state = load_alert_state()
    status = {
        "checked_at": _now_iso(),
        "bots": {},
        "cron_heartbeats": {},
    }

    try:
        status["bots"] = check_bots(alert_state)
    except Exception as e:
        print(f"[health-checker] check_bots hatası: {e}")
        traceback.print_exc()
        status["bots_error"] = str(e)

    try:
        status["cron_heartbeats"] = check_cron_heartbeats(alert_state)
    except Exception as e:
        print(f"[health-checker] check_cron_heartbeats hatası: {e}")
        traceback.print_exc()
        status["cron_error"] = str(e)

    save_alert_state(alert_state)
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2))
    HEALTH_HEARTBEAT_FILE.write_text(_now_iso())
    print(f"[{_now_iso()}] sağlık kontrolü tamamlandı -> {STATUS_FILE}")


def main():
    print(f"health-checker başlatıldı. Kontrol aralığı: {CHECK_INTERVAL_SECONDS}s")
    while True:
        try:
            run_check_cycle()
        except Exception as e:
            print(f"[health-checker] genel hata: {e}")
            traceback.print_exc()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
