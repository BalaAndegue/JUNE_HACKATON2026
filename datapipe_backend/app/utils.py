from flask import request
from flask_jwt_extended import get_jwt_identity
from .models import OrgMember, Pipeline, Workspace, User
import re


def validate_required(data, fields):
    if not data:
        return 'Request body is required'
    for f in fields:
        if f not in data or data[f] is None or data[f] == '':
            return f'Field "{f}" is required'
    return None


def paginate(query, default_per_page=20):
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', default_per_page, type=int), 100)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, {'total': total, 'page': page, 'per_page': per_page, 'pages': (total + per_page - 1) // per_page}


def get_current_user():
    uid = get_jwt_identity()
    return User.query.get(uid)


def check_org_role(org_id, user_id, min_role='viewer'):
    roles_order = ['viewer', 'editor', 'admin', 'owner']
    member = OrgMember.query.filter_by(org_id=org_id, user_id=user_id).first()
    if not member:
        return False
    return roles_order.index(member.role) >= roles_order.index(min_role)


def check_pipeline_access(pipeline_id, user_id):
    pipeline = Pipeline.query.get(pipeline_id)
    if not pipeline:
        return None, 'Pipeline not found'
    ws = Workspace.query.get(pipeline.workspace_id)
    if not ws:
        return None, 'Workspace not found'
    if not check_org_role(ws.org_id, user_id, 'viewer'):
        return None, 'Access denied'
    return pipeline, None


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^\w-]', '', text)
    return text


def log_audit(user_id, org_id, action, resource_type, resource_id, metadata=None):
    from .models import AuditLog
    from .extensions import db
    log = AuditLog(
        user_id=user_id,
        org_id=org_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip=request.remote_addr,
    )
    if metadata:
        log._metadata = __import__('json').dumps(metadata)
    db.session.add(log)
