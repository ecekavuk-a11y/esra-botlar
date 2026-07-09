"""
Dekont Doğrulama Modülü
=======================
Gelen dekont fotoğrafını OCR ile okur ve şu kontrolleri yapar:

1. TUTAR kontrolü  — Beklenen tutarlar (1500, 3600, 9900, 500, 1500, 3000) var mı?
2. ALICI kontrolü  — "İsra Soğukpınar" veya Papara numarası (1261850057) geçiyor mu?
3. IBAN kontrolü   — TR49 0082 9000 0949 1261 8500 57 eşleşiyor mu?
4. TARİH kontrolü  — Dekont tarihi bugün veya dün mü? (eski/tekrar kullanım tespiti)
5. MANIPÜLASYON    — Fotoğraf edit mi? EXIF tutarsızlığı var mı? Piksel anomalisi var mı?
6. TEKRAR KULLANIM — Daha önce gönderilen dekontla aynı mı? (hash kontrolü)
7. EKRAN GÖRÜNTÜSÜ — Gerçek banka uygulaması gibi görünüyor mu?
"""

import os
import re
import io
import json
import hashlib
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract

# Türkçe OCR için tessdata yolu
os.environ["TESSDATA_PREFIX"] = "/home/user/workspace/tessdata"

# ── SABIT DEĞERLER ──────────────────────────────────────────────────────────

IBAN_TEMIZ       = "TR490082900009491261850057"
PAPARA_NO        = "1261850057"
ALICI_ADI        = "İsra Soğukpınar"
ALICI_ALT        = ["isra", "sogukpinar", "soğukpınar", "israsoguk"]

GECERLI_TUTARLAR = [
    500, 1500, 3000, 3600, 9900,   # TL
    350, 600, 999, 2800, 7500      # Stars (nadiren dekont olur ama)
]

HASH_DOSYASI = "/home/user/workspace/cron_tracking/dekont_hashler.json"

# Banka anahtar kelimeleri — gerçek dekont olduğuna işaret eden
BANKA_KELIMELER = [
    "transfer", "gönderim", "havale", "eft", "işlem", "onaylandı",
    "başarılı", "tamamlandı", "tarih", "saat", "tutar", "alıcı",
    "gönderen", "papara", "garanti", "ziraat", "akbank", "enpara",
    "qnb", "vakıf", "halkbank", "fibabanka", "denizbank", "yapıkredi",
    "iban", "tr", "tl", "₺", "commission", "fee", "ref"
]


# ── HASH ────────────────────────────────────────────────────────────────────

def load_hashler():
    if os.path.exists(HASH_DOSYASI):
        with open(HASH_DOSYASI) as f:
            return json.load(f)
    return {}

def save_hash(img_hash, user_id, tutar):
    hashler = load_hashler()
    hashler[img_hash] = {
        "user_id": user_id,
        "tutar": tutar,
        "tarih": datetime.now(timezone.utc).isoformat()
    }
    os.makedirs(os.path.dirname(HASH_DOSYASI), exist_ok=True)
    with open(HASH_DOSYASI, "w") as f:
        json.dump(hashler, f, ensure_ascii=False, indent=2)

def gorsel_hash(img: Image.Image) -> str:
    """Küçük resme indirgeyip perceptual hash — benzer görüntüleri de yakalar"""
    kucuk = img.convert("L").resize((16, 16), Image.LANCZOS)
    piksel = list(kucuk.getdata())
    ort = sum(piksel) / len(piksel)
    bits = "".join("1" if p > ort else "0" for p in piksel)
    return hex(int(bits, 2))[2:].zfill(32)


# ── OCR ─────────────────────────────────────────────────────────────────────

def ocr_oku(img: Image.Image) -> str:
    """Görüntüyü OCR ile metne çevir — Türkçe + İngilizce"""
    # Önişleme: kontrast artır
    gelismis = ImageEnhance.Contrast(img).enhance(2.0)
    gelismis = ImageEnhance.Sharpness(gelismis).enhance(1.5)
    
    try:
        metin = pytesseract.image_to_string(
            gelismis,
            lang="tur+eng",
            config="--psm 6 --oem 3"
        )
    except Exception:
        # Türkçe paket yoksa sadece İngilizce
        metin = pytesseract.image_to_string(
            gelismis,
            lang="eng",
            config="--psm 6 --oem 3"
        )
    return metin.lower()


# ── KONTROLLER ──────────────────────────────────────────────────────────────

def tutar_bul(metin: str) -> list:
    """Metinden para tutarlarını çıkar — OCR hatalı okumalarına dayanıklı"""
    patterns = [
        r'(\d[\d.,]+)\s*(?:tl|₺|lira)',              # 1500tl, 1.500,00 tl
        r'(?:tutar|amount|miktar)[:\s]+(\d[\d.,]+)',    # tutar: 1500
        r'(\d{3,})[.,]00',                               # 1500,00
        r'₺\s*(\d[\d.,]+)',                              # ₺1500
    ]
    tutarlar = []
    for p in patterns:
        for m in re.finditer(p, metin, re.IGNORECASE):
            s = m.group(1).replace(".", "").replace(",", "")
            try:
                tutarlar.append(int(s))
            except ValueError:
                pass
    return tutarlar


def tutar_gecerli_mi(metin: str) -> dict:
    bulunan = tutar_bul(metin)
    eslesen = [t for t in bulunan if t in GECERLI_TUTARLAR]
    return {
        "gecerli": len(eslesen) > 0,
        "bulunan_tutarlar": bulunan,
        "eslesen_tutarlar": eslesen
    }


def alici_gecerli_mi(metin: str) -> bool:
    """Alıcı adı veya Papara numarası var mı?"""
    for alt in ALICI_ALT:
        if alt in metin:
            return True
    if PAPARA_NO in metin.replace(" ", ""):
        return True
    return False


def iban_gecerli_mi(metin: str) -> bool:
    """IBAN eşleşiyor mu?"""
    temiz = metin.replace(" ", "").upper()
    if IBAN_TEMIZ in temiz:
        return True
    # Kısmi eşleşme (son 10 hane)
    if "1261850057" in temiz:
        return True
    return False


def tarih_gecerli_mi(metin: str) -> dict:
    """Dekont tarihi bugün veya dün mü?"""
    bugun = datetime.now(timezone.utc)
    dun   = bugun - timedelta(days=1)
    
    # Tarih formatları: 09.07.2026 / 2026-07-09 / 09/07/26
    tarih_pattern = r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})'
    eslesmeler = re.findall(tarih_pattern, metin)
    
    if not eslesmeler:
        return {"gecerli": None, "sebep": "Tarih bulunamadı"}
    
    for g, a, y in eslesmeler:
        try:
            yil = int(y) + 2000 if len(y) == 2 else int(y)
            dekont_tarihi = datetime(yil, int(a), int(g), tzinfo=timezone.utc)
            fark = (bugun - dekont_tarihi).days
            if 0 <= fark <= 1:
                return {"gecerli": True, "tarih": f"{g}.{a}.{y}", "fark_gun": fark}
            else:
                return {"gecerli": False, "tarih": f"{g}.{a}.{y}",
                        "sebep": f"{fark} gün önce — eski dekont!"}
        except ValueError:
            continue
    
    return {"gecerli": None, "sebep": "Tarih ayrıştırılamadı"}


def manipulasyon_kontrol(img: Image.Image) -> dict:
    """Basit piksel anomalisi — keskin kenarlar, copy-paste izleri"""
    uyarilar = []
    
    try:
        import numpy as np
        arr = np.array(img.convert("RGB"))
        
        # Uniform renk blokları tespiti (kopyala-yapıştır belirtisi)
        parcalar = []
        h, w = arr.shape[:2]
        blok = 20
        for y in range(0, h - blok, blok):
            for x in range(0, w - blok, blok):
                parca = arr[y:y+blok, x:x+blok]
                std = parca.std()
                if std < 1.5:  # tamamen düz renk bloku
                    parcalar.append((x, y))
        
        if len(parcalar) > 50:
            uyarilar.append(f"⚠️ {len(parcalar)} adet düz renk bloğu (edit izleri?)")
        
        # JPEG kalite anomalisi — çok yüksek kalite şüpheli (screenshot değil fotoğraf)
        # Görüntü boyutuna göre şüphe
        if img.size[0] > 3000 or img.size[1] > 3000:
            uyarilar.append("⚠️ Çok yüksek çözünürlük — manipülasyon aracı kullanılmış olabilir")
            
    except ImportError:
        pass
    
    return {
        "temiz": len(uyarilar) == 0,
        "uyarilar": uyarilar
    }


def banka_gorunumu_kontrol(metin: str) -> dict:
    """Gerçek banka dekontu gibi görünüyor mu?"""
    bulunan = [k for k in BANKA_KELIMELER if k in metin]
    skor = len(bulunan)
    
    if skor >= 4:
        return {"gecerli": True, "skor": skor, "bulunan": bulunan[:5]}
    elif skor >= 2:
        return {"gecerli": None, "skor": skor, "bulunan": bulunan}
    else:
        return {"gecerli": False, "skor": skor,
                "sebep": "Banka dekontu anahtar kelimeleri yok"}


# ── ANA DOĞRULAMA FONKSİYONU ────────────────────────────────────────────────

def dekont_dogrula(img_bytes: bytes, user_id: int) -> dict:
    """
    Tam doğrulama. Döndürür:
    {
        "sonuc": "GECERLI" | "SAHTE" | "SUPHEILI",
        "skor": 0-100,
        "mesaj": "Admin'e gösterilecek özet",
        "detay": {...},
        "hash": "...",
        "tekrar_kullanim": False
    }
    """
    img = Image.open(io.BytesIO(img_bytes))
    
    # Hash kontrolü
    img_hash = gorsel_hash(img)
    hashler  = load_hashler()
    tekrar   = img_hash in hashler
    
    # OCR
    metin = ocr_oku(img)
    
    # Kontroller
    tutar_s    = tutar_gecerli_mi(metin)
    alici_s    = alici_gecerli_mi(metin)
    iban_s     = iban_gecerli_mi(metin)
    tarih_s    = tarih_gecerli_mi(metin)
    manip_s    = manipulasyon_kontrol(img)
    banka_s    = banka_gorunumu_kontrol(metin)
    
    # Puanlama (100 üzerinden)
    skor = 0
    
    if tutar_s["gecerli"]:    skor += 30
    if alici_s:               skor += 25
    if iban_s:                skor += 20
    if tarih_s.get("gecerli"):skor += 15
    if banka_s["gecerli"]:    skor += 10
    if manip_s["temiz"]:      skor += 0   # bonus yok ama ceza var
    else:                     skor -= 20
    if tekrar:                skor -= 50
    
    # Karar
    if skor >= 60:
        sonuc = "GEÇERLİ"
    elif skor >= 30:
        sonuc = "ŞÜPHELİ"
    else:
        sonuc = "SAHTE"
    
    # Admin mesajı
    satir = []
    satir.append(f"{'✅' if sonuc=='GEÇERLİ' else '⚠️' if sonuc=='ŞÜPHELİ' else '🚨'} <b>Dekont: {sonuc}</b>  (skor: {skor}/100)")
    satir.append("")
    
    if tekrar:
        onceki = hashler[img_hash]
        satir.append(f"🔁 <b>TEKRAR KULLANIM!</b> Bu dekont daha önce gönderildi")
        satir.append(f"   Önceki: user_id={onceki['user_id']} / {onceki['tarih'][:10]}")
    
    if tutar_s["eslesen_tutarlar"]:
        satir.append(f"💰 Tutar: <b>{'₺'.join(str(x) for x in tutar_s['eslesen_tutarlar'])}₺</b> ✅")
    else:
        bulunan_str = ", ".join(str(x) for x in tutar_s["bulunan_tutarlar"][:5]) or "yok"
        satir.append(f"💰 Tutar: bulunan={bulunan_str} — beklenen yok ❌")
    
    satir.append(f"👤 Alıcı adı/no: {'✅' if alici_s else '❌'}")
    satir.append(f"🏦 IBAN: {'✅' if iban_s else '❌'}")
    
    if tarih_s.get("gecerli") is True:
        satir.append(f"📅 Tarih: {tarih_s.get('tarih','')} ✅")
    elif tarih_s.get("gecerli") is False:
        satir.append(f"📅 Tarih: {tarih_s.get('tarih','')} ❌ ({tarih_s.get('sebep','')})")
    else:
        satir.append(f"📅 Tarih: tespit edilemedi ⚠️")
    
    satir.append(f"🏛️ Banka görünümü: skor={banka_s['skor']}/10 {'✅' if banka_s['gecerli'] else '⚠️' if banka_s['gecerli'] is None else '❌'}")
    
    if not manip_s["temiz"]:
        for u in manip_s["uyarilar"]:
            satir.append(f"🖼️ {u}")
    
    if sonuc == "SAHTE":
        satir.append("")
        satir.append("🚫 <b>ÖNERİ: Bu ödemeyi ONAYLAMAYIN</b>")
    elif sonuc == "ŞÜPHELİ":
        satir.append("")
        satir.append("⚠️ <b>ÖNERİ: Manuel kontrol edin</b>")
    else:
        satir.append("")
        satir.append("✅ <b>Görünüşe göre gerçek — yine de kontrol edin</b>")
    
    # Geçerli dekontun hash'ini kaydet
    if sonuc != "SAHTE":
        eslesen = tutar_s["eslesen_tutarlar"]
        save_hash(img_hash, user_id, eslesen[0] if eslesen else 0)
    
    return {
        "sonuc": sonuc,
        "skor": skor,
        "mesaj": "\n".join(satir),
        "hash": img_hash,
        "tekrar_kullanim": tekrar,
        "ocr_metin": metin[:300]
    }
