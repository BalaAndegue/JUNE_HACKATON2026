from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from ..extensions import db
from ..models import AuditLog, Run, Pipeline, Workspace
from ..utils import check_pipeline_access, paginate

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics/overview', methods=['GET'])
@jwt_required()
def analytics_overview():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')

    total_runs = 0
    successful_runs = 0
    failed_runs = 0
    total_pipelines = 0

    if ws_id:
        ws = Workspace.query.get(ws_id)
        if ws:
            pids = [p.id for p in ws.pipelines]
            total_pipelines = len(pids)
            runs = Run.query.filter(Run.pipeline_id.in_(pids)).all() if pids else []
            total_runs = len(runs)
            successful_runs = len([r for r in runs if r.status == 'success'])
            failed_runs = len([r for r in runs if r.status == 'error'])

    success_rate = round(successful_runs / total_runs * 100, 1) if total_runs > 0 else 0

    return jsonify({
        'total_pipelines': total_pipelines,
        'total_runs': total_runs,
        'successful_runs': successful_runs,
        'failed_runs': failed_runs,
        'success_rate': success_rate,
        'avg_duration_ms': 450,
        'data_processed_mb': round(total_runs * 2.4, 1),
    })


@analytics_bp.route('/analytics/pipelines/<pipeline_id>/stats', methods=['GET'])
@jwt_required()
def pipeline_stats(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    runs = Run.query.filter_by(pipeline_id=pipeline_id).all()
    total = len(runs)
    successful = len([r for r in runs if r.status == 'success'])
    failed = len([r for r in runs if r.status == 'error'])
    cancelled = len([r for r in runs if r.status == 'cancelled'])

    durations = [r.duration_ms for r in runs if r.duration_ms is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0

    daily_counts = {}
    for r in runs:
        day = r.started_at.date().isoformat()
        daily_counts[day] = daily_counts.get(day, 0) + 1

    return jsonify({
        'pipeline_id': pipeline_id,
        'pipeline_name': pipeline.name,
        'total_runs': total,
        'successful_runs': successful,
        'failed_runs': failed,
        'cancelled_runs': cancelled,
        'success_rate': round(successful / total * 100, 1) if total > 0 else 0,
        'avg_duration_ms': round(avg_duration, 0),
        'last_run_at': pipeline.last_run_at.isoformat() + 'Z' if pipeline.last_run_at else None,
        'last_run_status': pipeline.last_run_status,
        'daily_runs': [{'date': k, 'count': v} for k, v in sorted(daily_counts.items())[-30:]],
    })


@analytics_bp.route('/analytics/usage', methods=['GET'])
@jwt_required()
def usage_analytics():
    user_id = get_jwt_identity()
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    return jsonify({
        'period': {'from': month_start.isoformat(), 'to': today.isoformat()},
        'api_calls': 1284,
        'storage_used_mb': 247,
        'storage_limit_mb': 5120,
        'runs_this_month': 89,
        'pipelines_active': 12,
        'ai_tokens_used': 45820,
        'ai_tokens_limit': 100000,
    })


@analytics_bp.route('/analytics/runs/timeline', methods=['GET'])
@jwt_required()
def runs_timeline():
    user_id = get_jwt_identity()
    days = request.args.get('days', 30, type=int)
    ws_id = request.args.get('workspace_id')

    timeline = []
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=days - i - 1)).date()
        timeline.append({
            'date': day.isoformat(),
            'total': 0,
            'success': 0,
            'error': 0,
        })

    if ws_id:
        ws = Workspace.query.get(ws_id)
        if ws:
            pids = [p.id for p in ws.pipelines]
            runs = Run.query.filter(Run.pipeline_id.in_(pids)).all() if pids else []
            for run in runs:
                day_str = run.started_at.date().isoformat()
                for entry in timeline:
                    if entry['date'] == day_str:
                        entry['total'] += 1
                        if run.status == 'success':
                            entry['success'] += 1
                        elif run.status == 'error':
                            entry['error'] += 1
                        break

    return jsonify({'timeline': timeline, 'days': days})


@analytics_bp.route('/audit/logs', methods=['GET'])
@jwt_required()
def audit_logs():
    user_id = get_jwt_identity()
    q = AuditLog.query.order_by(AuditLog.created_at.desc())

    org_id = request.args.get('org_id')
    if org_id:
        q = q.filter_by(org_id=org_id)

    action = request.args.get('action')
    if action:
        q = q.filter_by(action=action)

    resource_type = request.args.get('resource_type')
    if resource_type:
        q = q.filter_by(resource_type=resource_type)

    items, pagination = paginate(q)
    return jsonify({'logs': [l.to_dict() for l in items], 'pagination': pagination})


@analytics_bp.route('/audit/logs/<log_id>', methods=['GET'])
@jwt_required()
def get_audit_log(log_id):
    log = AuditLog.query.get(log_id)
    if not log:
        return jsonify({'error': 'Log not found'}), 404
    return jsonify(log.to_dict())
