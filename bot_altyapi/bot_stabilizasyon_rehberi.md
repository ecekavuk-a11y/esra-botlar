# Malatya Esra Bot Sistemi — Stabilizasyon Rehberi

> Bu belge, mevcut Telegram bot sisteminin (odeme_bot, Vip_iesrabot, esra_arsiv_bot, react_bot, Cicisinibot) Cloudflare Workers + Render karışık altyapısından **Docker Compose tabanlı, tek bir VPS üzerinde çalışan production-grade altyapıya** taşınması için hazırlanmıştır.
>
> İlgili dosyalar: `docker-compose.yml`, `.env.example`, `nginx/`, `health-checker/health_checker.py`, `deploy.sh`

---

## İçindekiler

1. [Mevcut Sorunların Kök Neden Analizi](#1-mevcut-sorunların-kök-neden-analizi)
2. [Çözüm Mimarisi](#2-çözüm-mimarisi)
3. [Docker Compose Kurulum Adımları](#3-docker-compose-kurulum-adımları)
4. [Monitoring ve Uyarı Sistemi](#4-monitoring-ve-uyarı-sistemi)
5. [Sık Karşılaşılan Sorunlar ve Çözümleri](#5-sık-karşılaşılan-sorunlar-ve-çözümleri)
6. [VPS Gereksinimleri](#6-vps-gereksinimleri)
7. [Cloudflare Workers vs VPS Karşılaştırması](#7-cloudflare-workers-vs-vps-karşılaştırması)
8. [Kalan Riskler](#8-kalan-riskler)

---

## 1. Mevcut Sorunların Kök Neden Analizi

### 1.1 Çift webhook çakışması (odeme_bot ve Vip_iesrabot)

**Sorun:** `odeme_bot` (8907710571) ve `Vip_iesrabot` (8934662828) her ikisi de `https://odeme-bot.ecekavuk.workers.dev` adresine webhook olarak point ediyor.

**Kök neden:** Cloudflare Worker tek bir URL üzerinden çalışır ve gelen `update` payload'ında hangi botun token'ıyla çağrıldığı **URL'den ayırt edilemez** — sadece payload içeriğinden (chat_id, komutlar vb.) tahmin edilmeye çalışılıyor olabilir. Bu, iki botun mesajlarının aynı worker kodunda karışmasına, birinin diğerinin mantığını tetiklemesine yol açar.

**Docker çözümü:** Her bot artık kendi path'ine sahip: `/webhook/odeme` ve `/webhook/vip`. nginx bu path'lere göre doğru upstream servise yönlendirir, `server.js` içinde ayrı route'lar ayrı işlenir. `deploy.sh webhooks` komutu her botun webhook'unu doğru path'e set eder.

### 1.2 react_bot ölmüş

**Sorun:** `react_bot` (8655923137) hem webhook'a hem polling'e sahip değil; 33 bekleyen güncelleme (`pending_update_count`) birikmiş durumda.

**Kök neden:** Muhtemelen webhook silinmiş veya hiç kurulmamış, bot kodu da `getUpdates` ile polling yapmıyor — bot "askıda" kalmış.

**Docker çözümü:** `health-checker` servisi bu botu özel olarak izler; webhook yoksa ve `getUpdates` de çağrılmıyorsa admin'e "ölü bot" uyarısı gönderir. Kalıcı çözüm için ya bota webhook atanmalı (yeni bir servis eklenerek) ya da bot kalıcı olarak devre dışı bırakılıp Telegram'dan silinmeli. Bekleyen 33 mesajı temizlemek için `deploy.sh` size manuel `getUpdates?offset=-1` komutunu gösterir.

### 1.3 Video arşivi hızla tükeniyor

**Sorun:** 9 videoluk arşivde bazı videolar 4-5 kez kullanılmış, tükenme riski yüksek.

**Kök neden:** Yeni video eklenme hızı, paylaşım hızının (günde 3 kez × 3 kanal) altında kalıyor.

**Docker çözümü:** `arsiv-bot` servisi her paylaşımdan önce kalan video sayısını kontrol eder; `MIN_VIDEO_ESIK` (varsayılan 5) altına düşerse admin'e otomatik uyarı gönderir — böylece arşiv tükenmeden önce müdahale edilebilir.

### 1.4 State kayıpları (JSON dosyaları disk'te)

**Sorun:** Sandbox/servis restart olduğunda JSON dosyaları (örn. `video_arsiv.json`, kullanım sayaçları) sıfırlanıyor veya eski haline dönüyor.

**Kök neden:** Ephemeral (kalıcı olmayan) dosya sistemi kullanan platformlarda (Cloudflare Workers, bazı Render planları) yerel dosya değişiklikleri container yeniden başlatıldığında kaybolur.

**Docker çözümü:** `redis` servisi eklendi — `appendonly yes` ile kalıcı hale getirildi ve Docker named volume (`redis-data`) üzerinde saklanıyor. Uzun vadede kritik sayaçlar (video kullanım sayısı, üye durumu vb.) JSON dosyalarından Redis'e taşınmalı. `video_arsiv.json` gibi dosyalar da artık bind-mount ile host diskinde kalıcı tutuluyor (container silinse bile veri kaybolmaz).

### 1.5 Cloudflare Workers ücretsiz plan limiti (100k istek/gün)

**Sorun:** Limit aşıldığında worker istekleri reddediyor, bot fiilen ölüyor.

**Kök neden:** Ücretsiz Cloudflare Workers planı günlük 100.000 istekle sınırlı; reaksiyon botları, arşiv paylaşımları ve webhook trafiği birleştiğinde bu limit yoğun günlerde aşılabilir.

**Docker çözümü:** VPS üzerinde çalışan nginx + Node/Python servislerinde bu tür bir istek limiti yoktur (sadece sunucu kaynaklarıyla sınırlıdır). Detaylı karşılaştırma [Bölüm 7](#7-cloudflare-workers-vs-vps-karşılaştırması)'de.

### 1.6 VIP caption tekrarı

**Sorun:** VIP tanıtım metni birden fazla dosyada hardcoded (sabit kodlanmış) olarak tekrarlanıyor; her düzeltme ihtiyacında hepsi tek tek güncellenmesi gerekiyor.

**Kök neden:** Merkezi bir "caption/metin şablonu" servisi/modülü olmadığından her worker/script kendi kopyasını tutuyor.

**Docker çözümü:** `caption_motor.py` modülü `arsiv-bot` servisine dahil edildi ve tek kaynak (single source of truth) olarak kullanılmalı. Uzun vadede bu modül tüm servislerin import edebileceği paylaşılan bir kütüphane/paket haline getirilmeli (örn. dahili bir pip paketi veya paylaşılan volume).

### 1.7 Script timeout (reaction_onlineisra.py, 630s)

**Sorun:** Script 630 saniyede zaman aşımına uğradı; API çağrıları birbirini bloklamış.

**Kök neden:** Sıralı (senkron) API çağrıları + zaman aşımı sınırı olmayan HTTP istekleri, bir çağrı yavaş yanıt verdiğinde tüm script'i kilitliyor.

**Docker çözümü:** `reaction-bot` servisinde:
- Her HTTP çağrısına `HTTP_TIMEOUT_SECONDS` (varsayılan 25s) sınırı
- Tüm iş `subprocess.run(timeout=JOB_TIMEOUT_SECONDS)` (varsayılan 300s) ile sarılı — zaman aşımı olursa iş sonlandırılır, servis çökmez, sonraki saatlik çalışma bloklanmaz
- Kilit dosyası (`reaction_bot.lock`) ile aynı işin üst üste binmesi önlenir

### 1.8 Cron çakışması (abf04916 ve b738eb18, aynı saatte 06:37 UTC)

**Sorun:** İki farklı cron job aynı saatte tetiklenip Telegram API'ye eşzamanlı istek gönderiyor, rate limit'e (429 Too Many Requests) çarpıyor.

**Kök neden:** Perplexity cron'ları merkezi bir zamanlama koordinasyonuna sahip değil; farklı görevler bağımsız olarak benzer saatlere denk gelebiliyor.

**Docker çözümü:** Docker altyapısında her scheduler kendi container'ında **tek bir döngü** olarak çalışır ve saatler kasıtlı olarak ayrıştırılmıştır:
- `reaction-bot`: her saat `:00`
- `arsiv-bot`: günde 3 kez, `06:00`, `12:00`, `18:00` UTC
- `vip-manager`: günde 1 kez, `06:00` UTC

Aynı dakikada çakışma riski olan görevler (örn. reaction ve onlineisra) farklı dakikalara kaydırılmalı (bkz `reaction-bot/scheduler.py` içindeki not). Kilit dosyası mekanizması, olası çakışmalarda ikinci çalışmayı atlayarak rate limit riskini azaltır.

### 1.9 Versiyon karmaşası (odeme_worker v1-v5, arsiv_worker v1-v4)

**Sorun:** Hangi versiyonun production'da aktif olduğu belirsiz; eski versiyonlar hâlâ dosya sisteminde duruyor.

**Kök neden:** Versiyon kontrolü (git) yerine dosya adına sayı ekleyerek (`_v2`, `_v3`...) versiyonlama yapılmış; eski dosyalar temizlenmemiş.

**Docker çözümü:** `docker-compose.yml` içinde her servisin **hangi dosyayı çalıştırdığı açıkça ve tek bir yerde tanımlı** (örn. `odeme-bot/Dockerfile` sadece `odeme_worker_v5.js`'i kopyalar). Artık "hangi versiyon aktif?" sorusunun cevabı `docker-compose.yml` ve ilgili `Dockerfile`'a bakmaktan ibarettir. **Önerilir:** Bu altyapıyı bir git deposuna taşıyıp eski `_v1`–`_v4` dosyalarını `archive/` klasörüne kaldırın veya silin.

### 1.10 getUpdates 409 Conflict (yildiz_filtre_bot)

**Sorun:** Webhook aktifken aynı bot için `getUpdates` çağrılıyor, Telegram API bunu tek bir bot için iki farklı güncelleme alma yöntemi (webhook + polling) aynı anda kullanılamayacağından `409 Conflict` ile reddediyor.

**Kök neden:** Bot kodunun bir kısmı polling modunda (`getUpdates` döngüsü), bir kısmı webhook modunda tasarlanmış; ikisi birlikte deploy edilmiş.

**Docker çözümü:** `health_checker.py` her bot için bu deseni **aktif olarak tespit eder**: webhook URL'i varsa VE `getUpdates` çağrısı 409 Conflict dönüyorsa, admin'e "polling kodu kapatılmalı" uyarısı gönderir. Kalıcı çözüm: `yildiz_filtre_bot` kodundaki polling döngüsünü tamamen kaldırıp yalnızca webhook modunda çalıştırmak.

---

## 2. Çözüm Mimarisi

```
                          ┌─────────────────────┐
                          │   Telegram API       │
                          └─────────┬────────────┘
                                    │ webhook (HTTPS)
                                    ▼
                          ┌─────────────────────┐
                          │   nginx (443/80)     │  <- TLS termination, rate limit
                          └─────────┬────────────┘
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │  odeme-bot      │ │  arsiv-bot      │ │ (gelecek: cici) │
        │  /webhook/odeme │ │  /webhook/arsiv │ │                 │
        │  /webhook/vip   │ │  + scheduler    │ │                 │
        └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                 │                    │                    │
                 └──────────┬─────────┴──────────┬─────────┘
                            ▼                     ▼
                     ┌─────────────┐      ┌──────────────────┐
                     │   redis      │      │  reaction-bot     │
                     │  (state)     │      │  vip-manager       │
                     └─────────────┘      │  (saatlik/günlük   │
                                           │   scheduler)        │
                                           └─────────┬───────────┘
                                                      ▼
                                           ┌────────────────────┐
                                           │  health-checker      │
                                           │  (5 dk'da bir kontrol,│
                                           │   admin'e Telegram DM│
                                           │   + health_status.json)│
                                           └────────────────────┘
```

**Temel prensipler:**

- **Tek giriş noktası:** Tüm webhook trafiği nginx üzerinden geçer, path bazlı routing ile hangi botun hangi servise gideceği açıkça tanımlıdır.
- **Merkezi state:** Redis, JSON dosyalarının yerini kademeli olarak alır; container restart'larında veri kaybı riski ortadan kalkar.
- **İzole scheduler'lar:** Her periyodik görev kendi container'ında, kendi zaman tablosunda çalışır — çakışma riski azaltılmış, timeout korumalı.
- **Aktif sağlık izleme:** `health-checker` servisi hem Telegram API durumunu hem de cron heartbeat'lerini izler, sorunları admin'e otomatik bildirir.
- **Kaynak sınırları:** Her servis 256MB RAM / 0.5 CPU ile sınırlıdır — tek bir servisin sunucuyu tüketmesi önlenir.

---

## 3. Docker Compose Kurulum Adımları

### 3.1 Ön koşullar

- Ubuntu 22.04 (veya benzeri) VPS, min. 2GB RAM (bkz [Bölüm 6](#6-vps-gereksinimleri))
- Bir domain adı (webhook TLS gerektirdiği için — Telegram sadece HTTPS webhook kabul eder)
- Domain'in VPS IP'sine A kaydı ile yönlendirilmiş olması

### 3.2 Adım adım kurulum

```bash
# 1. Dosyaları VPS'e aktarın (örn. git clone veya scp)
scp -r bot_altyapi/ root@<VPS_IP>:/opt/esra-bot/
ssh root@<VPS_IP>
cd /opt/esra-bot

# 2. deploy.sh'ı çalıştırılabilir yapın
chmod +x deploy.sh

# 3. Tam otomatik kurulumu başlatın
./deploy.sh all
```

`deploy.sh all` şu adımları sırasıyla yapar:
1. Docker + Docker Compose kurulumu (yoksa)
2. UFW güvenlik duvarı (22, 80, 443 portları)
3. Swap alanı oluşturma (RAM azsa)
4. `.env` dosyasını `.env.example`'dan oluşturma ve doldurmanız için duraklama
5. nginx yapılandırmasında `${DOMAIN}` değişkenini gerçek domain ile değiştirme
6. `docker compose build && docker compose up -d`
7. İlk sağlık kontrolü çıktısını gösterme

### 3.3 TLS sertifikası

```bash
./deploy.sh tls
```

Bu adım `certbot` ile Let's Encrypt sertifikası alır. Sertifika alındıktan sonra `nginx/conf.d/bots.conf` dosyasına 443 portu ve sertifika yolları için bir `server` bloğu eklemeniz gerekir (şablon `bots.conf` içinde HTTP-01 doğrulama için `/.well-known/acme-challenge/` zaten hazırdır).

### 3.4 Webhook'ları set etme

```bash
./deploy.sh webhooks
```

Bu adım `.env` dosyasındaki `*_WEBHOOK_URL` değerlerini kullanarak her bot için `setWebhook` çağrısı yapar. **Kritik:** Bu adımdan sonra Cloudflare Worker'lardaki eski webhook kayıtları otomatik olarak geçersiz hale gelir (Telegram bir bot için yalnızca tek bir webhook URL'i tutar).

### 3.5 Servisleri kontrol etme

```bash
docker compose ps                      # servis durumları
docker compose logs -f                 # tüm loglar (canlı)
docker compose logs -f health-checker  # sadece sağlık kontrolcüsü
docker compose restart odeme-bot       # tek servis yeniden başlatma
```

---

## 4. Monitoring ve Uyarı Sistemi

`health-checker` servisi her `CHECK_INTERVAL_SECONDS` (varsayılan 300s = 5 dk) şu kontrolleri yapar:

| Kontrol | Eşik / Koşul | Aksiyon |
|---|---|---|
| `getWebhookInfo` başarısız | API hatası | Admin'e 🔴 kritik uyarı |
| `pending_update_count` | > 10 | Admin'e ⚠️ uyarı |
| `last_error_message` | Doluysa | Admin'e 🔴 kritik uyarı |
| Webhook URL beklenenden farklı | URL uyuşmazlığı | Admin'e ⚠️ uyarı |
| İki bot aynı webhook URL'inde | Çakışma tespiti | Admin'e 🔴 kritik uyarı |
| Webhook var + `getUpdates` 409 | Conflict deseni | Admin'e ⚠️ uyarı |
| Cron heartbeat yaşı | > `CRON_STALE_HOURS` (varsayılan 2 saat) | Admin'e ⚠️ uyarı |

**Rate limiting:** Aynı sorun için `ALERT_COOLDOWN_SECONDS` (varsayılan 1800s = 30 dk) içinde birden fazla mesaj gönderilmez — admin'in mesaj bombardımanına uğraması önlenir.

**Çıktı dosyası:** Her kontrol döngüsü sonunda `/home/user/workspace/cron_tracking/health_status.json` güncellenir (Docker'da `cron_tracking/` klasörü bu yola bağlanır — bkz `deploy.sh` içindeki `setup_cron_tracking` fonksiyonu). Örnek içerik:

```json
{
  "checked_at": "2026-07-12T10:05:00+00:00",
  "bots": {
    "odeme_bot": {"ok": true, "pending_update_count": 0, "last_error_message": null},
    "react_bot": {"ok": true, "url": "", "polling_check": {"ok": false, "conflict": false}}
  },
  "cron_heartbeats": {
    "reaction-bot (saatlik)": {"ok": true, "age_hours": 0.3},
    "arsiv-bot (günde 3x)": {"ok": true, "age_hours": 1.8},
    "vip-manager (günlük)": {"ok": true, "age_hours": 5.1}
  }
}
```

Bu dosya harici bir dashboard'a (örn. Notion, Grafana) beslenerek görselleştirilebilir.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

| Sorun | Olası Neden | Çözüm |
|---|---|---|
| Container sürekli restart oluyor (`Restarting`) | Healthcheck başarısız veya kod hatası | `docker compose logs <servis>` ile hata mesajını görün |
| Webhook set edilemiyor (`setWebhook` false dönüyor) | Domain'e henüz TLS sertifikası yok | Önce `./deploy.sh tls` çalıştırın |
| `pending_update_count` sürekli artıyor | Servis update'i işleyip 200 dönmüyor | nginx/servis loglarını kontrol edin, `proxy_read_timeout` yeterli mi bakın |
| Redis'e bağlanılamıyor | `REDIS_PASSWORD` .env'de boş/yanlış | `.env` dosyasındaki `REDIS_PASSWORD` değerini `redis://:` URL'sindekiyle eşleştirin |
| Video arşivi uyarısı sürekli geliyor | Yeni video eklenmemiş | Admin video yükleme akışını (`esra_arsiv_bot`) kullanarak arşive yeni video ekleyin |
| İki bot mesajları karışıyor | Webhook path'leri hâlâ eski (tekil) URL'e point ediyor | `./deploy.sh webhooks` ile path bazlı URL'leri yeniden set edin |
| Health-checker admin'e mesaj göndermiyor | `ADMIN_ALERT_BOT_TOKEN` / `ODEME_BOT_TOKEN` boş | `.env` dosyasında ilgili token'ı doldurun |
| `docker compose build` disk alanı hatası | Eski image'lar temizlenmemiş | `docker system prune -af` (dikkatli kullanın) |
| VPS RAM doluyor | Swap yok veya servis limitleri aşılıyor | `deploy.sh docker` swap kurar; `docker stats` ile kontrol edin |

---

## 6. VPS Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---|---|---|
| İşletim Sistemi | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| RAM | 2 GB | 4 GB |
| CPU | 2 vCPU | 2-4 vCPU |
| Disk | 20 GB SSD | 40 GB SSD |
| Swap | 2 GB (RAM azsa) | 2 GB |
| Ağ | Sabit IP, 80/443 açık | Sabit IP, 80/443 açık |

7 servis toplamda ~1.8GB RAM (256MB × 7) üst sınırına sahiptir; gerçek kullanım genelde bunun altındadır ancak 2GB RAM'lik bir VPS'te swap **zorunludur**. 4GB RAM önerilir çünkü Docker daemon, nginx buffer'ları ve build sırasında ek bellek gerekir.

**Önerilen sağlayıcılar** (mevcut `vps_docker_rehberi.md` dosyasından):

| Sağlayıcı | Plan | Fiyat | RAM | CPU |
|---|---|---|---|---|
| Hetzner | CAX11 | ~5€/ay | 4GB | 2 vCPU |
| DigitalOcean | Basic | $6/ay | 1GB | 1 vCPU (2GB'a yükseltin) |
| Contabo | VPS S | ~5€/ay | 8GB | 4 vCPU |

---

## 7. Cloudflare Workers vs VPS Karşılaştırması

| Kriter | Cloudflare Workers (ücretsiz) | VPS + Docker |
|---|---|---|
| Günlük istek limiti | 100.000 (aşılırsa bot ölür) | Sunucu kapasitesiyle sınırlı, pratikte limitsiz |
| State/kalıcılık | KV/Durable Objects ile ek ücret gerekir | Redis + disk, ek ücret yok |
| Cold start | Yok (edge'de her zaman hazır) | Yok (container her zaman çalışır durumda) |
| Uptime kontrolü | Cloudflare'e bağımlı | Tam kontrol (systemd + Docker restart policy) |
| Zamanlı görevler (cron) | Cloudflare Cron Triggers (sınırlı, ücretsizde kısıtlı) | Sınırsız, kod içinde `schedule` kütüphanesi |
| Debugging | Sınırlı log görünürlüğü | Tam log erişimi (`docker compose logs`) |
| Maliyet | Ücretsiz (limit dahilinde) / $5+/ay (Paid plan) | ~5-6€/ay sabit VPS maliyeti |
| Karmaşık iş mantığı (uzun süren, çoklu adım) | Worker CPU süresi limitli (10-50ms ücretsiz) | Sınırsız (kendi kaynağınız) |
| Ölçeklenebilirlik | Otomatik, global | Manuel (tek VPS'te sınırlı, ek VPS ile ölçeklenir) |

**Sonuç:** Şu anki sistemde tespit edilen 10 kök sorunun büyük çoğunluğu (webhook çakışması, state kaybı, timeout, cron çakışması) **platform kısıtlarından** kaynaklanıyor. VPS + Docker geçişi bu sınırları ortadan kaldırır ama işletim sorumluluğunu (güvenlik güncellemeleri, disk doluluğu, TLS yenileme) size verir. Trafik düşükse Cloudflare Workers yeterli olabilir; ancak mevcut ölçekte (5 bot + 9 cron + reaksiyon botları) VPS geçişi **önerilir**.

---

## 8. Kalan Riskler

Docker Compose altyapısına geçiş yukarıdaki 10 sorunun teknik altyapı kısmını çözer, ancak şu riskler devam eder ve operasyonel dikkat gerektirir:

1. **Tek VPS = tek nokta arızası (single point of failure).** VPS çökerse tüm botlar durur. Düşünülmesi gereken: otomatik yedek VPS veya en azından günlük yapılandırma yedeği.
2. **Redis kalıcılığı `appendonly` ile sağlanıyor ama VPS diski bozulursa veri kaybı riski var.** Düzenli Redis yedeği (`redis-cli --rdb` veya `BGSAVE` + off-site kopya) önerilir.
3. **Video arşivi hâlâ küçük (9 video).** Otomatik uyarı sistemi tükenmeyi haber verir ama içerik üretimi/yükleme insan müdahalesi gerektirir — bu otomatikleştirilemez.
4. **VIP caption tekrarı tam çözülmedi.** `caption_motor.py` merkezi hale getirildi ama tüm worker'ların (özellikle Node.js tarafındaki `odeme_worker_v5.js`) bu modülü kullanacak şekilde yeniden yazılması gerekiyor — bu bir kod refactor işi, sadece altyapı değişikliğiyle çözülmez.
5. **react_bot'un nihai kaderi belirlenmedi.** Bot şu an "izleniyor" durumda ama aktif hale getirilip getirilmeyeceği veya kalıcı olarak kapatılacağı iş kararına bağlı.
6. **Versiyon karmaşası (v1-v5) sadece "hangi dosya aktif" sorusuna cevap verdi.** Eski versiyonların git ile versiyonlanması ve `archive/` klasörüne taşınması hâlâ manuel bir iştir.
7. **Perplexity cron'ların 9 tanesinin de bu Docker altyapısına taşınıp taşınmayacağı netleşmedi.** Bu rehber sadece 3 ana scheduler'ı (arşiv, reaction, VIP) kapsıyor; dashboard, bot denetim, yedekleme, yıldız filtre, tekrar kontrol gibi görevler için ayrı servisler eklenmeli veya mevcut cron altyapısında bırakılmalı.
8. **Supabase bağımlılığı.** VIP üyelik verisi hâlâ harici Supabase'de; Supabase kesintisi `vip-manager` servisini etkiler — bu VPS geçişiyle çözülmeyen bir dış bağımlılıktır.
9. **TLS sertifikası otomatik yenileme henüz kurulmadı.** `certbot` cron/systemd timer ile otomatik yenileme (`certbot renew`) ayarlanmalı, aksi halde 90 gün sonra webhook'lar TLS hatasıyla düşer.
10. **Güvenlik sertleştirmesi (hardening) sınırlı.** Bu rehber temel UFW kurallarını kapsıyor; SSH anahtar tabanlı giriş zorunluluğu, fail2ban, düzenli `apt upgrade` otomasyonu gibi adımlar production için ayrıca yapılmalı.

---

*Bu belge `/home/user/workspace/bot_altyapi/` altındaki dosyalarla birlikte kullanılmak üzere hazırlanmıştır. Sorular veya güncellemeler için ilgili dosyaları (`docker-compose.yml`, `health-checker/health_checker.py`, `deploy.sh`) referans alın.*
