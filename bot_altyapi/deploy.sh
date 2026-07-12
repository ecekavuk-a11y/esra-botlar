#!/usr/bin/env bash
########################################################################
# deploy.sh — Malatya Esra Bot Sistemi Otomatik Kurulum Scripti
#
# Kullanım:
#   chmod +x deploy.sh
#   ./deploy.sh                # tam kurulum (Docker + .env kontrolü + start + webhook + sağlık)
#   ./deploy.sh docker         # sadece Docker/Compose kurulumu
#   ./deploy.sh webhooks       # sadece webhook'ları set et
#   ./deploy.sh up             # servisleri build edip başlat
#   ./deploy.sh health         # ilk sağlık kontrolünü çalıştır
#   ./deploy.sh tls            # Let's Encrypt TLS sertifikası al
#
# Gereksinimler: Ubuntu 22.04 (veya benzeri systemd tabanlı Linux), root/sudo
########################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Renkli çıktı yardımcıları ────────────────────────────────────────
c_green() { echo -e "\033[32m$*\033[0m"; }
c_yellow() { echo -e "\033[33m$*\033[0m"; }
c_red() { echo -e "\033[31m$*\033[0m"; }
c_blue() { echo -e "\033[34m$*\033[0m"; }

# ── 1. Docker ve Docker Compose kurulumu ─────────────────────────────
install_docker() {
    c_blue "==> Docker kurulumu kontrol ediliyor..."
    if command -v docker &>/dev/null; then
        c_green "Docker zaten kurulu: $(docker --version)"
    else
        c_yellow "Docker kurulmamış, kuruluyor..."
        curl -fsSL https://get.docker.com | sh
        sudo systemctl enable docker
        sudo systemctl start docker
        c_green "Docker kuruldu."
    fi

    if docker compose version &>/dev/null; then
        c_green "Docker Compose zaten kurulu: $(docker compose version)"
    else
        c_yellow "Docker Compose plugin kuruluyor..."
        sudo apt-get update -y
        sudo apt-get install -y docker-compose-plugin
        c_green "Docker Compose kuruldu."
    fi

    # Kullanıcıyı docker grubuna ekle (sudo'suz docker komutu için)
    if ! groups "$USER" | grep -q docker; then
        c_yellow "Kullanıcı docker grubuna ekleniyor (yeniden login gerekebilir)..."
        sudo usermod -aG docker "$USER" || true
    fi

    # Güvenlik duvarı
    if command -v ufw &>/dev/null; then
        c_blue "==> UFW güvenlik duvarı ayarlanıyor (22, 80, 443)..."
        sudo ufw allow 22/tcp || true
        sudo ufw allow 80/tcp || true
        sudo ufw allow 443/tcp || true
        sudo ufw --force enable || true
    fi

    # Swap kontrolü (min 2GB RAM VPS için önemli)
    if [ "$(swapon --show | wc -l)" -eq 0 ]; then
        c_yellow "Swap alanı bulunamadı, 2GB swap oluşturuluyor..."
        sudo fallocate -l 2G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        if ! grep -q "/swapfile" /etc/fstab; then
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        fi
        c_green "Swap alanı oluşturuldu."
    else
        c_green "Swap alanı zaten mevcut."
    fi
}

# ── 2. .env dosyası oluşturma rehberi ────────────────────────────────
setup_env() {
    c_blue "==> .env dosyası kontrol ediliyor..."
    if [ -f .env ]; then
        c_green ".env dosyası zaten mevcut, atlanıyor."
        return
    fi

    cp .env.example .env
    c_yellow "────────────────────────────────────────────────────────────"
    c_yellow " .env dosyası .env.example'dan oluşturuldu."
    c_yellow " Devam etmeden önce AŞAĞIDAKİ ALANLARI DOLDURMANIZ GEREKİYOR:"
    c_yellow "────────────────────────────────────────────────────────────"
    echo "   nano $SCRIPT_DIR/.env"
    echo
    echo "   Doldurulması gereken kritik alanlar:"
    echo "     - ODEME_BOT_TOKEN, VIP_BOT_TOKEN, ARSIV_BOT_TOKEN, REACT_BOT_TOKEN, CICI_BOT_TOKEN"
    echo "     - DOMAIN (kendi alan adınız, örn: bot.esrabal.com)"
    echo "     - SUPABASE_URL, SUPABASE_KEY"
    echo "     - REDIS_PASSWORD (güçlü bir şifre üretin: openssl rand -hex 24)"
    echo "     - CERTBOT_EMAIL"
    echo
    read -rp "Değerleri doldurduktan sonra ENTER'a basın (devam etmek için)... " _
}

# ── 3. cron_tracking klasörünü workspace ile eşleştir ────────────────
setup_cron_tracking() {
    c_blue "==> cron_tracking dizini bağlantısı kuruluyor..."
    WORKSPACE_CRON="/home/user/workspace/cron_tracking"
    LOCAL_CRON="$SCRIPT_DIR/cron_tracking"

    if [ -d "$WORKSPACE_CRON" ] && [ "$WORKSPACE_CRON" != "$LOCAL_CRON" ]; then
        c_yellow "Workspace ortamı tespit edildi, health_status.json workspace'e yazılacak şekilde bağlanıyor."
        rm -rf "$LOCAL_CRON"
        ln -s "$WORKSPACE_CRON" "$LOCAL_CRON"
    else
        mkdir -p "$LOCAL_CRON"
    fi
    c_green "cron_tracking hazır: $LOCAL_CRON"
}

# ── 4. Webhook'ları doğru URL'e set etme ─────────────────────────────
set_webhooks() {
    c_blue "==> Telegram webhook'ları ayarlanıyor..."
    # shellcheck disable=SC1091
    source .env

    set_one_webhook() {
        local bot_name="$1" token="$2" url="$3"
        if [ -z "$token" ] || [[ "$token" == *"<"* ]]; then
            c_yellow "  [$bot_name] token tanımlı değil, atlanıyor."
            return
        fi
        if [ -z "$url" ]; then
            c_yellow "  [$bot_name] webhook URL tanımlı değil, atlanıyor (kasıtlı olabilir - örn. react_bot)."
            return
        fi
        resp=$(curl -s -X POST "https://api.telegram.org/bot${token}/setWebhook" \
            -d "url=${url}" -d "drop_pending_updates=false" \
            -d "allowed_updates=[\"message\",\"callback_query\",\"channel_post\"]")
        ok=$(echo "$resp" | grep -o '"ok":true' || true)
        if [ -n "$ok" ]; then
            c_green "  [$bot_name] webhook ayarlandı -> $url"
        else
            c_red "  [$bot_name] webhook ayarlanamadı: $resp"
        fi
    }

    # ÖNEMLİ: odeme_bot ve Vip_iesrabot artık AYRI path'lere sahip.
    # Bu, çift webhook çakışması kök sorununu çözer.
    set_one_webhook "odeme_bot" "${ODEME_BOT_TOKEN:-}" "${ODEME_BOT_WEBHOOK_URL:-}"
    set_one_webhook "Vip_iesrabot" "${VIP_BOT_TOKEN:-}" "${VIP_BOT_WEBHOOK_URL:-}"
    set_one_webhook "esra_arsiv_bot" "${ARSIV_BOT_TOKEN:-}" "${ARSIV_BOT_WEBHOOK_URL:-}"
    set_one_webhook "Cicisinibot" "${CICI_BOT_TOKEN:-}" "${CICI_BOT_WEBHOOK_URL:-}"

    # react_bot: webhook set etme — bilinçli olarak devre dışı.
    # Eğer bu botu yeniden aktive etmek istiyorsanız, önce REACT_BOT_WEBHOOK_URL
    # ekleyin ve aşağıdaki satırı açın:
    # set_one_webhook "react_bot" "${REACT_BOT_TOKEN:-}" "${REACT_BOT_WEBHOOK_URL:-}"
    if [ -n "${REACT_BOT_TOKEN:-}" ] && [[ "${REACT_BOT_TOKEN}" != *"<"* ]]; then
        c_yellow "  [react_bot] Bu bot ÖLÜ durumda (33 bekleyen mesaj, webhook/polling yok)."
        c_yellow "  Bekleyen mesajları temizlemek isterseniz aşağıdaki komutu MANUEL çalıştırın:"
        echo "    curl -s \"https://api.telegram.org/bot${REACT_BOT_TOKEN}/getUpdates?offset=-1\""
    fi
}

# ── 5. nginx conf içindeki ${DOMAIN} değişkenini işleme ──────────────
render_nginx_conf() {
    c_blue "==> nginx yapılandırması DOMAIN değişkeni ile oluşturuluyor..."
    # shellcheck disable=SC1091
    source .env
    if [ -z "${DOMAIN:-}" ]; then
        c_red "DOMAIN tanımlı değil, .env dosyasını kontrol edin."
        exit 1
    fi
    export DOMAIN
    envsubst '${DOMAIN}' < nginx/conf.d/bots.conf > nginx/conf.d/bots.conf.rendered
    mv nginx/conf.d/bots.conf.rendered nginx/conf.d/bots.conf
    c_green "nginx yapılandırması güncellendi: DOMAIN=${DOMAIN}"
}

# ── 6. TLS sertifikası (Let's Encrypt / certbot) ─────────────────────
setup_tls() {
    c_blue "==> TLS sertifikası kuruluyor (certbot)..."
    source .env
    if ! command -v certbot &>/dev/null; then
        sudo apt-get update -y
        sudo apt-get install -y certbot python3-certbot-nginx
    fi
    c_yellow "certbot standalone modda çalıştırılacak, nginx container'ının 80 portunu"
    c_yellow "geçici olarak durdurmanız gerekebilir. Detaylar için bot_stabilizasyon_rehberi.md."
    sudo certbot certonly --standalone -d "${DOMAIN}" -m "${CERTBOT_EMAIL}" --agree-tos --non-interactive || {
        c_red "certbot başarısız oldu. Manuel kurulum için rehbere bakın."
    }
}

# ── 7. Servisleri build edip başlatma ────────────────────────────────
start_services() {
    c_blue "==> Docker servisleri build ediliyor ve başlatılıyor..."
    docker compose build
    docker compose up -d
    c_green "Tüm servisler başlatıldı."
    docker compose ps
}

# ── 8. İlk sağlık kontrolü ────────────────────────────────────────────
run_health_check() {
    c_blue "==> İlk sağlık kontrolü çalıştırılıyor..."
    sleep 10
    docker compose ps
    echo
    c_blue "health-checker logları (son 30 satır):"
    docker compose logs --tail=30 health-checker
    echo
    if [ -f cron_tracking/health_status.json ]; then
        c_green "health_status.json bulundu:"
        cat cron_tracking/health_status.json
    else
        c_yellow "health_status.json henüz oluşmadı, birkaç dakika sonra tekrar kontrol edin:"
        echo "   cat $SCRIPT_DIR/cron_tracking/health_status.json"
    fi
}

# ── Ana akış ──────────────────────────────────────────────────────────
main() {
    case "${1:-all}" in
        docker)
            install_docker
            ;;
        env)
            setup_env
            ;;
        webhooks)
            set_webhooks
            ;;
        nginx)
            render_nginx_conf
            ;;
        tls)
            setup_tls
            ;;
        up)
            start_services
            ;;
        health)
            run_health_check
            ;;
        all)
            c_blue "########################################################"
            c_blue "  Malatya Esra Bot Sistemi — Tam Kurulum"
            c_blue "########################################################"
            install_docker
            setup_env
            setup_cron_tracking
            render_nginx_conf
            start_services
            c_yellow "TLS sertifikası kurmak için: ./deploy.sh tls"
            c_yellow "Webhook'ları set etmek için (DOMAIN + TLS hazır olduktan sonra): ./deploy.sh webhooks"
            run_health_check
            c_green "########################################################"
            c_green "  Kurulum tamamlandı!"
            c_green "  Sonraki adımlar:"
            c_green "    1. ./deploy.sh tls        (TLS sertifikası al)"
            c_green "    2. ./deploy.sh webhooks    (webhook'ları set et)"
            c_green "    3. docker compose logs -f  (canlı log takibi)"
            c_green "########################################################"
            ;;
        *)
            echo "Kullanım: $0 [docker|env|webhooks|nginx|tls|up|health|all]"
            exit 1
            ;;
    esac
}

main "$@"
