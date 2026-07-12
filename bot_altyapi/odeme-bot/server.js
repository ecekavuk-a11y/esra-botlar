/**
 * odeme-bot — Express sarmalayıcı
 * ---------------------------------
 * odeme_worker_v5.js Cloudflare Worker olarak yazılmış olabilir; bu dosya
 * onu Node.js/Express ortamında webhook endpoint olarak çalıştırır.
 *
 * ÖNEMLİ — ÇİFT WEBHOOK ÇAKIŞMASI ÇÖZÜMÜ:
 * odeme_bot (8907710571) ve Vip_iesrabot (8934662828) AYNI Cloudflare
 * Worker URL'sine (https://odeme-bot.ecekavuk.workers.dev) point ediyordu.
 * Bu servis her botu ayrı path üzerinden ayırt eder:
 *   POST /webhook/odeme        -> odeme_bot güncellemeleri
 *   POST /webhook/vip          -> Vip_iesrabot güncellemeleri
 * nginx bu path'lere göre doğru upstream'e yönlendirir (bkz nginx/conf.d).
 * Telegram setWebhook çağrılarını da bu path'lere göre YENİDEN yapmak
 * gerekir (bkz deploy.sh -> set_webhooks fonksiyonu).
 */

const express = require("express");
const fetch = require("node-fetch");
const redis = require("redis");

const PORT = process.env.PORT || 3001;
const ODEME_BOT_TOKEN = process.env.BOT_TOKEN || "";
const VIP_BOT_TOKEN = process.env.VIP_BOT_TOKEN || "";
const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379/0";

const app = express();
app.use(express.json({ limit: "2mb" }));

let redisClient;
let redisReady = false;

async function initRedis() {
  redisClient = redis.createClient({ url: REDIS_URL });
  redisClient.on("error", (err) => {
    console.error(`[redis] bağlantı hatası: ${err.message}`);
    redisReady = false;
  });
  try {
    await redisClient.connect();
    redisReady = true;
    console.log("[redis] bağlantı başarılı");
  } catch (err) {
    console.error(`[redis] ilk bağlantı başarısız: ${err.message}`);
  }
}
initRedis();

// ── Sağlık kontrolü ────────────────────────────────────────────
app.get("/health", (req, res) => {
  res.status(200).json({
    status: "ok",
    service: "odeme-bot",
    redis: redisReady,
    timestamp: new Date().toISOString(),
  });
});

// ── odeme_bot webhook ──────────────────────────────────────────
app.post("/webhook/odeme", async (req, res) => {
  try {
    const update = req.body;
    console.log(`[odeme] update_id=${update.update_id}`);

    if (redisReady) {
      await redisClient.set(
        "odeme:last_update",
        JSON.stringify({ ts: Date.now(), update_id: update.update_id })
      );
    }

    // odeme_worker_v5.js içindeki işleme fonksiyonunu burada çağırın.
    // require("./odeme_worker_v5").handleUpdate(update, { botToken: ODEME_BOT_TOKEN });

    res.sendStatus(200);
  } catch (err) {
    console.error(`[odeme] hata: ${err.message}`);
    res.sendStatus(200); // Telegram'ın tekrar denemesini önlemek için 200 dön, hatayı logla
  }
});

// ── Vip_iesrabot webhook (AYRI PATH — çakışma çözümü) ──────────
app.post("/webhook/vip", async (req, res) => {
  try {
    const update = req.body;
    console.log(`[vip] update_id=${update.update_id}`);

    if (redisReady) {
      await redisClient.set(
        "vip:last_update",
        JSON.stringify({ ts: Date.now(), update_id: update.update_id })
      );
    }

    // VIP botuna özel işleme mantığı buraya (odeme_worker_v5.js'den ayrıştırılmış).

    res.sendStatus(200);
  } catch (err) {
    console.error(`[vip] hata: ${err.message}`);
    res.sendStatus(200);
  }
});

app.listen(PORT, () => {
  console.log(`odeme-bot servisi ${PORT} portunda dinliyor`);
});
