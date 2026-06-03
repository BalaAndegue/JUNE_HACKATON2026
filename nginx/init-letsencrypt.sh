#!/bin/sh
# Obtient le premier certificat Let's Encrypt puis démarre la stack en HTTPS.
# Usage (sur le VPS, à la racine du projet, après avoir rempli .env) :
#   sh nginx/init-letsencrypt.sh
set -e
. ./.env
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
CONF=/etc/letsencrypt/live/$DOMAIN

echo "1/4 Cert temporaire (pour que nginx démarre)…"
$COMPOSE run --rm --entrypoint "\
  sh -c 'mkdir -p $CONF && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout $CONF/privkey.pem -out $CONF/fullchain.pem -subj /CN=$DOMAIN'" certbot

echo "2/4 Démarrage de nginx + services…"
$COMPOSE up -d --build

echo "3/4 Demande du vrai certificat…"
$COMPOSE run --rm --entrypoint "\
  sh -c 'rm -rf /etc/letsencrypt/live/$DOMAIN /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf; \
  certbot certonly --webroot -w /var/www/certbot -d $DOMAIN \
    --email $CERTBOT_EMAIL --agree-tos --no-eff-email --non-interactive'" certbot

echo "4/4 Rechargement de nginx…"
$COMPOSE exec nginx nginx -s reload
echo "✅ HTTPS prêt : https://$DOMAIN"
