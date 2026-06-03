"""End-to-end smoke test of the real engine through the HTTP layer.

Registers a user, uploads the dirty demo CSV, builds a banking pipeline
(csv_reader -> mask_pii -> detect_anomalies -> aggregate) and runs it,
printing the REAL node results. Run: python scripts/smoke_engine.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db

SAMPLE = os.path.join(os.path.dirname(__file__), '..', 'samples', 'transactions_demo.csv')


def jpost(c, url, data, headers=None):
    return c.post(url, data=json.dumps(data), content_type='application/json',
                  headers=headers or {})


def main():
    app = create_app(testing=True)
    with app.app_context():
        db.create_all()
        c = app.test_client()

        reg = jpost(c, '/api/v1/auth/register', {
            'email': 'demo@bank.cm', 'name': 'Wilson', 'password': 'Hackaton2026!',
            'org_name': 'Banque Démo'}).get_json()
        login = jpost(c, '/api/v1/auth/login',
                      {'email': 'demo@bank.cm', 'password': 'Hackaton2026!'}).get_json()
        h = {'Authorization': f"Bearer {login['access_token']}"}

        org = c.get('/api/v1/orgs', headers=h).get_json()['orgs'][0]['id']
        ws = c.get(f'/api/v1/orgs/{org}/workspaces', headers=h).get_json()['workspaces'][0]['id']

        # upload the dirty CSV
        with open(SAMPLE, 'rb') as f:
            content = f.read()
        up = c.post('/api/v1/files/upload',
                    data={'workspace_id': ws,
                          'file': (io.BytesIO(content), 'transactions_demo.csv')},
                    content_type='multipart/form-data', headers=h).get_json()
        file_id = up['id']
        print(f"Uploaded: {up['rows_count']} rows, {up['columns_count']} cols")

        pip = jpost(c, '/api/v1/pipelines',
                    {'name': 'Démo bancaire', 'workspace_id': ws}, headers=h).get_json()
        pid = pip['id']

        def add_node(type_slug, label, config):
            return jpost(c, f'/api/v1/pipelines/{pid}/nodes',
                         {'type': type_slug, 'label': label, 'config': config,
                          'position': {'x': 0, 'y': 0}}, headers=h).get_json()['id']

        n_src = add_node('csv_reader', 'Source CSV', {'file_id': file_id})
        n_mask = add_node('mask_pii', 'Masquage', {'auto': True})
        n_anom = add_node('detect_anomalies', 'Anomalies',
                          {'field': 'amount', 'method': 'all', 'threshold': 5_000_000})
        n_agg = add_node('aggregate', 'Agrégation',
                         {'group_by': ['transaction_type'],
                          'aggregations': [
                              {'field': 'amount', 'function': 'sum', 'alias': 'total'},
                              {'field': 'transaction_id', 'function': 'count', 'alias': 'nb'}]})

        def add_edge(s, t):
            jpost(c, f'/api/v1/pipelines/{pid}/edges',
                  {'source': s, 'target': t}, headers=h)

        add_edge(n_src, n_mask)
        add_edge(n_mask, n_anom)
        add_edge(n_anom, n_agg)

        run = jpost(c, f'/api/v1/pipelines/{pid}/run', {}, headers=h).get_json()
        print(f"\nRun status: {run['status']}  ({run['duration_ms']} ms)\n")

        res = run['node_results']
        print(f"[Source]   {res[n_src]['rows_output']} lignes — qualité {res[n_src]['quality']['score']}%")
        masked = res[n_mask]['extra']['masked_columns']
        print(f"[Masquage] colonnes anonymisées: {[m['column'] for m in masked]}")
        print(f"           ex: {res[n_mask]['output_preview'][0].get('client_name')} / "
              f"{res[n_mask]['output_preview'][0].get('account_number')}")
        print(f"[Anomalies] {res[n_anom]['extra']['anomalies']} transactions suspectes détectées")
        print(f"[Agrégation] {res[n_agg]['output_preview']}")

        assert run['status'] == 'success'
        assert res[n_anom]['extra']['anomalies'] >= 4
        assert masked, "le masquage doit anonymiser des colonnes"
        print("\n✅ SMOKE OK — le moteur transforme de VRAIES données de bout en bout")


if __name__ == '__main__':
    main()
