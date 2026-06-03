from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from ..extensions import db
from ..models import Schedule, Run, Pipeline
from ..utils import validate_required, check_pipeline_access, paginate

scheduling_bp = Blueprint('scheduling', __name__)

VALID_CRONS = ['* * * * *', '0 * * * *', '0 0 * * *', '0 0 * * 1', '0 0 1 * *']


def _next_run_from_cron(cron):
    return datetime.utcnow() + timedelta(hours=1)


@scheduling_bp.route('/pipelines/<pipeline_id>/schedule', methods=['GET'])
@jwt_required()
def get_schedule(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if not pipeline.schedule:
        return jsonify({'error': 'No schedule configured'}), 404
    return jsonify(pipeline.schedule.to_dict())


@scheduling_bp.route('/pipelines/<pipeline_id>/schedule', methods=['POST'])
@jwt_required()
def create_schedule(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if pipeline.schedule:
        return jsonify({'error': 'Schedule already exists. Use PATCH to update.'}), 409

    data = request.get_json()
    err = validate_required(data, ['cron'])
    if err:
        return jsonify({'error': err}), 400

    sch = Schedule(
        pipeline_id=pipeline_id,
        cron=data['cron'],
        timezone=data.get('timezone', 'UTC'),
        active=data.get('active', True),
    )
    sch.next_run_at = _next_run_from_cron(data['cron'])
    db.session.add(sch)
    db.session.commit()
    return jsonify(sch.to_dict()), 201


@scheduling_bp.route('/pipelines/<pipeline_id>/schedule', methods=['PATCH'])
@jwt_required()
def update_schedule(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if not pipeline.schedule:
        return jsonify({'error': 'No schedule configured'}), 404

    sch = pipeline.schedule
    data = request.get_json() or {}
    if 'cron' in data:
        sch.cron = data['cron']
        sch.next_run_at = _next_run_from_cron(data['cron'])
    if 'timezone' in data:
        sch.timezone = data['timezone']
    if 'active' in data:
        sch.active = data['active']
    db.session.commit()
    return jsonify(sch.to_dict())


@scheduling_bp.route('/pipelines/<pipeline_id>/schedule', methods=['DELETE'])
@jwt_required()
def delete_schedule(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if not pipeline.schedule:
        return jsonify({'error': 'No schedule configured'}), 404
    db.session.delete(pipeline.schedule)
    db.session.commit()
    return jsonify({'message': 'Schedule deleted'})


@scheduling_bp.route('/pipelines/<pipeline_id>/schedule/pause', methods=['POST'])
@jwt_required()
def pause_schedule(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if not pipeline.schedule:
        return jsonify({'error': 'No schedule configured'}), 404
    pipeline.schedule.active = False
    db.session.commit()
    return jsonify({'message': 'Schedule paused', 'active': False})


@scheduling_bp.route('/pipelines/<pipeline_id>/schedule/resume', methods=['POST'])
@jwt_required()
def resume_schedule(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    if not pipeline.schedule:
        return jsonify({'error': 'No schedule configured'}), 404
    pipeline.schedule.active = True
    pipeline.schedule.next_run_at = _next_run_from_cron(pipeline.schedule.cron)
    db.session.commit()
    return jsonify({'message': 'Schedule resumed', 'active': True})


@scheduling_bp.route('/schedules', methods=['GET'])
@jwt_required()
def list_schedules():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')
    if ws_id:
        from ..models import Workspace
        ws = Workspace.query.get(ws_id)
        pipeline_ids = [p.id for p in ws.pipelines] if ws else []
        schedules = Schedule.query.filter(Schedule.pipeline_id.in_(pipeline_ids)).all()
    else:
        schedules = Schedule.query.all()
    return jsonify({'schedules': [s.to_dict() for s in schedules]})


@scheduling_bp.route('/schedules/<schedule_id>/runs', methods=['GET'])
@jwt_required()
def schedule_runs(schedule_id):
    sch = Schedule.query.get(schedule_id)
    if not sch:
        return jsonify({'error': 'Schedule not found'}), 404
    runs = Run.query.filter_by(pipeline_id=sch.pipeline_id, trigger='schedule').order_by(Run.started_at.desc()).limit(20).all()
    return jsonify({'schedule_id': schedule_id, 'runs': [r.to_dict() for r in runs]})


@scheduling_bp.route('/schedules/<schedule_id>/trigger', methods=['POST'])
@jwt_required()
def trigger_scheduled(schedule_id):
    user_id = get_jwt_identity()
    sch = Schedule.query.get(schedule_id)
    if not sch:
        return jsonify({'error': 'Schedule not found'}), 404

    pipeline, err = check_pipeline_access(sch.pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 403

    from .runs import _simulate_run
    run = Run(pipeline_id=sch.pipeline_id, trigger='schedule')
    db.session.add(run)
    db.session.flush()
    _simulate_run(pipeline, run)

    sch.last_run_at = datetime.utcnow()
    sch.next_run_at = _next_run_from_cron(sch.cron)
    db.session.commit()
    return jsonify({'message': 'Triggered successfully', 'run': run.to_dict()})
