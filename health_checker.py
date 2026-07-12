#!/usr/bin/env python3
"""
Bot Sağlık Kontrol Sistemi
============================
Her 5 dakikada çalışır (cron: */5 * * * *):
- Tüm botların webhook durumunu kontrol eder
- Bekleyen güncelleme sayısını izler
- Cron son çalışma zamanlarını kontrol eder
- Sorun varsa admin'e Telegram DM gönderir
- health_status.json'a durum kaydeder
"""

import json, os, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

# --- CONFIG ---
ADMIN_BOT   = "8934662828:AAHpk-0SVDUzPzhgEtbczkmubY8qlwvldlE"  # Vip_iesrabot
ADMIN_ID    = 5019918710
STATUS_FILE = "/home/user/workspace/cron_tracking/health_status.json"
ALERT_FILE  = "/home/user/workspace/cron_tracking/health_alerts.json"

BOTLAR = {
    "odeme_bot":     "8907710571:AAHXQy5ABXgqe8CxHweK90v6WhlBYj2EbCA",
    "Vip_iesrabot":  "8934662828:AAHpk-0SVDUzPzhgEtbczkmubY8qlwvldlE",
    "esra_arsiv_bot":"8888317050:AAFbwP3FKE7TOAaF42IrOOMBHlDETjPP0fU",
    "react_bot":     "8655923137:AAF_qVciftUMZKfd3Lry0EtsVFlq6NLVf_Q",
    "Cicisinibot":   "8721708737:AAG4ANDrcTLkqbpkkhSFJxi4m0WD7DTlOpw",
}

# Cron'lar ve beklenen maksimum sessizlik süresi (saat)
CRON_KONTROL = {
    "b8961ac1": {"isim": "Kanal Reaction Bot",    "maks_sessiz_saat": 2},
    "d74f025f": {"isim": "OnlineIsra Reaction",    "maks_sessiz_saat": 2},
    "6fb07ddf": {"isim": "Arşiv Video Paylaşım",   "maks_sessiz_saat": 10},
    "e98bb808": {"isim": "Yıldız Filtre",          "maks_sessiz_saat": 4},
    "0663017f": {"isim": "VIP Üye Yöneticisi",     "maks_sessiz_saat": 26},
    "a35d099f": {"isim": "Dropbox Yedekleme",      "maks_sessiz_saat": 26},
}

# Uyarı bazı sorunlar için susturma süresi (dakika) — aynı uyarıyı tekrar etme
SUSTURMA_DK = 60

def tg(method, params=None):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{ADMIN_BOT}/{method}",
        data=json.dumps(params or {}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def susturuldu_mu(alert_key, alerts):
    """Bu uyarı son SUSTURMA_DK dakika içinde gönderildiyse True döner."""
    if alert_key not in alerts:
        return False
    last = alerts[alert_key]
    gecen = (datetime.now(timezone.utc).timestamp() - last) / 60
    return gecen < SUSTURMA_DK

def webhook_kontrol():
    """Tüm botların webhook durumunu kontrol et."""
    sorunlar = []
    durumlar = {}

    for bot_adi, token in BOTLAR.items():
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/getWebhookInfo",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())

            result      = data.get("result", {})
            url         = result.get("url", "")
            pending     = result.get("pending_update_count", 0)
            last_error  = result.get("last_error_message", "")
            last_err_dt = result.get("last_error_date", 0)

            durumlar[bot_adi] = {
                "webhook_url": url,
                "pending": pending,
                "last_error": last_error,
                "last_error_date": last_err_dt,
                "ok": True,
            }

            # Sorun tespiti
            if not url and bot_adi not in ["react_bot"]:
                sorunlar.append(f"⚠️ {bot_adi}: Webhook URL boş!")
            
            if pending > 50:
                sorunlar.append(f"🔴 {bot_adi}: {pending} bekleyen güncelleme (kritik!)")
            elif pending > 20:
                sorunlar.append(f"⚠️ {bot_adi}: {pending} bekleyen güncelleme")

            if last_error:
                import datetime as dt
                err_time = dt.datetime.fromtimestamp(last_err_dt).strftime('%H:%M') if last_err_dt else "?"
                # Son 30 dakika içindeyse uyar
                if last_err_dt and (time.time() - last_err_dt) < 1800:
                    sorunlar.append(f"⚠️ {bot_adi}: Webhook hatası ({err_time}): {last_error[:60]}")

        except Exception as e:
            sorunlar.append(f"❌ {bot_adi}: Erişilemiyor — {str(e)[:50]}")
            durumlar[bot_adi] = {"ok": False, "error": str(e)}

        time.sleep(0.3)

    return sorunlar, durumlar

def cron_kontrol():
    """Cron'ların son çalışma zamanlarını kontrol et."""
    sorunlar = []
    simdi    = datetime.now(timezone.utc)

    for cron_id, ayarlar in CRON_KONTROL.items():
        cron_dir = f"/home/user/workspace/cron_tracking/{cron_id}"
        if not os.path.exists(cron_dir):
            continue

        # Son çalışma dosyasını bul (en yeni JSON)
        try:
            dosyalar = sorted([
                f for f in os.listdir(cron_dir) if f.endswith(".json")
            ], key=lambda x: os.path.getmtime(f"{cron_dir}/{x}"), reverse=True)
        except Exception:
            continue

        if not dosyalar:
            continue

        son_degisim = os.path.getmtime(f"{cron_dir}/{dosyalar[0]}")
        gecen_saat  = (simdi.timestamp() - son_degisim) / 3600

        if gecen_saat > ayarlar["maks_sessiz_saat"]:
            sorunlar.append(
                f"⏰ {ayarlar['isim']}: {gecen_saat:.1f} saattir çalışmamış "
                f"(beklenen: maks {ayarlar['maks_sessiz_saat']}h)"
            )

    return sorunlar

def video_arsiv_kontrol():
    """Video arşivinin doluluk durumunu kontrol et."""
    sorunlar = []
    try:
        arsiv = load_json("/home/user/workspace/video_arsiv.json", [])
        toplam = len(arsiv)
        
        # Çok kullanılan videoları tespit et
        cok_kullanilan = [v for v in arsiv if v.get("kullanildi", 0) >= 3]
        az_kalan = [v for v in arsiv if v.get("kullanildi", 0) <= 1]
        
        if toplam < 5:
            sorunlar.append(f"🎬 Arşivde sadece {toplam} video var — yeni video ekle!")
        elif len(az_kalan) <= 2:
            sorunlar.append(f"🎬 Arşivdeki {toplam} videodan {len(az_kalan)}'i az kullanıldı — tükeniyor!")
        
        if len(cok_kullanilan) > toplam // 2:
            sorunlar.append(f"🎬 {len(cok_kullanilan)}/{toplam} video 3+ kez kullanıldı — tekrar riski!")
    except Exception:
        pass
    return sorunlar

def cift_webhook_kontrol(durumlar):
    """Aynı webhook URL'ine bağlı birden fazla bot var mı?"""
    sorunlar = []
    url_botlar = {}
    for bot, bilgi in durumlar.items():
        url = bilgi.get("webhook_url", "")
        if url:
            url_botlar.setdefault(url, []).append(bot)
    
    for url, botlar in url_botlar.items():
        if len(botlar) > 1:
            sorunlar.append(
                f"🔴 KRİTİK: {', '.join(botlar)} aynı webhook URL'ini paylaşıyor!\n"
                f"   URL: {url[:60]}\n"
                f"   Bu botlar birbirinin mesajlarını çalıyor!"
            )
    return sorunlar

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sağlık Kontrolü Başlıyor...")

    alerts   = load_json(ALERT_FILE, {})
    status   = load_json(STATUS_FILE, {})
    simdi    = datetime.now(timezone.utc)
    tum_sorun = []

    # 1. Webhook kontrolü
    webhook_sorunlar, durumlar = webhook_kontrol()
    tum_sorun.extend(webhook_sorunlar)

    # 2. Çift webhook kontrolü
    cift_sorunlar = cift_webhook_kontrol(durumlar)
    tum_sorun.extend(cift_sorunlar)

    # 3. Cron kontrolü
    cron_sorunlar = cron_kontrol()
    tum_sorun.extend(cron_sorunlar)

    # 4. Video arşiv kontrolü
    arsiv_sorunlar = video_arsiv_kontrol()
    tum_sorun.extend(arsiv_sorunlar)

    # Status kaydet
    status = {
        "son_kontrol": simdi.isoformat(),
        "sorun_sayisi": len(tum_sorun),
        "bot_durumlari": durumlar,
        "sorunlar": tum_sorun,
    }
    save_json(STATUS_FILE, status)

    if not tum_sorun:
        print("✅ Tüm sistemler normal")
        return

    # Susturma filtresi — aynı uyarıyı tekrar gönderme
    yeni_sorunlar = []
    for sorun in tum_sorun:
        key = sorun[:50]
        if not susturuldu_mu(key, alerts):
            yeni_sorunlar.append(sorun)
            alerts[key] = simdi.timestamp()

    save_json(ALERT_FILE, alerts)

    if not yeni_sorunlar:
        print(f"ℹ️ {len(tum_sorun)} sorun var ama hepsi son {SUSTURMA_DK}dk içinde bildirildi")
        return

    # Admin'e bildir
    rapor = f"🚨 <b>Bot Sistem Uyarısı</b>\n⏰ {simdi.strftime('%H:%M')} UTC\n\n"
    for i, sorun in enumerate(yeni_sorunlar[:8], 1):
        rapor += f"{i}. {sorun}\n\n"

    if len(yeni_sorunlar) > 8:
        rapor += f"... ve {len(yeni_sorunlar) - 8} sorun daha"

    tg("sendMessage", {
        "chat_id": ADMIN_ID,
        "text": rapor,
        "parse_mode": "HTML"
    })
    print(f"🚨 {len(yeni_sorunlar)} yeni sorun — admin bildirildi")
    for s in yeni_sorunlar:
        print(f"  - {s[:80]}")

if __name__ == "__main__":
    main()
