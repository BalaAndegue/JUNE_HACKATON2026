"""Tests d'intégration — Pipelines CRUD, versioning, templates (19 endpoints)."""
import pytest
from tests.conftest import post_json, patch_json

BASE = '/api/v1/pipelines'


class TestPipelinesCRUD:
    def test_list_pipelines(self, client, auth_headers, workspace_id):
        resp = client.get(f'{BASE}?workspace_id={workspace_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'data' in d
        assert 'pagination' in d
        assert d['pagination']['total'] >= 1

    def test_list_pipelines_missing_workspace(self, client, auth_headers):
        resp = client.get(BASE, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_with_search(self, client, auth_headers, workspace_id):
        resp = client.get(f'{BASE}?workspace_id={workspace_id}&search=Test', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert all('test' in p['name'].lower() for p in d['data'])

    def test_list_with_status_filter(self, client, auth_headers, workspace_id):
        resp = client.get(f'{BASE}?workspace_id={workspace_id}&status=active', headers=auth_headers)
        assert resp.status_code == 200

    def test_create_pipeline(self, client, auth_headers, workspace_id):
        resp = post_json(client, BASE, {
            'name': 'Pipeline Transactions',
            'workspace_id': workspace_id,
            'description': 'ETL transactions bancaires',
            'tags': ['etl', 'bancaire'],
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['name'] == 'Pipeline Transactions'
        assert d['tags'] == ['etl', 'bancaire']
        assert 'nodes' in d
        assert 'edges' in d

    def test_create_pipeline_missing_name(self, client, auth_headers, workspace_id):
        resp = post_json(client, BASE, {'workspace_id': workspace_id}, headers=auth_headers)
        assert resp.status_code == 400

    def test_create_pipeline_missing_workspace(self, client, auth_headers):
        resp = post_json(client, BASE, {'name': 'No WS'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_get_pipeline(self, client, auth_headers, pipeline_id):
        resp = client.get(f'{BASE}/{pipeline_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == pipeline_id
        assert 'nodes' in d
        assert 'edges' in d

    def test_get_pipeline_not_found(self, client, auth_headers):
        resp = client.get(f'{BASE}/pip_doesnotexist', headers=auth_headers)
        assert resp.status_code == 404

    def test_patch_pipeline(self, client, auth_headers, pipeline_id):
        resp = patch_json(client, f'{BASE}/{pipeline_id}',
                          {'name': 'Pipeline Test Updated', 'tags': ['updated']},
                          headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['name'] == 'Pipeline Test Updated'

    def test_put_pipeline(self, client, auth_headers, pipeline_id):
        resp = client.put(f'{BASE}/{pipeline_id}',
                          json={'name': 'Pipeline Replaced'},
                          headers=auth_headers)
        assert resp.status_code == 200


class TestPipelineActions:
    def test_duplicate(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{BASE}/{pipeline_id}/duplicate',
                         {'name': 'Pipeline Copie'}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['name'] == 'Pipeline Copie'
        assert d['id'] != pipeline_id

    def test_archive_and_restore(self, client, auth_headers, workspace_id):
        create_resp = post_json(client, BASE, {
            'name': 'Pipeline À Archiver',
            'workspace_id': workspace_id,
        }, headers=auth_headers)
        pip_id = create_resp.get_json()['id']

        archive_resp = post_json(client, f'{BASE}/{pip_id}/archive', {}, headers=auth_headers)
        assert archive_resp.status_code == 200
        assert archive_resp.get_json()['status'] == 'archived'

        restore_resp = post_json(client, f'{BASE}/{pip_id}/restore', {}, headers=auth_headers)
        assert restore_resp.status_code == 200
        assert restore_resp.get_json()['status'] == 'active'

    def test_publish_unpublish(self, client, auth_headers, pipeline_id):
        pub = post_json(client, f'{BASE}/{pipeline_id}/publish', {}, headers=auth_headers)
        assert pub.status_code == 200
        assert pub.get_json()['is_public'] is True

        unpub = post_json(client, f'{BASE}/{pipeline_id}/unpublish', {}, headers=auth_headers)
        assert unpub.status_code == 200
        assert unpub.get_json()['is_public'] is False

    def test_delete_pipeline(self, client, auth_headers, workspace_id):
        create_resp = post_json(client, BASE, {
            'name': 'Pipeline À Supprimer',
            'workspace_id': workspace_id,
        }, headers=auth_headers)
        pip_id = create_resp.get_json()['id']
        del_resp = client.delete(f'{BASE}/{pip_id}', headers=auth_headers)
        assert del_resp.status_code == 200


class TestVersioning:
    def test_create_snapshot(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{BASE}/{pipeline_id}/versions/snapshot',
                         {'label': 'Version stable v1'}, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['version_num'] >= 1
        assert d['label'] == 'Version stable v1'

    def test_list_versions(self, client, auth_headers, pipeline_id):
        post_json(client, f'{BASE}/{pipeline_id}/versions/snapshot', {}, headers=auth_headers)
        resp = client.get(f'{BASE}/{pipeline_id}/versions', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'versions' in d
        assert len(d['versions']) >= 1

    def test_get_version(self, client, auth_headers, pipeline_id):
        snap = post_json(client, f'{BASE}/{pipeline_id}/versions/snapshot',
                         {'label': 'v2'}, headers=auth_headers)
        version_id = snap.get_json()['id']

        resp = client.get(f'{BASE}/{pipeline_id}/versions/{version_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == version_id
        assert 'snapshot' in d

    def test_restore_version(self, client, auth_headers, pipeline_id):
        snap = post_json(client, f'{BASE}/{pipeline_id}/versions/snapshot', {}, headers=auth_headers)
        version_id = snap.get_json()['id']
        resp = post_json(client, f'{BASE}/{pipeline_id}/versions/{version_id}/restore',
                         {}, headers=auth_headers)
        assert resp.status_code == 200


class TestTemplates:
    def test_list_templates(self, client, auth_headers):
        resp = client.get(f'{BASE}/templates', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'templates' in d
        assert len(d['templates']) >= 4

    def test_list_templates_by_category(self, client, auth_headers):
        resp = client.get(f'{BASE}/templates?category=FinTech', headers=auth_headers)
        assert resp.status_code == 200

    def test_get_template(self, client, auth_headers):
        list_resp = client.get(f'{BASE}/templates', headers=auth_headers)
        tpl_id = list_resp.get_json()['templates'][0]['id']

        resp = client.get(f'{BASE}/templates/{tpl_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'nodes' in d
        assert 'edges' in d

    def test_instantiate_template(self, client, auth_headers, workspace_id):
        list_resp = client.get(f'{BASE}/templates', headers=auth_headers)
        tpl_id = list_resp.get_json()['templates'][0]['id']

        resp = post_json(client, f'{BASE}/templates/{tpl_id}/instantiate', {
            'workspace_id': workspace_id,
            'name': 'Depuis Template',
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['name'] == 'Depuis Template'
        assert len(d['nodes']) > 0


class TestImportExport:
    def test_export_json(self, client, auth_headers, pipeline_id):
        resp = client.get(f'{BASE}/{pipeline_id}/export', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'datapipe_version' in d
        assert 'name' in d
        assert 'nodes' in d
        assert 'edges' in d

    def test_import_pipeline(self, client, auth_headers, workspace_id):
        definition = {
            'name': 'Pipeline Importé',
            'description': 'Import test',
            'nodes': [
                {'type': 'csv_reader', 'label': 'CSV', 'position': {'x': 0, 'y': 0}},
                {'type': 'sql_write', 'label': 'SQL', 'position': {'x': 300, 'y': 0}},
            ],
            'edges': [],
        }
        resp = post_json(client, f'{BASE}/import', {
            'workspace_id': workspace_id,
            'definition': definition,
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['name'] == 'Pipeline Importé'
        assert len(d['nodes']) == 2

    def test_import_missing_definition(self, client, auth_headers, workspace_id):
        resp = post_json(client, f'{BASE}/import',
                         {'workspace_id': workspace_id}, headers=auth_headers)
        assert resp.status_code == 400


class TestDiffAndMerge:
    def test_diff(self, client, auth_headers, pipeline_id):
        snap = post_json(client, f'{BASE}/{pipeline_id}/versions/snapshot', {}, headers=auth_headers)
        version_id = snap.get_json()['id']

        resp = client.get(
            f'{BASE}/{pipeline_id}/diff?version_a={version_id}&version_b=current',
            headers=auth_headers,
        )
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'nodes' in d
        assert 'edges' in d

    def test_merge_pipelines(self, client, auth_headers, workspace_id, pipeline_id):
        target = post_json(client, BASE, {
            'name': 'Pipeline Target',
            'workspace_id': workspace_id,
        }, headers=auth_headers).get_json()

        resp = post_json(client, f'{BASE}/merge', {
            'source_id': pipeline_id,
            'target_id': target['id'],
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert 'pipeline' in resp.get_json()
