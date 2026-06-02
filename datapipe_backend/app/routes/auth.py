from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
)
from datetime import datetime, timedelta
from uuid import uuid4

from ..extensions import db, bcrypt, blacklisted_tokens
from ..models import User, UserSession, Org, OrgMember
from ..utils import validate_required, get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    err = validate_required(data, ['email', 'name', 'password'])
    if err:
        return jsonify({'error': err}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(email=data['email'], name=data['name'], verify_token=uuid4().hex)
    user.set_password(data['password'])
    db.session.add(user)

    if data.get('org_name'):
        from ..utils import slugify
        slug = slugify(data['org_name'])
        org = Org(name=data['org_name'], slug=slug)
        db.session.add(org)
        db.session.flush()
        db.session.add(OrgMember(org_id=org.id, user_id=user.id, role='owner'))

    db.session.commit()
    return jsonify({
        'user': {'id': user.id, 'email': user.email, 'name': user.name, 'verified': user.verified},
        'message': 'Verification email sent',
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    err = validate_required(data, ['email', 'password'])
    if err:
        return jsonify({'error': err}), 400

    user = User.query.filter_by(email=data['email'], deleted_at=None).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    jti = uuid4().hex
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id, additional_claims={'jti': jti})

    session = UserSession(
        user_id=user.id,
        jti=jti,
        user_agent=request.headers.get('User-Agent', ''),
        ip=request.remote_addr,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.session.add(session)
    db.session.commit()

    org_id = user.org_members[0].org_id if user.org_members else None
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': 900,
        'user': {'id': user.id, 'name': user.name, 'email': user.email, 'org_id': org_id},
    })


@auth_bp.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    claims = get_jwt()
    old_jti = claims.get('jti', '')

    blacklisted_tokens.add(old_jti)
    sess = UserSession.query.filter_by(jti=old_jti).first()
    if sess:
        sess.revoked = True

    new_jti = uuid4().hex
    new_access = create_access_token(identity=user_id)
    new_refresh = create_refresh_token(identity=user_id, additional_claims={'jti': new_jti})

    new_sess = UserSession(
        user_id=user_id,
        jti=new_jti,
        user_agent=request.headers.get('User-Agent', ''),
        ip=request.remote_addr,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.session.add(new_sess)
    db.session.commit()

    return jsonify({'access_token': new_access, 'refresh_token': new_refresh, 'expires_in': 900})


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    data = request.get_json() or {}
    jti = get_jwt()['jti']
    blacklisted_tokens.add(jti)

    refresh_token_val = data.get('refresh_token')
    if refresh_token_val:
        sess = UserSession.query.filter_by(jti=jti).first()
        if sess:
            sess.revoked = True
            db.session.commit()

    return jsonify({'message': 'Logged out successfully'})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user = get_current_user()
    if not user or user.deleted_at:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())


@auth_bp.route('/me', methods=['PATCH'])
@jwt_required()
def update_me():
    user = get_current_user()
    data = request.get_json() or {}
    if 'name' in data:
        user.name = data['name']
    if 'avatar_url' in data:
        user.avatar_url = data['avatar_url']
    db.session.commit()
    return jsonify({'id': user.id, 'name': user.name, 'avatar_url': user.avatar_url})


@auth_bp.route('/me', methods=['DELETE'])
@jwt_required()
def delete_me():
    user = get_current_user()
    data = request.get_json() or {}
    if not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Invalid password'}), 400
    user.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Account deleted'})


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user = get_current_user()
    data = request.get_json()
    err = validate_required(data, ['current_password', 'new_password'])
    if err:
        return jsonify({'error': err}), 400
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 400
    if len(data['new_password']) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400

    user.set_password(data['new_password'])
    sessions = UserSession.query.filter_by(user_id=user.id, revoked=False).all()
    for s in sessions:
        s.revoked = True
        blacklisted_tokens.add(s.jti)
    db.session.commit()
    return jsonify({'message': 'Password updated. All sessions revoked.'})


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    err = validate_required(data, ['email'])
    if err:
        return jsonify({'error': err}), 400

    user = User.query.filter_by(email=data['email'], deleted_at=None).first()
    if user:
        user.reset_token = uuid4().hex
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
    return jsonify({'message': 'Reset email sent if account exists'})


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    err = validate_required(data, ['token', 'new_password'])
    if err:
        return jsonify({'error': err}), 400

    user = User.query.filter_by(reset_token=data['token']).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400

    user.set_password(data['new_password'])
    user.reset_token = None
    user.reset_token_expires = None
    db.session.commit()
    return jsonify({'message': 'Password reset successfully'})


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json()
    err = validate_required(data, ['token'])
    if err:
        return jsonify({'error': err}), 400

    user = User.query.filter_by(verify_token=data['token']).first()
    if not user:
        return jsonify({'error': 'Invalid token'}), 400

    user.verified = True
    user.verify_token = None
    db.session.commit()
    access_token = create_access_token(identity=user.id)
    return jsonify({'message': 'Email verified', 'access_token': access_token})


@auth_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    user_id = get_jwt_identity()
    current_jti = get_jwt()['jti']
    sessions = UserSession.query.filter_by(user_id=user_id, revoked=False).all()
    return jsonify({'sessions': [s.to_dict(current_jti) for s in sessions]})


@auth_bp.route('/sessions/<session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    user_id = get_jwt_identity()
    sess = UserSession.query.filter_by(id=session_id, user_id=user_id).first()
    if not sess:
        return jsonify({'error': 'Session not found'}), 404
    sess.revoked = True
    blacklisted_tokens.add(sess.jti)
    db.session.commit()
    return jsonify({'message': 'Session revoked'})


@auth_bp.route('/revoke-all-sessions', methods=['POST'])
@jwt_required()
def revoke_all_sessions():
    user_id = get_jwt_identity()
    current_jti = get_jwt()['jti']
    data = request.get_json() or {}
    except_current = data.get('except_current', False)

    sessions = UserSession.query.filter_by(user_id=user_id, revoked=False).all()
    count = 0
    for s in sessions:
        if except_current and s.jti == current_jti:
            continue
        s.revoked = True
        blacklisted_tokens.add(s.jti)
        count += 1
    db.session.commit()
    return jsonify({'revoked_count': count, 'message': 'All sessions revoked'})
