# TLS Setup Guide — Caddy Reverse Proxy

## Status: READY TO DEPLOY (needs domain)

---

## Prerequisites

1. **A domain** pointed at `77.42.40.146` (A record) and/or `2a01:4f9:c014:6571::1` (AAAA record)
   - Example: `jarvis.yourdomain.com`
   - Free options: Cloudflare, Namecheap, or use a subdomain of existing domain

2. **Ports 80 + 443 free** — currently used by nginx
   - Stop nginx: `docker stop jarvismax-nginx-1`
   - Or keep nginx and add Certbot (see Option B below)

---

## Option A: Replace nginx with Caddy (RECOMMENDED)

### 1. Add to docker-compose.yml:

```yaml
  caddy:
    image: caddy:2-alpine
    container_name: jarvis_caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - jarvis_net
    depends_on:
      - jarvis_core
```

Add volumes:
```yaml
volumes:
  caddy_data:
  caddy_config:
```

### 2. Create Caddyfile:

```
jarvis.yourdomain.com {
    # API + static
    reverse_proxy jarvis_core:8000

    # WebSocket
    @websocket {
        header Connection *upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websocket jarvis_core:8000
}
```

### 3. Remove nginx from docker-compose.yml

### 4. Deploy:
```bash
docker compose up -d caddy
```

Caddy auto-obtains Let's Encrypt certificate. Zero config.

### 5. Update Flutter `api_config.dart`:
```dart
static const String _prodBaseUrl = 'https://jarvis.yourdomain.com';
static const String _prodWsUrl = 'wss://jarvis.yourdomain.com/ws/stream';
```

---

## Option B: Add Certbot to existing nginx

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d jarvis.yourdomain.com
```

Then update nginx conf to use the certificate paths.

---

## Action Required

1. Get a domain (or subdomain)
2. Point DNS to `77.42.40.146`
3. Tell me the domain name
4. I'll deploy Caddy automatically
