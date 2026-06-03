"""Tests unitaires du moteur d'exécution ETL réel (app/engine.py)."""
import pytest

from app.engine import execute_pipeline, coerce_value, CycleError


class FakeNode:
    def __init__(self, id, type_slug, config=None, label=None):
        self.id = id
        self.type_slug = type_slug
        self.config = config or {}
        self.label = label


class FakeEdge:
    def __init__(self, source, target):
        self.source_node_id = source
        self.target_node_id = target


TX = [
    {'id': 1, 'montant': 1500, 'type': 'virement', 'region': 'Abidjan', 'client': 'A'},
    {'id': 2, 'montant': 80000, 'type': 'virement', 'region': 'Abidjan', 'client': 'B'},
    {'id': 3, 'montant': 50, 'type': 'retrait', 'region': 'Bouake', 'client': 'A'},
    {'id': 4, 'montant': 120000, 'type': 'virement', 'region': 'Bouake', 'client': 'C'},
    {'id': 5, 'montant': 9000, 'type': 'retrait', 'region': 'Abidjan', 'client': 'B'},
]


def run(nodes, edges, loader=None):
    return execute_pipeline(nodes, edges, file_loader=loader)


# ─────────────────────────── Coercition ──────────────────────────────────────

class TestCoerce:
    def test_int(self):
        assert coerce_value('42') == 42

    def test_float(self):
        assert coerce_value('3.14') == 3.14

    def test_text_kept(self):
        assert coerce_value('abc') == 'abc'

    def test_non_string_passthrough(self):
        assert coerce_value(10) == 10
        assert coerce_value(None) is None


# ─────────────────────────── Transforms ──────────────────────────────────────

class TestFilter:
    def test_gt_numeric(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('f', 'filter', {'conditions': [{'field': 'montant', 'operator': 'gt', 'value': 50000}]}),
        ]
        res = run(nodes, [FakeEdge('r', 'f')], loader=lambda fid: TX)
        assert res['status'] == 'success'
        out = res['node_results']['f']
        assert out['rows_output'] == 2
        assert {r['id'] for r in out['output_preview']} == {2, 4}

    def test_or_logic(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('f', 'filter', {'logic': 'OR', 'conditions': [
                {'field': 'type', 'operator': 'eq', 'value': 'retrait'},
                {'field': 'montant', 'operator': 'gte', 'value': 100000},
            ]}),
        ]
        res = run(nodes, [FakeEdge('r', 'f')], loader=lambda fid: TX)
        assert res['node_results']['f']['rows_output'] == 3  # id 3,5 (retrait) + id 4 (>=100000)


class TestAggregate:
    def test_group_sum_count(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('a', 'aggregate', {'group_by': ['region'], 'aggregations': [
                {'field': 'montant', 'function': 'sum', 'alias': 'total'},
                {'field': 'id', 'function': 'count', 'alias': 'nb'},
            ]}),
        ]
        res = run(nodes, [FakeEdge('r', 'a')], loader=lambda fid: TX)
        rows = {r['region']: r for r in res['node_results']['a']['output_preview']}
        assert rows['Abidjan']['total'] == 1500 + 80000 + 9000
        assert rows['Abidjan']['nb'] == 3
        assert rows['Bouake']['total'] == 50 + 120000


class TestJoin:
    def test_inner_join(self):
        left = [{'client': 'A', 'pays': 'CI'}, {'client': 'B', 'pays': 'SN'}]
        nodes = [
            FakeNode('l', 'json_reader', {'file_id': 'L'}),
            FakeNode('r', 'json_reader', {'file_id': 'R'}),
            FakeNode('j', 'join', {'join_type': 'inner', 'left_key': 'client', 'right_key': 'client'}),
        ]
        edges = [FakeEdge('l', 'j'), FakeEdge('r', 'j')]
        loader = lambda fid: left if fid == 'L' else TX
        res = run(nodes, edges, loader=loader)
        out = res['node_results']['j']['output_preview']
        # 3 transactions client A/B (id 1,2,5) ont une correspondance
        assert res['node_results']['j']['rows_output'] == 4  # A:1,3 ; B:2,5 -> clients A(2)+B(2)
        assert all('pays' in r for r in out)


class TestSort:
    def test_desc(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('s', 'sort', {'sort_by': [{'field': 'montant', 'direction': 'desc'}]}),
        ]
        res = run(nodes, [FakeEdge('r', 's')], loader=lambda fid: TX)
        montants = [r['montant'] for r in res['node_results']['s']['output_preview']]
        assert montants == sorted(montants, reverse=True)


class TestDedup:
    def test_dedup_on_key(self):
        data = [{'k': 1, 'v': 'a'}, {'k': 1, 'v': 'b'}, {'k': 2, 'v': 'c'}]
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('d', 'dedup', {'keys': ['k'], 'keep': 'first'}),
        ]
        res = run(nodes, [FakeEdge('r', 'd')], loader=lambda fid: data)
        out = res['node_results']['d']['output_preview']
        assert res['node_results']['d']['rows_output'] == 2
        assert out[0]['v'] == 'a'


class TestSqlTransform:
    def test_group_by_sql(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('q', 'sql_transform', {
                'query': 'SELECT region, SUM(montant) as total FROM {input} GROUP BY region ORDER BY total DESC'}),
        ]
        res = run(nodes, [FakeEdge('r', 'q')], loader=lambda fid: TX)
        out = res['node_results']['q']['output_preview']
        assert out[0]['region'] == 'Bouake'  # 120050 > Abidjan 90500
        assert out[0]['total'] == 120050

    def test_dangerous_sql_blocked(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('q', 'sql_transform', {'query': 'DROP TABLE input'}),
        ]
        res = run(nodes, [FakeEdge('r', 'q')], loader=lambda fid: TX)
        assert res['status'] == 'error'
        assert res['node_results']['q']['status'] == 'error'


class TestMerge:
    def test_merge_concatenates(self):
        nodes = [
            FakeNode('a', 'json_reader', {'file_id': 'A'}),
            FakeNode('b', 'json_reader', {'file_id': 'B'}),
            FakeNode('m', 'merge', {}),
        ]
        edges = [FakeEdge('a', 'm'), FakeEdge('b', 'm')]
        loader = lambda fid: [{'x': 1}] if fid == 'A' else [{'x': 2}, {'x': 3}]
        res = run(nodes, edges, loader=loader)
        assert res['node_results']['m']['rows_output'] == 3


class TestGraph:
    def test_cycle_detected(self):
        nodes = [FakeNode('a', 'filter', {}), FakeNode('b', 'filter', {})]
        edges = [FakeEdge('a', 'b'), FakeEdge('b', 'a')]
        with pytest.raises(CycleError):
            run(nodes, edges)

    def test_reader_without_file_is_empty_but_succeeds(self):
        nodes = [FakeNode('r', 'csv_reader', {})]
        res = run(nodes, [])
        assert res['status'] == 'success'
        assert res['node_results']['r']['rows_output'] == 0

    def test_topological_order_chain(self):
        nodes = [
            FakeNode('r', 'json_reader', {'file_id': 'F'}),
            FakeNode('f', 'filter', {'conditions': [{'field': 'montant', 'operator': 'gt', 'value': 0}]}),
            FakeNode('a', 'aggregate', {'group_by': ['type'], 'aggregations': [
                {'field': 'id', 'function': 'count', 'alias': 'nb'}]}),
        ]
        edges = [FakeEdge('r', 'f'), FakeEdge('f', 'a')]
        res = run(nodes, edges, loader=lambda fid: TX)
        assert res['status'] == 'success'
        nb_by_type = {r['type']: r['nb'] for r in res['node_results']['a']['output_preview']}
        assert nb_by_type == {'virement': 3, 'retrait': 2}
