"""Tests d'intégration — Organisations & Workspaces (14 endpoints)."""
import pytest
from tests.conftest import post_json, patch_json

BASE = '/api/v1/orgs'


class TestOrgs:
    def test_list_orgs(self, client, auth_headers):
        resp = client.get(BASE, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'orgs' in d
        assert len(d['orgs']) >= 1

    def test_list_orgs_unauthenticated(self, client):
        assert client.get(BASE).status_code == 401

    def test_create_org(self, client, auth_headers):
        resp = post_json(client, BASE, {
            'name': 'Nouvelle Banque',
            'plan': 'pro',
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['name'] == 'Nouvelle Banque'
        assert d['plan'] == 'pro'
        assert 'slug' in d

    def test_create_org_missing_name(self, client, auth_headers):
        resp = post_json(client, BASE, {'plan': 'free'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_get_org(self, client, auth_headers, org_id):
        resp = client.get(f'{BASE}/{org_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == org_id
        assert 'name' in d
        assert 'plan' in d

    def test_get_org_not_found(self, client, auth_headers):
        resp = client.get(f'{BASE}/org_doesnotexist', headers=auth_headers)
        assert resp.status_code in (403, 404)

    def test_update_org(self, client, auth_headers, org_id):
        resp = patch_json(client, f'{BASE}/{org_id}',
                          {'name': 'Banque Updated'},
                          headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'Banque Updated'

    def test_update_org_settings(self, client, auth_headers, org_id):
        resp = patch_json(client, f'{BASE}/{org_id}',
                          {'settings': {'allow_public_pipelines': True}},
                          headers=auth_headers)
        assert resp.status_code == 200


class TestOrgMembers:
    def test_list_members(self, client, auth_headers, org_id):
        resp = client.get(f'{BASE}/{org_id}/members', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'members' in d
        assert len(d['members']) >= 1
        first = d['members'][0]
        assert 'user_id' in first
        assert 'role' in first
        assert first['role'] == 'owner'

    def test_invite_member(self, client, auth_headers, org_id):
        resp = post_json(client, f'{BASE}/{org_id}/members/invite', {
            'email': 'invite@bank.ci',
            'role': 'editor',
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert 'invite_id' in d
        assert d['email'] == 'invite@bank.ci'

    def test_invite_invalid_role(self, client, auth_headers, org_id):
        resp = post_json(client, f'{BASE}/{org_id}/members/invite', {
            'email': 'bad@bank.ci',
            'role': 'superadmin',
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_invite_missing_fields(self, client, auth_headers, org_id):
        resp = post_json(client, f'{BASE}/{org_id}/members/invite',
                         {'email': 'nope@bank.ci'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_accept_invite_invalid_token(self, client, auth_headers, org_id):
        resp = post_json(client, f'{BASE}/{org_id}/members/accept-invite',
                         {'token': 'invalid_token_xyz'}, headers=auth_headers)
        assert resp.status_code == 400


class TestWorkspaces:
    def test_list_workspaces(self, client, auth_headers, org_id):
        resp = client.get(f'{BASE}/{org_id}/workspaces', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'workspaces' in d
        assert len(d['workspaces']) >= 1

    def test_create_workspace(self, client, auth_headers, org_id):
        resp = post_json(client, f'{BASE}/{org_id}/workspaces', {
            'name': 'Staging',
            'description': 'Environnement de test',
            'color': '#f59e0b',
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['name'] == 'Staging'
        assert d['color'] == '#f59e0b'
        assert d['org_id'] == org_id

    def test_create_workspace_missing_name(self, client, auth_headers, org_id):
        resp = post_json(client, f'{BASE}/{org_id}/workspaces', {}, headers=auth_headers)
        assert resp.status_code == 400

    def test_get_workspace(self, client, auth_headers, org_id, workspace_id):
        resp = client.get(f'{BASE}/{org_id}/workspaces/{workspace_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == workspace_id

    def test_update_workspace(self, client, auth_headers, org_id, workspace_id):
        resp = patch_json(client, f'{BASE}/{org_id}/workspaces/{workspace_id}',
                          {'name': 'Production Updated', 'color': '#22c55e'},
                          headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['color'] == '#22c55e'

    def test_get_workspace_not_found(self, client, auth_headers, org_id):
        resp = client.get(f'{BASE}/{org_id}/workspaces/ws_doesnotexist', headers=auth_headers)
        assert resp.status_code == 404

    def test_unauthenticated(self, client, org_id):
        assert client.get(f'{BASE}/{org_id}/workspaces').status_code == 401
