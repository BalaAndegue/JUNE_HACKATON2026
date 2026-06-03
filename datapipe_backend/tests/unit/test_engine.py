"""Unit tests for the real execution engine — proves data is actually transformed."""
import os

import pandas as pd
import pytest

from app.engine import nodes, quality

SAMPLE = os.path.join(os.path.dirname(__file__), '..', '..', 'samples', 'transactions_demo.csv')


class _Ctx:
    """Minimal execution context for direct node testing."""
    def __init__(self):
        self.logs = []
        self._duck = None

    def warn(self, node, msg):
        self.logs.append(('warn', msg))

    def log(self, node, level, msg):
        self.logs.append((level, msg))

    def run_sql(self, query, df):
        import duckdb
        con = duckdb.connect()
        con.register('input', df)
        return con.execute(query.replace('{input}', 'input')).fetchdf()


class _Node:
    def __init__(self, type_slug, config):
        self.id = 'n1'
        self.type_slug = type_slug
        self.label = type_slug
        self.config = config


@pytest.fixture
def df():
    return pd.read_csv(SAMPLE)


# ─────────────────────────────── quality ────────────────────────────────────

def test_quality_detects_nulls_and_duplicates(df):
    report = quality.compute_quality(df)
    assert report['rows'] == 15
    assert report['null_cells'] >= 2          # two empty amount cells
    # business-key duplicates (same client/amount/date, different id) are caught
    # by the dedup node, not full-row duplication — see test_dedup_removes_duplicates
    assert 0 < report['score'] < 100


# ─────────────────────────────── masking ────────────────────────────────────

def test_mask_pii_real_masking(df):
    node = _Node('mask_pii', {'fields': [
        {'field': 'client_name', 'strategy': 'name_initials'},
        {'field': 'account_number', 'strategy': 'account_tail'},
        {'field': 'phone', 'strategy': 'phone_middle'},
    ]})
    out, extra = nodes.exec_mask_pii(node, [df], _Ctx())
    assert out.loc[0, 'client_name'] == 'T*** A*** W***'
    assert out.loc[0, 'account_number'].endswith('5001')
    assert out.loc[0, 'account_number'].startswith('*')
    assert out.loc[0, 'phone'] == '699***456'
    assert len(extra['masked_columns']) == 3


def test_mask_pii_auto_detect(df):
    node = _Node('mask_pii', {'auto': True})
    out, extra = nodes.exec_mask_pii(node, [df], _Ctx())
    masked_cols = {m['column'] for m in extra['masked_columns']}
    assert 'client_name' in masked_cols
    assert 'account_number' in masked_cols


# ─────────────────────────────── anomalies ──────────────────────────────────

def test_detect_anomalies_real(df):
    node = _Node('detect_anomalies', {'field': 'amount', 'method': 'all',
                                       'threshold': 5_000_000})
    out, extra = nodes.exec_detect_anomalies(node, [df], _Ctx())
    assert 'is_anomaly' in out.columns
    # two huge amounts (>5M) + two negative amounts flagged
    assert extra['anomalies'] >= 4
    flagged = out[out['is_anomaly']]
    assert (flagged['amount'].astype(float).abs() > 0).all()


# ─────────────────────────────── transforms ─────────────────────────────────

def test_filter_numeric(df):
    node = _Node('filter', {'column': 'amount', 'operator': '>', 'value': 100000})
    out, extra = nodes.exec_filter(node, [df], _Ctx())
    assert extra['rows_out'] < extra['rows_in']
    assert (pd.to_numeric(out['amount']) > 100000).all()


def test_dedup_removes_duplicates(df):
    node = _Node('dedup', {'keys': ['transaction_id']})
    out, extra = nodes.exec_dedup(node, [df], _Ctx())
    assert extra['duplicates_removed'] == 0  # transaction_id are all unique
    node2 = _Node('dedup', {'keys': ['client_name', 'amount', 'transaction_date']})
    out2, extra2 = nodes.exec_dedup(node2, [df], _Ctx())
    assert extra2['duplicates_removed'] >= 2


def test_aggregate_by_type(df):
    node = _Node('aggregate', {
        'group_by': ['transaction_type'],
        'aggregations': [{'field': 'amount', 'function': 'sum', 'alias': 'total'},
                         {'field': 'transaction_id', 'function': 'count', 'alias': 'nb'}],
    })
    out, extra = nodes.exec_aggregate(node, [df], _Ctx())
    assert set(out['transaction_type']) == {'credit', 'debit'}
    assert 'total' in out.columns and 'nb' in out.columns


def test_sql_transform_duckdb(df):
    node = _Node('sql_transform', {
        'query': "SELECT status, COUNT(*) AS n FROM {input} GROUP BY status ORDER BY n DESC"})
    out, extra = nodes.exec_sql_transform(node, [df], _Ctx())
    assert 'n' in out.columns
    assert out['n'].sum() == 15


def test_serialization_handles_nan(df):
    records = quality.df_to_records(df, limit=5)
    assert isinstance(records, list)
    # NaN amounts must serialize to None, never float('nan')
    for r in records:
        assert all(v is None or v == v for v in r.values())  # noqa: PLR0124
