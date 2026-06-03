"""
Telegram bot — mode polling (test local, sans URL publique).

Relaie les messages Telegram vers le webhook local du backend. À utiliser quand
tu ne peux pas exposer le backend en HTTPS (en prod, configure plutôt le webhook).

  export TELEGRAM_BOT_TOKEN=123456:ABC...   (ou dans datapipe_backend/.env)
  python scripts/telegram_bot.py            (backend lancé sur :5000)
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    except Exception:
        pass
if not TOKEN:
    sys.exit("TELEGRAM_BOT_TOKEN manquant (export ou .env).")

API = f'https://api.telegram.org/bot{TOKEN}'
WEBHOOK = os.getenv('DATAPIPE_WEBHOOK', 'http://localhost:5000/api/v1/telegram/webhook')


def _get(url):
    with urllib.request.urlopen(url, timeout=70) as r:
        return json.loads(r.read())


def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except Exception as e:
        print("  webhook error:", e)
        return None


COMMANDS = [
    {"command": "login", "description": "Se connecter : /login <email> <mdp>"},
    {"command": "logout", "description": "Se déconnecter"},
    {"command": "whoami", "description": "Compte + pipeline courant"},
    {"command": "pipeline", "description": "Résumé du pipeline + lien éditeur"},
    {"command": "new", "description": "Créer un pipeline : /new <nom>"},
    {"command": "run", "description": "Exécuter le pipeline"},
    {"command": "preview", "description": "Aperçu des données (CSV)"},
    {"command": "audit", "description": "Rapport d'audit conformité (JSON)"},
    {"command": "anomalies", "description": "Transactions suspectes"},
    {"command": "chart", "description": "Graphique du résultat (image)"},
    {"command": "alert", "description": "Alerte si anomalies > n : /alert <n>"},
    {"command": "schedule", "description": "Exécution récurrente : /schedule <min>"},
    {"command": "unschedule", "description": "Annuler la planification"},
    {"command": "help", "description": "Aide"},
]


def _register_commands():
    """Affiche le menu « / » dans Telegram."""
    try:
        _post(f'{API}/setMyCommands', {'commands': COMMANDS})
        print("   Menu de commandes enregistré.")
    except Exception:
        pass


def main():
    print(f"🤖 Bot en polling. Webhook local: {WEBHOOK}")
    _register_commands()
    print("   Écris à ton bot sur Telegram (/start).")
    offset = 0
    while True:
        try:
            data = _get(f'{API}/getUpdates?timeout=60&offset={offset}')
            for upd in data.get('result', []):
                offset = upd['update_id'] + 1
                txt = (upd.get('message') or {}).get('text')
                if txt:
                    print(f"→ {txt}")
                _post(WEBHOOK, upd)   # le backend traite + répond directement à Telegram
        except Exception as e:
            print("poll error:", e)
            time.sleep(3)


if __name__ == '__main__':
    main()
