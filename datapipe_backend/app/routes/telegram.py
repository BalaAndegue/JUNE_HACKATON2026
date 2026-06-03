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
from ..agent_exec import run_action, ingest_file
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


def _download_telegram_file(file_id):
    """Télécharge le contenu d'un fichier Telegram (getFile -> file API)."""
    token = current_app.config.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        return None, None
    info = _tg('getFile', {'file_id': file_id})
    if not info or not info.get('ok'):
        return None, None
    file_path = info['result']['file_path']
    try:
        url = f'https://api.telegram.org/file/bot{token}/{file_path}'
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.read(), file_path
    except Exception as e:  # noqa: BLE001
        current_app.logger.error(f"Telegram download error: {e}")
        return None, None


def _send_document(chat_id, filename, content, caption='', mime='text/csv'):
    """Envoie un fichier en pièce jointe (sendDocument, multipart)."""
    token = current_app.config.get('TELEGRAM_BOT_TOKEN', '')
    if not token:
        return None
    boundary = 'dpBoundary7MA4YWxkTrZu0gW'
    body = b''
    for k, v in {'chat_id': str(chat_id), 'caption': caption[:1000]}.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n').encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
             f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode()
    body += (content if isinstance(content, bytes) else content.encode()) + f'\r\n--{boundary}--\r\n'.encode()
    try:
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendDocument', data=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        current_app.logger.error(f"Telegram sendDocument error: {e}")
        return None


def _latest_run(pipeline):
    from ..models import Run
    return (Run.query.filter_by(pipeline_id=pipeline.id)
            .order_by(Run.started_at.desc()).first())


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

    msg = update.get('message') or {}
    chat_id = (msg.get('chat') or {}).get('id')

    # 2) Document (CSV/JSON envoyé dans Telegram) -> import + source du pipeline
    doc = msg.get('document')
    if doc and chat_id is not None:
        fname = doc.get('file_name') or 'upload.csv'
        ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
        if ext not in ('csv', 'json', 'txt'):
            _send(chat_id, "Format non supporté. Envoie un fichier .csv ou .json.")
            return jsonify({'ok': True})
        content, _ = _download_telegram_file(doc.get('file_id'))
        if not content:
            _send(chat_id, "Téléchargement du fichier impossible.")
            return jsonify({'ok': True})
        user_id, pid = _demo_context(chat_id)
        f = ingest_file(user_id, fname, content)
        if not f:
            _send(chat_id, "Import impossible (workspace introuvable).")
            return jsonify({'ok': True})
        node_type = 'json_reader' if ext == 'json' else 'csv_reader'
        run_action(user_id, 'add_node',
                   {'node_type': node_type, 'label': fname, 'config': {'file_id': f.id}}, pid)
        pipe = Pipeline.query.get(pid)
        summary = ('\n\n' + _pipeline_summary(pipe)) if pipe else ''
        _send(chat_id, f"📥 « {fname} » importé — {f.rows_count} lignes, "
                       f"{f.columns_count} colonnes. Ajouté comme source.{summary}")
        return jsonify({'ok': True})

    # 3) Message texte
    text = (msg.get('text') or '').strip()
    if not text or chat_id is None:
        return jsonify({'ok': True})

    if text.startswith('/'):
        user_id, pid = _demo_context(chat_id)
        pipe = Pipeline.query.get(pid) if pid else None
        cmd = text.split()[0].lower()
        arg = text[len(cmd):].strip()

        if cmd in ('/start', '/help'):
            _send(chat_id, "👋 Je pilote DataPipe.\n"
                           "Commandes : /pipeline · /run · /new <nom> · /preview · /audit\n"
                           "Ou écris en clair : « masque les clients puis exécute ».\n"
                           "Tu peux aussi m'envoyer un fichier CSV/JSON.")
        elif cmd == '/pipeline':
            _send(chat_id, _pipeline_summary(pipe) if pipe else "Aucun pipeline courant.")
        elif cmd == '/new':
            res = run_action(user_id, 'create_pipeline', {'name': arg or 'Nouveau pipeline'})
            if res.get('pipeline_id'):
                _CHAT_PIPE[chat_id] = res['pipeline_id']
            _send(chat_id, res.get('message', ''))
        elif cmd == '/run':
            res = run_action(user_id, 'run_pipeline', {}, pid)
            pipe = Pipeline.query.get(pid)
            _send(chat_id, res.get('message', '') + (('\n\n' + _pipeline_summary(pipe)) if pipe else ''))
        elif cmd == '/preview':
            run = _latest_run(pipe) if pipe else None
            if not run or not run.node_results:
                _send(chat_id, "Exécute d'abord le pipeline (/run).")
                return jsonify({'ok': True})
            nid = list(run.node_results.keys())[-1]
            rows = run.node_results[nid].get('output_preview', [])
            if not rows:
                _send(chat_id, "Aucune donnée en sortie.")
                return jsonify({'ok': True})
            import csv as _csv, io as _io
            buf = _io.StringIO()
            w = _csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
            _send_document(chat_id, 'apercu.csv', buf.getvalue(),
                           caption=f"Aperçu — {len(rows)} ligne(s)")
        elif cmd == '/audit':
            run = _latest_run(pipe) if pipe else None
            if not run:
                _send(chat_id, "Exécute d'abord le pipeline (/run).")
                return jsonify({'ok': True})
            from ..agent_exec import build_audit_report
            rep = build_audit_report(run, pipe)
            _send_document(chat_id, 'rapport_audit.json',
                           json.dumps(rep, indent=2, ensure_ascii=False),
                           caption="Rapport d'audit conformité", mime='application/json')
        else:
            _send(chat_id, "Commande inconnue. Tape /help")
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
