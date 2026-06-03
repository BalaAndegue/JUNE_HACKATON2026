"""
Telegram bot integration — pilote DataPipe par chat.

Tu écris au bot -> /telegram/webhook -> l'agent (Groq) propose une action/plan ->
boutons inline « Confirmer / Annuler » -> exécution SERVEUR (agent_exec) -> réponse
au bot + event temps réel vers le web (l'éditeur redessine le pipeline en direct).

Le bot agit comme le compte démo, sur son pipeline courant.
"""
import json
import urllib.request

from flask import Blueprint, request, jsonify, current_app

from .ai import plan_from_message
from ..agent_exec import run_action
from ..models import User, Pipeline, OrgMember, Workspace

telegram_bp = Blueprint('telegram', __name__)

_PENDING = {}     # chat_id -> plan (action ou plan multi-étapes)
_CHAT_PIPE = {}   # chat_id -> pipeline_id courant


def _tg(method, payload):
    token = current_app.config.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        current_app.logger.warning("TELEGRAM_BOT_TOKEN absent — message non envoyé")
        return None
    try:
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/{method}',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        current_app.logger.error(f"Telegram API error: {e}")
        return None


def _send(chat_id, text, confirm=False):
    payload = {'chat_id': chat_id, 'text': text}
    if confirm:
        payload['reply_markup'] = {'inline_keyboard': [[
            {'text': '✅ Confirmer', 'callback_data': 'confirm'},
            {'text': '✖️ Annuler', 'callback_data': 'cancel'},
        ]]}
    return _tg('sendMessage', payload)


def _demo_context(chat_id):
    """(user_id, pipeline_id) sur lequel le bot opère — compte démo + pipeline courant."""
    user = User.query.filter_by(email='demo@bank.cm').first()
    if not user:
        return None, None
    pid = _CHAT_PIPE.get(chat_id)
    if not pid:
        member = OrgMember.query.filter_by(user_id=user.id).first()
        ws = Workspace.query.filter_by(org_id=member.org_id).first() if member else None
        pipe = (Pipeline.query.filter_by(workspace_id=ws.id).first() if ws else None)
        pid = pipe.id if pipe else None
        if pid:
            _CHAT_PIPE[chat_id] = pid
    return user.id, pid


def _pipeline_summary(pipeline):
    """Résumé lisible du pipeline : étapes ordonnées + lien éditeur."""
    from ..engine.executor import _topological_order
    nodes = {n.id: n for n in pipeline.nodes}
    if not nodes:
        return f"📊 {pipeline.name} — pipeline vide."
    order, _ = _topological_order(list(nodes.keys()), list(pipeline.edges))
    lines = [f"📊 {pipeline.name} — {len(nodes)} étape(s) :"]
    for i, nid in enumerate(order, 1):
        n = nodes[nid]
        lines.append(f"  {i}. {n.label or n.type_slug}  ·  {n.type_slug}")
    base = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
    lines.append(f"🔗 Éditeur : {base}/dashboard/pipelines/{pipeline.id}/editor")
    return '\n'.join(lines)


def _execute_plan(chat_id, user_id, pipeline_id, plan):
    steps = plan.get('steps') if plan.get('type') == 'plan' else [plan]
    lines = []
    for step in steps:
        res = run_action(user_id, step.get('action'), step.get('params'), pipeline_id)
        # un create_pipeline redéfinit le pipeline courant du chat
        if res.get('pipeline_id'):
            pipeline_id = res['pipeline_id']
            _CHAT_PIPE[chat_id] = pipeline_id
        lines.append(('✅ ' if res.get('ok') else '⚠️ ') + res.get('message', ''))
    # Résumé du pipeline après les actions
    pipe = Pipeline.query.get(pipeline_id) if pipeline_id else None
    if pipe:
        lines.append('')
        lines.append(_pipeline_summary(pipe))
    return '\n'.join(lines)


@telegram_bp.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    # Optional shared-secret check (set in Telegram setWebhook).
    secret = current_app.config.get('TELEGRAM_WEBHOOK_SECRET', '')
    if secret and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != secret:
        return jsonify({'ok': False}), 403

    update = request.get_json(silent=True) or {}

    # 1) Bouton confirmer / annuler
    cb = update.get('callback_query')
    if cb:
        chat_id = cb['message']['chat']['id']
        if cb.get('data') == 'confirm' and chat_id in _PENDING:
            plan = _PENDING.pop(chat_id)
            user_id, pid = _demo_context(chat_id)
            result = _execute_plan(chat_id, user_id, pid, plan)
            _send(chat_id, result or 'Action effectuée.')
        else:
            _PENDING.pop(chat_id, None)
            _send(chat_id, 'Annulé.')
        _tg('answerCallbackQuery', {'callback_query_id': cb['id']})
        return jsonify({'ok': True})

    # 2) Message texte
    msg = update.get('message') or {}
    text = (msg.get('text') or '').strip()
    chat_id = (msg.get('chat') or {}).get('id')
    if not text or chat_id is None:
        return jsonify({'ok': True})

    if text in ('/start', '/help'):
        _send(chat_id, "👋 Je pilote DataPipe. Dis-moi par ex. : « masque les clients », "
                       "« détecte les anomalies puis exécute ». Je propose, tu confirmes.")
        return jsonify({'ok': True})

    plan = plan_from_message(text)
    if plan.get('type') == 'reply':
        _send(chat_id, plan.get('message', '...'))
        return jsonify({'ok': True})

    _PENDING[chat_id] = plan
    if plan.get('type') == 'plan':
        steps = '\n'.join(f"{i+1}. {s.get('message') or s.get('action')}"
                          for i, s in enumerate(plan.get('steps', [])))
        _send(chat_id, f"🟣 Plan proposé :\n{steps}", confirm=True)
    else:
        warn = f"\n⚠️ {plan['warning']}" if plan.get('warning') else ''
        _send(chat_id, f"🟠 {plan.get('message', '')}{warn}", confirm=True)
    return jsonify({'ok': True})
