from flask import Blueprint, request, jsonify, Response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os
import csv as _csv
import io
import json

from ..extensions import db
from ..models import Run, RunLog, Node, Edge, Pipeline, File
from ..engine import execute_pipeline, coerce_value, CycleError
from ..utils import check_pipeline_access, paginate, run_results_path

runs_bp = Blueprint('runs', __name__)


def _persist_full_results(run, datasets):
    """Écrit le dataset complet du nœud terminal sur disque pour l'export/download.

    `node_results` ne conserve qu'un aperçu (10 lignes) ; ce fichier garde toutes
    les lignes du dernier nœud du pipeline (sa sortie finale).
    """
    if not datasets:
        return
    last_node_id = list(datasets.keys())[-1]
    rows = datasets[last_node_id]
    folder, path = run_results_path(run.id)
    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False)
    except Exception:
        current_app.logger.warning(f'Impossible de persister les résultats du run {run.id}')


def _read_file_rows(db_file):
    """Charge les lignes complètes d'un fichier uploadé (CSV/JSON)."""
    if db_file.path and os.path.exists(db_file.path):
        ext = db_file.path.rsplit('.', 1)[-1].lower()
        try:
            with open(db_file.path, 'rb') as fp:
                content = fp.read()
            if ext == 'csv':
                text = content.decode('utf-8', errors='replace')
                reader = _csv.DictReader(io.StringIO(text))
                return [{k: coerce_value(v) for k, v in row.items()} for row in reader]
            if ext == 'json':
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return [r for r in parsed if isinstance(r, dict)]
                return []
        except Exception:
            pass
    # Repli sur l'aperçu stocké en base si le fichier n'est pas lisible sur disque
    return [dict(r) for r in (db_file.preview or [])]


def _file_loader(file_id):
    db_file = File.query.get(file_id)
    if not db_file:
        return []
    return _read_file_rows(db_file)


def _sql_generator(instruction, columns):
    """Génère une requête SQL depuis une instruction NL (pour le nœud ai_transform)."""
    from .ai import generate_sql
    sql, _model, _mock = generate_sql(instruction, columns)
    return sql


def _execute_run(pipeline, run):
    """Exécute réellement le pipeline nœud par nœud via le moteur ETL."""
    run.status = 'running'
    db.session.commit()

    nodes = pipeline.nodes
    edges = Edge.query.filter_by(pipeline_id=pipeline.id).all()

    try:
        result = execute_pipeline(nodes, edges, file_loader=_file_loader,
                                  sql_generator=_sql_generator)
    except CycleError as e:
        run.status = 'error'
        run.error_message = str(e)
        run.finished_at = datetime.utcnow()
        db.session.add(RunLog(run_id=run.id, level='error', message=str(e)))
        pipeline.last_run_at = run.started_at
        pipeline.last_run_status = 'error'
        db.session.commit()
        return

    for lg in result['logs']:
        db.session.add(RunLog(
            run_id=run.id,
            node_id=lg.get('node_id'),
            level=lg.get('level', 'info'),
            message=lg.get('message', ''),
        ))

    run.node_results = result['node_results']
    run.status = result['status']
    run.finished_at = datetime.utcnow()
    _persist_full_results(run, result.get('datasets'))
    if result['status'] == 'error':
        run.error_message = result['error']
    else:
        db.session.add(RunLog(run_id=run.id, level='info',
                              message='Pipeline terminé avec succès'))

    pipeline.last_run_at = run.started_at
    pipeline.last_run_status = result['status']
    db.session.commit()


@runs_bp.route('/pipelines/<pipeline_id>/run', methods=['POST'])
@jwt_required()
def trigger_run(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    if not pipeline.nodes:
        return jsonify({'error': 'Pipeline has no nodes'}), 400

    data = request.get_json() or {}
    run = Run(
        pipeline_id=pipeline_id,
        trigger=data.get('trigger', 'manual'),
        status='pending',
    )
    db.session.add(run)
    db.session.flush()

    _execute_run(pipeline, run)
    return jsonify(run.to_dict(include_results=True)), 201


@runs_bp.route('/pipelines/<pipeline_id>/runs', methods=['GET'])
@jwt_required()
def list_runs(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    q = Run.query.filter_by(pipeline_id=pipeline_id).order_by(Run.started_at.desc())
    if request.args.get('status'):
        q = q.filter_by(status=request.args.get('status'))
    items, pagination = paginate(q)
    return jsonify({'data': [r.to_dict() for r in items], 'pagination': pagination})


@runs_bp.route('/pipelines/<pipeline_id>/runs/<run_id>', methods=['GET'])
@jwt_required()
def get_run(pipeline_id, run_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    run = Run.query.filter_by(id=run_id, pipeline_id=pipeline_id).first()
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    return jsonify(run.to_dict(include_results=True))


@runs_bp.route('/pipelines/<pipeline_id>/runs/<run_id>', methods=['DELETE'])
@jwt_required()
def delete_run(pipeline_id, run_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    run = Run.query.filter_by(id=run_id, pipeline_id=pipeline_id).first()
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    _, path = run_results_path(run.id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    db.session.delete(run)
    db.session.commit()
    return jsonify({'message': 'Run deleted'})


@runs_bp.route('/pipelines/<pipeline_id>/runs/<run_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_run(pipeline_id, run_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    run = Run.query.filter_by(id=run_id, pipeline_id=pipeline_id).first()
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    if run.status not in ('pending', 'running'):
        return jsonify({'error': 'Run cannot be cancelled'}), 400
    run.status = 'cancelled'
    run.finished_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Run cancelled', 'run_id': run_id})


@runs_bp.route('/pipelines/<pipeline_id>/runs/<run_id>/retry', methods=['POST'])
@jwt_required()
def retry_run(pipeline_id, run_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    old_run = Run.query.filter_by(id=run_id, pipeline_id=pipeline_id).first()
    if not old_run:
        return jsonify({'error': 'Run not found'}), 404

    new_run = Run(pipeline_id=pipeline_id, trigger='retry', status='pending')
    db.session.add(new_run)
    db.session.flush()
    _execute_run(pipeline, new_run)
    return jsonify(new_run.to_dict(include_results=True)), 201


@runs_bp.route('/runs/<run_id>/logs', methods=['GET'])
@jwt_required()
def get_logs(run_id):
    run = Run.query.get(run_id)
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    logs = RunLog.query.filter_by(run_id=run_id).order_by(RunLog.timestamp).all()
    return jsonify({'logs': [l.to_dict() for l in logs], 'count': len(logs)})


@runs_bp.route('/runs/<run_id>/logs/stream', methods=['GET'])
@jwt_required()
def stream_logs(run_id):
    run = Run.query.get(run_id)
    if not run:
        return jsonify({'error': 'Run not found'}), 404

    def generate():
        logs = RunLog.query.filter_by(run_id=run_id).order_by(RunLog.timestamp).all()
        for log in logs:
            yield f"data: {json.dumps(log.to_dict())}\n\n"
        yield "data: {\"done\": true}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@runs_bp.route('/runs/<run_id>/nodes/<node_id>/output', methods=['GET'])
@jwt_required()
def get_node_output(run_id, node_id):
    run = Run.query.get(run_id)
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    results = run.node_results
    node_result = results.get(node_id)
    if not node_result:
        return jsonify({'error': 'No output for this node in this run'}), 404
    return jsonify({'run_id': run_id, 'node_id': node_id, 'result': node_result})
