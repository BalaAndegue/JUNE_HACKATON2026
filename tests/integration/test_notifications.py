"""Tests d'intégration — Notifications & alertes."""
from tests.conftest import post_json, patch_json


def test_create_email_alert_requires_recipient(client, auth_headers):
    resp = post_json(client, '/api/v1/alerts', {
        'name': 'Alerte email',
        'condition': 'run.status == error',
        'channel': 'email',
    }, headers=auth_headers)

    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'Email alerts require at least one recipient'


def test_test_email_alert_requires_mail_configuration(client, auth_headers):
    create_resp = post_json(client, '/api/v1/alerts', {
        'name': 'Alerte SMTP',
        'condition': 'run.status == error',
        'channel': 'email',
        'recipients': ['ops@datapipe.io'],
    }, headers=auth_headers)
    assert create_resp.status_code == 201

    alert_id = create_resp.get_json()['id']
    resp = post_json(client, f'/api/v1/alerts/{alert_id}/test', {}, headers=auth_headers)

    assert resp.status_code == 503
    assert resp.get_json()['code'] == 'email_not_configured'


def test_test_email_alert_sends_when_configured(client, auth_headers, monkeypatch):
    sent = {}

    def fake_send_email(recipients, subject, body):
        sent['recipients'] = recipients
        sent['subject'] = subject
        sent['body'] = body
        return {'recipients': recipients, 'subject': subject}

    monkeypatch.setattr('app.routes.notifications.send_email', fake_send_email)

    create_resp = post_json(client, '/api/v1/alerts', {
        'name': 'Alerte opérationnelle',
        'condition': 'run.status == error',
        'channel': 'email',
        'recipients': ['ops@datapipe.io'],
    }, headers=auth_headers)
    assert create_resp.status_code == 201

    alert_id = create_resp.get_json()['id']
    resp = post_json(client, f'/api/v1/alerts/{alert_id}/test', {}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()['simulated'] is False
    assert sent['recipients'] == ['ops@datapipe.io']
    assert 'Alerte opérationnelle' in sent['subject']


def test_update_email_alert_requires_recipient(client, auth_headers):
    create_resp = post_json(client, '/api/v1/alerts', {
        'name': 'Alerte Slack',
        'condition': 'run.status == error',
        'channel': 'slack',
    }, headers=auth_headers)
    assert create_resp.status_code == 201

    alert_id = create_resp.get_json()['id']
    resp = patch_json(client, f'/api/v1/alerts/{alert_id}', {
        'channel': 'email',
    }, headers=auth_headers)

    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'Email alerts require at least one recipient'
