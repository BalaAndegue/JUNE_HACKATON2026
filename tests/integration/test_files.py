"""Tests d'intégration — Fichiers & Datasources (upload, preview, analyze, CRUD)."""
import io
import json
import pytest
from tests.conftest import post_json, patch_json

FBASE = '/api/v1/files'
DBASE = '/api/v1/datasources'

CSV = (
    "id,montant,type\n"
    "1,1500,virement\n"
    "2,80000,retrait\n"
    "3,9000,virement\n"
)
JSON_DATA = [
    {"id": 1, "client": "A", "solde": 1000},
    {"id": 2, "client": "B", "solde": 2500},
]


def _upload(client, auth_headers, workspace_id, content, filename, content_type='multipart/form-data'):
    return client.post(
        f'{FBASE}/upload',
        data={'workspace_id': workspace_id,
              'file': (io.BytesIO(content), filename)},
        content_type=content_type,
        headers=auth_headers,
    )


class TestUpload:
    def test_upload_csv_success(self, client, auth_headers, workspace_id):
        resp = _upload(client, auth_headers, workspace_id, CSV.encode(), 'transactions.csv')
        assert resp.status_code == 201, resp.get_data(as_text=True)
        d = resp.get_json()
        assert d['rows_count'] == 3
        assert d['columns_count'] == 3
        assert d['columns'] == ['id', 'montant', 'type']
        assert d['original_name'] == 'transactions.csv'
        assert d['id'].startswith('fil_')

    def test_upload_json_success(self, client, auth_headers, workspace_id):
        resp = _upload(client, auth_headers, workspace_id,
                       json.dumps(JSON_DATA).encode(), 'clients.json')
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['rows_count'] == 2
        assert set(d['columns']) == {'id', 'client', 'solde'}

    def test_upload_missing_workspace_id(self, client, auth_headers):
        resp = client.post(f'{FBASE}/upload',
                           data={'file': (io.BytesIO(CSV.encode()), 'a.csv')},
                           content_type='multipart/form-data', headers=auth_headers)
        assert resp.status_code == 400

    def test_upload_no_file(self, client, auth_headers, workspace_id):
        resp = client.post(f'{FBASE}/upload', data={'workspace_id': workspace_id},
                           content_type='multipart/form-data', headers=auth_headers)
        assert resp.status_code == 400

    def test_upload_disallowed_extension(self, client, auth_headers, workspace_id):
        resp = _upload(client, auth_headers, workspace_id, b'<html>', 'page.html')
        assert resp.status_code == 400

    def test_upload_unauthenticated(self, client, workspace_id):
        resp = client.post(f'{FBASE}/upload',
                           data={'workspace_id': workspace_id,
                                 'file': (io.BytesIO(CSV.encode()), 'a.csv')},
                           content_type='multipart/form-data')
        assert resp.status_code == 401

    def test_upload_unknown_workspace(self, client, auth_headers):
        resp = _upload(client, auth_headers, 'ws_inexistant', CSV.encode(), 'a.csv')
        assert resp.status_code in (403, 404)


class TestFileLifecycle:
    @pytest.fixture
    def uploaded_csv(self, client, auth_headers, workspace_id):
        resp = _upload(client, auth_headers, workspace_id, CSV.encode(), 'lifecycle.csv')
        return resp.get_json()['id']

    def test_list_files(self, client, auth_headers, workspace_id, uploaded_csv):
        resp = client.get(f'{FBASE}?workspace_id={workspace_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'data' in d and 'pagination' in d
        assert any(f['id'] == uploaded_csv for f in d['data'])

    def test_list_files_missing_workspace(self, client, auth_headers):
        resp = client.get(FBASE, headers=auth_headers)
        assert resp.status_code == 400

    def test_get_file(self, client, auth_headers, uploaded_csv):
        resp = client.get(f'{FBASE}/{uploaded_csv}', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['id'] == uploaded_csv

    def test_get_file_not_found(self, client, auth_headers):
        resp = client.get(f'{FBASE}/fil_inexistant', headers=auth_headers)
        assert resp.status_code == 404

    def test_preview(self, client, auth_headers, uploaded_csv):
        resp = client.get(f'{FBASE}/{uploaded_csv}/preview', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['columns'] == ['id', 'montant', 'type']
        assert d['rows_count'] == 3
        assert len(d['preview']) <= 3

    def test_analyze(self, client, auth_headers, uploaded_csv):
        resp = client.post(f'{FBASE}/{uploaded_csv}/analyze', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['rows'] == 3
        assert 'quality_score' in d
        names = {c['name'] for c in d['columns']}
        assert names == {'id', 'montant', 'type'}
        montant_col = next(c for c in d['columns'] if c['name'] == 'montant')
        assert montant_col['type'] == 'number'

    def test_delete_file(self, client, auth_headers, uploaded_csv):
        resp = client.delete(f'{FBASE}/{uploaded_csv}', headers=auth_headers)
        assert resp.status_code == 200
        # Le fichier n'existe plus
        assert client.get(f'{FBASE}/{uploaded_csv}', headers=auth_headers).status_code == 404


class TestDatasources:
    @pytest.fixture
    def ds_id(self, client, auth_headers, workspace_id):
        resp = post_json(client, DBASE, {
            'workspace_id': workspace_id, 'type': 'postgresql', 'name': 'PG Prod',
            'config': {'host': 'localhost', 'port': 5432, 'password': 'secret'},
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.get_data(as_text=True)
        return resp.get_json()['id']

    def test_create_invalid_type(self, client, auth_headers, workspace_id):
        resp = post_json(client, DBASE, {
            'workspace_id': workspace_id, 'type': 'oracle', 'name': 'X',
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_missing_field(self, client, auth_headers, workspace_id):
        resp = post_json(client, DBASE, {'workspace_id': workspace_id, 'type': 'mysql'},
                         headers=auth_headers)
        assert resp.status_code == 400

    def test_config_secrets_hidden(self, client, auth_headers, ds_id):
        resp = client.get(f'{DBASE}/{ds_id}', headers=auth_headers)
        assert resp.status_code == 200
        assert 'password' not in resp.get_json()['config']

    def test_list_datasources(self, client, auth_headers, workspace_id, ds_id):
        resp = client.get(f'{DBASE}?workspace_id={workspace_id}', headers=auth_headers)
        assert resp.status_code == 200
        assert any(d['id'] == ds_id for d in resp.get_json()['datasources'])

    def test_patch_datasource(self, client, auth_headers, ds_id):
        resp = patch_json(client, f'{DBASE}/{ds_id}', {'name': 'PG Renamed', 'active': False},
                          headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['name'] == 'PG Renamed'
        assert d['active'] is False

    def test_test_connection(self, client, auth_headers, ds_id):
        resp = client.post(f'{DBASE}/{ds_id}/test', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_get_schema(self, client, auth_headers, ds_id):
        resp = client.get(f'{DBASE}/{ds_id}/schema', headers=auth_headers)
        assert resp.status_code == 200
        assert 'tables' in resp.get_json()['schema']

    def test_sync_and_status(self, client, auth_headers, ds_id):
        sync = client.post(f'{DBASE}/{ds_id}/sync', headers=auth_headers)
        assert sync.status_code == 200
        status = client.get(f'{DBASE}/{ds_id}/sync-status', headers=auth_headers)
        assert status.status_code == 200
        assert status.get_json()['sync_status'] == 'idle'

    def test_list_types(self, client, auth_headers):
        resp = client.get(f'{DBASE}/types', headers=auth_headers)
        assert resp.status_code == 200
        types = {t['type'] for t in resp.get_json()['types']}
        assert 'postgresql' in types

    def test_delete_datasource(self, client, auth_headers, ds_id):
        resp = client.delete(f'{DBASE}/{ds_id}', headers=auth_headers)
        assert resp.status_code == 200
        assert client.get(f'{DBASE}/{ds_id}', headers=auth_headers).status_code == 404
