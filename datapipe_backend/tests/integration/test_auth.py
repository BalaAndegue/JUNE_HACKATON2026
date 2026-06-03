"""Tests d'intégration — Auth & Sessions (14 endpoints)."""
import pytest
import json
from tests.conftest import post_json, patch_json, delete_json

BASE = '/api/v1/auth'


class TestRegister:
    def test_success(self, client):
        resp = post_json(client, f'{BASE}/register', {
            'email': 'newuser@bank.ci',
            'name': 'Nouveau User',
            'password': 'Secure2026!',
        })
        assert resp.status_code == 201
        d = resp.get_json()
        assert 'user' in d
        assert d['user']['email'] == 'newuser@bank.ci'
        assert d['user']['verified'] is False
        assert 'message' in d

    def test_with_org_name(self, client):
        resp = post_json(client, f'{BASE}/register', {
            'email': 'withorg@bank.ci',
            'name': 'Org User',
            'password': 'Secure2026!',
            'org_name': 'Ma Banque',
        })
        assert resp.status_code == 201

    def test_duplicate_email(self, client, registered_user):
        resp = post_json(client, f'{BASE}/register', {
            'email': 'test@datapipe.io',
            'name': 'Dup',
            'password': 'Secure2026!',
        })
        assert resp.status_code == 409
        assert 'error' in resp.get_json()

    def test_missing_email(self, client):
        resp = post_json(client, f'{BASE}/register', {
            'name': 'No Email',
            'password': 'Secure2026!',
        })
        assert resp.status_code == 400

    def test_missing_password(self, client):
        resp = post_json(client, f'{BASE}/register', {
            'email': 'nopwd@test.ci',
            'name': 'No Pwd',
        })
        assert resp.status_code == 400

    def test_short_password(self, client):
        resp = post_json(client, f'{BASE}/register', {
            'email': 'short@test.ci',
            'name': 'Short',
            'password': '123',
        })
        assert resp.status_code == 400

    def test_missing_body(self, client):
        resp = client.post(f'{BASE}/register', content_type='application/json')
        assert resp.status_code == 400


class TestLogin:
    def test_success(self, client, registered_user):
        resp = post_json(client, f'{BASE}/login', {
            'email': 'test@datapipe.io',
            'password': 'Hackaton2026!',
        })
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'access_token' in d
        assert 'refresh_token' in d
        assert d['expires_in'] == 900
        assert 'user' in d

    def test_wrong_password(self, client, registered_user):
        resp = post_json(client, f'{BASE}/login', {
            'email': 'test@datapipe.io',
            'password': 'WrongPassword!',
        })
        assert resp.status_code == 401

    def test_unknown_email(self, client):
        resp = post_json(client, f'{BASE}/login', {
            'email': 'nobody@unknown.ci',
            'password': 'Whatever1',
        })
        assert resp.status_code == 401

    def test_missing_fields(self, client):
        resp = post_json(client, f'{BASE}/login', {'email': 'test@datapipe.io'})
        assert resp.status_code == 400


class TestGetMe:
    def test_authenticated(self, client, auth_headers):
        resp = client.get(f'{BASE}/me', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['email'] == 'test@datapipe.io'
        assert 'password_hash' not in d
        assert 'orgs' in d

    def test_unauthenticated(self, client):
        resp = client.get(f'{BASE}/me')
        assert resp.status_code == 401


class TestUpdateMe:
    def test_update_name(self, client, auth_headers):
        resp = patch_json(client, f'{BASE}/me', {'name': 'Jean Updated'}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'Jean Updated'

    def test_update_avatar(self, client, auth_headers):
        resp = patch_json(client, f'{BASE}/me', {'avatar_url': 'https://example.com/avatar.png'}, headers=auth_headers)
        assert resp.status_code == 200
        assert 'avatar_url' in resp.get_json()

    def test_unauthenticated(self, client):
        resp = patch_json(client, f'{BASE}/me', {'name': 'Hacker'})
        assert resp.status_code == 401


class TestSessions:
    def test_list_sessions(self, client, auth_headers):
        resp = client.get(f'{BASE}/sessions', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'sessions' in d
        assert isinstance(d['sessions'], list)
        assert len(d['sessions']) >= 1
        first = d['sessions'][0]
        assert 'id' in first
        assert 'ip' in first
        assert 'current' in first

    def test_unauthenticated(self, client):
        resp = client.get(f'{BASE}/sessions')
        assert resp.status_code == 401

    def test_revoke_all_sessions(self, client, auth_tokens):
        login_resp = post_json(client, f'{BASE}/login', {
            'email': 'test@datapipe.io',
            'password': 'Hackaton2026!',
        })
        token = login_resp.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        resp = post_json(client, f'{BASE}/revoke-all-sessions',
                         {'except_current': True}, headers=headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'revoked_count' in d
        assert 'message' in d


class TestForgotPassword:
    def test_existing_email(self, client):
        resp = post_json(client, f'{BASE}/forgot-password', {'email': 'test@datapipe.io'})
        assert resp.status_code == 200
        assert 'message' in resp.get_json()

    def test_nonexistent_email_same_response(self, client):
        resp = post_json(client, f'{BASE}/forgot-password', {'email': 'ghost@nowhere.ci'})
        assert resp.status_code == 200

    def test_missing_email(self, client):
        resp = post_json(client, f'{BASE}/forgot-password', {})
        assert resp.status_code == 400


class TestResetPassword:
    def test_invalid_token(self, client):
        resp = post_json(client, f'{BASE}/reset-password', {
            'token': 'invalidtoken123',
            'new_password': 'NewPass2026!',
        })
        assert resp.status_code == 400

    def test_missing_fields(self, client):
        resp = post_json(client, f'{BASE}/reset-password', {'token': 'abc'})
        assert resp.status_code == 400


class TestVerifyEmail:
    def test_invalid_token(self, client):
        resp = post_json(client, f'{BASE}/verify-email', {'token': 'badtoken'})
        assert resp.status_code == 400

    def test_valid_token(self, client):
        from app.models import User
        from app.extensions import db
        with client.application.app_context():
            user = User.query.filter_by(email='test@datapipe.io').first()
            if user:
                user.verify_token = 'validtoken123'
                db.session.commit()

        resp = post_json(client, f'{BASE}/verify-email', {'token': 'validtoken123'})
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'access_token' in d


class TestChangePassword:
    def test_wrong_current_password(self, client, auth_headers):
        resp = post_json(client, f'{BASE}/change-password', {
            'current_password': 'WrongPassword!',
            'new_password': 'NewPass2026!',
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_missing_fields(self, client, auth_headers):
        resp = post_json(client, f'{BASE}/change-password',
                         {'current_password': 'x'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_unauthenticated(self, client):
        resp = post_json(client, f'{BASE}/change-password', {
            'current_password': 'a', 'new_password': 'b',
        })
        assert resp.status_code == 401
