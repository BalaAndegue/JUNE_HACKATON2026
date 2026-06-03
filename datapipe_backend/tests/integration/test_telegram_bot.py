"""Bot Telegram : multi-utilisateurs (/login) + seuil d'alerte (/alert)."""
import json
from tests.conftest import post_json


def _wh(client, payload):
    return client.post('/api/v1/telegram/webhook', data=json.dumps(payload),
                       content_type='application/json')


def test_login_links_chat_to_user(client, registered_user):
    from app.models import BotChat
    chat_id = 4242
    _wh(client, {'update_id': 1, 'message': {'message_id': 1,
        'chat': {'id': chat_id}, 'text': 'test@datapipe.io'}})  # warmup ensure_chat
    r = _wh(client, {'update_id': 2, 'message': {'message_id': 2, 'chat': {'id': chat_id},
        'text': '/login test@datapipe.io Hackaton2026!'}})
    assert r.status_code == 200
    chat = BotChat.query.get(str(chat_id))
    assert chat is not None
    assert chat.user_id == registered_user['user']['id']


def test_alert_threshold_set(client):
    from app.models import BotChat
    chat_id = 4343
    _wh(client, {'update_id': 3, 'message': {'message_id': 3, 'chat': {'id': chat_id},
        'text': '/alert 3'}})
    chat = BotChat.query.get(str(chat_id))
    assert chat is not None and chat.anomaly_threshold == 3
