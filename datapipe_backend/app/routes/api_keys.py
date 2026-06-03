from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
import hashlib

from ..extensions import db
from ..models import ApiKey, Integration
from ..utils import validate_required

api_keys_bp = Blueprint('api_keys', __name__)

INTEGRATION_TYPES = ['slack', 'email', 'pagerduty', 'jira', 'github', 'teams', 's3', 'gcs']


@api_keys_bp.route('/api-keys', methods=['GET'])
@jwt_required()
def list_api_keys():
    user_id = get_jwt_identity()
    keys = ApiKey.query.filter_by(user_id=user_id).all()
    return jsonify({'api_keys': [k.to_dict() for k in keys]})


@api_keys_bp.route('/api-keys', methods=['POST'])
@jwt_required()
def create_api_key():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['name'])
    if err:
        return jsonify({'error': err}), 400

    raw_key = f"dp_{uuid4().hex}{uuid4().hex}"
    prefix = raw_key[:10]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    key = ApiKey(
        user_id=user_id,
        org_id=data.get('org_id'),
        name=data['name'],
        key_prefix=prefix,
        key_hash=key_hash,
    )
    db.session.add(key)
    db.session.commit()

    result = key.to_dict()
    result['key'] = raw_key
    result['warning'] = 'Store this key safely — it will not be shown again'
    return jsonify(result), 201


@api_keys_bp.route('/api-keys/<key_id>', methods=['DELETE'])
@jwt_required()
def delete_api_key(key_id):
    user_id = get_jwt_identity()
    key = ApiKey.query.filter_by(id=key_id, user_id=user_id).first()
    if not key:
        return jsonify({'error': 'API key not found'}), 404
    db.session.delete(key)
    db.session.commit()
    return jsonify({'message': 'API key deleted'})


@api_keys_bp.route('/integrations', methods=['GET'])
@jwt_required()
def list_integrations():
    user_id = get_jwt_identity()
    org_id = request.args.get('org_id')
    q = Integration.query
    if org_id:
        q = q.filter_by(org_id=org_id)
    integrations = q.all()
    return jsonify({'integrations': [i.to_dict() for i in integrations]})


@api_keys_bp.route('/integrations', methods=['POST'])
@jwt_required()
def create_integration():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['org_id', 'type', 'name'])
    if err:
        return jsonify({'error': err}), 400
    if data['type'] not in INTEGRATION_TYPES:
        return jsonify({'error': f'Invalid type. Allowed: {INTEGRATION_TYPES}'}), 400

    intg = Integration(
        org_id=data['org_id'],
        type=data['type'],
        name=data['name'],
        active=data.get('active', True),
    )
    intg._config = __import__('json').dumps(data.get('config', {}))
    db.session.add(intg)
    db.session.commit()
    return jsonify(intg.to_dict()), 201


@api_keys_bp.route('/integrations/<integration_id>', methods=['GET'])
@jwt_required()
def get_integration(integration_id):
    intg = Integration.query.get(integration_id)
    if not intg:
        return jsonify({'error': 'Integration not found'}), 404
    return jsonify(intg.to_dict())


@api_keys_bp.route('/integrations/<integration_id>', methods=['PATCH'])
@jwt_required()
def update_integration(integration_id):
    intg = Integration.query.get(integration_id)
    if not intg:
        return jsonify({'error': 'Integration not found'}), 404
    data = request.get_json() or {}
    if 'name' in data:
        intg.name = data['name']
    if 'active' in data:
        intg.active = data['active']
    if 'config' in data:
        intg._config = __import__('json').dumps(data['config'])
    db.session.commit()
    return jsonify(intg.to_dict())


@api_keys_bp.route('/integrations/<integration_id>', methods=['DELETE'])
@jwt_required()
def delete_integration(integration_id):
    intg = Integration.query.get(integration_id)
    if not intg:
        return jsonify({'error': 'Integration not found'}), 404
    db.session.delete(intg)
    db.session.commit()
    return jsonify({'message': 'Integration deleted'})
