#!/usr/bin/env python3
"""
Esra Arşiv Paylaşım Botu — Cron Sürümü
=======================================
VPS gerektirmez. Her çalıştırıldığında:
  1. video_arsiv.json'dan en az kullanılan videoyu seçer
  2. 3 kanala yıldızlı (ücretli) olarak gönderir
  3. Sonucu admin'e Telegram DM ile bildirir

Kullanım:
  python3 arsiv_paylasim_cron.py          # Paylaşım yap
  python3 arsiv_paylasim_cron.py --liste  # Arşivi listele (terminal)
"""

import urllib.request, urllib.error
import json, os, sys, time
from datetime import datetime, timezone

# Caption motorunu içe aktar
try:
    sys.path.insert(0, "/home/user/workspace")
    from caption_motor import caption_uret, onay_ile_calistir, onay_kontrol
    ONAY_MODU = False  # Cron modunda onay bekleme — direkt gönder
except ImportError:
    ONAY_MODU = False

# ─── AYARLAR ────────────────────────────────────────────────────
BOT_TOKEN = "8888317050:AAFbwP3FKE7TOAaF42IrOOMBHlDETjPP0fU"  # esra_arsiv_bot
ADMIN_ID  = 5019918710
VIP_LINK  = "https://t.me/Vip_iesrabot"

KANALLAR = [
    -1003494573579,   # Ücretsiz 1
    -1002956424495,   # Ücretsiz 2
    -1003959424039,   # Arşiv
]

ARSIV_DOSYASI   = "/home/user/workspace/video_arsiv.json"
PAYLASIM_LOG    = "/home/user/workspace/cron_tracking/paylasim_log.json"

# ─── CAPTION ŞABLONLARI — Yedek (caption_motor import edilemezse) ─
CAPTION_SABLONLAR = {
    "sabah": [
        "günaydın 🌸 sabahı benimle aç\ndevamı VIP'te sizi bekliyor 😏\n\n💎 {vip}\n⭐ {yildiz} yıldız ile izle",
        "sabah sabah aklıma siz düştünüz 🌹\nbir şeyler hazırladım, kalanı VIP'te\n\n→ {vip}\n⭐ {yildiz} yıldız",
        "güne güzel başlayalım 🔥\nönizleme bu kadar, gerisi VIP'te\n\n💎 {vip}\n⭐ {yildiz} yıldız ile devamını gör",
        "sabah kahvenden önce bunu gör 😈\ngerçek olan VIP kanalda\n\n🔗 {vip}\n⭐ {yildiz} yıldız",
    ],
    "ogle": [
        "öğle arası sizi düşündüm 🍯\nbir kısmını gösterdim, gerisi VIP'te\n\n💎 {vip}\n⭐ {yildiz} yıldız ile izle",
        "az önce çektim, size özel 🔥\ndevamı her zaman VIP'te oluyor 😏\n\n→ {vip}\n⭐ {yildiz} yıldız",
        "canım sıkıldı, sizi düşündüm 🌹\ngel VIP'te devamına bak 😏\n\n💎 {vip}\n⭐ {yildiz} yıldız",
        "yeni video sıcacık 🔥\ntüm içeriklere erişim VIP'te\n\n→ {vip}\n⭐ {yildiz} yıldız ile izle",
    ],
    "aksam": [
        "akşam oldu, sizi özledim 🌅\ndevamını görmek isteyene kapım açık\n\n💎 {vip}\n⭐ {yildiz} yıldız ile izle",
        "bu kadar mı? tabii ki hayır 😈\ngeri kalanı sana özel VIP'te\n\n🔗 {vip}\n⭐ {yildiz} yıldız",
        "akşamı güzelleştirelim mi 🔥\nönizleme bu kadar, devamı VIP'te\n\n→ {vip}\n⭐ {yildiz} yıldız",
        "sadece sizin için çektim 🍯\nbir kısmını gösterdim, gerisi VIP'te\n\n💎 {vip}\n⭐ {yildiz} yıldız ile devamını gör",
    ],
    "gece": [
        "bu gece biraz eğlendim 🌙\nkalanı VIP'te sizi bekliyor...\n\n→ {vip}\n⭐ {yildiz} yıldız",
        "iyi geceler 🔥 ya da daha iyi mi yapalım?\ndevamı için biliyorsunuz ne yapılacağını\n\n{vip}\n⭐ {yildiz} yıldız ile izle",
        "gece yarısı aklıma siz geldiniz 😈\ngerçek olan VIP kanalda\n\n🔗 {vip}\n⭐ {yildiz} yıldız",
        "sadece seçilmişler için 🌙\nVIP üyelerim her şeyi tam görüyor\n\ngel katıl: {vip}\n⭐ {yildiz} yıldız",
    ],
}

# ─── YARDIMCI ────────────────────────────────────────────────────

def api(method, params):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(params).encode()
    req  = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "description": str(e)}


def load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def gun_zamani() -> str:
    saat = (datetime.now(timezone.utc).hour + 3) % 24
    if 6 <= saat < 12:   return "sabah"
    elif 12 <= saat < 18: return "ogle"
    elif 18 <= saat < 22: return "aksam"
    else:                 return "gece"


def siradaki_caption(yildiz: int, index: int) -> str:
    zaman    = gun_zamani()
    sablonlar = CAPTION_SABLONLAR[zaman]
    sablon   = sablonlar[index % len(sablonlar)]
    return sablon.format(vip=VIP_LINK, yildiz=yildiz)


def admin_bildir(metin: str):
    api("sendMessage", {"chat_id": ADMIN_ID, "text": metin, "parse_mode": "HTML"})

# ─── PAYLAŞIM ────────────────────────────────────────────────────

def paylasim_yap():
    arsiv = load_json(ARSIV_DOSYASI, [])
    if not isinstance(arsiv, list):
        arsiv = []

    if not arsiv:
        admin_bildir("⚠️ <b>Arşiv boş!</b>\nVideo eklemek için botu açman gerekiyor.")
        print("❌ Arşiv boş")
        return

    # Sadece +18 (tur/kategori = 'porno' veya '18+') videolar
    arsiv_18 = [v for v in arsiv if v.get("tur", "").lower() in ("porno", "18+", "+18", "adult", "x")]
    if not arsiv_18:
        # Kategori yoksa tüm arşivi kullan (geriye uyumluluk)
        arsiv_18 = arsiv

    # En az kullanılan videoyu seç
    video   = min(arsiv_18, key=lambda x: x.get("kullanildi", 0))
    file_id = video["file_id"]
    sure_sn = video.get("sure_sn", 120)

    # Yıldız fiyatı — dakikaya göre: 0-5dk=350, 5-10dk=600, 10dk+=999
    if sure_sn <= 300:   yildiz = 350    # 0-5 dakika
    elif sure_sn <= 600: yildiz = 600    # 5-10 dakika
    else:                yildiz = 999    # 10+ dakika

    # Caption index — log'dan al
    log    = load_json(PAYLASIM_LOG, {"caption_index": 0, "gecmis": []})
    idx    = log.get("caption_index", 0)
    # Caption motoru varsa onay akışını kullan
    if ONAY_MODU:
        print("  📝 Caption motoru aktif — onay bekleniyor")
        onay_ile_calistir(
            file_id=file_id,
            yildiz=yildiz,
            sure_sn=sure_sn,
        )
        admin_bildir(
            f"📝 Caption hazır, onay bekleniyor.\n"
            f"📹 {video.get('dosya_adi','?')} · {yildiz}⭐\n"
            f"Onaylamak için yukarıdaki mesajı kullan."
        )
        print("✅ Onay isteği gönderildi — gönderim onay sonrası yapılacak")
        return  # Onay gelene kadar dur

    # caption_motor varsa onu kullan (100 caption havuzu), yoksa yedek şablona düş
    try:
        from caption_motor import caption_uret
        caption, idx = caption_uret(yildiz, idx)
    except Exception:
        caption = siradaki_caption(yildiz, idx)

    now_str = datetime.now(timezone.utc).strftime
    basari  = 0
    hatalar = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Paylaşım başlıyor — {len(KANALLAR)} kanal, {yildiz}⭐")

    for kanal_id in KANALLAR:
        # Önce yıldızlı (ücretli) dene
        r = api("sendPaidMedia", {
            "chat_id":     kanal_id,
            "star_count":  yildiz,
            "media":       [{"type": "video", "media": file_id, "supports_streaming": True}],
            "caption":     caption,
            "parse_mode":  "HTML",
        })

        if not r.get("ok"):
            # Yıldızlı başarısız → normal video gönder
            desc = r.get("description", "")
            print(f"  ⚠️ Kanal {kanal_id} yıldızlı hata: {desc[:60]} — normal deneniyor")
            r = api("sendVideo", {
                "chat_id":           kanal_id,
                "video":             file_id,
                "caption":           caption,
                "parse_mode":        "HTML",
                "supports_streaming": True,
            })

        if r.get("ok"):
            basari += 1
            print(f"  ✅ Kanal {kanal_id} → gönderildi")
        else:
            err = r.get("description", "?")
            hatalar.append(f"Kanal {kanal_id}: {err[:80]}")
            print(f"  ❌ Kanal {kanal_id} → {err[:60]}")

        time.sleep(2)

    # Kullanım sayısını güncelle
    for v in arsiv:
        if v["file_id"] == file_id:
            v["kullanildi"] = v.get("kullanildi", 0) + 1
    save_json(ARSIV_DOSYASI, arsiv)

    # Log güncelle
    log["caption_index"] = idx + 1
    log.setdefault("gecmis", []).append({
        "zaman":   datetime.now(timezone.utc).isoformat(),
        "basari":  basari,
        "kanal":   len(KANALLAR),
        "yildiz":  yildiz,
        "hatalar": hatalar,
    })
    log["gecmis"] = log["gecmis"][-60:]  # Son 60 paylaşım
    save_json(PAYLASIM_LOG, log)

    # Admin bildirimi
    saat_ist = (datetime.now(timezone.utc).hour + 3) % 24
    dk       = sure_sn // 60
    sn_      = sure_sn % 60

    if basari > 0:
        metin = (
            f"✅ <b>Paylaşım tamamlandı</b>\n"
            f"⏰ {saat_ist:02d}:{datetime.now(timezone.utc).minute:02d} (İstanbul)\n\n"
            f"📹 {video.get('dosya_adi','?')} ({dk}:{sn_:02d})\n"
            f"⭐ {yildiz} yıldız\n"
            f"📡 {basari}/{len(KANALLAR)} kanala gönderildi"
        )
        if hatalar:
            metin += "\n\n⚠️ Hatalar:\n" + "\n".join(hatalar)
    else:
        metin = (
            f"❌ <b>Paylaşım başarısız</b>\n"
            f"⏰ {saat_ist:02d}:{datetime.now(timezone.utc).minute:02d}\n\n"
            + "\n".join(hatalar)
        )

    admin_bildir(metin)
    print(f"{'✅' if basari > 0 else '❌'} {basari}/{len(KANALLAR)} kanal | {yildiz}⭐")


def arsiv_listele():
    arsiv = load_json(ARSIV_DOSYASI, [])
    if not arsiv:
        print("Arşiv boş.")
        return
    print(f"\n📦 Arşivde {len(arsiv)} video:\n")
    for i, v in enumerate(arsiv, 1):
        sure = v.get("sure_sn", 0)
        dk, sn = sure // 60, sure % 60
        print(f"  {i}. {v.get('dosya_adi','?')} | {dk}:{sn:02d} | "
              f"{v.get('yildiz',0)}⭐ | {v.get('kullanildi',0)}× kullanıldı")
    print()


# ─── ANA ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--liste" in sys.argv:
        arsiv_listele()
    else:
        paylasim_yap()
