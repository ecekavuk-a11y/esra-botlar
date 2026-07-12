#!/usr/bin/env python3
"""
Caption Dönüşüm Motoru + Onay Akışı
======================================
Çalışma mantığı:
  1. Taslak metni alır (veya saate göre otomatik üretir)
  2. Emoji-yoğun, etkileşim odaklı +18 metne dönüştürür
  3. Onay için admin'e DM gönderir (inline butonlar: ✅ Gönder / ✏️ Değiştir / ❌ İptal)
  4. Admin onaylarsa kanallara yayınlar
  5. "Değiştir" seçilirse alternatif şablon sunar

Kullanım:
  python3 caption_motor.py                    # Otomatik caption üret + onay iste
  python3 caption_motor.py --onay-kontrol     # Bekleyen onayları kontrol et
  python3 caption_motor.py --test "metin"     # Metni dönüştür, göndermeden göster
"""

import urllib.request, urllib.error
import json, os, sys, time, random
from datetime import datetime, timezone

# ════════════════════════════════════════════════════════════════════
# ⚙️  AYARLAR
# ════════════════════════════════════════════════════════════════════

BOT_TOKEN  = "8888317050:AAFbwP3FKE7TOAaF42IrOOMBHlDETjPP0fU"  # esra_arsiv_bot
ADMIN_ID   = 5019918710
VIP_LINK   = "https://t.me/Vip_iesrabot"

KANALLAR = [
    -1003494573579,   # Ücretsiz 1
    -1002956424495,   # Ücretsiz 2
    -1003959424039,   # Arşiv
]

ONAY_BEKLEYEN_DOSYA = "/home/user/workspace/cron_tracking/onay_bekleyen.json"
CAPTION_LOG_DOSYA   = "/home/user/workspace/cron_tracking/caption_log.json"

# ════════════════════════════════════════════════════════════════════
# CAPTION HAVUZU — Katmanlı Yapı
# Her şablon {vip} ve {yildiz} yer tutucuları içerir
# Emoji yoğunluğu: yüksek, orta, minimal — rotasyonla seçilir
# ════════════════════════════════════════════════════════════════════

# Kullanıcının caption listesi — az emoji, azdırıcı ve doğal
CAPTION_LISTESI = [
    'Sabah uyandım, ilk aklıma sen geldin ',
    'Bugün hiç giymek istemedim ',
    'Vücudum seni arıyor şu an ',
    'Yavaşça soyunuyorum, izliyor musun ',
    'Dokunuşunu hissedebiliyorum sanki ',
    'Bugün çok azdım, ne yapacağımı bilemedim ',
    'Ellerini hissetsem şu an... ',
    'Gözlerimi kapatınca seninle oluyorum ',
    'Islak ve beklemedeyim ',
    'Seni düşününce durduramıyorum kendimi ',
    'Kalçalarımı izlersen ne olur acaba ',
    'Bugün kamera önünde çok rahatladım ',
    'İçimde bir şeyler yanıyor, söndürecek biri yok ',
    'Yavaşça açılmak istiyorum sana ',
    'Sesim titredi çekerken, hissettin mi ',
    'Bu gece yalnız yatamam ',
    'Seni içimde hissetmeyi hayal ettim bugün ',
    'Göğüslerim sertleşti, ne yapmalıyım ',
    'Bugün kendimi tutamadım ',
    'Kamerayı açtım, aklımda sadece sen vardın ',
    'Islak yerim seni bekliyor ',
    'Yavaş yavaş iniyorum, takip ediyor musun ',
    'Bu videoyu izlerken dudağını ısırırsın ',
    'Dokunulmak için can atıyorum ',
    'Vücudum bugün çok hassas ',
    'Kalçalarımı verirken düşündüm seni ',
    'Neler yaptım bugün, bilsen ',
    'Ağzımı açtım kameraya, hissettim mi dedin ',
    'Seni azdırmak için özel çektim bunu ',
    'Elimle kendime dokundum, seni düşünerek ',
    'Sabahtan beri azdım, kimse bilmiyor ',
    'Bu gece özel bir şey hazırladım sana ',
    'Yavaş ve derin, hissediyor musun ',
    'Dudaklarım seni istiyor ',
    'İçime girmek ister misin ',
    'Vücudum senin, ne yaparsan yap ',
    'Bugün hiç iç çamaşırı giymeden çektim ',
    'Sesi bile beni azdırdı ',
    'Derinlere inmek istiyorum seninle ',
    'Kalçalarım seni bekliyor bu gece ',
    'İzlesen bile tahrik ederim seni ',
    'Kendimi tutamadım bugün ',
    'Ağzımla neler yapabileceğimi biliyor musun ',
    'Bu gece çok ateşliyim, yak beni ',
    'Dokunuşunu özledim, ellerini özledim ',
    'Kameranın önünde eriyorum ',
    'Sana özel bir şey sakladım ',
    'Islak ve azgın, gel söndür ',
    'Dudaklarımı ısırırken seni düşünüyorum ',
    'Bu videoyu izle, pişman olmayacaksın ',
    'Vücudum titriyor, kontrol edemiyorum ',
    'Yavaşça bacaklarımı açıyorum ',
    'Bugün ne kadar iyi hissettirdiğimi göreceksin ',
    'Göğüslerimi okşarken gözlerimi kapattım ',
    'Seni içimde hayal ettim, ıslandım ',
    'Bu saatte bu kadar azmak normal mi ',
    'Sadece sana gösteriyorum bunu ',
    'Ellerim seni arıyor şu an ',
    'Yatağa uzandım, aklımda sadece sen varsın ',
    'Bir şey hazırladım, utandım bile çekerken ',
    'Kalçalarıma baktığında ne hissediyorsun ',
    'Ağzım açıkken çektim, izle ',
    'Seni beklerken kendime dokundum ',
    'Bu gece erken yatmayacaksın ',
    'Vücudumu seninle paylaşmak istiyorum ',
    'Islak yerim için gel şu an ',
    'Dudağımı ısırırken hep seni düşünüyorum ',
    'Bu videoyu bitirince daha fazlasını isteyeceksin ',
    'Ellerinle ne yapardın acaba ',
    'Sadece senin için soyunuyorum ',
    'Vücudum hazır, sen hazır mısın ',
    'Bugün çok yaramaz hissediyorum ',
    'Kalçalarıma bak, sonra konuşuruz ',
    'Derin bir nefes aldım, sen aklıma geldin ',
    'Gece yarısı uyandım, ıslanmışım ',
    'Seni izlerken bile azdım ',
    'Dudaklarım seni arıyor ',
    'Bugün kendi elimle tattım ',
    'İzlersen pişman olmayacaksın, söz ',
    'Seninle olmayı o kadar istedim ki ',
    'Vücudum senin emrinde bu gece ',
    'Seni içime almak istiyorum şu an ',
    'Sabah kalktım, ilk iş bunu çektim ',
    'Ağzımda seni hissediyorum ',
    'Bu gece yalnız değilim, sen varsın aklımda ',
    'Kalçalarımı verirken ismin aklımda döndü ',
    'Islak ve sıcak, gel ',
    'Bugün hiç duramadım, çok azdım ',
    'Beni izlerken dudağını ısırıyorsun değil mi ',
    'Sadece sana açılıyorum bu gece ',
    'Ellerini hissetsem yeterdi ',
    'Seni düşünerek yaptım bunu ',
    'Bu gece özel, sadece senin için ',
    'Uyumadan önce bir bak, pişman olmayacaksın ',
    'Dudaklarımla neler yapabilirim, biliyor musun ',
    'Bugün kendimi çok iyi hissettim ',
    'Sana olan açlığımı tarif edemiyorum ',
    'Gel, sana her şeyi göstereyim ',
    'Bugün sadece senin için çektim ',
    'Vücudum seninle yanmak istiyor ',
]

# Geriye dönük uyumluluk için zaman dilimine göre listeden çek
CAPTION_HAVUZU = {
    "sabah": CAPTION_LISTESI[0:25],
    "ogle":  CAPTION_LISTESI[25:50],
    "aksam": CAPTION_LISTESI[50:75],
    "gece":  CAPTION_LISTESI[75:100],
}

# Özel durum şablonları — VIP linkleri ve yönlendirme tamamen kapatıldı
OZEL_SABLONLAR = {}


# ════════════════════════════════════════════════════════════════════
# Yardımcı
# ════════════════════════════════════════════════════════════════════

def api(method, params=None, timeout=30):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(params or {}).encode()
    req  = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        return {"ok": False, "description": body[:200]}
    except Exception as e:
        return {"ok": False, "description": str(e)[:100]}


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
    if   6 <= saat < 12: return "sabah"
    elif 12 <= saat < 18: return "ogle"
    elif 18 <= saat < 22: return "aksam"
    else:                 return "gece"


def hafta_sonu_mu() -> bool:
    # UTC+3 günü
    gun = datetime.now(timezone.utc).weekday()  # 5=Cmt, 6=Paz
    return gun >= 5


# ════════════════════════════════════════════════════════════════════
# Caption Üretimi
# ════════════════════════════════════════════════════════════════════

def caption_uret(yildiz: int, idx: int = None, ozel: str = None) -> tuple[str, int]:
    """
    Caption üretir.
    Döndürür: (caption_metni, kullanilan_idx)
    """
    # Özel şablon isteniyorsa
    if ozel and ozel in OZEL_SABLONLAR:
        metin = OZEL_SABLONLAR.get(ozel, "")
        return metin, -1

    # Hafta sonu özel — artık normal havuzdan seçilir
    # (OZEL_SABLONLAR boş, VIP liŏi kaldırıldı)

    zaman    = gun_zamani()
    havuz    = CAPTION_HAVUZU[zaman]

    if idx is None:
        log = load_json(CAPTION_LOG_DOSYA, {})
        idx = log.get("caption_idx", 0)

    kullanilan = idx % len(havuz)
    metin      = havuz[kullanilan]
    return metin, kullanilan


def alternatif_caption(yildiz: int, mevcut_idx: int) -> tuple[str, int]:
    """Mevcut caption'dan farklı bir alternatif üretir."""
    zaman = gun_zamani()
    havuz = CAPTION_HAVUZU[zaman]
    yeni_idx = (mevcut_idx + 1) % len(havuz)
    metin = havuz[yeni_idx]
    return metin, yeni_idx


# ════════════════════════════════════════════════════════════════════
# Onay Akışı
# ════════════════════════════════════════════════════════════════════

def onay_iste(caption: str, caption_idx: int, meta: dict = None) -> bool:
    """
    Admin'e onay mesajı gönderir (inline butonlar).
    meta: {'file_id': ..., 'yildiz': ..., 'sure_sn': ...}
    Döndürür: True (mesaj gönderildi)
    """
    zaman = gun_zamani()
    ist_saat = (datetime.now(timezone.utc).hour + 3) % 24
    ist_dk   = datetime.now(timezone.utc).minute

    onay_metni = (
        f"📝 <b>Caption Onay Bekleniyor</b>\n"
        f"⏰ {ist_saat:02d}:{ist_dk:02d} · {zaman.capitalize()}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{caption}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Bu caption {len(KANALLAR)} kanala gönderilecek."
    )

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Gönder",      "callback_data": f"onay_gonder_{caption_idx}"},
            {"text": "✏️ Değiştir",   "callback_data": f"onay_degistir_{caption_idx}"},
            {"text": "❌ İptal",       "callback_data": "onay_iptal"},
        ]]
    }

    r = api("sendMessage", {
        "chat_id":      ADMIN_ID,
        "text":         onay_metni,
        "parse_mode":   "HTML",
        "reply_markup": keyboard,
    })

    if r.get("ok"):
        msg_id = r["result"]["message_id"]
        # Onay bekleyen kaydını oluştur
        bekleyen = load_json(ONAY_BEKLEYEN_DOSYA, {})
        bekleyen[str(msg_id)] = {
            "caption":     caption,
            "caption_idx": caption_idx,
            "zaman":       datetime.now(timezone.utc).isoformat(),
            "meta":        meta or {},
            "durum":       "bekliyor",
        }
        save_json(ONAY_BEKLEYEN_DOSYA, bekleyen)
        print(f"  ✅ Onay mesajı gönderildi (msg_id: {msg_id})")
        return True
    else:
        print(f"  ❌ Onay mesajı gönderilemedi: {r.get('description','?')[:80]}")
        return False


def onay_kontrol():
    """
    getUpdates ile callback_query'leri okur.
    Admin'in ✅/✏️/❌ butonuna bastığını tespit eder.
    """
    log = load_json(CAPTION_LOG_DOSYA, {})
    offset = log.get("callback_offset", 0)

    r = api("getUpdates", {
        "offset":          offset,
        "limit":           50,
        "timeout":         0,
        "allowed_updates": ["callback_query"],
    })

    if not r.get("ok"):
        print(f"⚠️ getUpdates hatası: {r.get('description','?')[:80]}")
        return

    updates  = r.get("result", [])
    yeni_off = offset

    for upd in updates:
        upd_id   = upd.get("update_id", 0)
        yeni_off = upd_id + 1

        cq = upd.get("callback_query")
        if not cq:
            continue

        # Sadece admin'den gelen callback'ler
        from_id = cq.get("from", {}).get("id")
        if from_id != ADMIN_ID:
            continue

        data    = cq.get("data", "")
        msg_id  = str(cq.get("message", {}).get("message_id", ""))
        cq_id   = cq.get("id")

        bekleyen = load_json(ONAY_BEKLEYEN_DOSYA, {})
        kayit    = bekleyen.get(msg_id, {})

        if not kayit or kayit.get("durum") != "bekliyor":
            api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Bu istek artık geçerli değil."})
            continue

        caption     = kayit.get("caption", "")
        caption_idx = kayit.get("caption_idx", 0)
        meta        = kayit.get("meta", {})

        # ── GÖNDER ──
        if data.startswith("onay_gonder_"):
            api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "✅ Gönderiliyor..."})
            _kanala_gonder(caption, meta)
            kayit["durum"] = "onaylandi"
            bekleyen[msg_id] = kayit
            save_json(ONAY_BEKLEYEN_DOSYA, bekleyen)

            # Mesajı güncelle
            api("editMessageText", {
                "chat_id":    ADMIN_ID,
                "message_id": int(msg_id),
                "text":       f"✅ <b>Gönderildi</b>\n\n{caption}",
                "parse_mode": "HTML",
            })

            # Caption idx güncelle
            log["caption_idx"] = caption_idx + 1
            save_json(CAPTION_LOG_DOSYA, log)
            print(f"  ✅ Onaylandı ve gönderildi (caption_idx={caption_idx})")

        # ── DEĞİŞTİR ──
        elif data.startswith("onay_degistir_"):
            yildiz = meta.get("yildiz", 350)
            alt_caption, alt_idx = alternatif_caption(yildiz, caption_idx)

            api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "✏️ Alternatif hazırlandı"})

            # Yeni caption'ı göster
            alt_metni = (
                f"✏️ <b>Alternatif Caption</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{alt_caption}\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            keyboard2 = {
                "inline_keyboard": [[
                    {"text": "✅ Bu'nu Gönder",  "callback_data": f"onay_gonder_{alt_idx}"},
                    {"text": "✏️ Bir Daha",      "callback_data": f"onay_degistir_{alt_idx}"},
                    {"text": "❌ İptal",          "callback_data": "onay_iptal"},
                ]]
            }

            # Mevcut kaydı güncelle
            kayit["caption"]     = alt_caption
            kayit["caption_idx"] = alt_idx
            bekleyen[msg_id]     = kayit
            save_json(ONAY_BEKLEYEN_DOSYA, bekleyen)

            api("editMessageText", {
                "chat_id":      ADMIN_ID,
                "message_id":   int(msg_id),
                "text":         alt_metni,
                "parse_mode":   "HTML",
                "reply_markup": keyboard2,
            })
            print(f"  ✏️ Alternatif caption sunuldu (idx={alt_idx})")

        # ── İPTAL ──
        elif data == "onay_iptal":
            api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "❌ İptal edildi"})
            kayit["durum"] = "iptal"
            bekleyen[msg_id] = kayit
            save_json(ONAY_BEKLEYEN_DOSYA, bekleyen)

            api("editMessageText", {
                "chat_id":    ADMIN_ID,
                "message_id": int(msg_id),
                "text":       "❌ <b>İptal edildi</b>",
                "parse_mode": "HTML",
            })
            print(f"  ❌ İptal edildi")

    # Offset güncelle
    log["callback_offset"] = yeni_off
    save_json(CAPTION_LOG_DOSYA, log)


def _kanala_gonder(caption: str, meta: dict):
    """Caption'ı kanallara gönderir."""
    file_id = meta.get("file_id")
    yildiz  = meta.get("yildiz", 350)

    if not file_id:
        # Sadece metin testi (file_id yoksa)
        for kanal_id in KANALLAR:
            api("sendMessage", {
                "chat_id":    kanal_id,
                "text":       caption,
                "parse_mode": "HTML",
            })
            time.sleep(1)
        return

    for kanal_id in KANALLAR:
        r = api("sendPaidMedia", {
            "chat_id":    kanal_id,
            "star_count": yildiz,
            "media":      [{"type": "video", "media": file_id, "supports_streaming": True}],
            "caption":    caption,
            "parse_mode": "HTML",
        })
        if not r.get("ok"):
            r = api("sendVideo", {
                "chat_id":           kanal_id,
                "video":             file_id,
                "caption":           caption,
                "parse_mode":        "HTML",
                "supports_streaming": True,
            })
        status = "✅" if r.get("ok") else f"❌ {r.get('description','?')[:40]}"
        print(f"  {status} → Kanal {kanal_id}")
        time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# Ana işlemler
# ════════════════════════════════════════════════════════════════════

def onay_ile_calistir(file_id: str = None, yildiz: int = 350, sure_sn: int = 120):
    """
    Caption üret → onay iste.
    arsiv_paylasim_cron.py tarafından çağrılır.
    """
    caption, idx = caption_uret(yildiz)
    print(f"\n📝 Caption üretildi (idx={idx}, zaman={gun_zamani()}):")
    print(f"{'─'*40}")
    print(caption)
    print(f"{'─'*40}\n")

    meta = {
        "file_id":  file_id,
        "yildiz":   yildiz,
        "sure_sn":  sure_sn,
    }
    onay_iste(caption, idx, meta)


def test_goster(taslak: str = None):
    """Test modu — caption üretip ekrana yaz, gönderme."""
    print(f"\n🧪 Test Modu — {gun_zamani().upper()}")
    print(f"Hafta sonu: {hafta_sonu_mu()}\n")

    for yildiz in [350, 600, 999]:
        caption, idx = caption_uret(yildiz, idx=0)
        print(f"[{yildiz}⭐ · idx=0]")
        print(caption)
        print()

    print("─ Alternatifler ─")
    caption, idx = caption_uret(350, idx=0)
    alt, alt_idx = alternatif_caption(350, 0)
    print(f"Alternatif (idx={alt_idx}):")
    print(alt)


# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--test" in sys.argv:
        taslak = sys.argv[2] if len(sys.argv) > 2 else None
        test_goster(taslak)
    elif "--onay-kontrol" in sys.argv:
        print("🔍 Onay callback'leri kontrol ediliyor...")
        onay_kontrol()
    else:
        # Standalone çalıştırma — onay iste (file_id olmadan)
        onay_ile_calistir()
