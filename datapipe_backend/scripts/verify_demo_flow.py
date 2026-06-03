"""Verify the FRONTEND demo flow against a running backend (localhost:5000).

Mimics exactly what the Next.js client does, using the compat endpoints:
login -> orgs -> workspaces -> pipelines -> get graph -> execute ->
node preview -> AI generate/sql -> chat. Proves the integration contract.

Run (backend must be up):  python scripts/verify_demo_flow.py
"""
import json
import urllib.request

BASE = 'http://localhost:5000/api/v1'


def call(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read())


def main():
    ok = True

    _, login = call('POST', '/auth/login',
                    body={'email': 'demo@bank.cm', 'password': 'Hackaton2026!'})
    token = login['access_token']
    print(f"✓ login            -> token ok, user={login['user']['name']}")

    _, orgs = call('GET', '/orgs', token)
    org_id = orgs['orgs'][0]['id']
    _, ws = call('GET', f'/orgs/{org_id}/workspaces', token)
    ws_id = ws['workspaces'][0]['id']
    print(f"✓ orgs/workspaces  -> {orgs['orgs'][0]['name']} / {ws['workspaces'][0]['name']}")

    _, pipes = call('GET', f'/pipelines?workspace_id={ws_id}', token)
    pid = pipes['data'][0]['id']
    print(f"✓ pipelines (list) -> {pipes['data'][0]['name']}")

    _, pipe = call('GET', f'/pipelines/{pid}', token)
    nodes = pipe['nodes']
    assert all('data' in n and 'config' in n['data'] for n in nodes), "node shape adapter"
    print(f"✓ pipeline (graph) -> {len(nodes)} nœuds (forme React Flow ok), {len(pipe['edges'])} liens")

    _, run = call('POST', f'/pipelines/{pid}/execute', token, body={})
    assert run['status'] == 'success', run
    print(f"✓ execute (sync)   -> status={run['status']} en {run['duration_ms']}ms")

    # Inspect each node's real result
    nr = run['node_results']
    for n in nodes:
        r = nr.get(n['id'], {})
        line = f"    • {n['label']:<22} {r.get('rows_output', '?')} lignes"
        extra = r.get('extra', {})
        if extra.get('masked_columns'):
            line += f"  🛡️ masqué: {[m['column'] for m in extra['masked_columns']]}"
        if 'anomalies' in extra:
            line += f"  🚨 {extra['anomalies']} anomalies"
        if r.get('quality'):
            line += f"  qualité={r['quality']['score']}%"
        print(line)

    # Node preview (DataPreview shape: columns + rows[][])
    src = nodes[0]['id']
    _, prev = call('GET', f"/runs/{run['run_id']}/nodes/{src}/preview", token)
    assert 'columns' in prev and 'rows' in prev
    print(f"✓ node preview     -> {len(prev['columns'])} colonnes, {len(prev['rows'])} lignes (grille)")

    # AI: generate SQL (agent fallback works without API key)
    _, sql = call('POST', '/ai/generate/sql', token,
                  body={'prompt': 'total des montants par type',
                        'schema': [{'name': 'amount'}, {'name': 'transaction_type'}]})
    print(f"✓ ai/generate/sql  -> {sql['sql'][:60]}...")

    # AI: chat (messages[] shape)
    _, chat = call('POST', '/ai/chat', token,
                   body={'messages': [{'role': 'user', 'content': 'Comment masquer un IBAN ?'}]})
    assert chat['message']['role'] == 'assistant'
    print(f"✓ ai/chat          -> réponse assistant ({len(chat['message']['content'])} car.)")

    print("\n✅ PARCOURS DÉMO COMPLET — front & back parlent le même langage, données réelles")
    return ok


if __name__ == '__main__':
    main()
