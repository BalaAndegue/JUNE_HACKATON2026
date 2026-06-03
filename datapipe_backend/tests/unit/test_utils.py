"""Tests unitaires des fonctions utilitaires."""
import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
from app.utils import (
    validate_required,
    slugify,
    paginate,
    check_org_role,
    check_pipeline_access,
    log_audit,
)


class TestValidateRequired:
    def test_missing_body(self):
        assert validate_required(None, ['email']) == 'Request body is required'

    def test_missing_field(self):
        assert validate_required({'name': 'x'}, ['name', 'email']) == 'Field "email" is required'

    def test_empty_string_field(self):
        assert validate_required({'email': ''}, ['email']) == 'Field "email" is required'

    def test_none_field(self):
        assert validate_required({'email': None}, ['email']) == 'Field "email" is required'

    def test_all_present(self):
        assert validate_required({'email': 'a@b.com', 'password': 'xxx'}, ['email', 'password']) is None

    def test_extra_fields_allowed(self):
        assert validate_required({'email': 'a@b.com', 'extra': 'ignored'}, ['email']) is None

    def test_empty_fields_list(self):
        assert validate_required({'x': 1}, []) is None

    def test_zero_value_accepted(self):
        assert validate_required({'count': 0}, ['count']) is None


class TestSlugify:
    def test_basic(self):
        assert slugify('Banque Nationale') == 'banque-nationale'

    def test_special_chars(self):
        result = slugify("Côte d'Ivoire!")
        assert 'ivoire' in result
        assert '!' not in result

    def test_multiple_spaces(self):
        assert slugify('  hello   world  ') == 'hello-world'

    def test_underscores_converted(self):
        assert slugify('my_org_name') == 'my-org-name'

    def test_already_slug(self):
        assert slugify('already-slug') == 'already-slug'

    def test_numbers(self):
        result = slugify('Pipeline 2026')
        assert '2026' in result


class TestPaginate:
    def test_pagination_basic(self):
        app = Flask(__name__)
        query = MagicMock()
        query.count.return_value = 5
        query.offset.return_value.limit.return_value.all.return_value = ['a', 'b']

        with app.test_request_context('/?page=2&per_page=2'):
            items, pagination = paginate(query)

        query.offset.assert_called_once_with(2)
        assert items == ['a', 'b']
        assert pagination == {'total': 5, 'page': 2, 'per_page': 2, 'pages': 3}

    def test_per_page_is_capped(self):
        app = Flask(__name__)
        query = MagicMock()
        query.count.return_value = 0
        query.offset.return_value.limit.return_value.all.return_value = []

        with app.test_request_context('/?per_page=999'):
            _, pagination = paginate(query)

        assert pagination['per_page'] == 100


class TestOrgAndPipelineChecks:
    @patch('app.utils.OrgMember')
    def test_check_org_role_true(self, mock_org_member):
        member = MagicMock()
        member.role = 'admin'
        mock_org_member.query.filter_by.return_value.first.return_value = member
        assert check_org_role('org_1', 'usr_1', 'editor') is True

    @patch('app.utils.OrgMember')
    def test_check_org_role_false_when_no_member(self, mock_org_member):
        mock_org_member.query.filter_by.return_value.first.return_value = None
        assert check_org_role('org_1', 'usr_1', 'viewer') is False

    @patch('app.utils.check_org_role')
    @patch('app.utils.Workspace')
    @patch('app.utils.Pipeline')
    def test_check_pipeline_access_success(self, mock_pipeline, mock_workspace, mock_check_org_role):
        pipeline = MagicMock()
        pipeline.workspace_id = 'ws_1'
        workspace = MagicMock()
        workspace.org_id = 'org_1'

        mock_pipeline.query.get.return_value = pipeline
        mock_workspace.query.get.return_value = workspace
        mock_check_org_role.return_value = True

        found, err = check_pipeline_access('pip_1', 'usr_1')
        assert found is pipeline
        assert err is None

    @patch('app.utils.Pipeline')
    def test_check_pipeline_access_pipeline_not_found(self, mock_pipeline):
        mock_pipeline.query.get.return_value = None
        found, err = check_pipeline_access('pip_x', 'usr_1')
        assert found is None
        assert err == 'Pipeline not found'


class TestAuditLog:
    @patch('app.extensions.db.session.add')
    @patch('app.models.AuditLog')
    def test_log_audit_adds_record(self, mock_audit_log, mock_add):
        app = Flask(__name__)
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
            log_audit('usr_1', 'org_1', 'create', 'pipeline', 'pip_1', {'source': 'test'})

        mock_audit_log.assert_called_once()
        mock_add.assert_called_once()
