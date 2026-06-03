"""Tests for the frontend compatibility layer (alias routes + shapes)."""
import io

from tests.conftest import post_json

V = '/api/v1'


class TestRunAliases:
    def test_execute_alias_returns_run_id(self, client, auth_headers, pipeline_id, node_id):
        resp = post_json(client, f'{V}/pipelines/{pipeline_id}/execute', {}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['run_id']
        assert d['status'] == 'success'
        assert d['pipeline_id'] == pipeline_id
        assert 'node_results' in d

    def test_get_run_alias(self, client, auth_headers, pipeline_id, node_id):
        run = post_json(client, f'{V}/pipelines/{pipeline_id}/execute', {}, headers=auth_headers).get_json()
        resp = client.get(f"{V}/runs/{run['run_id']}", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == run['run_id']
        assert 'nodes_executed' in d

    def test_node_preview_shape(self, client, auth_headers, pipeline_id, node_id):
        run = post_json(client, f'{V}/pipelines/{pipeline_id}/execute', {}, headers=auth_headers).get_json()
        resp = client.get(f"{V}/runs/{run['run_id']}/nodes/{node_id}/preview", headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'columns' in d and 'rows' in d and 'total_rows' in d

    def test_dry_run(self, client, auth_headers, pipeline_id, node_id):
        resp = post_json(client, f'{V}/pipelines/{pipeline_id}/execute/dry-run', {}, headers=auth_headers)
        assert resp.status_code == 200
        assert 'valid' in resp.get_json()


class TestAIAliases:
    def test_generate_sql_alias(self, client, auth_headers):
        resp = post_json(client, f'{V}/ai/generate/sql', {
            'prompt': 'agréger le montant par type',
            'schema': [{'name': 'montant'}, {'name': 'transaction_type'}],
        }, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['sql'] and 'explanation' in d and 'tokens_used' in d

    def test_generate_pipeline_alias(self, client, auth_headers):
        resp = post_json(client, f'{V}/ai/generate/pipeline', {
            'prompt': 'importer un csv, filtrer les montants élevés et exporter',
        }, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'pipeline' in d and 'nodes' in d['pipeline']
        assert len(d['pipeline']['nodes']) > 0

    def test_chat_accepts_messages_array(self, client, auth_headers):
        resp = post_json(client, f'{V}/ai/chat', {
            'messages': [{'role': 'user', 'content': 'Comment créer un pipeline ?'}],
        }, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['message']['role'] == 'assistant'
        assert d['message']['content']


class TestFileSchemaAlias:
    def test_file_schema(self, client, auth_headers, workspace_id):
        csv = b'montant,type\n100,credit\n200,debit\n'
        up = client.post(f'{V}/files/upload',
                         data={'workspace_id': workspace_id,
                               'file': (io.BytesIO(csv), 'x.csv')},
                         content_type='multipart/form-data', headers=auth_headers).get_json()
        resp = client.get(f"{V}/files/{up['id']}/schema", headers=auth_headers)
        assert resp.status_code == 200
        cols = resp.get_json()['columns']
        assert {c['name'] for c in cols} == {'montant', 'type'}


class TestNodeShapeAdapter:
    def test_node_has_data_wrapper(self, client, auth_headers, pipeline_id):
        node = post_json(client, f'{V}/pipelines/{pipeline_id}/nodes', {
            'type': 'filter', 'position': {'x': 0, 'y': 0},
            'data': {'config': {'column': 'montant'}, 'label': 'Mon filtre'},
        }, headers=auth_headers).get_json()
        assert node['data']['label'] == 'Mon filtre'
        assert node['data']['config'] == {'column': 'montant'}
        assert node['config'] == {'column': 'montant'}  # flat kept for tests
