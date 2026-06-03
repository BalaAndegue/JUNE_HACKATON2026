"""Tests unitaires des modèles SQLAlchemy."""
import pytest
import json
from datetime import datetime

from app.extensions import db
from app.models import (
    User, Org, OrgMember, Workspace, Pipeline, Node, Edge,
    NodeType, Run, RunLog, gen_id,
)


class TestGenId:
    def test_format(self):
        uid = gen_id('usr')
        assert uid.startswith('usr_')
        assert len(uid) == 16

    def test_unique(self):
        ids = {gen_id('pip') for _ in range(100)}
        assert len(ids) == 100

    def test_different_prefixes(self):
        assert gen_id('org').startswith('org_')
        assert gen_id('ws').startswith('ws_')
        assert gen_id('pip').startswith('pip_')


class TestUserModel:
    def test_password_hashing(self, app):
        with app.app_context():
            user = User(email='hash@test.io', name='Test')
            user.set_password('MonMotDePasse1')
            assert user.password_hash != 'MonMotDePasse1'
            assert user.check_password('MonMotDePasse1')
            assert not user.check_password('mauvais')

    def test_to_dict_fields(self, app):
        with app.app_context():
            user = User(email='dict@test.io', name='Dict User')
            user.set_password('TestPass123')
            db.session.add(user)
            db.session.flush()
            d = user.to_dict()
            assert 'id' in d
            assert d['email'] == 'dict@test.io'
            assert d['name'] == 'Dict User'
            assert 'password_hash' not in d
            assert 'verified' in d
            assert 'created_at' in d
            assert 'orgs' in d
            db.session.rollback()

    def test_default_verified_false(self, app):
        with app.app_context():
            user = User(email='unverified@test.io', name='U')
            user.set_password('Pass1234')
            db.session.add(user)
            db.session.flush()
            assert user.verified is False
            db.session.rollback()

    def test_soft_delete(self, app):
        with app.app_context():
            user = User(email='delete@test.io', name='Del')
            user.set_password('Pass1234')
            db.session.add(user)
            db.session.flush()
            assert user.deleted_at is None
            user.deleted_at = datetime.utcnow()
            assert user.deleted_at is not None
            db.session.rollback()


class TestOrgModel:
    def test_settings_json(self, app):
        with app.app_context():
            org = Org(name='Test Org', slug='test-org')
            org.settings = {'allow_public_pipelines': True, 'timezone': 'UTC'}
            assert org.settings['allow_public_pipelines'] is True
            assert org.settings['timezone'] == 'UTC'

    def test_to_dict(self, app):
        with app.app_context():
            org = Org(name='Banque CI', slug='banque-ci', plan='pro')
            db.session.add(org)
            db.session.flush()
            d = org.to_dict()
            assert d['name'] == 'Banque CI'
            assert d['slug'] == 'banque-ci'
            assert d['plan'] == 'pro'
            assert 'members_count' in d
            db.session.rollback()

    def test_default_plan_free(self, app):
        with app.app_context():
            org = Org(name='Free Org', slug='free-org-x')
            db.session.add(org)
            db.session.flush()
            assert org.plan == 'free'
            db.session.rollback()


class TestPipelineModel:
    def test_tags_json(self, app):
        with app.app_context():
            ws = Workspace(org_id='org_test', name='WS')
            db.session.add(ws)
            db.session.flush()

            pip = Pipeline(workspace_id=ws.id, name='Test Pipeline')
            pip.tags = ['bancaire', 'mensuel', 'etl']
            assert pip.tags == ['bancaire', 'mensuel', 'etl']
            db.session.rollback()

    def test_to_dict_without_graph(self, app):
        with app.app_context():
            ws = Workspace(org_id='org_test', name='WS2')
            db.session.add(ws)
            db.session.flush()

            pip = Pipeline(workspace_id=ws.id, name='Pipeline Dict')
            db.session.add(pip)
            db.session.flush()

            d = pip.to_dict()
            assert d['name'] == 'Pipeline Dict'
            assert 'nodes' not in d
            assert 'edges' not in d

            d_full = pip.to_dict(include_graph=True)
            assert 'nodes' in d_full
            assert 'edges' in d_full
            db.session.rollback()


class TestNodeModel:
    def test_config_json(self, app):
        with app.app_context():
            ws = Workspace(org_id='org_x', name='WS')
            db.session.add(ws)
            db.session.flush()

            pip = Pipeline(workspace_id=ws.id, name='P')
            db.session.add(pip)
            db.session.flush()

            node = Node(pipeline_id=pip.id, type_slug='csv_reader')
            node.config = {'delimiter': ';', 'has_header': True, 'encoding': 'utf-8'}
            assert node.config['delimiter'] == ';'
            assert node.config['has_header'] is True
            db.session.rollback()

    def test_pinned_data(self, app):
        with app.app_context():
            ws = Workspace(org_id='org_y', name='WS')
            db.session.add(ws)
            db.session.flush()

            pip = Pipeline(workspace_id=ws.id, name='P')
            db.session.add(pip)
            db.session.flush()

            node = Node(pipeline_id=pip.id, type_slug='filter')
            assert node.pinned_data is None

            node.pinned_data = [{'id': 1, 'montant': 1500}]
            assert node.pinned_data == [{'id': 1, 'montant': 1500}]

            node.pinned_data = None
            assert node.pinned_data is None
            db.session.rollback()

    def test_to_dict(self, app):
        with app.app_context():
            ws = Workspace(org_id='org_z', name='WS')
            db.session.add(ws)
            db.session.flush()

            pip = Pipeline(workspace_id=ws.id, name='P')
            db.session.add(pip)
            db.session.flush()

            node = Node(pipeline_id=pip.id, type_slug='aggregate', label='Agréger', position_x=100, position_y=200)
            node.config = {}
            db.session.add(node)
            db.session.flush()

            d = node.to_dict()
            assert d['type'] == 'aggregate'
            assert d['label'] == 'Agréger'
            assert d['position'] == {'x': 100.0, 'y': 200.0}
            assert d['has_pinned_data'] is False
            db.session.rollback()


class TestRunModel:
    def test_duration_ms(self, app):
        with app.app_context():
            from datetime import timedelta
            run = Run(pipeline_id='pip_x', status='success')
            run.started_at = datetime(2026, 6, 1, 10, 0, 0)
            run.finished_at = datetime(2026, 6, 1, 10, 0, 5, 500000)
            assert run.duration_ms == 5500

    def test_duration_ms_none_when_running(self, app):
        with app.app_context():
            run = Run(pipeline_id='pip_x', status='running')
            run.started_at = datetime.utcnow()
            assert run.duration_ms is None

    def test_node_results_json(self, app):
        with app.app_context():
            run = Run(pipeline_id='pip_x')
            run.node_results = {'nod_1': {'status': 'success', 'rows': 100}}
            assert run.node_results['nod_1']['rows'] == 100
