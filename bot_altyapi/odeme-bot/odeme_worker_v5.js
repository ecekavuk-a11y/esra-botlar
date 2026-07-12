// ═══════════════════════════════════════════════════════════
// ÖDEME BOTU v5 — @malatyaesra_odeme_bot
// YENİ: F — A/B Test sistemi (kanal bazlı parametre takibi)
//           flash_k1_fiyat / flash_k2_aciliyet / flash_k3_fayda / flash_k4_kontrol
//           KV'ye tıklama + satış sayacı, admin /rapor komutu
// ═══════════════════════════════════════════════════════════

const BOT_TOKEN = "8907710571:AAHXQy5ABXgqe8CxHweK90v6WhlBYj2EbCA";
const API = "https://api.telegram.org/bot" + BOT_TOKEN;
const ADMIN_ID = 5019918710;
const VIP_KANAL_ID = -1003947278046;

// ─── VIP HOŞ GELDİN SERİSİ ──────────────────────────────────────
const VIP_HOSGELDIN_1 = (ad) =>
  `Hoş geldin 🖤

Açıkçası seni bekliyordum. Bu kanal sadece birkaç kişinin girebildiği bir yer —
ve sen artık içerisin.

Rahat ol, burada her şey çok daha farklı.`;

const VIP_HOSGELDIN_2 = (ad) =>
  `Burada ne bulacaksın, biraz anlatayım 📲

Haftada birkaç kez yeni içerik yüklüyorum — fotoğraf, kısa video, bazen sesli
şeyler de oluyor. Arada bir özel bir seri başlatıyorum, sadece VIP'e, başka hiçbir
yerde göremezsin.

Bildirimleri aç, bir şeyleri kaçırmak istemezsin. 🔔`;

const VIP_HOSGELDIN_3 = (ad) =>
  `Bu gece biraz uğraştım kendimle 📸

Özel bir şey yükledim kanala — uzun süredir aklımdaydı, bugün oldu işte.
Şimdi gidip bak.`;

async function vipHosgeldinSer(uid, ad) {
  // 1. mesaj hemen — kısa, sıcak karşılama
  await tg("sendMessage", {
    chat_id: uid,
    text: VIP_HOSGELDIN_1(ad),
    parse_mode: "HTML",
  });
  // 2. mesaj 5 sn sonra — ne var ne yok + yönlendirme
  await new Promise(r => setTimeout(r, 5000));
  await tg("sendMessage", {
    chat_id: uid,
    text: VIP_HOSGELDIN_2(ad),
    parse_mode: "HTML",
    reply_markup: {
      inline_keyboard: [
        [{ text: "🎬 Sanal Şov Rezervasyonu", url: "https://t.me/malatyaesra_odeme_bot" }],
        [{ text: "💬 Soru sormak istiyorum", url: "https://t.me/malatya_esra44" }],
      ]
    }
  });
}

const IBAN    = "TR49 0082 9000 0949 1261 8500 57";
const IBAN_AD = "İsra Soğukpınar";
const PAPARA  = "1261850057";

const TAKIP_SAAT = 24;
const SESSIZ_GUN  = 30;

// Flash indirim fiyatları
const FLASH_NORMAL = 1500;
const FLASH_INDIRIM = 900; // %40 indirim

// ─── A/B TEST KONFIG ──────────────────────────────────────────────
// Parametre formatı: flash_[kanal]_[metin_turu]
// Ör: flash_k1_fiyat, flash_k2_aciliyet, flash_k3_fayda, flash_k4_kontrol

// Kanal bazlı A/B flash metinleri
const AB_FLASH_METINLERI = {
  // Kanal 1 — FİYAT ODAKLI
  "k1": (kalanSaat) =>
    "💰 <b>HESAP YAPAN KAZANIR</b>\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
    "normalde 1.500₺ olan VIP üyelik\n" +
    "bu gece sadece <b>900₺</b>\n\n" +
    "600₺ tasarruf — tek seferlik\n" +
    `⏰ ${kalanSaat} saat sonra kapanıyor\n\n` +
    "günde 30₺. bir kahve parası.\n" +
    "ama karşılığı bambaska bir şey 😏",

  // Kanal 2 — ACİLİYET ODAKLI
  "k2": (kalanSaat) =>
    "⚡ <b>ŞİMDİ ALMAZSAN BU FİYAT GİDER Mİ?</b>\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
    "gider.\n\n" +
    `tam ${kalanSaat} saat kaldı\n` +
    "gece yarısı saat 00:00'da fiyat 1.500₺'ye çıkıyor\n\n" +
    "şu an 900₺\n" +
    "sabah 1.500₺\n\n" +
    "fark: 600₺\n" +
    "karar: senin 😈",

  // Arşiv Kanal — FAYDA ODAKLI
  "k3": (kalanSaat) =>
    "🗂️ <b>ARŞİVDEYSEN AMA GERÇEk ARŞİVİ GÖRMEDİN</b>\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
    "bu kanal genel arşiv\n" +
    "VIP arşivinde 2 yıllık özel içerik var\n" +
    "kimse göremez — sadece üyeler\n\n" +
    "bu gece kapı 900₺'ye açık\n" +
    `${kalanSaat} saat sonra kapanıyor\n\n` +
    "bir kez içeri gir\n" +
    "anlarsın farkı 🔥",

  // Kanal 4 — KONTROL (standart)
  "k4": (kalanSaat) =>
    "🔥 <b>24 SAATLİK FLASH İNDİRİM — ŞİMDİ AKTİF</b>\n" +
    "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
    "Normalde <s>1.500₺</s> olan 1 aylık VIP üyelik,\n" +
    "sadece bugün gece yarısına kadar:\n\n" +
    "💥 <b>900₺</b> — %40 indirim\n\n" +
    `⏰ Kalan süre: yaklaşık <b>${kalanSaat} saat</b>\n\n` +
    "━━━━━━━━━━━━━━━━━━━━━━\n" +
    "Bu fiyat sabah uyanınca olmayacak.\n" +
    "Karar vermek için daha iyi an olmaz. 😈",
};



// Ücretsiz kanallar (duyuru için)
const UCRETSIZ_KANALLAR = [-1003494573579, -1002956424495, -1003959424039, -1003524644687];

// ─── METİNLER ─────────────────────────────────────────────────────
const VIP_METIN =
  "👑 <b>VIP ÜYELİK — SEÇENLER İÇİN</b>\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
  "Herkes göremez. Herkes giremez.\n" +
  "<i>Sen özel birisin — o yüzden buradasın.</i> 🔥\n\n" +
  "🥉 <b>1 Aylık</b>\n" +
  "└ 1.500₺ — Tadına bak 😏\n\n" +
  "🥈 <b>3 Aylık</b>\n" +
  "└ 3.600₺ — Aşk böyle başlar 🍯\n\n" +
  "🥇 <b>Ömür Boyu</b>\n" +
  "└ 9.900₺ — Bir kez öde, sonsuza sahip ol 💎\n\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n" +
  "✨ VIP kanalda seni bekleyen:\n" +
  "🔞 Kimsenin göremediği özel videolar\n" +
  "📲 Her gün yeni içerik — hiç durmuyor\n" +
  "🗂️ Tüm arşive sınırsız erişim\n" +
  "⚡ Öncelikli mesaj hakkı\n\n" +
  "<b>Karar ver. Pişman olmayacaksın.</b> 😈\n\n" +
  "💳 Nasıl ödemek istersin? 👇";

const SHOW_METIN =
  "🎬 <b>ÖZEL / SANAL ŞOV — BİREBİR, CANLI</b>\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
  "Seninle baş başa. Sadece sen. Sadece ben. 🌙\n" +
  "<i>Kameranın karşısında, tamamen senin için...</i>\n\n" +
  "⏳ <b>5 Dakika</b>\n" +
  "└ 500₺ — Hız kazanır, ateş yakar 🔥\n\n" +
  "⏳ <b>15 Dakika</b>\n" +
  "└ 1.500₺ — Gerçek keyif bu kadar sürer 😏\n\n" +
  "⏳ <b>30 Dakika</b>\n" +
  "└ 3.000₺ — Yarım saatlik özel dünya 🍯\n\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n" +
  "💫 Nasıl işliyor?\n" +
  "1️⃣ Süreyi seç, ödemeyi yap\n" +
  "2️⃣ Dekontu buradan ilet\n" +
  "3️⃣ Ödeme onaylanır onaylanmaz başlıyoruz 🎯\n\n" +
  "<b>Randevun hazır. Tek yapman gereken adım atmak.</b> 🔑\n\n" +
  "💳 Nasıl ödemek istersin? 👇";

const ODEME_BILGI = (tur) =>
  "💳 <b>ÖDEME BİLGİLERİ</b>\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
  "🏦 <b>IBAN (Banka Havalesi):</b>\n" +
  "<code>" + IBAN + "</code>\n" +
  "👤 <b>Alıcı:</b> " + IBAN_AD + "\n\n" +
  "📱 <b>Papara:</b>\n" +
  "<code>" + PAPARA + "</code>\n\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n" +
  (tur === "vip"
    ? "📝 Açıklamaya <b>\"VIP\"</b> yaz\n"
    : "📝 Açıklamaya <b>\"Şov\"</b> + süreyi yaz\n") +
  "📸 <b>Dekontu buraya ilet → anında aktif edilir ✅</b>\n\n" +
  "<i>Ödeme sonrası en geç 5 dakika içinde işlemin tamamlanır. 🚀</i>";

const HOSGELDIN = (ad) =>
  "Merhaba " + ad + "! 🍯\n\n" +
  "Ben <b>Esra BAL</b> 🍯\n" +
  "<i>Seçilmişlerin dünyasına hoş geldin...</i> 😈\n\n" +
  "Aşağıdan istediğini seç 👇";

const ARKADASGETIR_METIN =
  "🎁 <b>ARKADAŞ GETİR — 1 HAFTA BEDAVA</b>\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
  "VIP üyeysen ve bir arkadaşını getirirsen → <b>1 hafta ücretsiz ek süre</b> kazanırsın 🔥\n\n" +
  "📌 <b>Nasıl çalışır?</b>\n" +
  "1️⃣ Arkadaşına özel bağlantını paylaş:\n" +
  "   <code>https://t.me/malatyaesra_odeme_bot?start=ref_SENIN_ID</code>\n\n" +
  "2️⃣ Arkadaşın VIP üye olunca admin seni bilgilendirir\n" +
  "3️⃣ Hesabına 7 gün eklenir — otomatik ✅\n\n" +
  "Arkadaş sayısı sınırsız — getirdiğin kadar kazan! 😈";

// ─── FLASH İNDİRİM METNİ ──────────────────────────────────────────
const flashMetni = (kalanSaat) =>
  "🔥 <b>24 SAATLİK FLASH İNDİRİM — ŞIMDI AKTIF</b>\n" +
  "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
  "Normalde <s>1.500₺</s> olan 1 aylık VIP üyelik,\n" +
  "sadece bugün gece yarısına kadar:\n\n" +
  "💥 <b>900₺</b> — %40 indirim\n\n" +
  `⏰ Kalan süre: yaklaşık <b>${kalanSaat} saat</b>\n\n` +
  "━━━━━━━━━━━━━━━━━━━━━━\n" +
  "Bu fiyat sabah uyanınca olmayacak.\n" +
  "Karar vermek için daha iyi an olmaz. 😈\n\n" +
  "💳 Hemen almak için 👇";

function flashKb() {
  return {
    inline_keyboard: [
      [{ text: "🔥 900₺'ye HEMEN AL", callback_data: "flash_al" }],
      [{ text: "💬 Soru sormak istiyorum", url: "https://t.me/malatya_esra44" }],
    ],
  };
}

// ─── TERK EDEN TAKİP METİNLERİ ──────────────────────────────────────
const TAKIP_MESAJLARI = [
  (ad) =>
    "Hey " + ad + " 👋\n\n" +
    "Dün VIP hakkında bilgi almıştın, aklında kalmış mıydı?\n\n" +
    "Sana özel: <b>bugün üye olursan 200₺ indirim</b> yapıyorum. Sadece bu mesajı göster yeterli 🍯\n\n" +
    "Ödeme yapmak istersen burada — ya da soru sorabilirsin, cevaplarım 💋",
  (ad) =>
    "Merhaba " + ad + " 🌙\n\n" +
    "Fiyatları sorduktan sonra kayboldun — merak ettim 😏\n\n" +
    "VIP'te bu hafta özel içerik var, tam 3 yeni video geldi. Hâlâ düşünüyor musun?\n\n" +
    "Bir şey sorarsan buradayım 🔥",
  (ad) =>
    ad + ", dur bir dakika ✋\n\n" +
    "Fiyat mı engelliyor? Söyle, çözüm buluruz.\n\n" +
    "1 aylık <b>1.500₺</b> → günde <b>50₺</b>. Bir kahveden az 😄\n\n" +
    "Kararsızsan aşağıdaki butona bas, konuşalım 👇",
];

// ─── 7 GÜNLÜK HOŞ GELDİN ZİNCİRİ METİNLERİ ──────────────────────────
const ZINCIR_2GUN = (ad) =>
  `${ad} dün katıldın 😊\n\n` +
  `dün VIP'te ne paylaştım biliyor musun?\n\n` +
  `kimse göremedi. sadece üyeler gördü.\n\n` +
  `merak ettim, bir bak istersen → @malatyaesra_odeme_bot 🔥`;

const ZINCIR_4GUN = (ad) =>
  `${ad} — sana özel bir teklifim var 🎁\n\n` +
  `normalde 1.500₺ olan VIP üyelik için bugün sana özel fiyat veriyorum.\n\n` +
  `sadece bu mesaja cevap ver, konuşalım 😘`;

const ZINCIR_7GUN = (ad) =>
  `${ad} bir haftadır buradasın 👀\n\n` +
  `VIP kanalı hiç merak etmedin mi?\n\n` +
  `sana dürüst olayım: 7 gündür ücretsiz kanalda olanlar VIP'in onda birini bile görmüyor.\n\n` +
  `bu hafta son şans teklifi yapıyorum, hazırsan söyle 🔥`;

function zincirKb() {
  return {
    inline_keyboard: [
      [{ text: "👑 VIP'e bak", callback_data: "menu_vip" }],
      [{ text: "💬 Konuşalım", url: "https://t.me/malatya_esra44" }],
    ],
  };
}

// ─── ANAHTAR KELİMELER ────────────────────────────────────────────
const VIP_KEL = ["vip", "üye", "uye", "üyelik", "uyelik", "abone",
  "katıl", "katil", "fiyat", "ücret", "ucret", "kaç para",
  "kac para", "ne kadar", "kanal", "premium", "özel kanal", "ozel kanal"];

const SHOW_KEL = ["show", "şov", "sov", "sanal", "özel show", "ozel show",
  "sanal şov", "sanal sov", "görüntülü", "goruntulu",
  "canlı", "canli", "görüşme", "gorusme", "video call",
  "özel", "ozel", "birebir", "performans", "rezerv"];

function kelimeVar(metin, liste) {
  const m = metin.toLowerCase();
  return liste.some((k) => m.includes(k));
}

// ─── KLAVYELER ────────────────────────────────────────────────────
function vipKb() {
  return {
    inline_keyboard: [
      [{ text: "🏦 Banka / IBAN ile Öde", callback_data: "iban_vip" }],
      [{ text: "⭐ Telegram Stars ile Öde (999 Stars)", callback_data: "stars_vip" }],
      [{ text: "🎁 Arkadaş Getir → 1 Hafta Bedava", callback_data: "arkadasgetir" }],
      [{ text: "💬 Soru Sormak İstiyorum", url: "https://t.me/malatya_esra44" }],
    ],
  };
}

function showKb() {
  return {
    inline_keyboard: [
      [{ text: "🏦 Banka / IBAN ile Öde", callback_data: "iban_show" }],
      [{ text: "📱 Papara ile Öde", callback_data: "papara_show" }],
      [{ text: "💬 Soru Sormak İstiyorum", url: "https://t.me/malatya_esra44" }],
    ],
  };
}

function anaMenuKb() {
  return {
    inline_keyboard: [
      [{ text: "👑 VIP Üyelik — Özel Dünyam", callback_data: "menu_vip" }],
      [{ text: "🎬 Sanal Şov — Birebir & Canlı", callback_data: "menu_show" }],
      [{ text: "💳 Ödeme Bilgileri", callback_data: "menu_odeme" }],
      [{ text: "🎁 Arkadaş Getir → 1 Hafta Bedava", callback_data: "arkadasgetir" }],
    ],
  };
}

function takipKb(uid) {
  return {
    inline_keyboard: [
      [{ text: "👑 VIP Üye Olmak İstiyorum", callback_data: "menu_vip" }],
      [{ text: "💬 Soru Sormak İstiyorum", url: "https://t.me/malatya_esra44" }],
      [{ text: "⛔ Mesaj Gönderme", callback_data: "takip_dur_" + uid }],
    ],
  };
}

// ─── TELEGRAM API ─────────────────────────────────────────────────
async function tg(method, data) {
  const r = await fetch(API + "/" + method, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return r.json();
}

// ─── KV: Terk eden kullanıcıları kaydet ───────────────────────────
async function terkKaydet(env, uid, ad) {
  if (!env?.TERK_KV) return;
  const dur = await env.TERK_KV.get("dur_" + uid);
  if (dur) return;
  const mevcut = await env.TERK_KV.get("terk_" + uid);
  if (mevcut) return;
  await env.TERK_KV.put("terk_" + uid, JSON.stringify({
    ad, uid, zaman: Date.now(), gonderildi: false
  }), { expirationTtl: 7 * 24 * 60 * 60 });
}

async function terkTemizle(env, uid) {
  if (!env?.TERK_KV) return;
  await env.TERK_KV.delete("terk_" + uid);
}

// ─── KV: 7 günlük hoş geldin zinciri kaydı ────────────────────────
async function zincirKaydet(env, uid, ad) {
  if (!env?.TERK_KV) return;
  const mevcut = await env.TERK_KV.get("zincir_" + uid);
  if (mevcut) return; // Zaten kayıtlı
  await env.TERK_KV.put("zincir_" + uid, JSON.stringify({
    ad, uid, zaman: Date.now(),
    gun2: false, gun4: false, gun7: false
  }), { expirationTtl: 10 * 24 * 60 * 60 }); // 10 gün sakla
}

// ─── KV: Sessiz üye kayıt ────────────────────────────────────────
async function sessizKaydet(env, uid, ad) {
  if (!env?.TERK_KV) return;
  const dur = await env.TERK_KV.get("dur_" + uid);
  if (dur) return;
  const mevcut = await env.TERK_KV.get("sessiz_" + uid);
  if (mevcut) return;
  await env.TERK_KV.put("sessiz_" + uid, JSON.stringify({
    ad, uid, zaman: Date.now(), gonderildi: false
  }), { expirationTtl: 35 * 24 * 60 * 60 });
}

async function sessizGonder(env) {
  if (!env?.TERK_KV) return;
  const list = await env.TERK_KV.list({ prefix: "sessiz_" });
  const OTUZ_GUN = SESSIZ_GUN * 24 * 60 * 60 * 1000;
  for (const key of list.keys) {
    try {
      const raw = await env.TERK_KV.get(key.name);
      if (!raw) continue;
      const kayit = JSON.parse(raw);
      if (kayit.gonderildi) continue;
      if ((Date.now() - kayit.zaman) < OTUZ_GUN) continue;
      const dur = await env.TERK_KV.get("dur_" + kayit.uid);
      if (dur) { await env.TERK_KV.delete(key.name); continue; }

      const SESSIZ_MESAJLARI = [
        (ad) => `${ad} seni ozledim 💜\n\nbir süre oldu, ne yapiyorsun?\n\nkanal biraz degisti, yeni seyler var — bak istersen 🔥`,
        (ad) => `${ad} hala buradasin mi? 👀\n\nuzun zamandır görünmedin. bir şey oldu mu?\n\nVIP'teki son içerikler çok konuşuldu, merak ettim görmedin mi diye 😘`,
        (ad) => `${ad} — bir dakika 🙋\n\n30 gündür sessizsin. seni kaybetmek istemiyorum.\n\nsöyle, ne istiyorsun? özel bir şey mi, farkli bir şey mi?`,
      ];
      const mesajFn = SESSIZ_MESAJLARI[Math.floor(Math.random() * SESSIZ_MESAJLARI.length)];
      await tg("sendMessage", {
        chat_id: kayit.uid,
        text: mesajFn(kayit.ad),
        parse_mode: "HTML",
        reply_markup: {
          inline_keyboard: [
            [{ text: "🔥 VIP'e bak", url: "https://t.me/malatyaesra_odeme_bot" }],
            [{ text: "⛔ Mesaj gönderme", callback_data: "takip_dur_" + kayit.uid }],
          ]
        }
      });
      kayit.gonderildi = true;
      await env.TERK_KV.put(key.name, JSON.stringify(kayit), { expirationTtl: 7 * 24 * 60 * 60 });
    } catch (_) {}
  }
}

// ─── SCHEDULED: Terk edenler ─────────────────────────────────────
async function takipGonder(env) {
  if (!env?.TERK_KV) return;
  const list = await env.TERK_KV.list({ prefix: "terk_" });
  for (const key of list.keys) {
    try {
      const raw = await env.TERK_KV.get(key.name);
      if (!raw) continue;
      const kayit = JSON.parse(raw);
      if (kayit.gonderildi) continue;
      const gecenMs = Date.now() - kayit.zaman;
      const gecenSaat = gecenMs / (1000 * 60 * 60);
      if (gecenSaat < TAKIP_SAAT) continue;
      const dur = await env.TERK_KV.get("dur_" + kayit.uid);
      if (dur) { await env.TERK_KV.delete(key.name); continue; }
      const mesajFn = TAKIP_MESAJLARI[Math.floor(Math.random() * TAKIP_MESAJLARI.length)];
      await tg("sendMessage", {
        chat_id: kayit.uid,
        text: mesajFn(kayit.ad),
        parse_mode: "HTML",
        reply_markup: takipKb(kayit.uid),
      });
      kayit.gonderildi = true;
      await env.TERK_KV.put(key.name, JSON.stringify(kayit), { expirationTtl: 7 * 24 * 60 * 60 });
    } catch (_) {}
  }
}

// ─── SCHEDULED: 7 günlük zincir kontrolü ─────────────────────────
async function zincirKontrol(env) {
  if (!env?.TERK_KV) return;
  const list = await env.TERK_KV.list({ prefix: "zincir_" });
  const GUNMS = 24 * 60 * 60 * 1000;

  for (const key of list.keys) {
    try {
      const raw = await env.TERK_KV.get(key.name);
      if (!raw) continue;
      const kayit = JSON.parse(raw);
      const gecenGun = (Date.now() - kayit.zaman) / GUNMS;

      // VIP almış mı kontrol et (terk kaydı silinmişse almış demektir)
      const terk = await env.TERK_KV.get("terk_" + kayit.uid);
      // Dur bayrağı
      const dur = await env.TERK_KV.get("dur_" + kayit.uid);
      if (dur) { await env.TERK_KV.delete(key.name); continue; }

      let guncellendi = false;

      // 2. gün mesajı
      if (!kayit.gun2 && gecenGun >= 2) {
        await tg("sendMessage", {
          chat_id: kayit.uid,
          text: ZINCIR_2GUN(kayit.ad),
          parse_mode: "HTML",
          reply_markup: zincirKb(),
        });
        kayit.gun2 = true;
        guncellendi = true;
      }
      // 4. gün mesajı
      else if (!kayit.gun4 && gecenGun >= 4) {
        await tg("sendMessage", {
          chat_id: kayit.uid,
          text: ZINCIR_4GUN(kayit.ad),
          parse_mode: "HTML",
          reply_markup: zincirKb(),
        });
        kayit.gun4 = true;
        guncellendi = true;
      }
      // 7. gün mesajı
      else if (!kayit.gun7 && gecenGun >= 7) {
        await tg("sendMessage", {
          chat_id: kayit.uid,
          text: ZINCIR_7GUN(kayit.ad),
          parse_mode: "HTML",
          reply_markup: zincirKb(),
        });
        kayit.gun7 = true;
        guncellendi = true;
      }

      if (guncellendi) {
        // Tüm mesajlar gönderildiyse kaydı sil
        if (kayit.gun2 && kayit.gun4 && kayit.gun7) {
          await env.TERK_KV.delete(key.name);
        } else {
          await env.TERK_KV.put(key.name, JSON.stringify(kayit), { expirationTtl: 10 * 24 * 60 * 60 });
        }
      }
    } catch (_) {}
  }
}

// ─── A/B: Tıklama sayacı ──────────────────────────────────────────
async function abTiklamaKaydet(env, param, uid) {
  if (!env?.TERK_KV) return;
  const sayacKey = "ab_tikla_" + param;
  const raw = await env.TERK_KV.get(sayacKey);
  const sayac = raw ? JSON.parse(raw) : { count: 0, uid_list: [] };
  sayac.count++;
  if (!sayac.uid_list.includes(String(uid))) sayac.uid_list.push(String(uid));
  await env.TERK_KV.put(sayacKey, JSON.stringify(sayac), { expirationTtl: 30 * 24 * 60 * 60 });
}

// ─── A/B: Satış sayacı ─────────────────────────────────────────────
async function abSatisKaydet(env, uid) {
  if (!env?.TERK_KV) return;
  const abParam = await env.TERK_KV.get("ab_uid_" + uid);
  if (!abParam) return;
  const sayacKey = "ab_satis_" + abParam;
  const raw = await env.TERK_KV.get(sayacKey);
  const sayac = raw ? JSON.parse(raw) : { count: 0 };
  sayac.count++;
  await env.TERK_KV.put(sayacKey, JSON.stringify(sayac), { expirationTtl: 30 * 24 * 60 * 60 });
}

// ─── A/B: Kullanıcı-param eşleştir ────────────────────────────────
async function abUidKaydet(env, uid, param) {
  if (!env?.TERK_KV) return;
  await env.TERK_KV.put("ab_uid_" + uid, param, { expirationTtl: 7 * 24 * 60 * 60 });
}

// ─── A/B: Admin raporu ─────────────────────────────────────────────
async function abRaporGonder(env) {
  if (!env?.TERK_KV) return;
  const params = [
    { key: "flash_k1_fiyat",    label: "Kanal 1 — Fiyat Odaklı" },
    { key: "flash_k2_aciliyet", label: "Kanal 2 — Aciliyet Odaklı" },
    { key: "flash_k3_fayda",    label: "Arşiv — Fayda Odaklı" },
    { key: "flash_k4_kontrol",  label: "Kanal 4 — Kontrol" },
  ];
  let rapor = "📊 <b>A/B Test Sonuçları</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n";
  for (const p of params) {
    const tikRaw  = await env.TERK_KV.get("ab_tikla_" + p.key);
    const satRaw  = await env.TERK_KV.get("ab_satis_" + p.key);
    const tikSayac = tikRaw ? JSON.parse(tikRaw).count : 0;
    const satSayac = satRaw ? JSON.parse(satRaw).count : 0;
    const donusum  = tikSayac > 0 ? ((satSayac / tikSayac) * 100).toFixed(1) : "0.0";
    rapor += `<b>${p.label}</b>\n`;
    rapor += `  Tıklama: ${tikSayac} | Satış: ${satSayac} | Dönüşüm: %${donusum}\n\n`;
  }
  await tg("sendMessage", { chat_id: ADMIN_ID, text: rapor, parse_mode: "HTML" });
}

// ─── SCHEDULED: Flash indirim (haftada bir Çarşamba 20:00 TR) ─────
async function flashGonder(env) {
  if (!env?.TERK_KV) return;

  // Bu hafta flash gönderildi mi?
  const haftaKey = "flash_hafta_" + Math.floor(Date.now() / (7 * 24 * 60 * 60 * 1000));
  const gonderildi = await env.TERK_KV.get(haftaKey);
  if (gonderildi) return;

  // Flash başlangıç zamanını kaydet (24 saat için)
  const flashBaslangic = Date.now();
  await env.TERK_KV.put("flash_aktif", String(flashBaslangic), { expirationTtl: 25 * 60 * 60 }); // 25 saat
  await env.TERK_KV.put(haftaKey, "1", { expirationTtl: 8 * 24 * 60 * 60 });

  const kalanSaat = 24;
  const mesaj = flashMetni(kalanSaat);

  // A/B: Her kanala kendi metni + kendi parametreli linki
  const AB_KANAL_PARAMS = [
    { id: -1003494573579, param: "flash_k1_fiyat",    metin: AB_FLASH_METINLERI["k1"](kalanSaat) },
    { id: -1002956424495, param: "flash_k2_aciliyet", metin: AB_FLASH_METINLERI["k2"](kalanSaat) },
    { id: -1003959424039, param: "flash_k3_fayda",    metin: AB_FLASH_METINLERI["k3"](kalanSaat) },
    { id: -1003524644687, param: "flash_k4_kontrol",  metin: AB_FLASH_METINLERI["k4"](kalanSaat) },
  ];
  for (const kanal of AB_KANAL_PARAMS) {
    try {
      await tg("sendMessage", {
        chat_id: kanal.id,
        text: kanal.metin,
        parse_mode: "HTML",
        reply_markup: {
          inline_keyboard: [
            [{ text: "🔥 900₺'ye HEMEN AL", url: `https://t.me/malatyaesra_odeme_bot?start=${kanal.param}` }],
          ]
        }
      });
    } catch (_) {}
  }

  // Admin'e bildir
  await tg("sendMessage", {
    chat_id: ADMIN_ID,
    text: "🔥 A/B Flash indirim başlatıldı!\n\nk1 → Fiyat Odaklı\nk2 → Aciliyet Odaklı\nk3 → Fayda Odaklı\nk4 → Kontrol\n\n24 saat sonra /rapor yaz → sonuçları gör.",
    parse_mode: "HTML",
  });
}

// ─── Günlük Rapor (her gece 01:00 TR → 22:00 UTC) ──────────────────
async function gunlukRaporGonder(env) {
  if (!env?.TERK_KV) return;

  // Bugün rapor gönderildi mi?
  const bugun = new Date().toISOString().slice(0, 10);
  const raporKey = "gunluk_rapor_" + bugun;
  const gonderildi = await env.TERK_KV.get(raporKey);
  if (gonderildi) return;
  await env.TERK_KV.put(raporKey, "1", { expirationTtl: 2 * 24 * 60 * 60 });

  // Terk listesi
  const terkList = await env.TERK_KV.list({ prefix: "terk_" });
  const terkSayisi = terkList.keys?.length || 0;

  // Sessiz listesi
  const sessizList = await env.TERK_KV.list({ prefix: "sessiz_" });
  const sessizSayisi = sessizList.keys?.length || 0;

  // Zincir aktif kullanıcılar
  const zincirList = await env.TERK_KV.list({ prefix: "zincir_" });
  const zincirSayisi = zincirList.keys?.length || 0;

  // Bugünkü satışlar (A/B sayaçlarından toplam)
  const params = ["flash_k1_fiyat", "flash_k2_aciliyet", "flash_k3_fayda", "flash_k4_kontrol"];
  let toplamSatis = 0;
  for (const p of params) {
    const raw = await env.TERK_KV.get("ab_satis_" + p);
    if (raw) {
      try { toplamSatis += JSON.parse(raw).count || 0; } catch {}
    }
  }

  // Flash indirim aktif mi?
  const flashAktif = await env.TERK_KV.get("flash_aktif");
  const flashDurum = flashAktif ? "🔥 Aktif" : "—";

  const saat = new Date().toLocaleString("tr-TR", { timeZone: "Europe/Istanbul", hour: "2-digit", minute: "2-digit" });
  const tarih = new Date().toLocaleDateString("tr-TR", { timeZone: "Europe/Istanbul", day: "numeric", month: "long" });

  const rapor =
    `📊 <b>Günlük Özet — ${tarih}</b>\n` +
    `━━━━━━━━━━━━━━━━━━━━━━\n\n` +
    `👤 Takipte olan (terk riski): <b>${terkSayisi}</b>\n` +
    `🔇 Sessiz kalan: <b>${sessizSayisi}</b>\n` +
    `⛓️ Zincir aktif: <b>${zincirSayisi}</b>\n` +
    `💰 Toplam kayıtlı satış: <b>${toplamSatis}</b>\n` +
    `🔥 Flash indirim: ${flashDurum}\n\n` +
    `<i>Saat ${saat} - Otomatik rapor</i>`;

  await tg("sendMessage", { chat_id: ADMIN_ID, text: rapor, parse_mode: "HTML" });
}

// ─── VIP satış kanalı duyurusu ─────────────────────────────────────
async function satisKanalDuyuru() {
  const DUYURULAR = [
    "👑 Yeni bir üye VIP ailesine katıldı. Hoş geldin! 🍯",
          // KAPATILDI (VIP duyurusu): "🔥 Az önce biri VIP üye oldu. Sen ne bekliyorsun? 😏",
    "💎 VIP ailemiz büyümeye devam ediyor. Yeni üye katıldı! ✅",
    "🎉 Bir kişi daha seçti. VIP kanalında görüşürüz 👑",
    "✨ Bugün de yeni bir üye katıldı. Doğru karar! 🔥",
  ];
  const mesaj = DUYURULAR[Math.floor(Math.random() * DUYURULAR.length)];

  // Ana ücretsiz kanala gönder
  await tg("sendMessage", {
    chat_id: UCRETSIZ_KANALLAR[0], // İlk ücretsiz kanal
          // KAPATILDI (VIP duyurusu): text: mesaj + "\n\n👉 Sen de katıl → @malatyaesra_odeme_bot",
    parse_mode: "HTML",
  });
}

// ─── REAKSİYON ─────────────────────────────────────────────────────
const REAKSIYONLAR_O = ["🔥","❤️","🥰","👏","😁","🎉","🤩","💋","😍","💯"];
async function reaksiyonAt(chatId, messageId) {
  const bekle = Math.floor(Math.random() * 30000) + 5000;
  await new Promise(r => setTimeout(r, bekle));
  await tg("setMessageReaction", {
    chat_id: chatId, message_id: messageId,
    reaction: [{ type: "emoji", emoji: REAKSIYONLAR_O[Math.floor(Math.random() * REAKSIYONLAR_O.length)] }],
    is_big: false,
  });
}

// ─── EXPORT ───────────────────────────────────────────────────────
export default {
  async fetch(req, env) {
    if (req.method !== "POST") return new Response("OK");
    let u;
    try { u = await req.json(); } catch { return new Response("OK"); }

    try {
      // ── KATILIM İSTEĞİ ANLIK ONAY + HOŞ GELDIN ZİNCİRİ ──
      if (u.chat_join_request) {
        const jreq    = u.chat_join_request;
        const chatId  = jreq.chat?.id;
        const userId  = jreq.from?.id;
        const ad      = jreq.from?.first_name || "birisi";

        if (!UCRETSIZ_KANALLAR.includes(chatId) || !userId) return new Response("OK");

        // 1. Onayla
        await tg("approveChatJoinRequest", { chat_id: chatId, user_id: userId });

        // Kayıtları tut
        await sessizKaydet(env, userId, ad);
        await zincirKaydet(env, userId, ad); // 7 günlük zincire ekle

        const simdi = Math.floor(Date.now() / 1000);

        // 2. Anında DM
        await tg("sendMessage", {
          chat_id: userId,
          text: `seni gördüm ${ad} 👀\n\nkanalıma hoş geldin. burada herkes özel, herkes seçilmiş.\n\niyi bak, herkese böyle yazmıyorum 🔥`,
          parse_mode: "HTML",
        });

        // 3. 12 dakika sonra
        await tg("sendMessage", {
          chat_id: userId,
          text: `hala buradasin dimi? 😏\n\nkanalda görünen sadece küçük bir parça. asıl olanları sadece benim VIP üyelerim görüyor.\n\nmerak ettim mi acaba 👀`,
          parse_mode: "HTML",
          schedule_date: simdi + 720,
        });

        // 4. 75 dakika sonra
        await tg("sendMessage", {
          chat_id: userId,
          text: `tamam sana söyleyeyim 😘\n\nVIP'te ne var?\n\n• hiç kimsenin görmediği özel videolar\n• istediğin zaman mesaj atabilirsin bana\n• özel şov imkanı\n\n1 ay sadece <b>1.500₺</b> — bir kez dene yeter.\n\nkatılmak istiyorsan → @malatyaesra_odeme_bot`,
          parse_mode: "HTML",
          schedule_date: simdi + 4500,
        });

        return new Response("OK");
      }

      // ── KANAL ÜYELİK ──
      if (u.message?.new_chat_members) {
        if (UCRETSIZ_KANALLAR.includes(u.message.chat.id)) {
          for (const yeni of u.message.new_chat_members) {
            if (!yeni.is_bot) {
              await sessizKaydet(env, yeni.id, yeni.first_name || "sen");
              await zincirKaydet(env, yeni.id, yeni.first_name || "sen");
            }
          }
        }
        return new Response("OK");
      }

      // ── MESAJLAR ──
      if (u.message) {
        const msg  = u.message;
        const cid  = msg.chat.id;
        const uid  = msg.from.id;
        const ad   = msg.from.first_name || "Merhaba";
        const user_tag = msg.from.username ? "@" + msg.from.username : String(uid);
        const metin = (msg.text || "").trim();

        // /start — referans kontrolü
        if (metin.startsWith("/start")) {
          const parts = metin.split(" ");

          // Flash indirim linki — A/B parametreli
          // flash | flash_k1_fiyat | flash_k2_aciliyet | flash_k3_fayda | flash_k4_kontrol
          if (parts[1] && (parts[1] === "flash" || parts[1].startsWith("flash_"))) {
            const abParam = parts[1];
            const flashAktif = await env?.TERK_KV?.get("flash_aktif");
            // A/B: tıklama kaydet + kullanıcı-param eşleştir
            await abTiklamaKaydet(env, abParam, uid);
            await abUidKaydet(env, uid, abParam);
            if (flashAktif) {
              const gecenSaat = (Date.now() - Number(flashAktif)) / (1000 * 60 * 60);
              const kalanSaat = Math.max(1, Math.round(24 - gecenSaat));
              // Varyanta özel metin göster
              const kanalKodu = abParam.split("_")[1] || "k4";
              const abMetinFn = AB_FLASH_METINLERI[kanalKodu] || AB_FLASH_METINLERI["k4"];
              await tg("sendMessage", {
                chat_id: cid,
                text: abMetinFn(kalanSaat),
                parse_mode: "HTML",
                reply_markup: flashKb(),
              });
            } else {
              await tg("sendMessage", {
                chat_id: cid,
                text: "Üzgünüm, flash indirim sona erdi 😔\n\nAma normal fiyatla hâlâ alabilirsin:",
                parse_mode: "HTML",
                reply_markup: vipKb(),
              });
            }
            await terkKaydet(env, uid, ad);
          }
          // Arkadaş referansı
          else if (parts[1] && parts[1].startsWith("ref_")) {
            const refUID = parts[1].replace("ref_", "");
            await tg("sendMessage", {
              chat_id: ADMIN_ID,
              text: `🎁 <b>Referans kullanıldı!</b>\n\nGelen: ${ad} (ID: ${uid})\nReferans veren ID: ${refUID}\n\nℹ️ ${ad} ödeme yaparsa, ${refUID} numaralı kullanıcıya +7 gün ekle.`,
              parse_mode: "HTML",
            });
            await tg("sendMessage", {
              chat_id: refUID,
              text: `🎉 birisi senin linkinle geldi!\n\narkadaşlarını getirmeye devam et — bir kişi VIP olursa sana <b>+7 gün ücretsiz</b> ekliyorum 👌\n\nlinkin: https://t.me/malatyaesra_odeme_bot?start=ref_${refUID}`,
              parse_mode: "HTML",
            });
            if (env?.TERK_KV) {
              await env.TERK_KV.put(`ref_${uid}`, JSON.stringify({
                refUID, uid, ad, zaman: Date.now()
              }), { expirationTtl: 30 * 24 * 60 * 60 });
            }
          }

          // Normal hoş geldin
          await tg("sendMessage", {
            chat_id: cid,
            text: HOSGELDIN(ad),
            parse_mode: "HTML",
            reply_markup: anaMenuKb(),
          });
          await terkKaydet(env, uid, ad);
          await zincirKaydet(env, uid, ad); // 7 günlük zincire ekle

        } else if (metin === "/rapor" && uid === ADMIN_ID) {
          // Admin A/B raporu
          await abRaporGonder(env);

        } else if (metin.startsWith("/onayla") && uid === ADMIN_ID) {
          // Admin: /onayla [user_id] → VIP davet linki gönder
          const parcalar = metin.trim().split(/\s+/);
          const hedefId  = parseInt(parcalar[1]);
          if (!hedefId || isNaN(hedefId)) {
            await tg("sendMessage", { chat_id: cid, text: "⚠️ Kullanım: /onayla [user_id]\nÖrnek: /onayla 123456789" });
          } else {
            try {
              // Tek kullanımlık VIP davet linki oluştur
              const davetRes = await tg("createChatInviteLink", {
                chat_id: VIP_KANAL_ID,
                member_limit: 1,
                name: "VIP_" + hedefId,
              });
              const davetLink = davetRes?.result?.invite_link;
              if (davetLink) {
                // Kullanıcıya mesaj gönder
                await tg("sendMessage", {
                  chat_id: hedefId,
                  text: "Girdin sonunda 🔑\n\nSeni buraya kadar getiren merakın için teşekkür etmiyorum — zaten biliyorduk bu olacak.\nŞimdi gerçekten başlıyor.\n\nVIP'te sana dışarıya göstermediğim taraflarımı paylaşıyorum. Özel seriler, anlık içerikler, sadece burada paylaştığım şeyler…\n\nKanalına katılmak için: " + davetLink + "\n\nGörüşürüz içeride 🖤",
                  parse_mode: "HTML",
                });
                // Admin'e bildir
                await tg("sendMessage", {
                  chat_id: ADMIN_ID,
                  text: "✅ VIP davet linki gönderildi!\nKullanıcı ID: " + hedefId + "\nLink: " + davetLink,
                });
              } else {
                await tg("sendMessage", { chat_id: cid, text: "❌ Davet linki oluşturulamadı. Bot VIP kanalında admin mi?\n" + JSON.stringify(davetRes) });
              }
            } catch (e) {
              await tg("sendMessage", { chat_id: cid, text: "❌ Hata: " + e.message });
            }
          }

        } else if (metin.startsWith("/onayla_") && uid === ADMIN_ID) {
          // Eski format: /onayla_[user_id]
          const hedefId = parseInt(metin.replace("/onayla_", ""));
          if (!hedefId || isNaN(hedefId)) {
            await tg("sendMessage", { chat_id: cid, text: "⚠️ Geçersiz kullanıcı ID" });
          } else {
            try {
              const davetRes = await tg("createChatInviteLink", {
                chat_id: VIP_KANAL_ID,
                member_limit: 1,
                name: "VIP_" + hedefId,
              });
              const davetLink = davetRes?.result?.invite_link;
              if (davetLink) {
                await tg("sendMessage", {
                  chat_id: hedefId,
                  text: "Girdin sonunda 🔑\n\nSeni buraya kadar getiren merakın için teşekkür etmiyorum — zaten biliyorduk bu olacak.\nŞimdi gerçekten başlıyor.\n\nVIP'te sana dışarıya göstermediğim taraflarımı paylaşıyorum. Özel seriler, anlık içerikler, sadece burada paylaştığım şeyler…\n\nKanalına katılmak için: " + davetLink + "\n\nGörüşürüz içeride 🖤",
                  parse_mode: "HTML",
                });
                await tg("sendMessage", {
                  chat_id: ADMIN_ID,
                  text: "✅ VIP davet linki gönderildi!\nKullanıcı ID: " + hedefId + "\nLink: " + davetLink,
                });
              } else {
                await tg("sendMessage", { chat_id: cid, text: "❌ Davet linki oluşturulamadı.\n" + JSON.stringify(davetRes) });
              }
            } catch (e) {
              await tg("sendMessage", { chat_id: cid, text: "❌ Hata: " + e.message });
            }
          }

        } else if (metin.startsWith("/menu")) {
          await tg("sendMessage", {
            chat_id: cid,
            text: HOSGELDIN(ad),
            parse_mode: "HTML",
            reply_markup: anaMenuKb(),
          });
          await terkKaydet(env, uid, ad);

        } else if (metin.startsWith("/vip")) {
          await terkKaydet(env, uid, ad);
          await tg("sendMessage", { chat_id: cid, text: VIP_METIN, parse_mode: "HTML", reply_markup: vipKb() });

        } else if (metin.startsWith("/show") || metin.startsWith("/sov")) {
          await tg("sendMessage", { chat_id: cid, text: SHOW_METIN, parse_mode: "HTML", reply_markup: showKb() });

        } else if (metin.startsWith("/odeme")) {
          await tg("sendMessage", { chat_id: cid, text: ODEME_BILGI("genel"), parse_mode: "HTML" });

        } else if (metin && kelimeVar(metin, VIP_KEL)) {
          await terkKaydet(env, uid, ad);
          // Kişisel ön mesaj — sonra VIP detayı
          const vipOnMesaj = [
            `Aa, demek o tarafı merak ediyorsun 🙂

VIP'im biraz farklı — orada gerçekten ne var, nasıl bir yer, sana düzgünce anlatayım.
Sadece "şunu al" demiyorum, önce ne aldığını bilmeni istiyorum.

Bir saniye, sana her şeyi yazıyorum.`,
            `Aa, demek o tarafı merak ediyorsun 🙂

VIP'im biraz farklı — orada gerçekten ne var, nasıl bir yer, sana düzgünce anlatayım.
Sadece "şunu al" demiyorum, önce ne aldığını bilmeni istiyorum.

Bir saniye, sana her şeyi yazıyorum.`,
            `Aa, demek o tarafı merak ediyorsun 🙂

VIP'im biraz farklı — orada gerçekten ne var, nasıl bir yer, sana düzgünce anlatayım.
Sadece "şunu al" demiyorum, önce ne aldığını bilmeni istiyorum.

Bir saniye, sana her şeyi yazıyorum.`,
          ];
          await tg("sendMessage", {
            chat_id: cid, parse_mode: "HTML",
            text: vipOnMesaj[Math.floor(Math.random() * vipOnMesaj.length)],
          });
          await new Promise(r => setTimeout(r, 800));
          await tg("sendMessage", { chat_id: cid, text: VIP_METIN, parse_mode: "HTML", reply_markup: vipKb() });
          // // kapatıldı: await tg("sendMessage", { chat_id: ADMIN_ID, text: "💎 VIP ilgisi!\nKullanıcı: " + user_tag + "\nMesaj: " + metin.slice(0, 100) }); // kapatıldı


        } else if (metin && kelimeVar(metin, SHOW_KEL)) {
          await tg("sendMessage", { chat_id: cid, text: SHOW_METIN, parse_mode: "HTML", reply_markup: showKb() });
          // // kapatıldı: await tg("sendMessage", { chat_id: ADMIN_ID, text: "🔥 Şov ilgisi!\nKullanıcı: " + user_tag + "\nMesaj: " + metin.slice(0, 100) }); // kapatıldı

        } else if (msg.photo || msg.document) {
          // Dekont geldi — OTOMATİK VIP EKLE
          await terkTemizle(env, uid);
          await abSatisKaydet(env, uid);

          // 1. Hemen VIP davet linki oluştur
          let vipLink = null;
          try {
            const davetRes = await tg("createChatInviteLink", {
              chat_id: VIP_KANAL_ID,
              member_limit: 1,
              name: "VIP_" + uid,
            });
            vipLink = davetRes?.result?.invite_link || null;
          } catch (e) {
            vipLink = null;
          }

          // 2. Kullanıcıya cevap ver
          if (vipLink) {
            await tg("sendMessage", {
              chat_id: cid,
              text: "ödemen onaylandı 🍯\n\nVIP kanalına katılmak için tıkla:\n" + vipLink + "\n\nhoş geldin 💜",
              parse_mode: "HTML",
            });
          } else {
            await tg("sendMessage", {
              chat_id: cid,
              text: "📨 Dekontun alındı! Birkaç dakika içinde VIP kanalı açılacak ✅",
              parse_mode: "HTML",
            });
          }

          // 3. Admin'e bildir
          const adminCaption = "💳 Yeni dekont!\nKullanıcı: " + user_tag + "\nID: " + uid +
            (vipLink ? "\n\n✅ VIP linki otomatik gönderildi:\n" + vipLink : "\n\n⚠️ Davet linki oluşturulamadı — manuel: /onayla " + uid);
          if (msg.photo) {
            const fid = msg.photo[msg.photo.length - 1].file_id;
            await tg("sendPhoto", { chat_id: ADMIN_ID, photo: fid, caption: adminCaption });
          } else {
            await tg("sendDocument", { chat_id: ADMIN_ID, document: msg.document.file_id, caption: adminCaption });
          }
        } else if (metin) {
          // Keyword eşleşmedi ama metin var — doğal, meraklı cevap ver
          await terkKaydet(env, uid, ad);

          // Kararsız kullanıcıya teaser teklifi
          const teaserMesajlari = [
            `Burada ne aradığını merak ettim açıkçası 🤔

Çoğu kişi ilk başta öyle gelir — bakar, sessiz durur. Ama bir şey arıyorsun, değil mi?

Söyle, ne görmek istersin?`,
            `Seninle biraz konuşalım mı? 💬

Buraya kadar geldin, yani bir şeyler döndü aklında. Ben ne sunduğumu biliyorum —
ama seni ne getirdi buraya?

Merak mı, yoksa karar neredeyse verilmiş mi? 😏`,
            `Sessiz duruyorsun ama buradasın 👀

Sorun değil, anlarım. Bazen insan bakmak ister ama sormak istemez.
O yüzden ben soruyorum: ne görmek isterdin burada?

Cevaplamak zorunda değilsin — aşağıdaki butonlar da söyler. 😏`,
          ];
          const rastgele = teaserMesajlari[Math.floor(Math.random() * teaserMesajlari.length)];

          await tg("sendMessage", {
            chat_id: cid,
            parse_mode: "HTML",
            text: rastgele,
            reply_markup: {
              inline_keyboard: [
                [{ text: "🍯 Evet, teaser göster", callback_data: "teaser_goster" }],
                [{ text: "💎 VIP hakkında bilgi al", callback_data: "menu_vip" }],
                [{ text: "💳 Fiyatlar ne?", callback_data: "menu_odeme" }],
              ]
            }
          });
        } else {
          await terkKaydet(env, uid, ad);
        }
      }

      // ── CALLBACK QUERY ──
      if (u.callback_query) {
        const cb   = u.callback_query;
        const cid  = cb.message.chat.id;
        const uid  = cb.from.id;
        const ad   = cb.from.first_name || "Merhaba";
        const user_tag = cb.from.username ? "@" + cb.from.username : String(uid);
        const data = cb.data;

        await tg("answerCallbackQuery", { callback_query_id: cb.id });

        if (data === "menu_vip") {
          await terkKaydet(env, uid, ad);
          await tg("sendMessage", { chat_id: cid, text: VIP_METIN, parse_mode: "HTML", reply_markup: vipKb() });

        } else if (data === "menu_show") {
          await tg("sendMessage", { chat_id: cid, text: SHOW_METIN, parse_mode: "HTML", reply_markup: showKb() });

        } else if (data === "menu_odeme") {
          await tg("sendMessage", { chat_id: cid, text: ODEME_BILGI("genel"), parse_mode: "HTML" });

        } else if (data === "arkadasgetir") {
          const refLink = "https://t.me/malatyaesra_odeme_bot?start=ref_" + uid;
          const metin = ARKADASGETIR_METIN.replace("ref_SENIN_ID", "ref_" + uid) +
            "\n\n🔗 <b>Senin özel linkin:</b>\n<code>" + refLink + "</code>";
          await tg("sendMessage", { chat_id: cid, text: metin, parse_mode: "HTML" });

        } else if (data === "flash_al") {
          // Flash indirim satın al
          await terkTemizle(env, uid);
          const abParamAl = (await env?.TERK_KV?.get("ab_uid_" + uid)) || "bilinmiyor";
          await tg("sendMessage", {
            chat_id: cid,
            text: "🔥 <b>Flash indirim — 900₺ VIP</b>\n\n" + ODEME_BILGI("vip") + "\n\n⚡ Açıklamaya <b>\"FLASH\"</b> yazmayı unutma!",
            parse_mode: "HTML",
          });
          // Admin'e bildir + A/B kaynağı
          await tg("sendMessage", {
            chat_id: ADMIN_ID,
            text: `🔥 Flash indirim alıcısı!\nKullanıcı: ${user_tag} (ID: ${uid})\nA/B Kaynak: ${abParamAl}\n\nÖdeme gelirse 900₺ VIP ver.`,
          });

        } else if (data === "stars_vip") {
          // Stars öncesi teaser göster
          await terkTemizle(env, uid);
          await tg("sendMessage", {
            chat_id: cid,
            parse_mode: "HTML",
            text: `⭐ <b>Telegram Stars ile ödeme</b>\n\n999 Stars = 1 aylık VIP üyelik\n\nVIP'e girince bunları bulacaksın:\n🔥 800+ özel içerik — arşivin tamamı\n📸 Günlük yeni paylaşımlar\n🎭 Kategoriler: banyo, gece, kostüm, sesli ve daha fazlası\n🎬 Sanal şov rezervasyonu önceliği\n\nÖdeme Telegram üzerinden yapılır — güvenli, anında, anonim.\nOnaylandığı saniye kanal açılır. 🍯`,
            reply_markup: {
              inline_keyboard: [
                [{ text: "⭐ Devam et — Ödeme Yap", callback_data: "stars_odeme_onayla" }],
                [{ text: "↩️ Geri", callback_data: "menu_vip" }],
              ]
            }
          });

        } else if (data === "stars_odeme_onayla") {
          // Telegram Stars ödeme faturası gönder
          const invoiceRes = await tg("sendInvoice", {
            chat_id: cid,
            title: "VIP Üyelik — 1 Ay",
            description: "1 aylık VIP üyelik. Ödeme onaylanır onaylanmaz kanal anında açılır 🍯",
            payload: "vip_stars_" + uid,
            currency: "XTR",
            prices: [{ label: "VIP Üyelik", amount: 999 }],
          });

          if (!invoiceRes?.ok) {
            // Fatura oluşturulamadı — kullanıcıya net hata ver
            await tg("sendMessage", {
              chat_id: cid,
              parse_mode: "HTML",
              text: `Bir şeyler takıldı, olur 🤷‍♀️

Stars ödemesi bazen böyle yapıyor — senin hatan değil. Eğer istersen farklı bir yoldan da halledebiliriz, aşağıda IBAN seçeneğini bıraktım.

Ya da tekrar denemek istersen, o buton da orada seni bekliyor.`,
              reply_markup: {
                inline_keyboard: [
                  [{ text: "⭐ Tekrar Dene — Stars", callback_data: "stars_odeme_onayla" }],
                  [{ text: "💳 IBAN ile Öde", callback_data: "iban_vip" }],
                  [{ text: "❓ Yardım Al", url: "https://t.me/malatya_esra44" }],
                ]
              }
            });
          } else {
            // Fatura gönderildi — iptal durumu için bilgi ver
            await tg("sendMessage", {
              chat_id: cid,
              parse_mode: "HTML",
              text: `fatura yukarıda 👆

"Pay" butonuna bas, saniyeler içinde VIP'te olursun 🍯

<i>Sorun yaşarsan buraya yaz, IBAN ile de halledebiliriz.</i>`,
              reply_markup: {
                inline_keyboard: [
                  [{ text: "💳 IBAN ile Öde (alternatif)", callback_data: "iban_vip" }],
                ]
              }
            });
            await tg("sendMessage", { chat_id: ADMIN_ID, text: `⭐ Stars faturası gönderildi!
Kullanıcı: ${user_tag} (ID: ${uid})` });
          }

        } else if (data === "iban_vip" || data === "papara_vip") {
          await terkTemizle(env, uid);
          // VIP satışı — kanala duyuru tetikle
          // await satisKanalDuyuru(); // kapatıldı
          await tg("sendMessage", { chat_id: cid, text: ODEME_BILGI("vip"), parse_mode: "HTML" });
          // await tg("sendMessage", { chat_id: ADMIN_ID, text: `💎 Ödeme adımına geçti!\nKullanıcı: ${user_tag} (ID: ${uid})` }); // kapatıldı

        } else if (data === "iban_show" || data === "papara_show") {
          await tg("sendMessage", { chat_id: cid, text: ODEME_BILGI("show"), parse_mode: "HTML" });

        } else if (data === "teaser_goster") {
          // Ücretsiz teaser teklifi — kullanıcıyı kanala yönlendir
          await tg("sendMessage", {
            chat_id: cid,
            parse_mode: "HTML",
            text: `harika 😊

ücretsiz kanalıma katıl, sana özel küçük bir teaser göndereyim 🍯

herkes göremez, sen özelsin 💜`,
            reply_markup: {
              inline_keyboard: [
                [{ text: "📲 Ücretsiz Kanala Katıl", url: "https://t.me/malatya_esra44" }],
                [{ text: "💎 Direkt VIP'e Geç", callback_data: "menu_vip" }],
              ]
            }
          });
          // teaser admin bildirimi kapatıldı

        } else if (data.startsWith("takip_dur_")) {
          const targetUid = data.replace("takip_dur_", "");
          if (env?.TERK_KV) {
            await env.TERK_KV.put("dur_" + targetUid, "1", { expirationTtl: 30 * 24 * 60 * 60 });
            await env.TERK_KV.delete("terk_" + targetUid);
          }
          await tg("sendMessage", {
            chat_id: cid,
            text: "Tamam, bir daha mesaj göndermeyeceğim 👋\nFikrin değişirse /start yazabilirsin.",
          });
        }
      }
    } catch (e) {
      console.error("Hata:", e);
      // Kritik hata → admin'e anında bildir
      try {
        const hataMesaji = String(e?.message || e).slice(0, 300);
        const updateOzet = u?.message?.from?.id
          ? `Kullanıcı: ${u.message.from.id}`
          : u?.callback_query?.from?.id
            ? `Callback: ${u.callback_query.from.id}`
            : "Bilinmiyor";
        await tg("sendMessage", {
          chat_id: ADMIN_ID,
          text: `🚨 <b>Bot Kritik Hata!</b>

${updateOzet}
Hata: <code>${hataMesaji}</code>`,
          parse_mode: "HTML",
        });
      } catch (_) {}
    }

    // ── PRE CHECKOUT QUERY (Stars ödeme onayı) ──
    if (u.pre_checkout_query) {
      const pcq = u.pre_checkout_query;
      await tg("answerPreCheckoutQuery", { pre_checkout_query_id: pcq.id, ok: true });
      return new Response("OK");
    }

    // ── SUCCESSFUL PAYMENT (Stars ödeme tamamlandı → otomatik VIP) ──
    if (u.message?.successful_payment) {
      const sp      = u.message.successful_payment;
      const uid     = u.message.from.id;
      const ad      = u.message.from.first_name || "Merhaba";
      const user_tag = u.message.from.username ? "@" + u.message.from.username : String(uid);

      if (sp.currency === "XTR" && sp.invoice_payload?.startsWith("vip_stars_")) {
        await terkTemizle(env, uid);
        await abSatisKaydet(env, uid);
        // await satisKanalDuyuru(); // kapatıldı

        // VIP davet linki oluştur ve gönder
        let vipLink = null;
        try {
          const davetRes = await tg("createChatInviteLink", {
            chat_id: VIP_KANAL_ID,
            member_limit: 1,
            name: "STARS_" + uid,
          });
          vipLink = davetRes?.result?.invite_link || null;
        } catch (e) { vipLink = null; }

        if (vipLink) {
          await tg("sendMessage", {
            chat_id: uid,
            text: "Girdin sonunda 🔑\n\nSeni buraya kadar getiren merakın için teşekkür etmiyorum — zaten biliyorduk bu olacak.\nŞimdi gerçekten başlıyor.\n\nVIP'te sana dışarıya göstermediğim taraflarımı paylaşıyorum. Özel seriler, anlık içerikler, sadece burada paylaştığım şeyler… Bazılarını görünce \"neden daha önce gelmemişim\" diyeceksin.\n\nKanalına katılmak için: " + vipLink + "\n\nGörüşürüz içeride 🖤",
            parse_mode: "HTML",
          });
          // Hoş geldin serisi başlat
          await vipHosgeldinSer(uid, ad);
        } else {
          await tg("sendMessage", {
            chat_id: uid,
            text: "⭐ Stars ödemin alındı! Birkaç dakika içinde VIP kanalı açılacak 🍯",
            parse_mode: "HTML",
          });
        }

        await tg("sendMessage", {
          chat_id: ADMIN_ID,
          text: "⭐ Stars ödeme tamamlandı!\nKullanıcı: " + user_tag + "\nID: " + uid + "\nMiktar: " + sp.total_amount + " Stars" +
            (vipLink ? "\n\n✅ VIP linki otomatik gönderildi" : "\n\n⚠️ Manuel ekle: /onayla " + uid),
        });
      }
      return new Response("OK");
    }

    return new Response("OK", { status: 200 });
  },

  // Cloudflare Scheduled — her saat çalışır
  async scheduled(event, env, ctx) {
    ctx.waitUntil((async () => {
      await takipGonder(env);
      await zincirKontrol(env);
      // Her gece 22:00 UTC (01:00 TR) günlük rapor gönder
      const now = new Date();
      if (now.getUTCHours() === 22 && now.getUTCMinutes() < 60) {
        await gunlukRaporGonder(env);
      }
    })());
    ctx.waitUntil(sessizGonder(env));
    ctx.waitUntil(zincirKontrol(env));

    // Çarşamba 17:00 UTC (TR 20:00) → flash indirim
    const now = new Date();
    const gun = now.getUTCDay(); // 3 = Çarşamba
    const saat = now.getUTCHours();
    if (gun === 3 && saat === 17) {
      ctx.waitUntil(flashGonder(env));
    }
  }
};
