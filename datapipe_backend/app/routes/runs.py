from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import time
import json

from ..extensions import db
from ..models import Run, RunLog, Node, Pipeline
from ..utils import check_pipeline_access, paginate

runs_bp = Blueprint('runs', __name__)


def _simulate_run(pipeline, run):
    """Simulate pipeline execution node by node."""
    nodes = pipeline.nodes
    results = {}

    run.status = 'running'
    db.session.commit()

    for i, node in enumerate(nodes):
        log = RunLog(
            run_id=run.id,
            node_id=node.id,
            level='info',
            message=f'Executing node: {node.label or node.type_slug}',
        )
        db.session.add(log)

        mock_rows = 100 + (i * 37)
        results[node.id] = {
            'status': 'success',
            'rows_processed': mock_rows,
            'rows_output': mock_rows,
            'duration_ms': 120 + (i * 45),
            'output_preview': [
                {'id': j + 1, 'montant': round(1000 + j * 157.3, 2), 'date': '2026-06-01'}
                for j in range(min(3, mock_rows))
            ],
        }

    run.status = 'success'
    run.finished_at = datetime.utcnow()
    run.node_results = results

    success_log = RunLog(run_id=run.id, level='info', message='Pipeline completed successfully')
    db.session.add(success_log)

    pipeline.last_run_at = run.started_at
    pipeline.last_run_status = 'success'
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

    _simulate_run(pipeline, run)
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
    _simulate_run(pipeline, new_run)
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
