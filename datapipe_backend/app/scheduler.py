"""
Planificateur léger en thread de fond.

Toutes les 30s, exécute les pipelines dont la planification (/schedule du bot) est due,
puis notifie le chat Telegram (résumé + alerte anomalies si seuil dépassé).
In-process : lancer le backend en 1 worker (cf. Dockerfile / run.py).
"""
import threading
import time
from datetime import datetime, timedelta

_started = False


def start_scheduler(app):
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            time.sleep(30)
            try:
                with app.app_context():
                    _tick()
            except Exception:  # noqa: BLE001
                app.logger.exception("scheduler tick error")

    threading.Thread(target=loop, daemon=True, name='dp-scheduler').start()
    app.logger.info("Scheduler démarré.")


def _tick():
    from .extensions import db
    from .models import BotChat, Run
    from .agent_exec import run_action
    from .routes.telegram import _send, _maybe_alert

    now = datetime.utcnow()
    due = BotChat.query.filter(
        BotChat.schedule_minutes.isnot(None),
        BotChat.next_run_at.isnot(None),
        BotChat.next_run_at <= now,
    ).all()
    for chat in due:
        if chat.current_pipeline_id:
            res = run_action(chat.user_id, 'run_pipeline', {}, chat.current_pipeline_id)
            _send(chat.chat_id, f"⏰ Exécution planifiée — {res.get('message', '')}")
            if res.get('run_id'):
                _maybe_alert(chat.chat_id, Run.query.get(res['run_id']))
        chat.next_run_at = now + timedelta(minutes=chat.schedule_minutes or 60)
        db.session.commit()
