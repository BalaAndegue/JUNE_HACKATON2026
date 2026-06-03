# Déploiement DataPipe sur un VPS

Stack conteneurisée : **backend** (Flask + gunicorn, :5000) + **frontend** (Next.js standalone, :3000).
La base est **SQLite** (volume persistant). Aucune autre dépendance.

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
git checkout Blhack_full

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
