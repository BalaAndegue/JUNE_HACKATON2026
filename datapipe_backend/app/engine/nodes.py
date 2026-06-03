"""
Node executors — the real transformations.

Each executor takes (node, inputs, ctx) where:
  - node   : the SQLAlchemy Node (node.config, node.type_slug, node.label)
  - inputs : list[pandas.DataFrame] coming from upstream edges (ordered)
  - ctx    : ExecutionContext (file loading, logging, warnings)

and returns (output_df, extra) where `extra` is a JSON-safe dict of
node-specific metrics surfaced in the UI.
"""
import os

import numpy as np
import pandas as pd

from . import quality


class NodeError(Exception):
    """Raised on an unrecoverable node error (fails just that node)."""


# ─────────────────────────────── helpers ─────────────────────────────────────

def _first_input(inputs):
    if not inputs:
        return pd.DataFrame()
    return inputs[0]


def _coerce_value(value, series):
    """Coerce a filter value to the dtype of the column being compared."""
    if pd.api.types.is_numeric_dtype(series):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    return value


# ─────────────────────────────── sources ─────────────────────────────────────

def exec_csv_reader(node, inputs, ctx):
    cfg = node.config
    file_id = cfg.get('file_id')
    if not file_id:
        ctx.warn(node, "Aucun fichier sélectionné — sortie vide")
        return pd.DataFrame(), {'source': None}
    df = ctx.load_csv(file_id, cfg)
    return df, {'source': file_id, 'rows_read': len(df)}


def exec_json_reader(node, inputs, ctx):
    cfg = node.config
    file_id = cfg.get('file_id')
    if not file_id:
        ctx.warn(node, "Aucun fichier sélectionné — sortie vide")
        return pd.DataFrame(), {'source': None}
    df = ctx.load_json(file_id, cfg)
    return df, {'source': file_id, 'rows_read': len(df)}


def exec_sql_query(node, inputs, ctx):
    """SQL source: query a real datasource (SQLite) if attached, else read a file."""
    cfg = node.config
    ds_id = cfg.get('datasource_id')
    query = cfg.get('query')
    if ds_id:
        df = ctx.query_datasource(ds_id, query or 'SELECT * FROM sqlite_master', cfg.get('limit'))
        return df, {'rows_read': len(df), 'source': 'datasource'}
    file_id = cfg.get('file_id')
    if file_id:
        df = ctx.load_csv(file_id, cfg)
        if query:
            df = ctx.run_sql(query, df)
        return df, {'rows_read': len(df), 'source': 'file'}
    ctx.warn(node, "SQL source sans datasource ni fichier — sortie vide")
    return pd.DataFrame(), {}


def exec_http_request(node, inputs, ctx):
    """HTTP source: fetch JSON from an API and normalise it to rows."""
    cfg = node.config
    url = cfg.get('url')
    if not url:
        ctx.warn(node, "HTTP source sans URL — sortie vide")
        return pd.DataFrame(), {}
    df = ctx.fetch_http(url, cfg.get('method', 'GET'), cfg.get('headers'), cfg.get('body'))
    return df, {'rows_read': len(df), 'source': url}


# ─────────────────────────────── transforms ──────────────────────────────────

_OPS = {
    'eq': lambda s, v: s == v,
    'neq': lambda s, v: s != v,
    'gt': lambda s, v: s > v,
    'lt': lambda s, v: s < v,
    'gte': lambda s, v: s >= v,
    'lte': lambda s, v: s <= v,
    'contains': lambda s, v: s.astype(str).str.contains(str(v), case=False, na=False),
    'is_null': lambda s, v: s.isna(),
    'is_not_null': lambda s, v: s.notna(),
}


def exec_filter(node, inputs, ctx):
    df = _first_input(inputs).copy()
    if df.empty:
        return df, {'rows_in': 0, 'rows_out': 0}
    cfg = node.config
    conditions = cfg.get('conditions') or []
    # Support the simplified single-condition shape used by the AI agent.
    if not conditions and cfg.get('column') and cfg.get('operator'):
        op_map = {'>': 'gt', '<': 'lt', '>=': 'gte', '<=': 'lte', '=': 'eq', '!=': 'neq'}
        conditions = [{
            'field': cfg['column'],
            'operator': op_map.get(cfg['operator'], cfg['operator']),
            'value': cfg.get('value'),
        }]
    logic = (cfg.get('logic') or 'AND').upper()

    mask = None
    rows_in = len(df)
    for cond in conditions:
        field = cond.get('field')
        op = cond.get('operator')
        if field not in df.columns or op not in _OPS:
            ctx.warn(node, f"Condition ignorée: {field} {op}")
            continue
        value = _coerce_value(cond.get('value'), df[field])
        col = df[field]
        if op in ('gt', 'lt', 'gte', 'lte'):
            col = pd.to_numeric(col, errors='coerce')
        m = _OPS[op](col, value)
        mask = m if mask is None else (mask & m if logic == 'AND' else mask | m)

    if mask is not None:
        df = df[mask.fillna(False)]
    return df, {'rows_in': rows_in, 'rows_out': len(df),
                'removed': rows_in - len(df)}


def exec_map(node, inputs, ctx):
    """Rename / drop columns (config: mappings[{source,target}], drops[], renames{})."""
    df = _first_input(inputs).copy()
    cfg = node.config
    renames = {}
    for m in cfg.get('mappings') or []:
        if m.get('source') and m.get('target'):
            renames[m['source']] = m['target']
    renames.update(cfg.get('renames') or {})
    if renames:
        df = df.rename(columns=renames)
    for col in cfg.get('drops') or []:
        if col in df.columns:
            df = df.drop(columns=[col])
    return df, {'renamed': list(renames.keys()), 'columns': quality.df_columns(df)}


_AGG_FUNCS = {
    'sum': 'sum', 'avg': 'mean', 'mean': 'mean', 'min': 'min',
    'max': 'max', 'count': 'count', 'count_distinct': 'nunique',
}


def exec_aggregate(node, inputs, ctx):
    df = _first_input(inputs).copy()
    if df.empty:
        return df, {}
    cfg = node.config
    group_by = cfg.get('group_by') or cfg.get('groupBy') or []
    group_by = [g for g in group_by if g in df.columns]
    aggs = cfg.get('aggregations') or cfg.get('aggregates') or []

    if not aggs:
        ctx.warn(node, "Aucune agrégation définie")
        return df, {}

    spec = {}
    rename = {}
    for a in aggs:
        field = a.get('field') or a.get('column')
        func = (a.get('function') or a.get('func') or 'count').lower()
        alias = a.get('alias') or f"{func}_{field}"
        pandas_func = _AGG_FUNCS.get(func, 'count')
        if field and field in df.columns:
            if pandas_func in ('sum', 'mean', 'min', 'max'):
                df[field] = pd.to_numeric(df[field], errors='coerce')
            spec.setdefault(field, []).append((alias, pandas_func))

    if group_by:
        grouped = df.groupby(group_by, dropna=False)
        out = pd.DataFrame()
        for field, pairs in spec.items():
            for alias, fn in pairs:
                out[alias] = grouped[field].agg(fn)
        out = out.reset_index()
    else:
        row = {}
        for field, pairs in spec.items():
            for alias, fn in pairs:
                row[alias] = getattr(df[field], fn)()
        out = pd.DataFrame([row])
    return out, {'group_by': group_by, 'rows_out': len(out)}


def exec_join(node, inputs, ctx):
    if len(inputs) < 2:
        ctx.warn(node, "Join nécessite 2 entrées")
        return _first_input(inputs), {}
    left, right = inputs[0].copy(), inputs[1].copy()
    cfg = node.config
    how = cfg.get('join_type') or cfg.get('type') or 'inner'
    how = how.lower()
    if how not in ('inner', 'left', 'right', 'outer', 'full'):
        how = 'inner'
    if how == 'full':
        how = 'outer'
    lk = cfg.get('left_key') or cfg.get('leftKey')
    rk = cfg.get('right_key') or cfg.get('rightKey')
    if not lk or not rk or lk not in left.columns or rk not in right.columns:
        raise NodeError(f"Clés de jointure invalides ({lk}, {rk})")
    out = left.merge(right, left_on=lk, right_on=rk, how=how, suffixes=('', '_right'))
    return out, {'how': how, 'rows_out': len(out)}


def exec_sort(node, inputs, ctx):
    df = _first_input(inputs).copy()
    cfg = node.config
    by, asc = [], []
    for s in cfg.get('sort_by') or cfg.get('sortBy') or []:
        if s.get('field') in df.columns:
            by.append(s['field'])
            asc.append((s.get('direction', 'asc').lower() != 'desc'))
    if by:
        df = df.sort_values(by=by, ascending=asc, kind='mergesort')
    return df, {'sorted_by': by}


def exec_dedup(node, inputs, ctx):
    df = _first_input(inputs).copy()
    cfg = node.config
    rows_in = len(df)
    keys = [k for k in (cfg.get('keys') or []) if k in df.columns] or None
    keep = cfg.get('keep', 'first')
    df = df.drop_duplicates(subset=keys, keep=keep)
    return df, {'rows_in': rows_in, 'rows_out': len(df),
                'duplicates_removed': rows_in - len(df)}


def exec_sql_transform(node, inputs, ctx):
    df = _first_input(inputs)
    cfg = node.config
    query = cfg.get('query') or cfg.get('generatedSql')
    if not query:
        ctx.warn(node, "Aucune requête SQL")
        return df, {}
    out = ctx.run_sql(query, df)
    return out, {'rows_out': len(out), 'query': query}


def exec_validate(node, inputs, ctx):
    """Validate rows against rules; output valid rows, report invalid ones."""
    df = _first_input(inputs).copy()
    cfg = node.config
    rules = cfg.get('rules') or []
    valid_mask = pd.Series(True, index=df.index)
    violations = []
    for rule in rules:
        field = rule.get('field')
        if field not in df.columns:
            continue
        if rule.get('required'):
            m = df[field].notna()
            bad = int((~m).sum())
            if bad:
                violations.append({'field': field, 'rule': 'required', 'failed': bad})
            valid_mask &= m
        rtype = rule.get('type')
        if rtype in ('number', 'integer'):
            m = pd.to_numeric(df[field], errors='coerce').notna() | df[field].isna()
            bad = int((~m).sum())
            if bad:
                violations.append({'field': field, 'rule': f'type:{rtype}', 'failed': bad})
            valid_mask &= m
    out = df[valid_mask]
    return out, {'rows_in': len(df), 'valid': len(out),
                 'invalid': len(df) - len(out), 'violations': violations}


# ─────────────────────────────── banking nodes ───────────────────────────────

def exec_mask_pii(node, inputs, ctx):
    """Anonymise sensitive columns. config: fields[{field|column, strategy}],
    or auto=True to auto-detect banking PII columns."""
    df = _first_input(inputs).copy()
    if df.empty:
        return df, {'masked_columns': []}
    cfg = node.config
    targets = []
    for f in cfg.get('fields') or []:
        col = f.get('field') or f.get('column')
        if col:
            targets.append({'column': col, 'strategy': f.get('strategy', 'hash')})
    if not targets and cfg.get('auto', True):
        targets = quality.detect_sensitive_columns(df)

    masked = []
    for t in targets:
        col = t['column']
        if col in df.columns:
            df[col] = quality.mask_series(df[col], t['strategy'])
            masked.append({'column': col, 'strategy': t['strategy']})
        else:
            ctx.warn(node, f"Colonne sensible introuvable: {col}")
    return df, {'masked_columns': masked}


def exec_detect_anomalies(node, inputs, ctx):
    """Flag anomalous rows. Adds `is_anomaly` + `anomaly_reason` columns.
    config: field, method(zscore|threshold|negative), threshold, z."""
    df = _first_input(inputs).copy()
    if df.empty:
        return df, {'anomalies': 0}
    cfg = node.config
    field = cfg.get('field') or cfg.get('amount_field') or 'montant'
    if field not in df.columns:
        # fall back to first numeric column
        numerics = df.select_dtypes(include=[np.number]).columns
        if len(numerics) == 0:
            ctx.warn(node, "Aucune colonne numérique pour la détection")
            return df, {'anomalies': 0}
        field = numerics[0]

    values = pd.to_numeric(df[field], errors='coerce')
    reason = pd.Series('', index=df.index)
    flag = pd.Series(False, index=df.index)

    method = cfg.get('method', 'zscore')
    if method in ('zscore', 'all'):
        mean, std = values.mean(), values.std(ddof=0)
        z = cfg.get('z', 3)
        if std and not np.isnan(std):
            zmask = (values - mean).abs() > z * std
            flag |= zmask.fillna(False)
            reason[zmask.fillna(False)] = f"écart > {z}σ"
    if method in ('threshold', 'all'):
        thr = cfg.get('threshold', 5_000_000)
        tmask = values > thr
        flag |= tmask.fillna(False)
        reason[tmask.fillna(False)] = f"montant > {thr}"
    if method in ('negative', 'all'):
        nmask = values < 0
        flag |= nmask.fillna(False)
        reason[nmask.fillna(False)] = "montant négatif"

    df['is_anomaly'] = flag.values
    df['anomaly_reason'] = reason.values
    n = int(flag.sum())
    return df, {'anomalies': n, 'field': field, 'method': method,
                'stats': {
                    'mean': quality._clean_scalar(values.mean()),
                    'std': quality._clean_scalar(values.std(ddof=0)),
                    'min': quality._clean_scalar(values.min()),
                    'max': quality._clean_scalar(values.max()),
                }}


def exec_quality_report(node, inputs, ctx):
    """Pass-through node that computes a quality report on its input."""
    df = _first_input(inputs)
    return df, {'quality': quality.compute_quality(df)}


# ─────────────────────────────── outputs ─────────────────────────────────────

def exec_file_export(node, inputs, ctx):
    df = _first_input(inputs)
    cfg = node.config
    fmt = (cfg.get('format') or 'csv').lower()
    filename = cfg.get('filename') or f"export_{node.id}.{fmt}"
    path = ctx.export_path(filename)
    if fmt == 'json':
        df.to_json(path, orient='records', force_ascii=False, indent=2)
    elif fmt in ('excel', 'xlsx'):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)
    return df, {'exported': filename, 'format': fmt, 'rows': len(df),
                'download_path': path}


def exec_passthrough(node, inputs, ctx):
    return _first_input(inputs), {}


# ─────────────────────────────── registry ────────────────────────────────────

EXECUTORS = {
    'csv_reader': exec_csv_reader,
    'json_reader': exec_json_reader,
    'sql_query': exec_sql_query,
    'http_request': exec_http_request,
    'filter': exec_filter,
    'map': exec_map,
    'aggregate': exec_aggregate,
    'join': exec_join,
    'sort': exec_sort,
    'dedup': exec_dedup,
    'sql_transform': exec_sql_transform,
    'validate': exec_validate,
    'mask_pii': exec_mask_pii,
    'detect_anomalies': exec_detect_anomalies,
    'quality_report': exec_quality_report,
    'file_export': exec_file_export,
    'sql_write': exec_passthrough,
    'webhook_send': exec_passthrough,
    'notification_send': exec_passthrough,
    'merge': exec_passthrough,
    'split': exec_passthrough,
    'schedule_trigger': exec_passthrough,
    # AI transform behaves like a SQL transform once the agent has produced SQL.
    'ai_transform': exec_sql_transform,
}


def get_executor(type_slug):
    return EXECUTORS.get(type_slug, exec_passthrough)
