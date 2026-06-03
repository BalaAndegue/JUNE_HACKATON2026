# Lancer & déployer DataPipe

Stack : **backend** (Flask, :5000) + **frontend** (Next.js, :3000) + **bot Telegram** (optionnel).
Base **SQLite**. Branche : **`blhack`** (sur les dépôts BalaAndegue et Delmat).

---

## 🖥️ Lancement en LOCAL (développement)

**Terminal A — backend** (mono-process : nécessaire pour le SSE temps réel) :
```bash
cd datapipe_backend
python -m venv .venv && source .venv/bin/activate     # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
cp .env.example .env        # y mettre GROQ_API_KEY (+ TELEGRAM_BOT_TOKEN si bot)
python run.py               # http://localhost:5000  (Swagger: /apidocs)
```

**Terminal B — frontend** :
```bash
cd datapipe-app
npm install
npm run dev                 # http://localhost:3000  -> /demo pour entrer
```

**Terminal C — bot Telegram (optionnel, sans URL publique)** :
```bash
cd datapipe_backend && source .venv/bin/activate
python scripts/telegram_bot.py     # poll Telegram -> webhook local
```
Puis écris à ton bot (@Data_Pipe_Bot) : « masque les clients puis exécute ».
Garde l'éditeur web ouvert sur le pipeline → il se redessine en direct.

---

## ☁️ Déploiement en PRODUCTION (VPS, conteneurs)

Stack conteneurisée : backend (gunicorn) + frontend (standalone) via Docker.

## Prérequis sur le VPS
- Docker + Docker Compose v2 (`docker compose version`)
- Les ports **3000** et **5000** ouverts (firewall / security group)

```bash
# Ubuntu — installer Docker (si absent)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # puis reconnecte-toi
```

## Déploiement (manuel, fiable)

```bash
git clone https://github.com/BalaAndegue/JUNE_HACKATON2026.git
cd JUNE_HACKATON2026
git checkout blhack

# 1) créer le .env backend (clés IA + secrets)
cp datapipe_backend/.env.example datapipe_backend/.env
nano datapipe_backend/.env      # mettre GROQ_API_KEY=... + SECRET_KEY/JWT_SECRET_KEY forts

# 2) build + lancement
docker compose up -d --build

# 3) vérifier
docker compose ps
curl http://localhost:5000/api/v1/health
```

Accès :
- App : `http://<IP_DU_VPS>:3000`  → page `/demo` pour entrer directement
- API : `http://<IP_DU_VPS>:5000` (Swagger : `/apidocs`)

> Le frontend déduit l'URL de l'API depuis l'hôte courant (`<hôte>:5000`), donc rien à
> configurer tant que le port 5000 est joignable.

## Commandes utiles
```bash
docker compose logs -f backend      # logs
docker compose restart backend
docker compose down                 # arrêter (les volumes/données restent)
docker compose up -d --build        # redéployer après un git pull
```

## Mettre à jour
```bash
git pull && docker compose up -d --build
```

## Option — un seul domaine + HTTPS (nginx)
Pour servir front + API derrière `https://ton-domaine.com` :
1. Installe nginx + certbot sur le VPS.
2. Reverse proxy : `/` → `localhost:3000`, `/api` → `localhost:5000`.
3. `certbot --nginx -d ton-domaine.com` pour le TLS.
> Dans ce cas, mets `NEXT_PUBLIC_API_URL=https://ton-domaine.com` au build du frontend
> (le code l'utilise si présent et non-localhost).

## CI/CD (optionnel)
`.github/workflows/deploy.yml` lance les **tests**, puis **build + push** des deux images
sur `ghcr.io`. Pour le déploiement automatique sur le VPS, dé-commente le job `deploy`
et ajoute les secrets repo : `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

## Production — checklist sécurité
- [ ] `SECRET_KEY` / `JWT_SECRET_KEY` forts dans `.env` (pas les valeurs par défaut)
- [ ] Restreindre le CORS au domaine (actuellement `*`) — `app/__init__.py`
- [ ] (Optionnel) PostgreSQL : `DATABASE_URL=postgresql://...` dans `.env` + `pip install psycopg2-binary`

## 🤖 Bot Telegram en production (webhook AUTOMATIQUE)
**Pas de curl, pas de poller.** Mets simplement dans `datapipe_backend/.env` :
```
TELEGRAM_BOT_TOKEN=...
PUBLIC_URL=https://TON-DOMAINE        # URL HTTPS publique du backend
TELEGRAM_WEBHOOK_SECRET=un-secret     # optionnel mais recommandé
FRONTEND_URL=https://TON-DOMAINE      # pour les liens éditeur dans le bot
```
Au démarrage, le backend **enregistre le webhook tout seul** (`setWebhook` + menu de commandes).
Le **webhook remplace le poller** → ne lance PAS `telegram_bot.py` en prod.

## 🔒 PROD avec HTTPS sur un seul domaine (nginx + Let's Encrypt)
Sert **tout** sur `https://TON-DOMAINE` (`/` → frontend, `/api` → backend, SSE compris).

Prérequis : un **nom de domaine** pointant (DNS A) vers l'IP du VPS, ports **80 et 443** ouverts.

```bash
git clone <repo> && cd <repo> && git checkout BACKEND
cp .env.example .env                       # -> DOMAIN=ton-domaine.com, CERTBOT_EMAIL=toi@ex.com
nano datapipe_backend/.env                 # PUBLIC_URL=https://ton-domaine.com  +  FRONTEND_URL=https://ton-domaine.com
sh nginx/init-letsencrypt.sh               # obtient le certificat puis lance toute la stack
```
- Au démarrage, le backend **enregistre le webhook Telegram tout seul** (PUBLIC_URL) — zéro poller.
- Le frontend est buildé avec `NEXT_PUBLIC_API_URL=https://ton-domaine.com` (appels API via nginx).
- Renouvellement TLS **automatique** (service `certbot`, toutes les 12h).

Mises à jour ensuite :
```bash
git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

> Sans domaine (IP seulement), reste en HTTP : `docker compose up -d --build` (ports 3000/5000).
