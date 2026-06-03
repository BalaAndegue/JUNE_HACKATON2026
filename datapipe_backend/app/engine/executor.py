"""
Pipeline orchestrator.

Computes a topological order over the node graph and runs each node with real
data. Produces a `node_results` dict that stays backward-compatible with the
previous simulated runner (same keys) while adding real metrics, previews,
column lists and a real per-step data-quality score.
"""
import os
import re
import time

import pandas as pd

from . import nodes, quality

PREVIEW_ROWS = 20
DANGEROUS_SQL = re.compile(r'\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE|ATTACH|COPY|PRAGMA)\b', re.I)


class ExecutionContext:
    """Per-run services: file loading, SQL execution, logging."""

    def __init__(self, upload_folder, logger=None):
        self.upload_folder = upload_folder
        self.logger = logger
        self.logs = []          # [(node_id, level, message)]
        self._duck = None

    # --- logging -------------------------------------------------------------
    def log(self, node, level, message):
        node_id = node.id if node is not None else None
        self.logs.append((node_id, level, message))

    def warn(self, node, message):
        self.log(node, 'warn', message)

    # --- file loading --------------------------------------------------------
    def _file_path(self, file_id):
        from ..models import File
        f = File.query.get(file_id)
        if not f or not f.path or not os.path.exists(f.path):
            return None
        return f.path

    def load_csv(self, file_id, cfg):
        path = self._file_path(file_id)
        if not path:
            return pd.DataFrame()
        delimiter = cfg.get('delimiter') or cfg.get('separator') or ','
        encoding = cfg.get('encoding') or 'utf-8'
        try:
            return pd.read_csv(path, sep=delimiter, encoding=encoding,
                               keep_default_na=True, on_bad_lines='skip')
        except Exception:
            return pd.read_csv(path, sep=delimiter, encoding='latin-1',
                               on_bad_lines='skip')

    def load_json(self, file_id, cfg):
        path = self._file_path(file_id)
        if not path:
            return pd.DataFrame()
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)

    # --- SQL -----------------------------------------------------------------
    def run_sql(self, query, input_df):
        if DANGEROUS_SQL.search(query or ''):
            raise nodes.NodeError("Requête SQL non autorisée (mutation détectée)")
        import duckdb
        if self._duck is None:
            self._duck = duckdb.connect()
        con = self._duck
        df = input_df if input_df is not None else pd.DataFrame()
        con.register('input', df)
        sql = (query or '').replace('{input}', 'input')
        # If the user query has no FROM input but references the table name,
        # DuckDB resolves the registered view directly.
        return con.execute(sql).fetchdf()

    def export_path(self, filename):
        out_dir = os.path.join(self.upload_folder, 'exports')
        os.makedirs(out_dir, exist_ok=True)
        return os.path.join(out_dir, filename)


def _topological_order(node_ids, edges):
    """Kahn's algorithm. Returns (ordered_ids, has_cycle)."""
    incoming = {nid: 0 for nid in node_ids}
    adj = {nid: [] for nid in node_ids}
    for e in edges:
        s, t = e.source_node_id, e.target_node_id
        if s in adj and t in incoming:
            adj[s].append(t)
            incoming[t] += 1
    queue = [nid for nid in node_ids if incoming[nid] == 0]
    # stable-ish ordering: keep declaration order
    queue.sort(key=lambda n: node_ids.index(n))
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in adj[n]:
            incoming[m] -= 1
            if incoming[m] == 0:
                queue.append(m)
    return order, len(order) != len(node_ids)


def _inputs_for(node_id, edges, outputs):
    """Collect upstream DataFrames feeding a node (ordered by edge order)."""
    ins = []
    for e in edges:
        if e.target_node_id == node_id and e.source_node_id in outputs:
            ins.append(outputs[e.source_node_id])
    return ins


def execute_pipeline(pipeline, run, ctx=None):
    """
    Execute a pipeline for real.

    Mutates `run` (status, node_results, finished_at) and returns a list of
    log tuples (node_id, level, message) for the caller to persist.
    """
    from datetime import datetime
    from flask import current_app

    if ctx is None:
        ctx = ExecutionContext(current_app.config['UPLOAD_FOLDER'])

    node_list = list(pipeline.nodes)
    node_ids = [n.id for n in node_list]
    node_by_id = {n.id: n for n in node_list}
    edges = list(pipeline.edges)

    order, has_cycle = _topological_order(node_ids, edges)
    if has_cycle:
        run.status = 'error'
        run.error_message = "Cycle détecté dans le pipeline"
        run.finished_at = datetime.utcnow()
        ctx.log(None, 'error', run.error_message)
        return ctx.logs

    ctx.log(None, 'info', f"Exécution de {len(order)} nœud(s)")

    outputs = {}
    results = {}
    run_failed = False

    for nid in order:
        node = node_by_id[nid]
        inputs = _inputs_for(nid, edges, outputs)
        rows_in = sum(len(df) for df in inputs)
        start = time.perf_counter()
        ctx.log(node, 'info', f"▶ {node.label or node.type_slug}")
        try:
            executor = nodes.get_executor(node.type_slug)
            out_df, extra = executor(node, inputs, ctx)
            if out_df is None:
                out_df = pd.DataFrame()
            outputs[nid] = out_df
            duration_ms = int((time.perf_counter() - start) * 1000)
            results[nid] = {
                'status': 'success',
                'rows_processed': rows_in,
                'rows_output': len(out_df),
                'duration_ms': duration_ms,
                'columns': quality.df_columns(out_df),
                'output_preview': quality.df_to_records(out_df, PREVIEW_ROWS),
                'quality': quality.compute_quality(out_df),
                'extra': extra,
            }
            ctx.log(node, 'info',
                    f"✓ {node.label or node.type_slug}: {len(out_df)} ligne(s)")
        except Exception as exc:  # noqa: BLE001 — isolate node failures
            duration_ms = int((time.perf_counter() - start) * 1000)
            outputs[nid] = pd.DataFrame()
            results[nid] = {
                'status': 'error',
                'rows_processed': rows_in,
                'rows_output': 0,
                'duration_ms': duration_ms,
                'error': str(exc),
                'output_preview': [],
            }
            run_failed = True
            ctx.log(node, 'error', f"✗ {node.label or node.type_slug}: {exc}")

    run.status = 'error' if run_failed else 'success'
    run.finished_at = datetime.utcnow()
    run.node_results = results

    if not run_failed:
        ctx.log(None, 'info', 'Pipeline terminé avec succès')
    return ctx.logs
