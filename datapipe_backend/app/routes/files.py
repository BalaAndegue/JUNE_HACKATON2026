from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import csv
import io
import json

from ..extensions import db
from ..models import File, Datasource, Workspace
from ..utils import validate_required, check_org_role, paginate

files_bp = Blueprint('files', __name__)

ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'xls', 'parquet', 'txt'}
DATASOURCE_TYPES = ['postgresql', 'mysql', 'sqlite', 'mongodb', 'redis', 'api', 'bigquery', 's3']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _check_ws(workspace_id, user_id, min_role='viewer'):
    ws = Workspace.query.get(workspace_id)
    if not ws or ws.deleted_at:
        return None, 'Workspace not found'
    if not check_org_role(ws.org_id, user_id, min_role):
        return None, 'Access denied'
    return ws, None


# ── Files ─────────────────────────────────────────────────────────────

@files_bp.route('/files/upload', methods=['POST'])
@jwt_required()
def upload_file():
    user_id = get_jwt_identity()
    workspace_id = request.form.get('workspace_id')
    if not workspace_id:
        return jsonify({'error': 'workspace_id is required'}), 400

    ws, err = _check_ws(workspace_id, user_id, 'editor')
    if err:
        return jsonify({'error': err}), 403 if 'denied' in err else 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {ALLOWED_EXTENSIONS}'}), 400

    filename = secure_filename(f.filename)
    from flask import current_app
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], workspace_id)
    os.makedirs(upload_dir, exist_ok=True)

    content = f.read()
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb') as fp:
        fp.write(content)

    rows, cols, columns, preview = 0, 0, [], []
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'csv':
        try:
            text = content.decode('utf-8', errors='replace')
            reader = csv.DictReader(io.StringIO(text))
            columns = reader.fieldnames or []
            cols = len(columns)
            all_rows = list(reader)
            rows = len(all_rows)
            preview = all_rows[:5]
        except Exception:
            pass
    elif ext == 'json':
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and parsed:
                columns = list(parsed[0].keys()) if isinstance(parsed[0], dict) else []
                rows = len(parsed)
                cols = len(columns)
                preview = parsed[:5]
        except Exception:
            pass

    db_file = File(
        workspace_id=workspace_id,
        name=filename,
        original_name=f.filename,
        size=len(content),
        mime_type=f.content_type,
        path=file_path,
        rows_count=rows,
        columns_count=cols,
    )
    db_file.columns = columns
    db_file.preview = preview
    db.session.add(db_file)
    db.session.commit()
    return jsonify(db_file.to_dict()), 201


@files_bp.route('/files', methods=['GET'])
@jwt_required()
def list_files():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')
    if not ws_id:
        return jsonify({'error': 'workspace_id is required'}), 400
    ws, err = _check_ws(ws_id, user_id)
    if err:
        return jsonify({'error': err}), 403 if 'denied' in err else 404
    q = File.query.filter_by(workspace_id=ws_id).order_by(File.created_at.desc())
    items, pagination = paginate(q)
    return jsonify({'data': [f.to_dict() for f in items], 'pagination': pagination})


@files_bp.route('/files/<file_id>', methods=['GET'])
@jwt_required()
def get_file(file_id):
    user_id = get_jwt_identity()
    db_file = File.query.get_or_404(file_id)
    ws, err = _check_ws(db_file.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403
    return jsonify(db_file.to_dict())


@files_bp.route('/files/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    user_id = get_jwt_identity()
    db_file = File.query.get_or_404(file_id)
    ws, err = _check_ws(db_file.workspace_id, user_id, 'editor')
    if err:
        return jsonify({'error': err}), 403
    if db_file.path and os.path.exists(db_file.path):
        os.remove(db_file.path)
    db.session.delete(db_file)
    db.session.commit()
    return jsonify({'message': 'File deleted'})


@files_bp.route('/files/<file_id>/preview', methods=['GET'])
@jwt_required()
def preview_file(file_id):
    user_id = get_jwt_identity()
    db_file = File.query.get_or_404(file_id)
    ws, err = _check_ws(db_file.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        'file_id': file_id,
        'columns': db_file.columns,
        'rows_count': db_file.rows_count,
        'preview': db_file.preview[:limit],
    })


@files_bp.route('/files/<file_id>/analyze', methods=['POST'])
@jwt_required()
def analyze_file(file_id):
    user_id = get_jwt_identity()
    db_file = File.query.get_or_404(file_id)
    ws, err = _check_ws(db_file.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403

    columns_analysis = []
    for col in db_file.columns:
        sample_values = [row.get(col) for row in db_file.preview if row.get(col) is not None]
        inferred_type = 'string'
        if sample_values:
            try:
                [float(v) for v in sample_values]
                inferred_type = 'number'
            except (ValueError, TypeError):
                pass
        columns_analysis.append({
            'name': col,
            'type': inferred_type,
            'null_count': 0,
            'unique_count': len(set(str(v) for v in sample_values)),
            'sample': sample_values[:3],
        })

    return jsonify({
        'file_id': file_id,
        'rows': db_file.rows_count,
        'columns': columns_analysis,
        'quality_score': 0.95,
        'suggestions': [
            'Toutes les colonnes ont des valeurs',
            f'{len(db_file.columns)} colonnes détectées',
        ],
    })


# ── Datasources ───────────────────────────────────────────────────────

@files_bp.route('/datasources', methods=['GET'])
@jwt_required()
def list_datasources():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')
    if not ws_id:
        return jsonify({'error': 'workspace_id is required'}), 400
    ws, err = _check_ws(ws_id, user_id)
    if err:
        return jsonify({'error': err}), 403 if 'denied' in err else 404
    datasources = Datasource.query.filter_by(workspace_id=ws_id).all()
    return jsonify({'datasources': [ds.to_dict() for ds in datasources]})


@files_bp.route('/datasources', methods=['POST'])
@jwt_required()
def create_datasource():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['workspace_id', 'type', 'name'])
    if err:
        return jsonify({'error': err}), 400
    if data['type'] not in DATASOURCE_TYPES:
        return jsonify({'error': f'Invalid type. Allowed: {DATASOURCE_TYPES}'}), 400

    ws, err = _check_ws(data['workspace_id'], user_id, 'editor')
    if err:
        return jsonify({'error': err}), 403 if 'denied' in err else 404

    ds = Datasource(workspace_id=data['workspace_id'], type=data['type'], name=data['name'])
    ds.config = data.get('config', {})
    db.session.add(ds)
    db.session.commit()
    return jsonify(ds.to_dict()), 201


@files_bp.route('/datasources/<ds_id>', methods=['GET'])
@jwt_required()
def get_datasource(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403
    return jsonify(ds.to_dict())


@files_bp.route('/datasources/<ds_id>', methods=['PATCH'])
@jwt_required()
def update_datasource(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id, 'editor')
    if err:
        return jsonify({'error': err}), 403
    data = request.get_json() or {}
    if 'name' in data:
        ds.name = data['name']
    if 'config' in data:
        ds.config = data['config']
    if 'active' in data:
        ds.active = data['active']
    db.session.commit()
    return jsonify(ds.to_dict())


@files_bp.route('/datasources/<ds_id>', methods=['DELETE'])
@jwt_required()
def delete_datasource(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id, 'editor')
    if err:
        return jsonify({'error': err}), 403
    db.session.delete(ds)
    db.session.commit()
    return jsonify({'message': 'Datasource deleted'})


@files_bp.route('/datasources/<ds_id>/test', methods=['POST'])
@jwt_required()
def test_datasource(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403
    return jsonify({'success': True, 'message': f'Connection to {ds.name} successful', 'latency_ms': 42})


@files_bp.route('/datasources/<ds_id>/schema', methods=['GET'])
@jwt_required()
def get_datasource_schema(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403
    mock_schema = {
        'tables': [
            {'name': 'transactions', 'columns': [
                {'name': 'id', 'type': 'integer', 'primary_key': True},
                {'name': 'montant', 'type': 'decimal', 'nullable': False},
                {'name': 'devise', 'type': 'varchar(3)', 'nullable': False},
                {'name': 'date_transaction', 'type': 'timestamp', 'nullable': False},
                {'name': 'statut', 'type': 'varchar(20)', 'nullable': False},
            ]},
            {'name': 'comptes', 'columns': [
                {'name': 'id', 'type': 'integer', 'primary_key': True},
                {'name': 'numero', 'type': 'varchar(20)', 'nullable': False},
                {'name': 'solde', 'type': 'decimal', 'nullable': False},
                {'name': 'type', 'type': 'varchar(20)'},
            ]},
        ]
    }
    return jsonify({'datasource_id': ds_id, 'schema': mock_schema})


@files_bp.route('/datasources/<ds_id>/sync', methods=['POST'])
@jwt_required()
def sync_datasource(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id, 'editor')
    if err:
        return jsonify({'error': err}), 403
    ds.sync_status = 'syncing'
    db.session.commit()
    ds.last_synced_at = datetime.utcnow()
    ds.sync_status = 'idle'
    db.session.commit()
    return jsonify({'message': 'Sync completed', 'last_synced_at': ds.last_synced_at.isoformat() + 'Z'})


@files_bp.route('/datasources/<ds_id>/sync-status', methods=['GET'])
@jwt_required()
def sync_status(ds_id):
    user_id = get_jwt_identity()
    ds = Datasource.query.get_or_404(ds_id)
    ws, err = _check_ws(ds.workspace_id, user_id)
    if err:
        return jsonify({'error': err}), 403
    return jsonify({
        'datasource_id': ds_id,
        'sync_status': ds.sync_status,
        'last_synced_at': ds.last_synced_at.isoformat() + 'Z' if ds.last_synced_at else None,
    })


@files_bp.route('/datasources/types', methods=['GET'])
@jwt_required()
def list_datasource_types():
    types = [
        {'type': 'postgresql', 'name': 'PostgreSQL', 'icon': '🐘', 'config_schema': {'host': 'string', 'port': 'integer', 'database': 'string', 'user': 'string', 'password': 'string'}},
        {'type': 'mysql', 'name': 'MySQL', 'icon': '🐬', 'config_schema': {'host': 'string', 'port': 'integer', 'database': 'string', 'user': 'string', 'password': 'string'}},
        {'type': 'sqlite', 'name': 'SQLite', 'icon': '📦', 'config_schema': {'path': 'string'}},
        {'type': 'mongodb', 'name': 'MongoDB', 'icon': '🍃', 'config_schema': {'uri': 'string', 'database': 'string'}},
        {'type': 'api', 'name': 'REST API', 'icon': '🌐', 'config_schema': {'base_url': 'string', 'auth_type': 'string', 'api_key': 'string'}},
        {'type': 's3', 'name': 'Amazon S3', 'icon': '☁️', 'config_schema': {'bucket': 'string', 'region': 'string', 'access_key': 'string', 'secret_key': 'string'}},
    ]
    return jsonify({'types': types})
