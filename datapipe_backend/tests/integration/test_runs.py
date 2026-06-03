"""Tests d'intégration — Exécution & Runs (9 endpoints)."""
import io
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


class TestRealExecution:
    """Exécution réelle bout-en-bout : upload CSV → filter → aggregate."""

    CSV = (
        "id,montant,type,region\n"
        "1,1500,virement,Abidjan\n"
        "2,80000,virement,Abidjan\n"
        "3,50,retrait,Bouake\n"
        "4,120000,virement,Bouake\n"
        "5,9000,retrait,Abidjan\n"
    )

    def _build(self, client, auth_headers, workspace_id):
        # 1. Upload d'un vrai CSV
        up = client.post(
            '/api/v1/files/upload',
            data={
                'workspace_id': workspace_id,
                'file': (io.BytesIO(self.CSV.encode()), 'transactions.csv'),
            },
            content_type='multipart/form-data',
            headers=auth_headers,
        )
        assert up.status_code == 201, up.get_data(as_text=True)
        file_id = up.get_json()['id']

        # 2. Pipeline dédié
        pip = post_json(client, '/api/v1/pipelines', {
            'name': 'ETL réel', 'workspace_id': workspace_id,
        }, headers=auth_headers).get_json()
        pid = pip['id']

        def add_node(type_slug, config, label):
            r = post_json(client, f'{PBASE}/{pid}/nodes', {
                'type': type_slug, 'label': label,
                'position': {'x': 0, 'y': 0}, 'config': config,
            }, headers=auth_headers)
            assert r.status_code == 201, r.get_data(as_text=True)
            return r.get_json()['id']

        n_read = add_node('csv_reader', {'file_id': file_id}, 'Lire CSV')
        n_filter = add_node('filter', {
            'conditions': [{'field': 'montant', 'operator': 'gt', 'value': 50000}]}, 'Gros montants')
        n_agg = add_node('aggregate', {
            'group_by': ['region'],
            'aggregations': [
                {'field': 'montant', 'function': 'sum', 'alias': 'total'},
                {'field': 'id', 'function': 'count', 'alias': 'nb'},
            ]}, 'Par région')

        for src, tgt in ((n_read, n_filter), (n_filter, n_agg)):
            e = post_json(client, f'{PBASE}/{pid}/edges',
                          {'source': src, 'target': tgt}, headers=auth_headers)
            assert e.status_code == 201, e.get_data(as_text=True)

        return pid, n_read, n_filter, n_agg

    def test_end_to_end_real_results(self, client, auth_headers, workspace_id):
        pid, n_read, n_filter, n_agg = self._build(client, auth_headers, workspace_id)

        resp = post_json(client, f'{PBASE}/{pid}/run', {}, headers=auth_headers)
        assert resp.status_code == 201, resp.get_data(as_text=True)
        d = resp.get_json()
        assert d['status'] == 'success'
        results = d['node_results']

        # Le reader a lu les 5 lignes réelles
        assert results[n_read]['rows_output'] == 5
        # Le filtre ne garde que les 2 montants > 50000
        assert results[n_filter]['rows_output'] == 2
        # L'agrégation produit 2 régions avec les vrais totaux
        agg_rows = {r['region']: r for r in results[n_agg]['output_preview']}
        assert agg_rows['Abidjan']['total'] == 80000
        assert agg_rows['Bouake']['total'] == 120000
        assert agg_rows['Abidjan']['nb'] == 1

    def test_node_output_reflects_real_data(self, client, auth_headers, workspace_id):
        pid, n_read, n_filter, n_agg = self._build(client, auth_headers, workspace_id)
        run = post_json(client, f'{PBASE}/{pid}/run', {}, headers=auth_headers).get_json()
        out = client.get(f'{RBASE}/{run["id"]}/nodes/{n_filter}/output', headers=auth_headers)
        assert out.status_code == 200
        rows = out.get_json()['result']['output_preview']
        assert {r['id'] for r in rows} == {2, 4}

    def test_export_returns_full_dataset_not_just_preview(self, client, auth_headers, workspace_id):
        """Régression : le download doit renvoyer TOUTES les lignes, pas l'aperçu (10)."""
        n = 25
        csv_content = 'id,montant\n' + '\n'.join(f'{i},{i * 100}' for i in range(1, n + 1)) + '\n'
        up = client.post('/api/v1/files/upload', data={
            'workspace_id': workspace_id,
            'file': (io.BytesIO(csv_content.encode()), 'big.csv'),
        }, content_type='multipart/form-data', headers=auth_headers)
        file_id = up.get_json()['id']

        pip = post_json(client, '/api/v1/pipelines', {
            'name': 'Export complet', 'workspace_id': workspace_id,
        }, headers=auth_headers).get_json()
        post_json(client, f'{PBASE}/{pip["id"]}/nodes', {
            'type': 'csv_reader', 'label': 'Lire', 'position': {'x': 0, 'y': 0},
            'config': {'file_id': file_id},
        }, headers=auth_headers)

        run = post_json(client, f'{PBASE}/{pip["id"]}/run', {}, headers=auth_headers).get_json()
        assert run['status'] == 'success'

        # Résultats JSON : dataset complet (25 lignes), pas l'aperçu de 10
        res = client.get(f'{RBASE}/{run["id"]}/results', headers=auth_headers)
        assert res.get_json()['rows_count'] == n

        # Download CSV : 25 lignes de données + 1 en-tête
        dl = client.get(f'/api/v1/results/{run["id"]}/download?format=csv', headers=auth_headers)
        assert dl.status_code == 200
        lines = [l for l in dl.get_data(as_text=True).splitlines() if l.strip()]
        assert len(lines) == n + 1
