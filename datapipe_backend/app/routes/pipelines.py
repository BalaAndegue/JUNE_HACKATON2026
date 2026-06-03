from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json

from ..extensions import db
from ..models import Pipeline, PipelineVersion, PipelineTemplate, Node, Edge, Workspace
from ..utils import validate_required, check_org_role, check_pipeline_access, paginate

pipelines_bp = Blueprint('pipelines', __name__)


def _get_ws_org(workspace_id, user_id):
    ws = Workspace.query.get(workspace_id)
    if not ws:
        return None, None, 'Workspace not found'
    if not check_org_role(ws.org_id, user_id, 'viewer'):
        return None, None, 'Access denied'
    return ws, ws.org_id, None


def _snapshot_pipeline(pipeline):
    return {
        'id': pipeline.id,
        'name': pipeline.name,
        'description': pipeline.description,
        'nodes': [n.to_dict() for n in pipeline.nodes],
        'edges': [e.to_dict() for e in pipeline.edges],
    }


# ── CRUD ─────────────────────────────────────────────────────────────

@pipelines_bp.route('', methods=['GET'])
@jwt_required()
def list_pipelines():
    user_id = get_jwt_identity()
    ws_id = request.args.get('workspace_id')
    if not ws_id:
        return jsonify({'error': 'workspace_id is required'}), 400

    ws, org_id, err = _get_ws_org(ws_id, user_id)
    if err:
        return jsonify({'error': err}), 403 if err == 'Access denied' else 404

    q = Pipeline.query.filter_by(workspace_id=ws_id)
    if request.args.get('status'):
        q = q.filter_by(status=request.args.get('status'))
    if request.args.get('search'):
        q = q.filter(Pipeline.name.ilike(f"%{request.args.get('search')}%"))

    sort = request.args.get('sort', 'updated_at')
    sort_map = {'name': Pipeline.name, 'updated_at': Pipeline.updated_at, 'last_run_at': Pipeline.last_run_at}
    q = q.order_by(sort_map.get(sort, Pipeline.updated_at).desc())

    items, pagination = paginate(q)
    return jsonify({'data': [p.to_dict() for p in items], 'pagination': pagination})


@pipelines_bp.route('', methods=['POST'])
@jwt_required()
def create_pipeline():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['name', 'workspace_id'])
    if err:
        return jsonify({'error': err}), 400

    ws, org_id, err = _get_ws_org(data['workspace_id'], user_id)
    if err:
        return jsonify({'error': err}), 403 if err == 'Access denied' else 404

    pipeline = Pipeline(
        workspace_id=data['workspace_id'],
        name=data['name'],
        description=data.get('description'),
    )
    if data.get('tags'):
        pipeline.tags = data['tags']
    db.session.add(pipeline)
    db.session.commit()
    return jsonify(pipeline.to_dict(include_graph=True)), 201


@pipelines_bp.route('/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    return jsonify(pipeline.to_dict(include_graph=True))


@pipelines_bp.route('/<pipeline_id>', methods=['PUT'])
@jwt_required()
def replace_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json()
    err = validate_required(data, ['name'])
    if err:
        return jsonify({'error': err}), 400

    pipeline.name = data['name']
    pipeline.description = data.get('description')
    pipeline.tags = data.get('tags', [])
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(pipeline.to_dict(include_graph=True))


@pipelines_bp.route('/<pipeline_id>', methods=['PATCH'])
@jwt_required()
def update_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json() or {}
    for field in ['name', 'description']:
        if field in data:
            setattr(pipeline, field, data[field])
    if 'tags' in data:
        pipeline.tags = data['tags']
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(pipeline.to_dict())


@pipelines_bp.route('/<pipeline_id>', methods=['DELETE'])
@jwt_required()
def delete_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    ws = Workspace.query.get(pipeline.workspace_id)
    if not check_org_role(ws.org_id, user_id, 'editor'):
        return jsonify({'error': 'Editor role required'}), 403

    pipeline.status = 'deleted'
    db.session.commit()
    return jsonify({'message': 'Pipeline deleted'})


# ── Actions ──────────────────────────────────────────────────────────

@pipelines_bp.route('/<pipeline_id>/duplicate', methods=['POST'])
@jwt_required()
def duplicate_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json() or {}
    new_name = data.get('name', f"{pipeline.name} (copie)")

    new_pipeline = Pipeline(
        workspace_id=pipeline.workspace_id,
        name=new_name,
        description=pipeline.description,
    )
    new_pipeline.tags = pipeline.tags
    db.session.add(new_pipeline)
    db.session.flush()

    id_map = {}
    for node in pipeline.nodes:
        new_node = Node(
            pipeline_id=new_pipeline.id,
            type_slug=node.type_slug,
            label=node.label,
            position_x=node.position_x,
            position_y=node.position_y,
        )
        new_node.config = node.config
        db.session.add(new_node)
        db.session.flush()
        id_map[node.id] = new_node.id

    for edge in pipeline.edges:
        new_edge = Edge(
            pipeline_id=new_pipeline.id,
            source_node_id=id_map.get(edge.source_node_id, edge.source_node_id),
            target_node_id=id_map.get(edge.target_node_id, edge.target_node_id),
            source_handle=edge.source_handle,
            target_handle=edge.target_handle,
        )
        db.session.add(new_edge)

    db.session.commit()
    return jsonify(new_pipeline.to_dict(include_graph=True)), 201


@pipelines_bp.route('/<pipeline_id>/archive', methods=['POST'])
@jwt_required()
def archive_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    pipeline.status = 'archived'
    db.session.commit()
    return jsonify({'message': 'Pipeline archived', 'status': 'archived'})


@pipelines_bp.route('/<pipeline_id>/restore', methods=['POST'])
@jwt_required()
def restore_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    pipeline.status = 'active'
    db.session.commit()
    return jsonify({'message': 'Pipeline restored', 'status': 'active'})


@pipelines_bp.route('/<pipeline_id>/publish', methods=['POST'])
@jwt_required()
def publish_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    pipeline.is_public = True
    db.session.commit()
    return jsonify({'message': 'Pipeline is now public', 'is_public': True})


@pipelines_bp.route('/<pipeline_id>/unpublish', methods=['POST'])
@jwt_required()
def unpublish_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    pipeline.is_public = False
    db.session.commit()
    return jsonify({'message': 'Pipeline is now private', 'is_public': False})


# ── Versions ─────────────────────────────────────────────────────────

@pipelines_bp.route('/<pipeline_id>/versions', methods=['GET'])
@jwt_required()
def list_versions(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    versions = PipelineVersion.query.filter_by(pipeline_id=pipeline_id).order_by(PipelineVersion.version_num.desc()).all()
    return jsonify({'versions': [v.to_dict() for v in versions]})


@pipelines_bp.route('/<pipeline_id>/versions/<version_id>', methods=['GET'])
@jwt_required()
def get_version(pipeline_id, version_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    version = PipelineVersion.query.filter_by(id=version_id, pipeline_id=pipeline_id).first()
    if not version:
        return jsonify({'error': 'Version not found'}), 404
    return jsonify(version.to_dict(include_snapshot=True))


@pipelines_bp.route('/<pipeline_id>/versions/<version_id>/restore', methods=['POST'])
@jwt_required()
def restore_version(pipeline_id, version_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    version = PipelineVersion.query.filter_by(id=version_id, pipeline_id=pipeline_id).first()
    if not version:
        return jsonify({'error': 'Version not found'}), 404

    snapshot = version.snapshot
    Node.query.filter_by(pipeline_id=pipeline_id).delete()
    Edge.query.filter_by(pipeline_id=pipeline_id).delete()
    db.session.flush()

    id_map = {}
    for nd in snapshot.get('nodes', []):
        node = Node(
            pipeline_id=pipeline_id,
            type_slug=nd.get('type', 'csv_reader'),
            label=nd.get('label'),
            position_x=nd.get('position', {}).get('x', 0),
            position_y=nd.get('position', {}).get('y', 0),
        )
        node.config = nd.get('config', {})
        db.session.add(node)
        db.session.flush()
        id_map[nd['id']] = node.id

    for ed in snapshot.get('edges', []):
        edge = Edge(
            pipeline_id=pipeline_id,
            source_node_id=id_map.get(ed.get('source'), ed.get('source')),
            target_node_id=id_map.get(ed.get('target'), ed.get('target')),
            source_handle=ed.get('sourceHandle', 'output'),
            target_handle=ed.get('targetHandle', 'input'),
        )
        db.session.add(edge)

    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': f'Restored to version {version.version_num}'})


@pipelines_bp.route('/<pipeline_id>/versions/snapshot', methods=['POST'])
@jwt_required()
def create_snapshot(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json() or {}
    last = PipelineVersion.query.filter_by(pipeline_id=pipeline_id).order_by(PipelineVersion.version_num.desc()).first()
    num = (last.version_num + 1) if last else 1

    version = PipelineVersion(
        pipeline_id=pipeline_id,
        version_num=num,
        label=data.get('label', f'Version {num}'),
    )
    version.snapshot = _snapshot_pipeline(pipeline)
    db.session.add(version)
    pipeline.version_count = num
    db.session.commit()
    return jsonify(version.to_dict()), 201


# ── Templates ────────────────────────────────────────────────────────

@pipelines_bp.route('/templates', methods=['GET'])
@jwt_required()
def list_templates():
    templates = PipelineTemplate.query.all()
    category = request.args.get('category')
    if category:
        templates = [t for t in templates if t.category == category]
    return jsonify({'templates': [t.to_dict() for t in templates]})


@pipelines_bp.route('/templates/<template_id>', methods=['GET'])
@jwt_required()
def get_template(template_id):
    tpl = PipelineTemplate.query.get_or_404(template_id)
    d = tpl.to_dict()
    d['nodes'] = tpl.nodes
    d['edges'] = tpl.edges
    return jsonify(d)


@pipelines_bp.route('/templates/<template_id>/instantiate', methods=['POST'])
@jwt_required()
def instantiate_template(template_id):
    user_id = get_jwt_identity()
    tpl = PipelineTemplate.query.get_or_404(template_id)
    data = request.get_json()
    err = validate_required(data, ['workspace_id'])
    if err:
        return jsonify({'error': err}), 400

    from ..models import Workspace
    ws = Workspace.query.get(data['workspace_id'])
    if not ws or not check_org_role(ws.org_id, user_id, 'editor'):
        return jsonify({'error': 'Access denied'}), 403

    pipeline = Pipeline(
        workspace_id=data['workspace_id'],
        name=data.get('name', tpl.name),
        description=tpl.description,
    )
    db.session.add(pipeline)
    db.session.flush()

    id_map = {}
    for nd in tpl.nodes:
        node = Node(
            pipeline_id=pipeline.id,
            type_slug=nd.get('type', 'csv_reader'),
            label=nd.get('label'),
            position_x=nd.get('position', {}).get('x', 0),
            position_y=nd.get('position', {}).get('y', 0),
        )
        db.session.add(node)
        db.session.flush()
        id_map[nd['id']] = node.id

    for ed in tpl.edges:
        edge = Edge(
            pipeline_id=pipeline.id,
            source_node_id=id_map.get(ed.get('source'), ed.get('source')),
            target_node_id=id_map.get(ed.get('target'), ed.get('target')),
        )
        db.session.add(edge)

    db.session.commit()
    return jsonify(pipeline.to_dict(include_graph=True)), 201


# ── Import / Export ──────────────────────────────────────────────────

@pipelines_bp.route('/import', methods=['POST'])
@jwt_required()
def import_pipeline():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['workspace_id', 'definition'])
    if err:
        return jsonify({'error': err}), 400

    defn = data['definition']
    ws = Workspace.query.get(data['workspace_id'])
    if not ws or not check_org_role(ws.org_id, user_id, 'editor'):
        return jsonify({'error': 'Access denied'}), 403

    pipeline = Pipeline(
        workspace_id=data['workspace_id'],
        name=defn.get('name', 'Imported Pipeline'),
        description=defn.get('description'),
    )
    db.session.add(pipeline)
    db.session.flush()

    id_map = {}
    for nd in defn.get('nodes', []):
        node = Node(
            pipeline_id=pipeline.id,
            type_slug=nd.get('type', 'csv_reader'),
            label=nd.get('label'),
            position_x=nd.get('position', {}).get('x', 0),
            position_y=nd.get('position', {}).get('y', 0),
        )
        node.config = nd.get('config', {})
        db.session.add(node)
        db.session.flush()
        id_map[nd.get('id', '')] = node.id

    for ed in defn.get('edges', []):
        edge = Edge(
            pipeline_id=pipeline.id,
            source_node_id=id_map.get(ed.get('source'), ed.get('source')),
            target_node_id=id_map.get(ed.get('target'), ed.get('target')),
            source_handle=ed.get('sourceHandle', 'output'),
            target_handle=ed.get('targetHandle', 'input'),
        )
        db.session.add(edge)

    db.session.commit()
    return jsonify(pipeline.to_dict(include_graph=True)), 201


@pipelines_bp.route('/<pipeline_id>/export', methods=['GET'])
@jwt_required()
def export_pipeline(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    definition = {
        'datapipe_version': '1.0',
        'name': pipeline.name,
        'description': pipeline.description,
        'tags': pipeline.tags,
        'nodes': [n.to_dict() for n in pipeline.nodes],
        'edges': [e.to_dict() for e in pipeline.edges],
    }
    fmt = request.args.get('format', 'json')
    if fmt == 'yaml':
        try:
            import yaml
            return yaml.dump(definition), 200, {'Content-Type': 'text/yaml'}
        except ImportError:
            pass
    return jsonify(definition)


# ── Diff ─────────────────────────────────────────────────────────────

@pipelines_bp.route('/<pipeline_id>/diff', methods=['GET'])
@jwt_required()
def diff_versions(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    va_id = request.args.get('version_a')
    vb_id = request.args.get('version_b')

    def get_snapshot(vid):
        if vid == 'current':
            return _snapshot_pipeline(pipeline)
        v = PipelineVersion.query.filter_by(id=vid, pipeline_id=pipeline_id).first()
        return v.snapshot if v else {}

    snap_a = get_snapshot(va_id)
    snap_b = get_snapshot(vb_id)

    nodes_a = {n['id']: n for n in snap_a.get('nodes', [])}
    nodes_b = {n['id']: n for n in snap_b.get('nodes', [])}

    added = [n for nid, n in nodes_b.items() if nid not in nodes_a]
    removed = [n for nid, n in nodes_a.items() if nid not in nodes_b]
    modified = [{'before': nodes_a[nid], 'after': n} for nid, n in nodes_b.items() if nid in nodes_a and nodes_a[nid] != n]

    return jsonify({
        'version_a': va_id,
        'version_b': vb_id,
        'nodes': {'added': added, 'removed': removed, 'modified': modified},
        'edges': {
            'added': [e for e in snap_b.get('edges', []) if e not in snap_a.get('edges', [])],
            'removed': [e for e in snap_a.get('edges', []) if e not in snap_b.get('edges', [])],
        },
    })


# ── Merge ────────────────────────────────────────────────────────────

@pipelines_bp.route('/merge', methods=['POST'])
@jwt_required()
def merge_pipelines():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['source_id', 'target_id'])
    if err:
        return jsonify({'error': err}), 400

    src, err = check_pipeline_access(data['source_id'], user_id)
    if err:
        return jsonify({'error': f'Source: {err}'}), 404 if 'not found' in err else 403
    tgt, err = check_pipeline_access(data['target_id'], user_id)
    if err:
        return jsonify({'error': f'Target: {err}'}), 404 if 'not found' in err else 403

    offset_x = data.get('offset_x', 200)
    for node in src.nodes:
        new_node = Node(
            pipeline_id=tgt.id,
            type_slug=node.type_slug,
            label=f"[merged] {node.label}",
            position_x=node.position_x + offset_x,
            position_y=node.position_y,
        )
        new_node.config = node.config
        db.session.add(new_node)

    tgt.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Pipelines merged', 'pipeline': tgt.to_dict(include_graph=True)})
