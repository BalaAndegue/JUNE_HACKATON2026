"""
Frontend compatibility layer.

The Next.js client (branche Jeff_Frontend) was built against a slightly
different API contract than the backend exposes. Rather than rewrite the
frontend blind, this blueprint adds alias routes that speak the exact shapes
the client expects, delegating to the real engine and AI logic.

Every route here is covered by tests in tests/integration/test_compat.py.
"""
from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import queue as _queue

from .. import realtime

from ..extensions import db
from ..models import Run, RunLog, Pipeline, File
from ..utils import check_pipeline_access, validate_required
from ..routes.runs import _execute
from ..routes import ai as ai_mod

compat_bp = Blueprint('compat', __name__)


# ─────────────────────────────── helpers ─────────────────────────────────────

def _run_owned(run_id, user_id):
    run = Run.query.get(run_id)
    if not run:
        return None, None, ('Run not found', 404)
    pipeline, err = check_pipeline_access(run.pipeline_id, user_id)
    if err:
        return None, None, (err, 404 if 'not found' in err else 403)
    return run, pipeline, None


def _node_run(node_id, result):
    return {
        'node_id': node_id,
        'status': result.get('status', 'success'),
        'duration_ms': result.get('duration_ms'),
        'rows_out': result.get('rows_output'),
        'rows_in': result.get('rows_processed'),
    }


def _records_to_grid(records, columns=None):
    """DataPreview wants rows as arrays aligned to columns."""
    if not records:
        return columns or [], []
    cols = columns or list(records[0].keys())
    rows = [[r.get(c) for c in cols] for r in records]
    return cols, rows


# ─────────────────────────────── RUN EXECUTION ───────────────────────────────

@compat_bp.route('/pipelines/<pipeline_id>/execute', methods=['POST'])
@jwt_required()
def execute_pipeline_alias(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if not pipeline.nodes:
        return jsonify({'error': 'Pipeline has no nodes'}), 400

    run = Run(pipeline_id=pipeline_id, trigger='manual', status='pending')
    db.session.add(run)
    db.session.flush()
    _execute(pipeline, run, user_id)

    return jsonify({
        'run_id': run.id,
        'status': run.status,
        'pipeline_id': pipeline_id,
        'started_at': run.started_at.isoformat() + 'Z' if run.started_at else None,
        # The run is synchronous: the client can read results immediately.
        'node_results': run.node_results,
        'finished_at': run.finished_at.isoformat() + 'Z' if run.finished_at else None,
        'duration_ms': run.duration_ms,
    }), 201


@compat_bp.route('/pipelines/<pipeline_id>/execute/dry-run', methods=['POST'])
@jwt_required()
def dry_run_alias(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    node_ids = {n.id for n in pipeline.nodes}
    warnings = []
    for e in pipeline.edges:
        if e.source_node_id not in node_ids or e.target_node_id not in node_ids:
            warnings.append(f"Edge {e.id} référence un nœud inexistant")
    return jsonify({
        'valid': len(warnings) == 0,
        'warnings': warnings,
        'estimated_duration_s': max(1, len(pipeline.nodes) // 2),
        'estimated_rows_processed': 0,
    })


@compat_bp.route('/pipelines/<pipeline_id>/events', methods=['GET'])
def pipeline_events(pipeline_id):
    """SSE: real-time pipeline change events (used by the editor to redraw live).
    No JWT: EventSource can't send headers; events are low-sensitivity notifications."""
    q = realtime.subscribe(pipeline_id)

    def stream():
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    msg = q.get(timeout=20)
                    yield f"data: {msg}\n\n"
                except _queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            realtime.unsubscribe(pipeline_id, q)

    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no',
                             'Access-Control-Allow-Origin': '*'})


@compat_bp.route('/runs/<run_id>', methods=['GET'])
@jwt_required()
def get_run_alias(run_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    results = run.node_results
    return jsonify({
        'id': run.id,
        'status': run.status,
        'pipeline_id': run.pipeline_id,
        'duration_ms': run.duration_ms,
        'rows_processed': sum((r.get('rows_output') or 0) for r in results.values()),
        'nodes_executed': len(results),
        'started_at': run.started_at.isoformat() + 'Z' if run.started_at else None,
        'finished_at': run.finished_at.isoformat() + 'Z' if run.finished_at else None,
        'node_results': results,
    })


@compat_bp.route('/runs/<run_id>/nodes', methods=['GET'])
@jwt_required()
def run_nodes_alias(run_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    nodes = [_node_run(nid, res) for nid, res in run.node_results.items()]
    return jsonify({'nodes': nodes})


@compat_bp.route('/runs/<run_id>/nodes/<node_id>', methods=['GET'])
@jwt_required()
def run_node_alias(run_id, node_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    res = run.node_results.get(node_id)
    if not res:
        return jsonify({'error': 'No result for this node'}), 404
    return jsonify(_node_run(node_id, res))


@compat_bp.route('/runs/<run_id>/nodes/<node_id>/preview', methods=['GET'])
@jwt_required()
def run_node_preview_alias(run_id, node_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    res = run.node_results.get(node_id) or {}
    records = res.get('output_preview', [])
    limit = request.args.get('limit', 50, type=int)
    cols, rows = _records_to_grid(records[:limit], res.get('columns'))
    return jsonify({
        'columns': cols,
        'rows': rows,
        'total_rows': res.get('rows_output', len(rows)),
        'truncated': res.get('rows_output', 0) > len(rows),
        # extras the banking UI can surface (quality, masking, anomalies)
        'quality': res.get('quality'),
        'extra': res.get('extra'),
    })


@compat_bp.route('/runs/<run_id>/nodes/<node_id>/stats', methods=['GET'])
@jwt_required()
def run_node_stats_alias(run_id, node_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    res = run.node_results.get(node_id) or {}
    quality = res.get('quality') or {}
    schema = [{'name': c['name'], 'type': c['dtype']}
              for c in quality.get('columns_detail', [])]
    return jsonify({
        'rows_in': res.get('rows_processed', 0),
        'rows_out': res.get('rows_output', 0),
        'columns_count': quality.get('columns', len(res.get('columns', []))),
        'size_bytes': 0,
        'duration_ms': res.get('duration_ms', 0),
        'schema': schema,
    })


@compat_bp.route('/runs/<run_id>/result', methods=['GET'])
@jwt_required()
def run_result_alias(run_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    return jsonify({'run_id': run_id, 'node_results': run.node_results})


@compat_bp.route('/runs/<run_id>/audit-report', methods=['GET'])
@jwt_required()
def run_audit_report(run_id):
    """
    Banking compliance report for a run — a real, exportable audit trail.

    Beyond an ETL: proves WHAT happened to sensitive data (anonymisation,
    anomalies flagged, quality before/after) for internal control & conformité.
    """
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    from ..agent_exec import build_audit_report
    return jsonify(build_audit_report(run, pipeline))


@compat_bp.route('/runs/<run_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_run_alias(run_id):
    run, pipeline, err = _run_owned(run_id, get_jwt_identity())
    if err:
        return jsonify({'error': err[0]}), err[1]
    if run.status not in ('pending', 'running'):
        # synchronous runs finish instantly; report current state gracefully
        return jsonify({'status': run.status, 'cancelled_at': None})
    run.status = 'cancelled'
    run.finished_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'cancelled', 'cancelled_at': run.finished_at.isoformat() + 'Z'})


@compat_bp.route('/runs/<run_id>/retry', methods=['POST'])
@jwt_required()
def retry_run_alias(run_id):
    user_id = get_jwt_identity()
    run, pipeline, err = _run_owned(run_id, user_id)
    if err:
        return jsonify({'error': err[0]}), err[1]
    new_run = Run(pipeline_id=run.pipeline_id, trigger='retry', status='pending')
    db.session.add(new_run)
    db.session.flush()
    _execute(pipeline, new_run, user_id)
    return jsonify({'new_run_id': new_run.id, 'status': new_run.status}), 201


# ─────────────────────────────── FILES ───────────────────────────────────────

@compat_bp.route('/files/<file_id>/schema', methods=['GET'])
@jwt_required()
def file_schema_alias(file_id):
    f = File.query.get(file_id)
    if not f:
        return jsonify({'error': 'File not found'}), 404
    columns = []
    for col in f.columns:
        sample = [row.get(col) for row in f.preview if isinstance(row, dict)]
        inferred = 'string'
        nums = [v for v in sample if v not in (None, '')]
        if nums:
            try:
                [float(v) for v in nums]
                inferred = 'number'
            except (ValueError, TypeError):
                pass
        columns.append({'name': col, 'type': inferred, 'nullable': True})
    return jsonify({'columns': columns})


# ─────────────────────────────── AI ALIASES ──────────────────────────────────

def _model_name(used_mock):
    if used_mock:
        return 'datapipe-analyst'
    return ai_mod._llm_model_name()


@compat_bp.route('/ai/generate/pipeline', methods=['POST'])
@jwt_required()
def ai_generate_pipeline_alias():
    data = request.get_json() or {}
    prompt = data.get('prompt') or data.get('goal') or ''
    node_types = ai_mod._detect_nodes(prompt)
    nodes, edges = ai_mod._build_nodes_and_edges(node_types, prompt)
    explanation = ai_mod._build_explanation(node_types)
    return jsonify({
        'pipeline': {'nodes': nodes, 'edges': edges},
        'explanation': explanation,
        'tokens_used': ai_mod.AI_USAGE.get('tokens_used', 0),
    })


@compat_bp.route('/ai/generate/sql', methods=['POST'])
@jwt_required()
def ai_generate_sql_alias():
    data = request.get_json() or {}
    prompt = data.get('prompt') or data.get('description') or ''
    schema = data.get('schema') or []
    columns = [c.get('name') if isinstance(c, dict) else c for c in schema] or [
        'montant', 'devise', 'date_transaction', 'transaction_type', 'statut']
    sql, explanation, used_mock = ai_mod._agent_sql_and_explanation(prompt, columns)
    return jsonify({'sql': sql, 'explanation': explanation,
                    'tokens_used': ai_mod.AI_USAGE.get('tokens_used', 0),
                    'model': _model_name(used_mock)})


@compat_bp.route('/ai/generate/code', methods=['POST'])
@jwt_required()
def ai_generate_code_alias():
    data = request.get_json() or {}
    prompt = data.get('prompt') or ''
    schema = data.get('schema') or []
    columns = [c.get('name') if isinstance(c, dict) else c for c in schema] or ['montant']
    sql, explanation, used_mock = ai_mod._agent_sql_and_explanation(prompt, columns)
    return jsonify({'code': sql, 'language': 'sql', 'explanation': explanation,
                    'tokens_used': ai_mod.AI_USAGE.get('tokens_used', 0)})


@compat_bp.route('/ai/generate/filter', methods=['POST'])
@jwt_required()
def ai_generate_filter_alias():
    data = request.get_json() or {}
    cfg = ai_mod._extract_filter_config(data.get('prompt', ''))
    expr = f"{cfg['column']} {cfg['operator']} {cfg['value']}"
    return jsonify({'expression': expr, 'columns_used': [cfg['column']]})


@compat_bp.route('/ai/suggest/columns', methods=['POST'])
@jwt_required()
def ai_suggest_columns_alias():
    data = request.get_json() or {}
    schema = data.get('schema') or []
    suggestions = [{'column': (c.get('name') if isinstance(c, dict) else c),
                    'confidence': 0.8, 'reason': 'Colonne pertinente détectée'}
                   for c in schema[:5]]
    return jsonify({'suggestions': suggestions})


@compat_bp.route('/ai/suggest/joins', methods=['POST'])
@jwt_required()
def ai_suggest_joins_alias():
    data = request.get_json() or {}
    left = [c.get('name') if isinstance(c, dict) else c for c in (data.get('schema_left') or [])]
    right = [c.get('name') if isinstance(c, dict) else c for c in (data.get('schema_right') or [])]
    common = [c for c in left if c in right]
    suggestions = [{'left_key': c, 'right_key': c, 'confidence': 0.9,
                    'reason': 'Colonne commune aux deux jeux de données'} for c in common[:3]]
    return jsonify({'suggestions': suggestions})


@compat_bp.route('/ai/suggest/pipeline', methods=['POST'])
@jwt_required()
def ai_suggest_pipeline_alias():
    data = request.get_json() or {}
    goal = data.get('goal', '')
    node_types = ai_mod._detect_nodes(goal)
    return jsonify({'suggestion': ai_mod._build_explanation(node_types),
                    'reasoning': f"Détecté {len(node_types)} étapes pertinentes",
                    'generate_now': True})


@compat_bp.route('/ai/explain/sql', methods=['POST'])
@jwt_required()
def ai_explain_sql_alias():
    data = request.get_json() or {}
    sql = data.get('sql', '')
    resp = ai_mod._call_llm(
        system="Tu expliques des requêtes SQL en français simple.",
        messages=[{'role': 'user', 'content': f"Explique en 2 phrases : {sql}"}])
    if not resp:
        resp = "Cette requête sélectionne et transforme les données selon les colonnes et conditions spécifiées."
    return jsonify({'explanation': resp, 'level': 'beginner'})


@compat_bp.route('/ai/explain/error', methods=['POST'])
@jwt_required()
def ai_explain_error_alias():
    data = request.get_json() or {}
    msg = data.get('error_message', '')
    return jsonify({
        'plain_explanation': f"Une erreur est survenue : {msg}",
        'suggested_fix': "Vérifiez les noms de colonnes et le format des données en entrée.",
        'severity': 'medium',
    })


@compat_bp.route('/ai/history', methods=['GET'])
@jwt_required()
def ai_history_alias():
    return jsonify({'sessions': []})
