"""
Fixtures partagées pour tous les tests DataPipe.
Utilise une base SQLite en mémoire — chaque session de test repart de zéro.
"""
import pytest
import json
import io

from app import create_app
from app.extensions import db as _db

# ─────────────────────────────── APP / DB ────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Application Flask en mode test (SQLite in-memory)."""
    application = create_app(testing=True)
    ctx = application.app_context()
    ctx.push()
    yield application
    ctx.pop()


@pytest.fixture(scope='session')
def db(app):
    """Base de données créée une fois pour toute la session."""
    _db.create_all()
    yield _db
    _db.drop_all()


@pytest.fixture(scope='function', autouse=True)
def db_rollback(db):
    """Rollback après chaque test pour isolation complète."""
    yield
    db.session.rollback()


@pytest.fixture(scope='session')
def client(app):
    """Client HTTP Flask pour les tests d'intégration."""
    return app.test_client()


# ─────────────────────────────── HELPERS ────────────────────────────────────

def post_json(client, url, data, headers=None):
    return client.post(url, data=json.dumps(data),
                       content_type='application/json', headers=headers or {})


def patch_json(client, url, data, headers=None):
    return client.patch(url, data=json.dumps(data),
                        content_type='application/json', headers=headers or {})


def delete_json(client, url, data=None, headers=None):
    kwargs = {'headers': headers or {}}
    if data:
        kwargs['data'] = json.dumps(data)
        kwargs['content_type'] = 'application/json'
    return client.delete(url, **kwargs)


def post_multipart(client, url, form=None, file_field='file', filename='data.csv',
                   content=b'', content_type='text/csv', headers=None):
    data = dict(form or {})
    data[file_field] = (io.BytesIO(content), filename, content_type)
    return client.post(url, data=data, content_type='multipart/form-data', headers=headers or {})


# ─────────────────────────────── USER / AUTH ────────────────────────────────

USER_EMAIL = 'test@datapipe.io'
USER_PASSWORD = 'Hackaton2026!'
USER_NAME = 'Jean Kouassi'
ORG_NAME = 'Banque Test CI'


@pytest.fixture(scope='session')
def registered_user(client):
    """Crée un utilisateur une seule fois pour la session."""
    resp = post_json(client, '/api/v1/auth/register', {
        'email': USER_EMAIL,
        'name': USER_NAME,
        'password': USER_PASSWORD,
        'org_name': ORG_NAME,
    })
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


@pytest.fixture(scope='session')
def auth_tokens(client, registered_user):
    """Retourne {access_token, refresh_token}."""
    resp = post_json(client, '/api/v1/auth/login', {
        'email': USER_EMAIL,
        'password': USER_PASSWORD,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


@pytest.fixture(scope='session')
def auth_headers(auth_tokens):
    """Headers Authorization prêts à l'emploi."""
    return {'Authorization': f"Bearer {auth_tokens['access_token']}"}


@pytest.fixture(scope='session')
def org_id(client, auth_headers):
    """ID de l'organisation créée automatiquement à l'inscription."""
    resp = client.get('/api/v1/orgs', headers=auth_headers)
    data = resp.get_json()
    assert data['orgs'], "Aucune organisation trouvée"
    return data['orgs'][0]['id']


@pytest.fixture(scope='session')
def workspace_id(client, auth_headers, org_id):
    """ID du premier workspace de l'org."""
    resp = client.get(f'/api/v1/orgs/{org_id}/workspaces', headers=auth_headers)
    data = resp.get_json()
    assert data['workspaces'], "Aucun workspace trouvé"
    return data['workspaces'][0]['id']


@pytest.fixture(scope='session')
def pipeline_id(client, auth_headers, workspace_id):
    """Crée un pipeline de test et retourne son ID."""
    resp = post_json(client, '/api/v1/pipelines', {
        'name': 'Pipeline Test',
        'workspace_id': workspace_id,
        'description': 'Pipeline de test automatisé',
        'tags': ['test', 'bancaire'],
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()['id']


@pytest.fixture(scope='session')
def node_id(client, auth_headers, pipeline_id):
    """Crée un nœud et retourne son ID."""
    resp = post_json(client, f'/api/v1/pipelines/{pipeline_id}/nodes', {
        'type': 'csv_reader',
        'label': 'Lire CSV',
        'position': {'x': 100, 'y': 200},
        'config': {'delimiter': ',', 'has_header': True},
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()['id']


@pytest.fixture(scope='session')
def second_node_id(client, auth_headers, pipeline_id):
    """Crée un second nœud (pour les tests d'edges)."""
    resp = post_json(client, f'/api/v1/pipelines/{pipeline_id}/nodes', {
        'type': 'filter',
        'label': 'Filtrer',
        'position': {'x': 400, 'y': 200},
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.get_json()['id']


@pytest.fixture(scope='session')
def run_id(client, auth_headers, pipeline_id, node_id):
    """Déclenche un run et retourne son ID."""
    resp = post_json(client, f'/api/v1/pipelines/{pipeline_id}/run', {}, headers=auth_headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()['id']
