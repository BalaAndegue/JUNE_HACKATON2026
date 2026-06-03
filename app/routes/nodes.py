from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from ..extensions import db
from ..models import Node, Edge, NodeType, Pipeline
from ..utils import validate_required, check_pipeline_access

nodes_bp = Blueprint('nodes', __name__)


def _check_editor(pipeline_id, user_id):
    from ..models import Workspace
    from ..utils import check_org_role
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return None, err
    ws = Workspace.query.get(pipeline.workspace_id)
    if not check_org_role(ws.org_id, user_id, 'editor'):
        return None, 'Editor role required'
    return pipeline, None


# ── Nodes ─────────────────────────────────────────────────────────────

@nodes_bp.route('/pipelines/<pipeline_id>/nodes', methods=['GET'])
@jwt_required()
def list_nodes(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    return jsonify({'nodes': [n.to_dict() for n in pipeline.nodes]})


@nodes_bp.route('/pipelines/<pipeline_id>/nodes', methods=['POST'])
@jwt_required()
def create_node(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json()
    err = validate_required(data, ['type'])
    if err:
        return jsonify({'error': err}), 400

    pos = data.get('position', {})
    node = Node(
        pipeline_id=pipeline_id,
        type_slug=data['type'],
        label=data.get('label', data['type']),
        position_x=pos.get('x', 0),
        position_y=pos.get('y', 0),
    )
    node.config = data.get('config', {})
    db.session.add(node)
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(node.to_dict()), 201


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/bulk', methods=['POST'])
@jwt_required()
def bulk_create_nodes(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json()
    nodes_data = data.get('nodes', [])
    if not nodes_data:
        return jsonify({'error': 'nodes array is required'}), 400

    created = []
    for nd in nodes_data:
        pos = nd.get('position', {})
        node = Node(
            pipeline_id=pipeline_id,
            type_slug=nd.get('type', 'csv_reader'),
            label=nd.get('label', nd.get('type', 'node')),
            position_x=pos.get('x', 0),
            position_y=pos.get('y', 0),
        )
        node.config = nd.get('config', {})
        db.session.add(node)
        db.session.flush()
        created.append(node.to_dict())

    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'nodes': created, 'count': len(created)}), 201


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>', methods=['GET'])
@jwt_required()
def get_node(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    return jsonify(node.to_dict())


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>', methods=['PUT'])
@jwt_required()
def replace_node(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404

    data = request.get_json()
    pos = data.get('position', {})
    node.type_slug = data.get('type', node.type_slug)
    node.label = data.get('label', node.label)
    node.position_x = pos.get('x', node.position_x)
    node.position_y = pos.get('y', node.position_y)
    node.config = data.get('config', {})
    node.updated_at = datetime.utcnow()
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(node.to_dict())


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>', methods=['PATCH'])
@jwt_required()
def update_node(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404

    data = request.get_json() or {}
    if 'label' in data:
        node.label = data['label']
    if 'config' in data:
        node.config = data['config']
    if 'position' in data:
        node.position_x = data['position'].get('x', node.position_x)
        node.position_y = data['position'].get('y', node.position_y)
    node.updated_at = datetime.utcnow()
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(node.to_dict())


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>', methods=['DELETE'])
@jwt_required()
def delete_node(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404

    Edge.query.filter(
        (Edge.source_node_id == node_id) | (Edge.target_node_id == node_id),
        Edge.pipeline_id == pipeline_id
    ).delete(synchronize_session=False)

    db.session.delete(node)
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Node deleted'})


# ── Pinned Data ───────────────────────────────────────────────────────

@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>/pin-data', methods=['POST'])
@jwt_required()
def pin_data(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404

    data = request.get_json()
    if 'data' not in data:
        return jsonify({'error': 'data field is required'}), 400

    node.pinned_data = data['data']
    db.session.commit()
    return jsonify({'message': 'Data pinned', 'node_id': node_id})


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>/pinned-data', methods=['GET'])
@jwt_required()
def get_pinned_data(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    if node.pinned_data is None:
        return jsonify({'error': 'No pinned data'}), 404

    return jsonify({'node_id': node_id, 'data': node.pinned_data})


@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>/pinned-data', methods=['DELETE'])
@jwt_required()
def delete_pinned_data(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404

    node.pinned_data = None
    db.session.commit()
    return jsonify({'message': 'Pinned data removed'})


# ── Edges ─────────────────────────────────────────────────────────────

@nodes_bp.route('/pipelines/<pipeline_id>/edges', methods=['GET'])
@jwt_required()
def list_edges(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403
    return jsonify({'edges': [e.to_dict() for e in pipeline.edges]})


@nodes_bp.route('/pipelines/<pipeline_id>/edges', methods=['POST'])
@jwt_required()
def create_edge(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    data = request.get_json()
    err = validate_required(data, ['source', 'target'])
    if err:
        return jsonify({'error': err}), 400

    dup = Edge.query.filter_by(
        pipeline_id=pipeline_id,
        source_node_id=data['source'],
        target_node_id=data['target'],
    ).first()
    if dup:
        return jsonify({'error': 'Edge already exists'}), 409

    edge = Edge(
        pipeline_id=pipeline_id,
        source_node_id=data['source'],
        target_node_id=data['target'],
        source_handle=data.get('sourceHandle', 'output'),
        target_handle=data.get('targetHandle', 'input'),
    )
    db.session.add(edge)
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(edge.to_dict()), 201


@nodes_bp.route('/pipelines/<pipeline_id>/edges/<edge_id>', methods=['DELETE'])
@jwt_required()
def delete_edge(pipeline_id, edge_id):
    user_id = get_jwt_identity()
    pipeline, err = _check_editor(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    edge = Edge.query.filter_by(id=edge_id, pipeline_id=pipeline_id).first()
    if not edge:
        return jsonify({'error': 'Edge not found'}), 404

    db.session.delete(edge)
    pipeline.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Edge deleted'})


@nodes_bp.route('/pipelines/<pipeline_id>/edges/validate', methods=['POST'])
@jwt_required()
def validate_edges(pipeline_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    edges = pipeline.edges
    node_ids = {n.id for n in pipeline.nodes}
    errors = []

    for edge in edges:
        if edge.source_node_id not in node_ids:
            errors.append({'edge_id': edge.id, 'error': f'Source node {edge.source_node_id} not found'})
        if edge.target_node_id not in node_ids:
            errors.append({'edge_id': edge.id, 'error': f'Target node {edge.target_node_id} not found'})

    adj = {nid: [] for nid in node_ids}
    for edge in edges:
        if edge.source_node_id in adj:
            adj[edge.source_node_id].append(edge.target_node_id)

    visited, rec_stack = set(), set()
    has_cycle = False

    def dfs(node):
        nonlocal has_cycle
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                has_cycle = True
        rec_stack.discard(node)

    for nid in node_ids:
        if nid not in visited:
            dfs(nid)

    if has_cycle:
        errors.append({'error': 'Pipeline contains a cycle'})

    return jsonify({'valid': len(errors) == 0, 'errors': errors})


# ── Test Data ─────────────────────────────────────────────────────────

@nodes_bp.route('/pipelines/<pipeline_id>/nodes/<node_id>/test-data', methods=['GET'])
@jwt_required()
def get_test_data(pipeline_id, node_id):
    user_id = get_jwt_identity()
    pipeline, err = check_pipeline_access(pipeline_id, user_id)
    if err:
        return jsonify({'error': err}), 404 if 'not found' in err else 403

    node = Node.query.filter_by(id=node_id, pipeline_id=pipeline_id).first()
    if not node:
        return jsonify({'error': 'Node not found'}), 404

    if node.pinned_data:
        return jsonify({'source': 'pinned', 'data': node.pinned_data})

    mock_data = [
        {'id': 1, 'montant': 15000.50, 'devise': 'XAF', 'date': '2026-06-01', 'type': 'virement', 'statut': 'traite'},
        {'id': 2, 'montant': 8500.00, 'devise': 'XAF', 'date': '2026-06-01', 'type': 'retrait', 'statut': 'en_attente'},
        {'id': 3, 'montant': 250000.00, 'devise': 'XAF', 'date': '2026-06-02', 'type': 'virement', 'statut': 'traite'},
    ]
    return jsonify({'source': 'mock', 'node_type': node.type_slug, 'data': mock_data})


# ── Node Types ─────────────────────────────────────────────────────────

@nodes_bp.route('/node-types', methods=['GET'])
@jwt_required()
def list_node_types():
    types = NodeType.query.all()
    category = request.args.get('category')
    if category:
        types = [t for t in types if t.category == category]
    categories = {}
    for t in types:
        cat = t.category or 'Other'
        categories.setdefault(cat, []).append(t.to_dict())
    return jsonify({'node_types': [t.to_dict() for t in types], 'by_category': categories})


@nodes_bp.route('/node-types/<type_slug>', methods=['GET'])
@jwt_required()
def get_node_type(type_slug):
    nt = NodeType.query.filter_by(slug=type_slug).first()
    if not nt:
        return jsonify({'error': 'Node type not found'}), 404
    return jsonify(nt.to_dict())


@nodes_bp.route('/node-types/<type_slug>/schema', methods=['GET'])
@jwt_required()
def get_node_type_schema(type_slug):
    nt = NodeType.query.filter_by(slug=type_slug).first()
    if not nt:
        return jsonify({'error': 'Node type not found'}), 404
    return jsonify({'slug': type_slug, 'schema': nt.schema})
