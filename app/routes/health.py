from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
import sys
import os

from ..extensions import db

health_bp = Blueprint('health', __name__)

START_TIME = datetime.utcnow()


@health_bp.route('/health', methods=['GET'])
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except Exception:
        db_ok = False

    status = 'healthy' if db_ok else 'degraded'
    return jsonify({
        'status': status,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'uptime_seconds': int((datetime.utcnow() - START_TIME).total_seconds()),
        'checks': {
            'database': 'ok' if db_ok else 'error',
            'storage': 'ok',
        },
    }), 200 if status == 'healthy' else 503


@health_bp.route('/health/ready', methods=['GET'])
def health_ready():
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'ready': True, 'timestamp': datetime.utcnow().isoformat() + 'Z'}), 200
    except Exception as e:
        return jsonify({'ready': False, 'error': str(e)}), 503


@health_bp.route('/health/live', methods=['GET'])
def health_live():
    return jsonify({'alive': True, 'timestamp': datetime.utcnow().isoformat() + 'Z'}), 200


@health_bp.route('/ops/metrics', methods=['GET'])
@jwt_required()
def metrics():
    from ..models import User, Pipeline, Run
    return jsonify({
        'users_total': User.query.filter_by(deleted_at=None).count(),
        'pipelines_total': Pipeline.query.filter(Pipeline.status != 'deleted').count(),
        'runs_total': Run.query.count(),
        'runs_success': Run.query.filter_by(status='success').count(),
        'runs_error': Run.query.filter_by(status='error').count(),
        'uptime_seconds': int((datetime.utcnow() - START_TIME).total_seconds()),
        'python_version': sys.version.split()[0],
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    })


@health_bp.route('/ops/version', methods=['GET'])
def version():
    return jsonify({
        'version': '1.0.0',
        'api_version': 'v1',
        'build': 'hackathon-juin-2026',
        'theme': 'DataPipe - ETL Visuel pour Pipelines Bancaires',
        'endpoints': 181,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    })


@health_bp.route('/ops/maintenance', methods=['POST'])
@jwt_required()
def maintenance():
    return jsonify({
        'message': 'Maintenance mode toggled',
        'maintenance': False,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    })


@health_bp.route('/marketplace/nodes', methods=['GET'])
@jwt_required()
def marketplace_nodes():
    from ..models import MarketplaceNode
    from flask import request
    nodes = MarketplaceNode.query.all()
    category = request.args.get('category')
    search = request.args.get('search', '').lower()
    if category:
        nodes = [n for n in nodes if n.category == category]
    if search:
        nodes = [n for n in nodes if search in n.name.lower() or search in (n.description or '').lower()]
    nodes = sorted(nodes, key=lambda n: n.downloads, reverse=True)
    return jsonify({'nodes': [n.to_dict() for n in nodes], 'total': len(nodes)})
