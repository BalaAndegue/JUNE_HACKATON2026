"""Tests d'intégration — Exécution & Runs (9 endpoints)."""
import pytest
from tests.conftest import post_json

PBASE = '/api/v1/pipelines'
RBASE = '/api/v1/runs'


class TestTriggerRun:
    def test_trigger_run_success(self, client, auth_headers, pipeline_id, node_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/run', {}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['status'] == 'success'
        assert d['pipeline_id'] == pipeline_id
        assert 'duration_ms' in d
        assert d['duration_ms'] is not None
        assert 'node_results' in d

    def test_trigger_run_fields(self, client, auth_headers, pipeline_id, node_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/run',
                         {'trigger': 'manual'}, headers=auth_headers)
        d = resp.get_json()
        assert d['trigger'] == 'manual'
        assert d['started_at'] is not None

    def test_trigger_empty_pipeline(self, client, auth_headers, workspace_id):
        pip = post_json(client, '/api/v1/pipelines', {
            'name': 'Vide', 'workspace_id': workspace_id,
        }, headers=auth_headers).get_json()
        resp = post_json(client, f'{PBASE}/{pip["id"]}/run', {}, headers=auth_headers)
        assert resp.status_code == 400

    def test_unauthenticated(self, client, pipeline_id):
        resp = client.post(f'{PBASE}/{pipeline_id}/run', json={})
        assert resp.status_code == 401


class TestListRuns:
    def test_list_runs(self, client, auth_headers, pipeline_id, run_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/runs', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'data' in d
        assert 'pagination' in d
        assert len(d['data']) >= 1

    def test_list_runs_filter_status(self, client, auth_headers, pipeline_id, run_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/runs?status=success', headers=auth_headers)
        assert resp.status_code == 200
        runs = resp.get_json()['data']
        assert all(r['status'] == 'success' for r in runs)

    def test_get_run(self, client, auth_headers, pipeline_id, run_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/runs/{run_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == run_id
        assert 'node_results' in d

    def test_get_run_not_found(self, client, auth_headers, pipeline_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/runs/run_doesnotexist', headers=auth_headers)
        assert resp.status_code == 404


class TestCancelRetry:
    def test_cancel_finished_run_error(self, client, auth_headers, pipeline_id, run_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/runs/{run_id}/cancel',
                         {}, headers=auth_headers)
        assert resp.status_code == 400

    def test_retry_run(self, client, auth_headers, pipeline_id, run_id, node_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/runs/{run_id}/retry',
                         {}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['status'] == 'success'
        assert d['trigger'] == 'retry'

    def test_delete_run(self, client, auth_headers, pipeline_id, node_id):
        run = post_json(client, f'{PBASE}/{pipeline_id}/run', {}, headers=auth_headers).get_json()
        del_resp = client.delete(f'{PBASE}/{pipeline_id}/runs/{run["id"]}', headers=auth_headers)
        assert del_resp.status_code == 200


class TestLogs:
    def test_get_logs(self, client, auth_headers, run_id):
        resp = client.get(f'{RBASE}/{run_id}/logs', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'logs' in d
        assert 'count' in d
        assert d['count'] >= 0

    def test_logs_have_correct_fields(self, client, auth_headers, run_id):
        resp = client.get(f'{RBASE}/{run_id}/logs', headers=auth_headers)
        logs = resp.get_json()['logs']
        if logs:
            log = logs[0]
            assert 'id' in log
            assert 'level' in log
            assert 'message' in log
            assert 'timestamp' in log

    def test_stream_logs(self, client, auth_headers, run_id):
        resp = client.get(f'{RBASE}/{run_id}/logs/stream', headers=auth_headers)
        assert resp.status_code == 200
        assert 'text/event-stream' in resp.content_type

    def test_node_output(self, client, auth_headers, run_id, node_id):
        resp = client.get(f'{RBASE}/{run_id}/nodes/{node_id}/output', headers=auth_headers)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            d = resp.get_json()
            assert 'run_id' in d
            assert 'result' in d
