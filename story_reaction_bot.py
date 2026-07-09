#!/usr/bin/env python3
"""
Reaction Bot v7 — 28 Bot, Kademeli Emoji Gönderimi
Her bot 10-12 dakika arayla atar → reaksiyonlar doğal birikir
"""

import json, os, random, time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

ALL_BOTS = [
    ("8423804850:AAEsIBrxOPOZ8cuICwLamcBTSjllvUeZlgE", "Zelisahin_bot"),
    ("8649828266:AAGiN_K6nDiIBMzHmrCk-CYzBVNbK_QULwM", "Zelusumun_bot"),
    ("8426078736:AAFQZuHYp8zHmsPN-XjBrvZj7Ww_dKzFMU0", "Zebitak_bot"),
    ("8645202362:AAHlQ3l29IDAT0EP42iEiAS2NxiOm8xkP8k", "Qubeaninin_bot"),
    ("8643185035:AAG_RnellfzlBog7Lm7GGCiiGz0egXRfE54", "esra_bal_kuzusu_bot"),
    ("8273394683:AAH0kAHnbb176SRgwtBcIqzF-x10peKooIw", "Zebillah_bot"),
    ("8622461024:AAFsavH-mhxywt0f9qFc_og8YKQox1F7pvg", "Zeriku_bot"),
    ("8934662828:AAHpk-0SVDUzPzhgEtbczkmubY8qlwvldlE", "Vip_iesrabot"),
    ("8280594775:AAFqtBrUOms9cHenhUz-tuSFqrMtVH1aZL8", "ie_srabot"),
    ("8888317050:AAFbwP3FKE7TOAaF42IrOOMBHlDETjPP0fU", "esra_arsiv_bot"),
    ("8647604906:AAH6xRJS18Sw18ak8q11mxScOVzyDdC9yHg", "esrabal_paylasim_bot"),
    ("8907710571:AAHXQy5ABXgqe8CxHweK90v6WhlBYj2EbCA", "malatyaesra_odeme_bot"),
    ("8906805286:AAEPOSYRaKbl330XxtDTGVtyyZPaHnoPKvw", "iesra_bal_bot"),
    ("8428831978:AAGodHm5uR_1b-XTUMSTPsMWPpfaKAFpW6I", "Klanerbotbot"),
    ("8661747708:AAEjR06nhW42zIyYyoqaTgmPW_IqAjwRgvs", "reaksiyoninsbot"),
    ("8732639288:AAHhes_DadTUfdqyBAk9hvMSG3WVXHdPDts", "emlyizbot"),
    ("8721708737:AAG4ANDrcTLkqbpkkhSFJxi4m0WD7DTlOpw", "Cicisinibot"),
    ("8888212362:AAGBFprAen27ikfeVQ_9eEttFqq2d0eSw44", "Esrakiymetlibot"),
    # Yeni 10 bot
    ("8653480058:AAElljxJqN7vLpqkC_8HdGdJCq5XoZD5dX4", "Dudiki_bot"),
    ("8577062775:AAH6-g34D5R6CKv8XB8zMBLvgrxfxMriJMI", "Rurukikiki_bot"),
    ("8401452057:AAGvGvB5fB9OkgML6Xnecc2PnpWsV-Q2hds", "Esrarm_bot"),
    ("8839334724:AAG_lDAJ_tBpKS1JhxfC1L_ybKIwGUuaSJc", "Zelahigs_bot"),
    ("8605154144:AAG_hlveLQhwaVu3S7Of6-I8KMfCdGjmwnI", "Seyyarimsi_bot"),
    ("8868716356:AAFfIVpnGKnd-rxhh_6ctWWsby1oauYcjcw", "Seyyarimiki_bot"),
    ("8864931173:AAHiVAps6A5Tahpqzdz7zcUUk9sxPJdoQbQ", "Zazinh_bot"),
    ("8825937377:AAEJYE3DyI9tFWg_4nprqSsFTnzqrJw5gjA", "Camicisi_bot"),
    ("8658388469:AAGPyDmkkMPbERmUlA-mcsZbcxDjZMzrb2c", "Dodddi_bot"),
    ("8615927973:AAHsIlxT0pLtIsTNpesItLD3oBHtsXcJGOU", "Kurmazlik_bot"),
]

ALL_CHATS = [
    -1003494573579,  # Ücretsiz 1
    -1002956424495,  # Ücretsiz 2
    -1003959424039,  # Arşiv
    -1003524644687,  # OnlineIsra
]

# Her kanal max 11 bot — REACTIONS_TOO_MANY = 0
CHANNEL_BOT_MAP = {
    -1003494573579: list(range(0, 11)),    # bot 0-10
    -1002956424495: list(range(7, 18)),    # bot 7-17
    -1003959424039: list(range(14, 25)),   # bot 14-24
    -1003524644687: list(range(17, 28)),   # bot 17-27
}

CHANNEL_EMOJI_MAP = {
    -1003494573579: ["🔥","❤","😍","💯","🥰","👏","🏆","😘","🥵","💋","😈"],
    -1002956424495: ["😱","🤗","👍","🫡","🥳","😋","👅","🥰","❤","🔥","💯"],
    -1003959424039: ["💋","😈","🥵","😍","😘","🏆","👏","😋","🫡","🥳","😱"],
    -1003524644687: ["🤗","👍","❤","🔥","🥰","💯","😍","😱","🏆","😘","👏"],
}

# Kademeli gönderim: botlar 3'er 3'er gruplar halinde, aralarında bekleme
# 11 bot → 4 grup → ~10-12 dk arayla → 1 saat içinde tümü tamamlanır
BATCH_SIZE  = 3    # aynı anda kaç bot atsın
BATCH_DELAY = 35   # saniye — gruplar arası bekleme (3 grup × 35sn = 105sn toplam)

PROBE_TOKEN = "8934662828:AAHpk-0SVDUzPzhgEtbczkmubY8qlwvldlE"
BASE_DIR    = "/home/user/workspace/cron_tracking/story_reactions"
STATE_FILE  = f"{BASE_DIR}/chat_state.json"
REACTED_FILE= f"{BASE_DIR}/reacted.json"
LOG_FILE    = f"{BASE_DIR}/last_run.json"

INITIAL_LAST = {
    -1003494573579: 314,
    -1002956424495: 530,
    -1003959424039: 87,
    -1003524644687: 435,
}

def api_call(token, method, data):
    import urllib.request
    url = f"https://api.telegram.org/bot{token}/{method}"
    payload = json.dumps(data).encode()
    try:
        req = urllib.request.Request(url, payload, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        try: return json.loads(e.read())
        except: return {"ok": False, "description": str(e)}

def scan_channel(chat_id, last_id):
    """Mesaj varl\u0131\u011f\u0131n\u0131 setMessageReaction ile test eder (okuma+yazma birle\u015ftirme).
    forwardMessage KULLANILMAZ. getMessageReactionCount bu kanallarda \u00e7al\u0131\u015fm\u0131yor.
    Strateji: probe botu ile emoji at — ok ise mesaj var, MESSAGE_ID_INVALID/not found ise yok.
    """
    found, new_last = [], last_id
    # Probe botu: Cicisinibot (kanal \u00fcyesi ve reaction yetkili)
    SCAN_TOKEN = "8721708737:AAG4ANDrcTLkqbpkkhSFJxi4m0WD7DTlOpw"
    emoji_pool = CHANNEL_EMOJI_MAP.get(chat_id, ["\ud83d\udc4d"])
    for mid in range(last_id + 1, last_id + 20):
        emoji = emoji_pool[mid % len(emoji_pool)]
        r = api_call(SCAN_TOKEN, "setMessageReaction", {
            "chat_id": chat_id, "message_id": mid,
            "reaction": [{"type": "emoji", "emoji": emoji}],
            "is_big": False,
        })
        if r.get("ok"):
            found.append(mid)
            new_last = mid
        else:
            desc = r.get("description", "").lower()
            # Ger\u00e7ekten yok
            if ("message_id_invalid" in desc or "message to react not found" in desc
                    or "not found" in desc):
                pass
            elif "reactions_too_many" in desc:
                # Mesaj var, sadece bu bot zaten reaksiyon atm\u0131\u015f
                found.append(mid)
                new_last = mid
            elif "not enough rights" in desc or "forbidden" in desc:
                # Yetki yok ama mesaj var olabilir — dene
                found.append(mid)
                new_last = mid
    return found, new_last

def send_one(token, username, chat_id, msg_id, emoji, reacted):
    key = f"{chat_id}:{msg_id}:{username}"
    if key in reacted:
        return ("skip",)
    r = api_call(token, "setMessageReaction", {
        "chat_id": chat_id, "message_id": msg_id,
        "reaction": [{"type": "emoji", "emoji": emoji}],
        "is_big": False,
    })
    if r.get("ok"):
        return ("ok", key, emoji)
    desc = r.get("description", "")
    if ("TOO_MANY" in desc or "not found" in desc.lower()
            or "REACTION_INVALID" in desc or "MESSAGE_ID_INVALID" in desc
            or "message_id_invalid" in desc.lower()):
        return ("ignore",)
    # Hata detayını döndür: ("fail", bot_adi, kanal_id, mesaj_id, hata_aciklamasi)
    return ("fail", username, chat_id, msg_id, desc)

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def main():
    t0 = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Reaction Bot v7 — {len(ALL_BOTS)} bot × {len(ALL_CHATS)} kanal")

    state   = load_json(STATE_FILE, {})
    reacted = load_json(REACTED_FILE, {})

    for cid, lid in INITIAL_LAST.items():
        if str(cid) not in state:
            state[str(cid)] = {"last_id": lid}

    # Kanalları tara
    channel_msgs = {}
    for chat_id in ALL_CHATS:
        last = state.get(str(chat_id), {}).get("last_id", 20)
        msgs, new_last = scan_channel(chat_id, last)
        channel_msgs[chat_id] = msgs
        state[str(chat_id)] = {"last_id": new_last}
        if msgs:
            print(f"  {chat_id}: {len(msgs)} yeni → {msgs}")

    save_json(STATE_FILE, state)

    # Görev listesi — kanal × mesaj × bot
    all_tasks = []
    for chat_id in ALL_CHATS:
        msgs = channel_msgs.get(chat_id, [])
        if not msgs: continue
        bot_indices  = CHANNEL_BOT_MAP[chat_id]
        channel_bots = [ALL_BOTS[i] for i in bot_indices if i < len(ALL_BOTS)]
        emoji_pool   = CHANNEL_EMOJI_MAP[chat_id]
        for msg_id in msgs:
            bots_copy = channel_bots.copy()
            random.shuffle(bots_copy)
            for idx, (token, username) in enumerate(bots_copy):
                emoji = emoji_pool[idx % len(emoji_pool)]
                all_tasks.append((token, username, chat_id, msg_id, emoji))

    total_msgs = sum(len(v) for v in channel_msgs.values())
    print(f"  Toplam görev: {len(all_tasks)} ({total_msgs} mesaj)")

    if not all_tasks:
        ce = state.get("consecutive_empty", 0) + 1
        state["consecutive_empty"] = ce
        save_json(STATE_FILE, state)
        elapsed = time.time() - t0
        save_json(LOG_FILE, {"last_run": _utcnow().isoformat(),
            "ok": 0, "skipped": 0, "failed": 0, "elapsed_sec": round(elapsed, 2),
            "bots": len(ALL_BOTS), "channels": len(ALL_CHATS), "consecutive_empty": ce})
        print(f"✓ 0 reaction | {elapsed:.1f}s")
        return

    state["consecutive_empty"] = 0

    # Kademeli gönderim — BATCH_SIZE botluk gruplar
    ok = skip = fail = 0
    fail_log = []  # hata detayı listesi
    batches = [all_tasks[i:i+BATCH_SIZE] for i in range(0, len(all_tasks), BATCH_SIZE)]

    for b_idx, batch in enumerate(batches):
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as ex:
            futures = [ex.submit(send_one, t[0], t[1], t[2], t[3], t[4], reacted)
                       for t in batch]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    if res[0] == "ok":
                        ok += 1
                        reacted[res[1]] = {"e": res[2], "t": int(time.time())}
                    elif res[0] in ("skip", "ignore"):
                        skip += 1
                    else:
                        fail += 1
                        # res = ("fail", username, chat_id, msg_id, desc)
                        if len(res) >= 5:
                            fail_log.append({
                                "bot":     res[1],
                                "channel": res[2],
                                "msg_id":  res[3],
                                "error":   res[4],
                                "time":    _utcnow().isoformat(),
                            })
                except Exception as e:
                    fail += 1
                    fail_log.append({"bot": "?", "channel": "?", "msg_id": "?",
                                     "error": str(e)[:120], "time": _utcnow().isoformat()})
        # Gruplar arası bekleme (son grup sonrası bekleme yok)
        if b_idx < len(batches) - 1:
            time.sleep(BATCH_DELAY)

    if len(reacted) > 5000:
        items = sorted(reacted.items(), key=lambda x: x[1].get("t", 0))
        reacted = dict(items[-3000:])
    save_json(REACTED_FILE, reacted)

    elapsed = time.time() - t0
    save_json(LOG_FILE, {"last_run": _utcnow().isoformat(),
        "ok": ok, "skipped": skip, "failed": fail,
        "elapsed_sec": round(elapsed, 2), "bots": len(ALL_BOTS),
        "channels": len(ALL_CHATS), "consecutive_empty": 0,
        "fail_log": fail_log[-20:]})

    # Kalıcı hata geçmişi (son 200 giriş)
    ERR_HISTORY = f"{BASE_DIR}/error_history.json"
    history = load_json(ERR_HISTORY, [])
    if not isinstance(history, list): history = []
    history.extend(fail_log)
    history = history[-200:]
    save_json(ERR_HISTORY, history)

    # ── SAATLİK LOG KAYDI ──────────────────────────────────────────
    # bot_admin_panel.py bu logu okuyarak saatlik analiz üretir
    hourly_log_path = f"{BASE_DIR}/hourly_log.json"
    hourly_entries  = load_json(hourly_log_path, [])
    if not isinstance(hourly_entries, list):
        hourly_entries = []

    # Kanal bazlı ok/fail hesapla
    channel_ok   = {}
    channel_fail = {}
    for task in all_tasks:
        cid = task[2]
        channel_ok[cid]   = channel_ok.get(cid, 0)
        channel_fail[cid] = channel_fail.get(cid, 0)

    # Tüm görevler için kanal dağılımı — basit tahmin
    # (task bazlı ok/fail ayrımı yapılmadığından toplam kullanılır)
    for chat_id in ALL_CHATS:
        ch_tasks = [t for t in all_tasks if t[2] == chat_id]
        if not ch_tasks:
            continue
        # Orantılı dağılım: ch_tasks/total * ok|fail
        ratio = len(ch_tasks) / len(all_tasks) if all_tasks else 0
        ch_ok   = round(ok   * ratio)
        ch_fail = round(fail * ratio)
        ch_msgs = list({t[3] for t in ch_tasks})  # benzersiz msg_id'ler
        ch_name = {
            -1003494573579: "Ücretsiz 1",
            -1002956424495: "Ücretsiz 2",
            -1003959424039: "Arşiv",
            -1003524644687: "OnlineIsra",
        }.get(chat_id, str(chat_id))
        entry = {
            "timestamp":    _utcnow().isoformat(),
            "hour":         _utcnow().hour,
            "channel":      chat_id,
            "channel_name": ch_name,
            "ok":           ch_ok,
            "fail":         ch_fail,
            "msg_id":       ch_msgs[0] if ch_msgs else None,
            "errors":       [],
        }
        hourly_entries.append(entry)

    # Son 7 günü tut (7×24×4 kanal = ~672 giriş maksimum)
    cutoff = _utcnow() - timedelta(days=7)
    hourly_entries = [
        e for e in hourly_entries
        if datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]
    save_json(hourly_log_path, hourly_entries)
    # ──────────────────────────────────────────────────────────────

    if ok == 0 and len(all_tasks) > 0:
        api_call(PROBE_TOKEN, "sendMessage",
                 {"chat_id": 5019918710, "text": f"⚠️ Reaction Bot: 0 reaction ({len(all_tasks)} görevden)"})
        status = "🚨"
    else:
        status = "✅"
    print(f"{status} {ok} reaction | {skip} atlandı | {fail} hata | {elapsed:.1f}s")

if __name__ == "__main__":
    main()
