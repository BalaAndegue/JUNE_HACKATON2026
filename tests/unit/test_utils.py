"""Tests unitaires des fonctions utilitaires."""
import pytest
from unittest.mock import MagicMock, patch
from app.utils import validate_required, slugify


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
