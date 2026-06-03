"""Tests d'intégration — Nodes, Edges, Pin-data, Node-types (14 endpoints)."""
import pytest
from tests.conftest import post_json, patch_json

PBASE = '/api/v1/pipelines'
NT_BASE = '/api/v1/node-types'


class TestNodes:
    def test_list_nodes(self, client, auth_headers, pipeline_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'nodes' in d
        assert isinstance(d['nodes'], list)

    def test_create_node(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/nodes', {
            'type': 'aggregate',
            'label': 'Agréger par mois',
            'position': {'x': 300, 'y': 100},
            'config': {'group_by': ['mois'], 'aggregations': [{'field': 'montant', 'function': 'sum'}]},
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['type'] == 'aggregate'
        assert d['label'] == 'Agréger par mois'
        assert d['position'] == {'x': 300.0, 'y': 100.0}

    def test_create_node_missing_type(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/nodes',
                         {'label': 'Sans type'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_get_node(self, client, auth_headers, pipeline_id, node_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes/{node_id}', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['id'] == node_id

    def test_get_node_not_found(self, client, auth_headers, pipeline_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes/nod_doesnotexist', headers=auth_headers)
        assert resp.status_code == 404

    def test_patch_node(self, client, auth_headers, pipeline_id, node_id):
        resp = patch_json(client, f'{PBASE}/{pipeline_id}/nodes/{node_id}', {
            'label': 'CSV Updated',
            'position': {'x': 150, 'y': 250},
        }, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['label'] == 'CSV Updated'
        assert d['position']['x'] == 150.0

    def test_put_node(self, client, auth_headers, pipeline_id, node_id):
        resp = client.put(f'{PBASE}/{pipeline_id}/nodes/{node_id}',
                          json={'type': 'csv_reader', 'label': 'PUT Node', 'config': {}},
                          headers=auth_headers)
        assert resp.status_code == 200

    def test_bulk_create_nodes(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/nodes/bulk', {
            'nodes': [
                {'type': 'filter', 'label': 'Filtre 1', 'position': {'x': 0, 'y': 0}},
                {'type': 'sort', 'label': 'Tri', 'position': {'x': 200, 'y': 0}},
                {'type': 'dedup', 'label': 'Dédup', 'position': {'x': 400, 'y': 0}},
            ],
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['count'] == 3
        assert len(d['nodes']) == 3

    def test_bulk_create_missing_nodes(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/nodes/bulk', {}, headers=auth_headers)
        assert resp.status_code == 400

    def test_unauthenticated(self, client, pipeline_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes')
        assert resp.status_code == 401


class TestPinData:
    def test_pin_and_get(self, client, auth_headers, pipeline_id, node_id):
        data = [{'id': 1, 'montant': 5000}, {'id': 2, 'montant': 12000}]
        pin_resp = post_json(client, f'{PBASE}/{pipeline_id}/nodes/{node_id}/pin-data',
                             {'data': data}, headers=auth_headers)
        assert pin_resp.status_code == 200

        get_resp = client.get(f'{PBASE}/{pipeline_id}/nodes/{node_id}/pinned-data',
                              headers=auth_headers)
        assert get_resp.status_code == 200
        d = get_resp.get_json()
        assert d['data'] == data

    def test_delete_pinned(self, client, auth_headers, pipeline_id, node_id):
        post_json(client, f'{PBASE}/{pipeline_id}/nodes/{node_id}/pin-data',
                  {'data': [{'x': 1}]}, headers=auth_headers)
        del_resp = client.delete(f'{PBASE}/{pipeline_id}/nodes/{node_id}/pinned-data',
                                 headers=auth_headers)
        assert del_resp.status_code == 200

    def test_get_pinned_none(self, client, auth_headers, pipeline_id):
        new_node = post_json(client, f'{PBASE}/{pipeline_id}/nodes',
                             {'type': 'map', 'label': 'Aucune pin'},
                             headers=auth_headers).get_json()
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes/{new_node["id"]}/pinned-data',
                          headers=auth_headers)
        assert resp.status_code == 404

    def test_pin_missing_data(self, client, auth_headers, pipeline_id, node_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/nodes/{node_id}/pin-data',
                         {}, headers=auth_headers)
        assert resp.status_code == 400


class TestTestData:
    def test_get_test_data_mock(self, client, auth_headers, pipeline_id, node_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes/{node_id}/test-data',
                          headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'data' in d
        assert 'source' in d

    def test_get_test_data_pinned(self, client, auth_headers, pipeline_id, node_id):
        pinned = [{'id': 99, 'montant': 99999}]
        post_json(client, f'{PBASE}/{pipeline_id}/nodes/{node_id}/pin-data',
                  {'data': pinned}, headers=auth_headers)
        resp = client.get(f'{PBASE}/{pipeline_id}/nodes/{node_id}/test-data',
                          headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['source'] == 'pinned'
        assert resp.get_json()['data'] == pinned


class TestEdges:
    def test_list_edges(self, client, auth_headers, pipeline_id):
        resp = client.get(f'{PBASE}/{pipeline_id}/edges', headers=auth_headers)
        assert resp.status_code == 200
        assert 'edges' in resp.get_json()

    def test_create_edge(self, client, auth_headers, pipeline_id, node_id, second_node_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/edges', {
            'source': node_id,
            'target': second_node_id,
            'sourceHandle': 'output',
            'targetHandle': 'input',
        }, headers=auth_headers)
        assert resp.status_code == 201
        d = resp.get_json()
        assert d['source'] == node_id
        assert d['target'] == second_node_id

    def test_create_edge_duplicate(self, client, auth_headers, pipeline_id, node_id, second_node_id):
        post_json(client, f'{PBASE}/{pipeline_id}/edges',
                  {'source': node_id, 'target': second_node_id}, headers=auth_headers)
        resp = post_json(client, f'{PBASE}/{pipeline_id}/edges',
                         {'source': node_id, 'target': second_node_id}, headers=auth_headers)
        assert resp.status_code == 409

    def test_create_edge_missing_fields(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/edges',
                         {'source': 'nod_x'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_validate_edges(self, client, auth_headers, pipeline_id):
        resp = post_json(client, f'{PBASE}/{pipeline_id}/edges/validate', {}, headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'valid' in d
        assert 'errors' in d

    def test_delete_edge(self, client, auth_headers, pipeline_id, node_id):
        n3 = post_json(client, f'{PBASE}/{pipeline_id}/nodes',
                       {'type': 'sort', 'label': 'Sort'}, headers=auth_headers).get_json()
        edge = post_json(client, f'{PBASE}/{pipeline_id}/edges',
                         {'source': node_id, 'target': n3['id']}, headers=auth_headers).get_json()
        del_resp = client.delete(f'{PBASE}/{pipeline_id}/edges/{edge["id"]}', headers=auth_headers)
        assert del_resp.status_code == 200


class TestNodeTypes:
    def test_list_node_types(self, client, auth_headers):
        resp = client.get('/api/v1/node-types', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'node_types' in d
        assert 'by_category' in d
        assert len(d['node_types']) == 23

    def test_list_by_category(self, client, auth_headers):
        resp = client.get('/api/v1/node-types?category=Input', headers=auth_headers)
        assert resp.status_code == 200
        types = resp.get_json()['node_types']
        assert all(t['category'] == 'Input' for t in types)

    def test_get_node_type(self, client, auth_headers):
        resp = client.get('/api/v1/node-types/csv_reader', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert d['slug'] == 'csv_reader'
        assert d['category'] == 'Input'

    def test_get_node_type_not_found(self, client, auth_headers):
        resp = client.get('/api/v1/node-types/type_inexistant', headers=auth_headers)
        assert resp.status_code == 404

    def test_get_schema(self, client, auth_headers):
        resp = client.get('/api/v1/node-types/csv_reader/schema', headers=auth_headers)
        assert resp.status_code == 200
        d = resp.get_json()
        assert 'schema' in d
        assert 'properties' in d['schema']

    def test_categories_present(self, client, auth_headers):
        resp = client.get('/api/v1/node-types', headers=auth_headers)
        categories = set(t['category'] for t in resp.get_json()['node_types'])
        assert 'Input' in categories
        assert 'Transform' in categories
        assert 'Output' in categories
