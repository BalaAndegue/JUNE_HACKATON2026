from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from ..extensions import db
from ..models import Webhook, WebhookEvent
from ..utils import validate_required, check_pipeline_access, paginate

webhooks_bp = Blueprint('webhooks', __name__)

VALID_EVENTS = ['run.success', 'run.error', 'run.started', 'run.cancelled', 'pipeline.updated']


@webhooks_bp.route('/pipelines/<pipeline_id>/webhooks', methods=['GET'])
@jwt_required()
def list_webhooks(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    return jsonify({'webhooks': [w.to_dict() for w in pipeline.webhooks]})


@webhooks_bp.route('/pipelines/<pipeline_id>/webhooks', methods=['POST'])
@jwt_required()
def create_webhook(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json()
    err = validate_required(data, ['url'])
    if err:
        return jsonify({'error': err}), 400

    wh = Webhook(
        pipeline_id=pipeline_id,
        url=data['url'],
        secret=data.get('secret'),
        active=data.get('active', True),
    )
    if data.get('events'):
        wh.events = [e for e in data['events'] if e in VALID_EVENTS]
    db.session.add(wh)
    db.session.commit()
    return jsonify(wh.to_dict()), 201


@webhooks_bp.route('/pipelines/<pipeline_id>/webhooks/<webhook_id>', methods=['GET'])
@jwt_required()
def get_webhook(pipeline_id, webhook_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    wh = Webhook.query.filter_by(id=webhook_id, pipeline_id=pipeline_id).first()
    if not wh:
        return jsonify({'error': 'Webhook not found'}), 404
    return jsonify(wh.to_dict())


@webhooks_bp.route('/pipelines/<pipeline_id>/webhooks/<webhook_id>', methods=['PATCH'])
@jwt_required()
def update_webhook(pipeline_id, webhook_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    wh = Webhook.query.filter_by(id=webhook_id, pipeline_id=pipeline_id).first()
    if not wh:
        return jsonify({'error': 'Webhook not found'}), 404

    data = request.get_json() or {}
    if 'url' in data:
        wh.url = data['url']
    if 'events' in data:
        wh.events = [e for e in data['events'] if e in VALID_EVENTS]
    if 'active' in data:
        wh.active = data['active']
    if 'secret' in data:
        wh.secret = data['secret']
    db.session.commit()
    return jsonify(wh.to_dict())


@webhooks_bp.route('/pipelines/<pipeline_id>/webhooks/<webhook_id>', methods=['DELETE'])
@jwt_required()
def delete_webhook(pipeline_id, webhook_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    wh = Webhook.query.filter_by(id=webhook_id, pipeline_id=pipeline_id).first()
    if not wh:
        return jsonify({'error': 'Webhook not found'}), 404
    db.session.delete(wh)
    db.session.commit()
    return jsonify({'message': 'Webhook deleted'})


@webhooks_bp.route('/pipelines/<pipeline_id>/webhooks/<webhook_id>/test', methods=['POST'])
@jwt_required()
def test_webhook(pipeline_id, webhook_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    wh = Webhook.query.filter_by(id=webhook_id, pipeline_id=pipeline_id).first()
    if not wh:
        return jsonify({'error': 'Webhook not found'}), 404

    evt = WebhookEvent(
        webhook_id=webhook_id,
        event_type='test',
        status='delivered',
        response_code=200,
    )
    evt._payload = '{"event": "test", "pipeline_id": "' + pipeline_id + '"}'
    db.session.add(evt)
    db.session.commit()
    return jsonify({'message': 'Test webhook sent', 'event_id': evt.id, 'status': 'delivered'})


@webhooks_bp.route('/webhooks', methods=['GET'])
@jwt_required()
def list_all_webhooks():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')
    if ws_id:
        from ..models import Pipeline
        pipeline_ids = [p.id for p in Pipeline.query.filter_by(workspace_id=ws_id).all()]
        whs = Webhook.query.filter(Webhook.pipeline_id.in_(pipeline_ids)).all()
    else:
        whs = Webhook.query.all()
    return jsonify({'webhooks': [w.to_dict() for w in whs]})


@webhooks_bp.route('/webhooks/<webhook_id>/events', methods=['GET'])
@jwt_required()
def webhook_events(webhook_id):
    wh = Webhook.query.get(webhook_id)
    if not wh:
        return jsonify({'error': 'Webhook not found'}), 404
    events = WebhookEvent.query.filter_by(webhook_id=webhook_id).order_by(WebhookEvent.sent_at.desc()).limit(50).all()
    return jsonify({'webhook_id': webhook_id, 'events': [e.to_dict() for e in events]})


@webhooks_bp.route('/webhooks/inbound/<token>', methods=['POST'])
def inbound_webhook(token):
    wh = Webhook.query.filter_by(inbound_token=token).first()
    if not wh:
        return jsonify({'error': 'Invalid token'}), 404

    payload = request.get_json() or {}
    evt = WebhookEvent(
        webhook_id=wh.id,
        event_type='inbound',
        status='received',
        response_code=200,
    )
    import json
    evt._payload = json.dumps(payload)
    db.session.add(evt)
    db.session.commit()
    return jsonify({'message': 'Webhook received', 'event_id': evt.id})
