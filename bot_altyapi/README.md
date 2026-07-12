# Malatya Esra Bot Sistemi — Docker Altyapısı

Bu klasör, Malatya Esra Telegram bot sisteminin (odeme_bot, Vip_iesrabot, esra_arsiv_bot, react_bot, Cicisinibot) production-grade Docker Compose altyapısını içerir.

## Hızlı Başlangıç

```bash
cd bot_altyapi
chmod +x deploy.sh
./deploy.sh all
```

Detaylı kurulum, sorun giderme ve mimari açıklamalar için: **[bot_stabilizasyon_rehberi.md](./bot_stabilizasyon_rehberi.md)**

## Klasör Yapısı

```
bot_altyapi/
├── docker-compose.yml          # 7 servisli ana yapılandırma (redis, nginx, 4 bot servisi, health-checker)
├── .env.example                # Ortam değişkenleri şablonu (cp .env.example .env)
├── deploy.sh                   # Otomatik kurulum scripti
├── bot_stabilizasyon_rehberi.md # Kapsamlı Türkçe dokümantasyon
│
├── odeme-bot/                  # Node.js — odeme_worker_v5.js webhook handler
│   ├── Dockerfile
│   ├── server.js               # Express wrapper (/webhook/odeme, /webhook/vip)
│   ├── odeme_worker_v5.js
│   └── package.json
│
├── arsiv-bot/                  # Python — arşiv paylaşım + webhook
│   ├── Dockerfile
│   ├── scheduler.py            # Flask health + günde 3x paylaşım scheduler
│   ├── arsiv_bot.py
│   ├── arsiv_paylasim_cron.py
│   ├── caption_motor.py
│   └── requirements.txt
│
├── reaction-bot/                # Python — saatlik reaksiyon botu
│   ├── Dockerfile
│   ├── scheduler.py             # Timeout korumalı, kilit dosyalı saatlik scheduler
│   ├── story_reaction_bot.py
│   └── requirements.txt
│
├── vip-manager/                 # Python — günlük VIP erişim yönetimi
│   ├── Dockerfile
│   ├── scheduler.py
│   ├── vip_erisim_yonetici.py
│   └── requirements.txt
│
├── health-checker/               # Python — 5 dakikalık sağlık kontrolü
│   ├── Dockerfile
│   ├── health_checker.py
│   └── requirements.txt
│
├── nginx/                        # Reverse proxy + TLS termination
│   ├── nginx.conf
│   └── conf.d/bots.conf
│
├── data/                         # Kalıcı veri (video_arsiv.json vb.)
└── cron_tracking/                # Heartbeat + health_status.json (workspace ile bağlantılı)
```

## Servisler Özeti

| Servis | Dil | Görev | Zamanlama |
|---|---|---|---|
| `redis` | - | Merkezi state (JSON dosya yerine) | Sürekli |
| `nginx` | - | Reverse proxy, TLS, webhook routing | Sürekli |
| `odeme-bot` | Node.js | odeme_bot + Vip_iesrabot webhook | İstek bazlı |
| `arsiv-bot` | Python | Arşiv paylaşım + webhook | Günde 3x (06:00, 12:00, 18:00 UTC) |
| `reaction-bot` | Python | Story reaksiyon botu | Saatlik |
| `vip-manager` | Python | VIP üyelik yönetimi | Günlük (06:00 UTC) |
| `health-checker` | Python | Sağlık kontrolü + admin uyarısı | 5 dakikada bir |

## Çözülen Kök Sorunlar

Bu altyapı 10 tespit edilen kök sorunu ele alır — detaylar için `bot_stabilizasyon_rehberi.md` Bölüm 1:

1. Çift webhook çakışması → ayrı path'ler (`/webhook/odeme`, `/webhook/vip`)
2. react_bot ölü → health-checker aktif izleme + uyarı
3. Video arşivi tükenmesi → otomatik stok uyarısı
4. State kayıpları → Redis + kalıcı volume
5. Cloudflare limit → VPS'te limitsiz istek kapasitesi
6. VIP caption tekrarı → merkezi `caption_motor.py`
7. Script timeout → timeout korumalı subprocess + thread yönetimi
8. Cron çakışması → izole scheduler'lar + kilit dosyası
9. Versiyon karmaşası → tek dosya, açık Dockerfile referansı
10. getUpdates 409 Conflict → health-checker aktif tespit

## Önemli Notlar

- `.env` dosyasını **asla** git'e commit etmeyin.
- Webhook'lar HTTPS gerektirir — TLS kurulmadan `setWebhook` başarısız olur (`./deploy.sh tls`).
- `cron_tracking/` klasörü, health-checker çıktısının workspace'te de görülebilmesi için bağlanmıştır.
