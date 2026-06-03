from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from ..extensions import db
from ..models import Org, OrgMember, OrgInvite, Workspace, User
from ..utils import validate_required, check_org_role, slugify, paginate

orgs_bp = Blueprint('orgs', __name__)


@orgs_bp.route('', methods=['POST'])
@jwt_required()
def create_org():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['name'])
    if err:
        return jsonify({'error': err}), 400

    slug = data.get('slug') or slugify(data['name'])
    if Org.query.filter_by(slug=slug).first():
        slug = f"{slug}-{__import__('uuid').uuid4().hex[:6]}"

    org = Org(name=data['name'], slug=slug, plan=data.get('plan', 'free'))
    db.session.add(org)
    db.session.flush()
    db.session.add(OrgMember(org_id=org.id, user_id=user_id, role='owner'))

    ws = Workspace(org_id=org.id, name='Production', color='#3b82f6')
    db.session.add(ws)
    db.session.commit()
    return jsonify(org.to_dict()), 201


@orgs_bp.route('', methods=['GET'])
@jwt_required()
def list_orgs():
    user_id = get_jwt_identity()
    members = OrgMember.query.filter_by(user_id=user_id).all()
    orgs = []
    for m in members:
        if m.org and not m.org.deleted_at:
            d = m.org.to_dict()
            d['role'] = m.role
            orgs.append(d)
    return jsonify({'orgs': orgs})


@orgs_bp.route('/<org_id>', methods=['GET'])
@jwt_required()
def get_org(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'viewer'):
        return jsonify({'error': 'Access denied'}), 403
    org = Org.query.get_or_404(org_id)
    if org.deleted_at:
        return jsonify({'error': 'Organization not found'}), 404
    return jsonify(org.to_dict())


@orgs_bp.route('/<org_id>', methods=['PATCH'])
@jwt_required()
def update_org(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'owner'):
        return jsonify({'error': 'Owner role required'}), 403
    org = Org.query.get_or_404(org_id)
    data = request.get_json() or {}
    if 'name' in data:
        org.name = data['name']
    if 'settings' in data:
        org.settings = data['settings']
    db.session.commit()
    return jsonify(org.to_dict())


@orgs_bp.route('/<org_id>', methods=['DELETE'])
@jwt_required()
def delete_org(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'owner'):
        return jsonify({'error': 'Owner role required'}), 403
    org = Org.query.get_or_404(org_id)
    org.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Organization deleted'})


# ── Members ──────────────────────────────────────────────────────────

@orgs_bp.route('/<org_id>/members/invite', methods=['POST'])
@jwt_required()
def invite_member(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'admin'):
        return jsonify({'error': 'Admin role required'}), 403
    data = request.get_json()
    err = validate_required(data, ['email', 'role'])
    if err:
        return jsonify({'error': err}), 400
    if data['role'] not in ['viewer', 'editor', 'admin', 'owner']:
        return jsonify({'error': 'Invalid role'}), 400

    invite = OrgInvite(org_id=org_id, email=data['email'], role=data['role'])
    db.session.add(invite)
    db.session.commit()
    return jsonify({
        'invite_id': invite.id,
        'email': invite.email,
        'expires_at': invite.expires_at.date().isoformat(),
    }), 201


@orgs_bp.route('/<org_id>/members', methods=['GET'])
@jwt_required()
def list_members(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'viewer'):
        return jsonify({'error': 'Access denied'}), 403
    members = OrgMember.query.filter_by(org_id=org_id).all()
    return jsonify({'members': [m.to_dict() for m in members]})


@orgs_bp.route('/<org_id>/members/<target_user_id>', methods=['PATCH'])
@jwt_required()
def update_member_role(org_id, target_user_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'admin'):
        return jsonify({'error': 'Admin role required'}), 403
    data = request.get_json()
    err = validate_required(data, ['role'])
    if err:
        return jsonify({'error': err}), 400
    member = OrgMember.query.filter_by(org_id=org_id, user_id=target_user_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    member.role = data['role']
    db.session.commit()
    return jsonify(member.to_dict())


@orgs_bp.route('/<org_id>/members/<target_user_id>', methods=['DELETE'])
@jwt_required()
def remove_member(org_id, target_user_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'admin'):
        return jsonify({'error': 'Admin role required'}), 403
    member = OrgMember.query.filter_by(org_id=org_id, user_id=target_user_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    db.session.delete(member)
    db.session.commit()
    return jsonify({'message': 'Member removed'})


@orgs_bp.route('/<org_id>/members/accept-invite', methods=['POST'])
@jwt_required()
def accept_invite(org_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['token'])
    if err:
        return jsonify({'error': err}), 400

    invite = OrgInvite.query.filter_by(org_id=org_id, token=data['token'], accepted=False).first()
    if not invite:
        return jsonify({'error': 'Invalid or expired invite'}), 400
    if invite.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invite expired'}), 400

    existing = OrgMember.query.filter_by(org_id=org_id, user_id=user_id).first()
    if not existing:
        db.session.add(OrgMember(org_id=org_id, user_id=user_id, role=invite.role))
    invite.accepted = True
    db.session.commit()
    return jsonify({'message': 'Joined organization successfully'})


# ── Workspaces ───────────────────────────────────────────────────────

@orgs_bp.route('/<org_id>/workspaces', methods=['GET'])
@jwt_required()
def list_workspaces(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'viewer'):
        return jsonify({'error': 'Access denied'}), 403
    workspaces = Workspace.query.filter_by(org_id=org_id, deleted_at=None).all()
    return jsonify({'workspaces': [w.to_dict() for w in workspaces]})


@orgs_bp.route('/<org_id>/workspaces', methods=['POST'])
@jwt_required()
def create_workspace(org_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'admin'):
        return jsonify({'error': 'Admin role required'}), 403
    data = request.get_json()
    err = validate_required(data, ['name'])
    if err:
        return jsonify({'error': err}), 400

    ws = Workspace(
        org_id=org_id,
        name=data['name'],
        description=data.get('description'),
        color=data.get('color'),
    )
    db.session.add(ws)
    db.session.commit()
    return jsonify(ws.to_dict()), 201


@orgs_bp.route('/<org_id>/workspaces/<ws_id>', methods=['GET'])
@jwt_required()
def get_workspace(org_id, ws_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'viewer'):
        return jsonify({'error': 'Access denied'}), 403
    ws = Workspace.query.filter_by(id=ws_id, org_id=org_id, deleted_at=None).first()
    if not ws:
        return jsonify({'error': 'Workspace not found'}), 404
    return jsonify(ws.to_dict())


@orgs_bp.route('/<org_id>/workspaces/<ws_id>', methods=['PATCH'])
@jwt_required()
def update_workspace(org_id, ws_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'admin'):
        return jsonify({'error': 'Admin role required'}), 403
    ws = Workspace.query.filter_by(id=ws_id, org_id=org_id, deleted_at=None).first()
    if not ws:
        return jsonify({'error': 'Workspace not found'}), 404
    data = request.get_json() or {}
    for field in ['name', 'description', 'color']:
        if field in data:
            setattr(ws, field, data[field])
    db.session.commit()
    return jsonify(ws.to_dict())


@orgs_bp.route('/<org_id>/workspaces/<ws_id>', methods=['DELETE'])
@jwt_required()
def delete_workspace(org_id, ws_id):
    user_id = get_jwt_identity()
    if not check_org_role(org_id, user_id, 'owner'):
        return jsonify({'error': 'Owner role required'}), 403
    ws = Workspace.query.filter_by(id=ws_id, org_id=org_id, deleted_at=None).first()
    if not ws:
        return jsonify({'error': 'Workspace not found'}), 404
    ws.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Workspace deleted'})
