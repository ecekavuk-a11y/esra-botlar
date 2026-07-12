#!/usr/bin/env python3
"""
VIP Erişim Yöneticisi
─────────────────────
Supabase'deki members tablosunu tarar:
  - Süresi dolan üyeler → banChatMember (kick) → status = 'expired'
  - 3 gün kalan üyeler → hatırlatma DM
  - 1 gün kalan üyeler → son uyarı DM
  - Her çalışmada özet raporu admin'e Telegram DM

Her gün 09:00 İstanbul (06:00 UTC) cron olarak çalışır.
Ayrıca /kontrol komutuyla manuel tetiklenebilir (VIP_BOT_TOKEN botu üzerinden).

Gereksinimler:
  SUPABASE_URL, SUPABASE_KEY env değişkenleri
  VIP_CHANNEL_ID   = -1003947278046
  BOT_TOKEN        = malatyaesra_odeme_bot tokenı (8907710571:...)
  ADMIN_ID         = 5019918710
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
import logging

# ─── YAPILANDIRMA ─────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://srxqnfmegrysnjktxdra.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_secret_hueL3v1m7OrDXgeXlGROfw_HyIPIrlq")
BOT_TOKEN    = os.environ.get("VIP_BOT_TOKEN", "8907710571:AAHXQy5ABXgqe8CxHweK90v6WhlBYj2EbCA")
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "5019918710"))
VIP_CHANNEL_ID = int(os.environ.get("VIP_CHANNEL_ID", "-1003947278046"))

TZ_ISTANBUL = timezone(timedelta(hours=3))
LOG_DIR     = "/home/user/workspace/cron_tracking/vip_yonetici"
LOG_FILE    = f"{LOG_DIR}/run_{datetime.now(TZ_ISTANBUL).strftime('%Y-%m-%d')}.log"

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("vip_yonetici")

# ─── YARDIMCI FONKSİYONLAR ────────────────────────────────────────────────────

def tg_api(method: str, payload: dict) -> dict:
    """Telegram Bot API çağrısı (urllib, proxy-safe)."""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        log.error(f"TG API {method} HTTP {e.code}: {body}")
        return {"ok": False, "error": body}
    except Exception as e:
        log.error(f"TG API {method} exception: {e}")
        return {"ok": False, "error": str(e)}


def sb_request(method: str, path: str, body: dict | None = None) -> dict | list | None:
    """Supabase REST API isteği."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("SUPABASE_URL veya SUPABASE_KEY eksik!")
        return None

    url     = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")
        log.error(f"Supabase {method} {path} HTTP {e.code}: {body_txt}")
        return None
    except Exception as e:
        log.error(f"Supabase {method} {path} exception: {e}")
        return None


def sb_get(path: str) -> list | None:
    return sb_request("GET", path)


def sb_patch(path: str, body: dict) -> dict | None:
    return sb_request("PATCH", path, body)


def sb_post(path: str, body: dict) -> dict | None:
    return sb_request("POST", path, body)


def send_dm(user_id: int, text: str) -> bool:
    """Kullanıcıya Telegram DM gönder."""
    r = tg_api("sendMessage", {
        "chat_id":    user_id,
        "text":       text,
        "parse_mode": "HTML",
    })
    return r.get("ok", False)


def kick_member(user_id: int) -> bool:
    """VIP kanalından üyeyi uzaklaştır."""
    # banChatMember ile banla, hemen unbanla → kick efekti
    r = tg_api("banChatMember", {
        "chat_id": VIP_CHANNEL_ID,
        "user_id": user_id,
        "revoke_messages": False,
    })
    if r.get("ok"):
        # Hemen unban — tekrar katılabilsin (ödeme yaparsa)
        tg_api("unbanChatMember", {
            "chat_id":        VIP_CHANNEL_ID,
            "user_id":        user_id,
            "only_if_banned": True,
        })
        return True
    log.warning(f"Kick başarısız uid={user_id}: {r}")
    return False


def paket_adi(paket: str) -> str:
    return {
        "aylik":     "1 Aylık VIP",
        "uc_aylik":  "3 Aylık VIP",
        "omur":      "Ömür Boyu VIP",
        "show_5":    "5dk Sanal Şov",
        "show_15":   "15dk Sanal Şov",
        "show_30":   "30dk Sanal Şov",
    }.get(paket, paket)


# ─── ANA KONTROL MANTIĞI ──────────────────────────────────────────────────────

def kontrol_et() -> dict:
    """
    Tüm aktif üyeleri tara.
    Döndürür: {expired, warned_3d, warned_1d, errors}
    """
    now = datetime.now(TZ_ISTANBUL)
    stats = {
        "expired":   [],   # kick edilenler
        "warned_3d": [],   # 3 gün uyarısı
        "warned_1d": [],   # 1 gün son uyarı
        "errors":    [],   # hatalı işlemler
    }

    # Supabase'den aktif üyeleri çek
    # status IN ('active','warned_3d','warned_1d')
    members = sb_get("members?member_status=in.(active,warned_3d,warned_1d)&select=*")
    if members is None:
        log.error("Supabase'den üye listesi alınamadı.")
        return stats

    log.info(f"Toplam kontrol edilecek üye: {len(members)}")

    for m in members:
        uid        = m.get("telegram_id")
        expire_str = m.get("expires_at")
        paket      = m.get("paket", "aylik")
        ad         = m.get("isim", "")
        member_id  = m.get("id")

        if not uid or not expire_str:
            continue

        try:
            # ISO 8601 parse
            expire_dt = datetime.fromisoformat(expire_str.replace("Z", "+00:00"))
            expire_istanbul = expire_dt.astimezone(TZ_ISTANBUL)
        except Exception as e:
            log.warning(f"Tarih parse hatası uid={uid}: {e}")
            stats["errors"].append(uid)
            continue

        kalan = expire_istanbul - now

        # ── SÜRE DOLDU ──────────────────────────────────────────
        if kalan.total_seconds() <= 0:
            log.info(f"Süre doldu → kick uid={uid} ({ad})")
            kick_ok = kick_member(uid)

            # Supabase güncelle
            sb_patch(f"members?id=eq.{member_id}", {
                "member_status":    "expired",
                "kicked_at": now.isoformat(),
            })

            # Üyeye DM
            send_dm(uid,
                f"⚠️ Merhaba {ad},\n\n"
                f"<b>{paket_adi(paket)}</b> üyeliğin sona erdi. "
                f"VIP kanalına erişimin kapatıldı.\n\n"
                f"Yeniden katılmak için ödeme yapabilirsin:\n"
                f"📲 t.me/malatyaesra_odeme_bot\n\n"
                f"Görüşürüz 🌹"
            )

            stats["expired"].append({
                "uid": uid, "ad": ad, "paket": paket,
                "kicked": kick_ok
            })

        # ── 1 GÜN KALDI ─────────────────────────────────────────
        elif kalan.total_seconds() <= 86400 and m.get("member_status") != "warned_1d":
            log.info(f"1 gün uyarısı uid={uid} ({ad})")
            sb_patch(f"members?id=eq.{member_id}", {"member_status": "warned_1d"})

            expire_fmt = expire_istanbul.strftime("%d.%m.%Y %H:%M")
            send_dm(uid,
                f"⏰ <b>{ad}</b>, üyeliğin yarın sona eriyor!\n\n"
                f"Bitiş: {expire_fmt}\n"
                f"Paket: {paket_adi(paket)}\n\n"
                f"Devam etmek istersen hemen yenile:\n"
                f"📲 t.me/malatyaesra_odeme_bot\n\n"
                f"Son gün fırsatını kaçırma 🔥"
            )

            stats["warned_1d"].append({"uid": uid, "ad": ad, "paket": paket})

        # ── 3 GÜN KALDI ─────────────────────────────────────────
        elif kalan.total_seconds() <= 259200 and m.get("member_status") == "active":
            log.info(f"3 gün uyarısı uid={uid} ({ad})")
            sb_patch(f"members?id=eq.{member_id}", {"member_status": "warned_3d"})

            expire_fmt = expire_istanbul.strftime("%d.%m.%Y")
            send_dm(uid,
                f"🔔 <b>{ad}</b>, üyeliğin 3 gün sonra bitiyor.\n\n"
                f"Son tarih: {expire_fmt}\n"
                f"Paket: {paket_adi(paket)}\n\n"
                f"Kaçırmadan yenile:\n"
                f"📲 t.me/malatyaesra_odeme_bot"
            )

            stats["warned_3d"].append({"uid": uid, "ad": ad, "paket": paket})

    return stats


def admin_raporu(stats: dict) -> None:
    """Özet raporu admin'e DM gönder."""
    now = datetime.now(TZ_ISTANBUL)
    tarih = now.strftime("%d.%m.%Y %H:%M")

    satir = [f"📋 <b>VIP Üye Raporu</b> — {tarih}\n"]

    if stats["expired"]:
        satir.append(f"🚫 <b>Süresi Dolanlar ({len(stats['expired'])} üye):</b>")
        for u in stats["expired"]:
            kick_txt = "✅ kick" if u.get("kicked") else "⚠️ kick başarısız"
            satir.append(f"  • {u['ad']} (ID: {u['uid']}) — {paket_adi(u['paket'])} — {kick_txt}")
    else:
        satir.append("✅ Süresi dolan üye yok")

    if stats["warned_1d"]:
        satir.append(f"\n⏰ <b>Yarın Bitenler ({len(stats['warned_1d'])} üye):</b>")
        for u in stats["warned_1d"]:
            satir.append(f"  • {u['ad']} (ID: {u['uid']})")

    if stats["warned_3d"]:
        satir.append(f"\n🔔 <b>3 Gün Kalanlar ({len(stats['warned_3d'])} üye):</b>")
        for u in stats["warned_3d"]:
            satir.append(f"  • {u['ad']} (ID: {u['uid']})")

    if stats["errors"]:
        satir.append(f"\n⚠️ <b>Hatalı İşlemler:</b> {len(stats['errors'])} üye atlandı")

    toplam = len(stats["expired"]) + len(stats["warned_1d"]) + len(stats["warned_3d"])
    satir.append(f"\n📊 Toplam işlem: {toplam}")

    mesaj = "\n".join(satir)
    r = tg_api("sendMessage", {
        "chat_id":    ADMIN_ID,
        "text":       mesaj,
        "parse_mode": "HTML",
    })
    if not r.get("ok"):
        log.error(f"Admin raporu gönderilemedi: {r}")


# ─── POLLING MODU (opsiyonel: /kontrol komutu) ────────────────────────────────

def polling_modu():
    """
    Basit long-polling — admin /kontrol yazarsa manuel kontrol başlatır.
    Cron modunda bu fonksiyon kullanılmaz.
    """
    log.info("Polling modu başladı — /kontrol bekleniyor...")
    offset = 0
    while True:
        try:
            r = tg_api("getUpdates", {"offset": offset, "timeout": 30})
            if not r.get("ok"):
                import time; time.sleep(5); continue

            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("channel_post")
                if not msg:
                    continue
                from_id = (msg.get("from") or {}).get("id")
                text    = (msg.get("text") or "").strip()

                if from_id == ADMIN_ID and text == "/kontrol":
                    tg_api("sendMessage", {
                        "chat_id": ADMIN_ID,
                        "text":    "🔄 VIP üye kontrolü başlatılıyor...",
                    })
                    stats = kontrol_et()
                    admin_raporu(stats)

        except KeyboardInterrupt:
            log.info("Polling durduruldu.")
            break
        except Exception as e:
            log.error(f"Polling hatası: {e}")
            import time; time.sleep(10)


# ─── GİRİŞ NOKTASI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cron"

    if mode == "polling":
        polling_modu()
    else:
        # CRON MODU — çalış, raporla, çık
        log.info("=== VIP Erişim Yöneticisi başladı (cron modu) ===")

        if not SUPABASE_URL or not SUPABASE_KEY:
            log.error("SUPABASE_URL / SUPABASE_KEY env değişkenleri eksik!")
            # Admin'e bildir
            tg_api("sendMessage", {
                "chat_id":    ADMIN_ID,
                "text":       "❌ VIP Yönetici: SUPABASE_URL veya SUPABASE_KEY eksik! Cron çalışamadı.",
                "parse_mode": "HTML",
            })
            sys.exit(1)

        stats = kontrol_et()
        admin_raporu(stats)

        toplam = len(stats["expired"]) + len(stats["warned_1d"]) + len(stats["warned_3d"])
        log.info(f"=== Tamamlandı. Toplam işlem: {toplam} ===")

        if stats["errors"]:
            sys.exit(1)
        sys.exit(0)
