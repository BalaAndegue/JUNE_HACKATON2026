from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from ..extensions import db
from ..models import Notification, Alert
from ..utils import validate_required, check_pipeline_access, paginate

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications', methods=['GET'])
@jwt_required()
def list_notifications():
    user_id = get_jwt_identity()
    q = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc())
    read_filter = request.args.get('read')
    if read_filter is not None:
        q = q.filter_by(read=(read_filter.lower() == 'true'))
    items, pagination = paginate(q)
    unread = Notification.query.filter_by(user_id=user_id, read=False).count()
    return jsonify({'notifications': [n.to_dict() for n in items], 'unread_count': unread, 'pagination': pagination})


@notifications_bp.route('/notifications/<notif_id>/read', methods=['PATCH'])
@jwt_required()
def mark_read(notif_id):
    user_id = get_jwt_identity()
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not notif:
        return jsonify({'error': 'Notification not found'}), 404
    notif.read = True
    db.session.commit()
    return jsonify(notif.to_dict())


@notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
@jwt_required()
def mark_all_read():
    user_id = get_jwt_identity()
    count = Notification.query.filter_by(user_id=user_id, read=False).update({'read': True})
    db.session.commit()
    return jsonify({'marked': count, 'message': f'{count} notifications marked as read'})


@notifications_bp.route('/notifications/<notif_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notif_id):
    user_id = get_jwt_identity()
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not notif:
        return jsonify({'error': 'Notification not found'}), 404
    db.session.delete(notif)
    db.session.commit()
    return jsonify({'message': 'Notification deleted'})


# ── Alerts ────────────────────────────────────────────────────────────

@notifications_bp.route('/alerts', methods=['GET'])
@jwt_required()
def list_alerts():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')
    q = Alert.query
    if ws_id:
        from ..models import Pipeline
        pids = [p.id for p in Pipeline.query.filter_by(workspace_id=ws_id).all()]
        q = q.filter(Alert.pipeline_id.in_(pids))
    items, pagination = paginate(q)
    return jsonify({'alerts': [a.to_dict() for a in items], 'pagination': pagination})


@notifications_bp.route('/alerts', methods=['POST'])
@jwt_required()
def create_alert():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['name', 'condition'])
    if err:
        return jsonify({'error': err}), 400

    alert = Alert(
        pipeline_id=data.get('pipeline_id'),
        name=data['name'],
        condition=data['condition'],
        channel=data.get('channel', 'email'),
        active=data.get('active', True),
    )
    if data.get('recipients'):
        alert._recipients = __import__('json').dumps(data['recipients'])
    db.session.add(alert)
    db.session.commit()
    return jsonify(alert.to_dict()), 201


@notifications_bp.route('/alerts/<alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    return jsonify(alert.to_dict())


@notifications_bp.route('/alerts/<alert_id>', methods=['PATCH'])
@jwt_required()
def update_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    data = request.get_json() or {}
    for field in ['name', 'condition', 'channel', 'active']:
        if field in data:
            setattr(alert, field, data[field])
    if 'recipients' in data:
        alert._recipients = __import__('json').dumps(data['recipients'])
    db.session.commit()
    return jsonify(alert.to_dict())


@notifications_bp.route('/alerts/<alert_id>', methods=['DELETE'])
@jwt_required()
def delete_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    db.session.delete(alert)
    db.session.commit()
    return jsonify({'message': 'Alert deleted'})


@notifications_bp.route('/alerts/<alert_id>/test', methods=['POST'])
@jwt_required()
def test_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    return jsonify({
        'message': f'Test alert "{alert.name}" sent via {alert.channel}',
        'alert_id': alert_id,
        'simulated': True,
    })
