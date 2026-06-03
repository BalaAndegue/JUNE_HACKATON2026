"""Tests d'integration - resultats et exports."""
import pytest

from tests.conftest import post_json
from app.routes.results import EXPORTS_STORE

BASE = '/api/v1'


@pytest.fixture(autouse=True)
def clear_exports_store():
    EXPORTS_STORE.clear()


class TestResults:
    def test_pipeline_and_run_results(self, client, auth_headers, pipeline_id, run_id):
        pipe_resp = client.get(f'{BASE}/pipelines/{pipeline_id}/results', headers=auth_headers)
        assert pipe_resp.status_code == 200
        pipeline_results = pipe_resp.get_json()['results']
        assert any(r['run_id'] == run_id for r in pipeline_results)

        run_resp = client.get(f'{BASE}/runs/{run_id}/results', headers=auth_headers)
        assert run_resp.status_code == 200
        run_data = run_resp.get_json()
        assert run_data['run_id'] == run_id
        assert run_data['rows_count'] >= 1
        assert isinstance(run_data['node_summary'], dict)

        result_resp = client.get(f'{BASE}/results/{run_id}', headers=auth_headers)
        assert result_resp.status_code == 200
        result_data = result_resp.get_json()
        assert result_data['id'] == run_id
        assert result_data['rows_count'] >= 1

    def test_download_result_csv_and_json(self, client, auth_headers, run_id):
        csv_resp = client.get(f'{BASE}/results/{run_id}/download?format=csv', headers=auth_headers)
        assert csv_resp.status_code == 200
        assert csv_resp.mimetype == 'text/csv'
        csv_text = csv_resp.get_data(as_text=True)
        assert 'montant' in csv_text

        json_resp = client.get(f'{BASE}/results/{run_id}/download?format=json', headers=auth_headers)
        assert json_resp.status_code == 200
        assert json_resp.mimetype == 'application/json'
        assert json_resp.get_data(as_text=True).startswith('[')

    def test_export_lifecycle(self, client, auth_headers, run_id):
        create_resp = post_json(client, f'{BASE}/results/{run_id}/export', {
            'format': 'json',
        }, headers=auth_headers)
        assert create_resp.status_code == 201
        export = create_resp.get_json()
        export_id = export['id']
        assert export['status'] == 'completed'
        assert export['run_id'] == run_id

        list_resp = client.get(f'{BASE}/exports', headers=auth_headers)
        assert list_resp.status_code == 200
        exports = list_resp.get_json()['exports']
        assert any(e['id'] == export_id for e in exports)

        get_resp = client.get(f'{BASE}/exports/{export_id}', headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.get_json()['id'] == export_id

        retry_resp = client.post(f'{BASE}/exports/{export_id}/retry', headers=auth_headers, json={})
        assert retry_resp.status_code == 200
        assert retry_resp.get_json()['status'] == 'completed'

        download_resp = client.get(f'{BASE}/exports/{export_id}/download', headers=auth_headers)
        assert download_resp.status_code == 200
        assert download_resp.mimetype == 'application/json'

        delete_resp = client.delete(f'{BASE}/exports/{export_id}', headers=auth_headers)
        assert delete_resp.status_code == 200

        missing_resp = client.get(f'{BASE}/exports/{export_id}', headers=auth_headers)
        assert missing_resp.status_code == 404

    def test_result_not_found(self, client, auth_headers):
        resp = client.get(f'{BASE}/results/run_does_not_exist', headers=auth_headers)
        assert resp.status_code == 404
