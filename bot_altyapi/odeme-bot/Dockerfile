# ──────────────────────────────────────────────────────────────
# odeme-bot — Node.js webhook handler (odeme_worker_v5.js)
# ──────────────────────────────────────────────────────────────
FROM node:20-alpine

# wget healthcheck için gerekli (alpine'de busybox wget zaten var, ama emin olalım)
RUN apk add --no-cache wget tini

WORKDIR /app

# Bağımlılıkları önce kopyala (layer cache verimliliği)
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# Uygulama kodu
COPY server.js ./
COPY odeme_worker_v5.js ./

# root olmayan kullanıcı ile çalıştır
RUN addgroup -S botgrp && adduser -S botuser -G botgrp
USER botuser

EXPOSE 3001

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "server.js"]
