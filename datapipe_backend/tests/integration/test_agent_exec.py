"""Server-side agent action executor (utilisé par le bot Telegram)."""
from app import create_app
from app.extensions import db
from app.models import User, Org, OrgMember, Workspace, Pipeline, Node
from app import agent_exec


def _setup(app):
    with app.app_context():
        db.create_all()
        u = User(email='bot@t.co', name='Bot'); u.set_password('x'); db.session.add(u); db.session.flush()
        org = Org(name='O'); db.session.add(org); db.session.flush()
        db.session.add(OrgMember(org_id=org.id, user_id=u.id, role='owner'))
        ws = Workspace(org_id=org.id, name='W'); db.session.add(ws); db.session.flush()
        p = Pipeline(workspace_id=ws.id, name='P'); db.session.add(p); db.session.flush()
        db.session.commit()
        return u.id, p.id


def test_run_action_crud_and_run():
    app = create_app(testing=True)
    uid, pid = _setup(app)
    with app.app_context():
        r = agent_exec.run_action(uid, 'create_pipeline', {'name': 'Démo Bot'})
        assert r['ok'] and r['pipeline_id']
        newpid = r['pipeline_id']

        r = agent_exec.run_action(uid, 'add_node', {'node_type': 'csv_reader', 'label': 'Source'}, newpid)
        assert r['ok']
        r = agent_exec.run_action(uid, 'add_node', {'node_type': 'mask_pii', 'label': 'Masquage'}, newpid)
        assert r['ok']

        r = agent_exec.run_action(uid, 'connect_nodes', {'source': 'Source', 'target': 'Masquage'}, newpid)
        assert r['ok'], r

        r = agent_exec.run_action(uid, 'run_pipeline', {}, newpid)
        assert r['ok'] and 'run_id' in r

        r = agent_exec.run_action(uid, 'delete_node', {'node': 'Masquage'}, newpid)
        assert r['ok']


def test_ingest_file_creates_file():
    app = create_app(testing=True)
    uid, _ = _setup(app)
    with app.app_context():
        csv = b"montant,type\n100,credit\n-50,debit\n9000,credit\n"
        f = agent_exec.ingest_file(uid, 'tx.csv', csv)
        assert f is not None
        assert f.rows_count == 3
        assert set(f.columns) == {'montant', 'type'}
        import os
        assert os.path.exists(f.path)
