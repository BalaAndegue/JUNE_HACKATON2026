"""
Demo seed — a frictionless, ready-to-run banking pipeline.

Creates (idempotently) a demo account, org, workspace, an uploaded dirty
transactions file and a full banking pipeline:

    CSV source -> Masquage PII -> Détection anomalies -> Agrégation par type

so a judge can log in and hit "Exécuter" to see the real engine at work.
Credentials: demo@bank.cm / Hackaton2026!
"""
import os
import shutil

from .extensions import db
from .models import (User, Org, OrgMember, Workspace, Pipeline, Node, Edge, File)

DEMO_EMAIL = 'demo@bank.cm'
DEMO_PASSWORD = 'Hackaton2026!'
SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'samples', 'transactions_demo.csv')


def seed_demo(upload_folder):
    if User.query.filter_by(email=DEMO_EMAIL).first():
        return  # already seeded

    user = User(email=DEMO_EMAIL, name='Wilson (Démo)', verified=True)
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()

    org = Org(name='Banque Démo', slug='banque-demo', plan='enterprise')
    db.session.add(org)
    db.session.flush()
    db.session.add(OrgMember(org_id=org.id, user_id=user.id, role='owner'))

    ws = Workspace(org_id=org.id, name='Conformité & Risques',
                   description='Pipelines de traitement des transactions', color='#0ea5e9')
    db.session.add(ws)
    db.session.flush()

    # Copy the sample CSV into the workspace upload dir and register it.
    file_rec = None
    if os.path.exists(SAMPLE):
        dest_dir = os.path.join(upload_folder, ws.id)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, 'transactions_demo.csv')
        shutil.copyfile(SAMPLE, dest)

        import csv as _csv
        with open(SAMPLE, encoding='utf-8') as fp:
            reader = _csv.DictReader(fp)
            cols = reader.fieldnames or []
            rows = list(reader)
        file_rec = File(workspace_id=ws.id, name='transactions_demo.csv',
                        original_name='transactions_demo.csv',
                        size=os.path.getsize(SAMPLE), mime_type='text/csv',
                        path=dest, rows_count=len(rows), columns_count=len(cols))
        file_rec.columns = cols
        file_rec.preview = rows[:5]
        db.session.add(file_rec)
        db.session.flush()

    pipe = Pipeline(workspace_id=ws.id, name='Nettoyage & conformité transactions',
                    description='CSV bancaire → masquage RGPD → détection anomalies → agrégation',
                    status='active')
    pipe.tags = ['bancaire', 'conformité', 'démo']
    db.session.add(pipe)
    db.session.flush()

    def node(slug, label, x, y, config):
        n = Node(pipeline_id=pipe.id, type_slug=slug, label=label,
                 position_x=x, position_y=y)
        n.config = config
        db.session.add(n)
        db.session.flush()
        return n

    src = node('csv_reader', 'Transactions CSV', 80, 200,
               {'file_id': file_rec.id if file_rec else None})
    mask = node('mask_pii', 'Masquage RGPD', 360, 200, {'auto': True})
    anom = node('detect_anomalies', 'Détection anomalies', 640, 200,
                {'field': 'amount', 'method': 'all', 'threshold': 5_000_000, 'z': 3})
    agg = node('aggregate', 'Agrégation par type', 920, 200,
               {'group_by': ['transaction_type'],
                'aggregations': [
                    {'field': 'amount', 'function': 'sum', 'alias': 'total'},
                    {'field': 'transaction_id', 'function': 'count', 'alias': 'nb'}]})

    for s, t in [(src, mask), (mask, anom), (anom, agg)]:
        db.session.add(Edge(pipeline_id=pipe.id, source_node_id=s.id, target_node_id=t.id))

    db.session.commit()
