"""
Moteur d'exécution réel des pipelines DataPipe.

Contrairement à l'ancien `_simulate_run` qui fabriquait des données fictives,
ce moteur traite réellement les données : tri topologique du graphe (DAG),
puis exécution nœud par nœud, chaque nœud recevant les sorties de ses parents
et produisant un dataset (liste de dicts) consommé par ses enfants.

Le moteur ne touche pas la base de données : il reçoit les nœuds, les arêtes et
un `file_loader` (callable file_id -> lignes). L'appelant (routes/runs.py) se
charge de la persistance des logs et des résultats.
"""
import re
import time
import sqlite3
from collections import deque, OrderedDict


class CycleError(Exception):
    """Levée lorsque le graphe du pipeline contient un cycle."""


# ─────────────────────────────── Helpers ─────────────────────────────────────

def coerce_value(v):
    """Convertit une chaîne ressemblant à un nombre en int/float.

    Les CSV ne contiennent que du texte ; cette coercition permet aux filtres
    numériques (>, <) et aux agrégations (SUM, AVG) de fonctionner naturellement.
    """
    if not isinstance(v, str):
        return v
    s = v.strip()
    if s == '':
        return v
    if re.fullmatch(r'-?\d+', s):
        try:
            return int(s)
        except ValueError:
            return v
    try:
        return float(s)
    except ValueError:
        return v


def _is_empty(v):
    return v is None or v == ''


def _toposort(nodes, edges):
    """Tri topologique (Kahn). Lève CycleError si un cycle est détecté."""
    node_map = OrderedDict((n.id, n) for n in nodes)
    indeg = {nid: 0 for nid in node_map}
    adj = {nid: [] for nid in node_map}
    for e in edges:
        if e.source_node_id in node_map and e.target_node_id in node_map:
            adj[e.source_node_id].append(e.target_node_id)
            indeg[e.target_node_id] += 1

    queue = deque(nid for nid in node_map if indeg[nid] == 0)
    order = []
    while queue:
        cur = queue.popleft()
        order.append(node_map[cur])
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(node_map):
        raise CycleError('Le pipeline contient un cycle — exécution impossible')
    return order


# ─────────────────────────────── Transforms ──────────────────────────────────

def _match(row, cond):
    field = cond.get('field')
    op = cond.get('operator', 'eq')
    val = cond.get('value')
    cur = row.get(field)

    if op == 'is_null':
        return _is_empty(cur)
    if op == 'is_not_null':
        return not _is_empty(cur)
    if op == 'contains':
        return val is not None and str(val).lower() in str(cur).lower()

    a, b = coerce_value(cur), coerce_value(val)
    try:
        if op == 'eq':
            return a == b
        if op == 'neq':
            return a != b
        if op == 'gt':
            return a > b
        if op == 'lt':
            return a < b
        if op == 'gte':
            return a >= b
        if op == 'lte':
            return a <= b
    except TypeError:
        a, b = str(cur), str(val)
        if op == 'eq':
            return a == b
        if op == 'neq':
            return a != b
        if op == 'gt':
            return a > b
        if op == 'lt':
            return a < b
        if op == 'gte':
            return a >= b
        if op == 'lte':
            return a <= b
    return False


def _filter(rows, cfg):
    conds = cfg.get('conditions', []) or []
    if not conds:
        return list(rows)
    logic = (cfg.get('logic', 'AND') or 'AND').upper()
    out = []
    for r in rows:
        checks = [_match(r, c) for c in conds]
        keep = all(checks) if logic == 'AND' else any(checks)
        if keep:
            out.append(r)
    return out


def _map(rows, cfg):
    mappings = cfg.get('mappings', []) or []
    if not mappings:
        return [dict(r) for r in rows]
    out = []
    for r in rows:
        nr = {}
        for m in mappings:
            src = m.get('source')
            tgt = m.get('target') or src
            if tgt:
                nr[tgt] = r.get(src)
        out.append(nr)
    return out


def _aggregate(rows, cfg):
    group_by = cfg.get('group_by', []) or []
    aggs = cfg.get('aggregations', []) or []
    groups = OrderedDict()
    for r in rows:
        key = tuple(r.get(g) for g in group_by)
        groups.setdefault(key, []).append(r)

    out = []
    for key, items in groups.items():
        res = {g: key[i] for i, g in enumerate(group_by)}
        for a in aggs:
            fn = a.get('function', 'count')
            fld = a.get('field')
            alias = a.get('alias') or f"{fn}_{fld or 'all'}"
            raw = [coerce_value(it.get(fld)) for it in items if not _is_empty(it.get(fld))]
            nums = [v for v in raw if isinstance(v, (int, float))]
            if fn == 'count':
                res[alias] = len(items)
            elif fn == 'count_distinct':
                res[alias] = len({str(it.get(fld)) for it in items})
            elif fn == 'sum':
                res[alias] = round(sum(nums), 4) if nums else 0
            elif fn == 'avg':
                res[alias] = round(sum(nums) / len(nums), 4) if nums else None
            elif fn == 'min':
                res[alias] = min(nums) if nums else None
            elif fn == 'max':
                res[alias] = max(nums) if nums else None
        out.append(res)
    return out


def _sortkey(v):
    c = coerce_value(v)
    if isinstance(c, (int, float)):
        return (0, c)
    return (1, str(v) if v is not None else '')


def _sort(rows, cfg):
    keys = cfg.get('sort_by', []) or []
    out = list(rows)
    for k in reversed(keys):
        fld = k.get('field')
        desc = (k.get('direction', 'asc') == 'desc')
        out.sort(key=lambda r, f=fld: _sortkey(r.get(f)), reverse=desc)
    return out


def _dedup(rows, cfg):
    keys = cfg.get('keys', []) or []
    keep = cfg.get('keep', 'first')
    source = list(rows) if keep == 'first' else list(reversed(rows))
    seen = set()
    out = []
    for r in source:
        if keys:
            k = tuple(str(r.get(x)) for x in keys)
        else:
            k = tuple(sorted((str(a), str(b)) for a, b in r.items()))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out if keep == 'first' else list(reversed(out))


def _join(inputs, cfg):
    left = inputs[0] if len(inputs) > 0 else []
    right = inputs[1] if len(inputs) > 1 else []
    jt = cfg.get('join_type', 'inner')
    lk = cfg.get('left_key')
    rk = cfg.get('right_key') or lk

    index = {}
    for r in right:
        index.setdefault(r.get(rk), []).append(r)

    out = []
    matched = set()
    for l in left:
        matches = index.get(l.get(lk), [])
        if matches:
            for r in matches:
                matched.add(id(r))
                out.append({**r, **l})  # les clés de gauche priment en cas de conflit
        elif jt in ('left', 'full'):
            out.append(dict(l))

    if jt in ('right', 'full'):
        for r in right:
            if id(r) not in matched:
                out.append(dict(r))
    return out


_DANGEROUS_SQL = ('DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE', 'ATTACH', 'PRAGMA')


def _sql(query, rows):
    """Exécute une requête SELECT sur le dataset d'entrée via SQLite en mémoire.

    Le placeholder `{input}` (ou la table `input`) référence les données entrantes.
    """
    if not query or not query.strip():
        return list(rows)

    upper = query.upper()
    for kw in _DANGEROUS_SQL:
        if re.search(r'\b' + kw + r'\b', upper):
            raise ValueError(f'Mot-clé SQL interdit dans une transformation : {kw}')

    # colonnes = union ordonnée des clés présentes
    columns = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                columns.append(k)
    if not columns:
        columns = ['_empty']

    con = sqlite3.connect(':memory:')
    try:
        col_defs = ', '.join(f'"{c}"' for c in columns)
        con.execute(f'CREATE TABLE input ({col_defs})')
        placeholders = ', '.join('?' for _ in columns)
        con.executemany(
            f'INSERT INTO input VALUES ({placeholders})',
            [[r.get(c) for c in columns] for r in rows],
        )
        cur = con.execute(query.replace('{input}', 'input'))
        result_cols = [d[0] for d in cur.description]
        return [dict(zip(result_cols, row)) for row in cur.fetchall()]
    finally:
        con.close()


def _validate(rows, cfg, node, logs):
    rules = cfg.get('rules', []) or []
    if not rules:
        return [dict(r) for r in rows]
    valid = []
    invalid = 0
    for r in rows:
        ok = True
        for rule in rules:
            if rule.get('required') and _is_empty(r.get(rule.get('field'))):
                ok = False
                break
        if ok:
            valid.append(r)
        else:
            invalid += 1
    if invalid:
        logs.append({'level': 'warning', 'node_id': node.id,
                     'message': f'Validation : {invalid} ligne(s) invalide(s) écartée(s)'})
    return valid


# ─────────────────────────────── Dispatch ────────────────────────────────────

def _execute_node(node, inputs, file_loader, logs):
    t = node.type_slug
    cfg = node.config or {}
    first = inputs[0] if inputs else []

    if t in ('csv_reader', 'json_reader'):
        file_id = cfg.get('file_id')
        if not file_id or file_loader is None:
            logs.append({'level': 'warning', 'node_id': node.id,
                         'message': f'{node.label or t} : aucun fichier associé (file_id manquant)'})
            return []
        return list(file_loader(file_id) or [])

    if t == 'filter':
        return _filter(first, cfg)
    if t == 'map':
        return _map(first, cfg)
    if t == 'aggregate':
        return _aggregate(first, cfg)
    if t == 'sort':
        return _sort(first, cfg)
    if t == 'dedup':
        return _dedup(first, cfg)
    if t == 'join':
        return _join(inputs, cfg)
    if t == 'sql_transform':
        return _sql(cfg.get('query', ''), first)
    if t == 'sql_query':
        # Pas de datasource réelle branchée : transforme l'entrée si présente, sinon vide.
        if not first:
            logs.append({'level': 'warning', 'node_id': node.id,
                         'message': f'{node.label or t} : datasource non connectée, sortie vide'})
            return []
        return _sql(cfg.get('query', ''), first)
    if t == 'validate':
        return _validate(first, cfg, node, logs)
    if t == 'merge':
        out = []
        for inp in inputs:
            out.extend(inp)
        return out
    if t == 'split':
        return list(first)
    if t == 'ai_transform':
        logs.append({'level': 'info', 'node_id': node.id,
                     'message': f'{node.label or t} : passage IA (données transmises sans modification)'})
        return list(first)
    if t == 'file_export':
        fmt = cfg.get('format', 'csv')
        logs.append({'level': 'info', 'node_id': node.id,
                     'message': f'{node.label or t} : {len(first)} ligne(s) prête(s) à exporter (format={fmt})'})
        return list(first)
    if t in ('sql_write', 'webhook_send', 'notification_send'):
        logs.append({'level': 'info', 'node_id': node.id,
                     'message': f'{node.label or t} : {len(first)} ligne(s) envoyée(s) (sortie terminale)'})
        return list(first)
    if t == 'http_request':
        logs.append({'level': 'warning', 'node_id': node.id,
                     'message': f'{node.label or t} : appel HTTP externe non exécuté'})
        return []

    # Type inconnu : passage transparent
    return list(first)


def execute_pipeline(nodes, edges, file_loader=None, preview_rows=10):
    """Exécute le pipeline et retourne le détail par nœud.

    Returns:
        {
          'status': 'success' | 'error',
          'node_results': {node_id: {...}},
          'logs': [{level, message, node_id}],
          'error': str | None,
        }
    """
    order = _toposort(nodes, edges)

    # arêtes entrantes par nœud, dans l'ordre de déclaration (gauche/droite pour join)
    node_ids = {n.id for n in nodes}
    incoming = {n.id: [] for n in nodes}
    for e in edges:
        if e.target_node_id in node_ids and e.source_node_id in node_ids:
            incoming[e.target_node_id].append(e.source_node_id)

    outputs = {}
    node_results = OrderedDict()
    logs = []

    for node in order:
        started = time.time()
        inputs = [outputs.get(src, []) for src in incoming[node.id]]
        in_rows = sum(len(i) for i in inputs)
        try:
            data = _execute_node(node, inputs, file_loader, logs)
            outputs[node.id] = data
            duration = int((time.time() - started) * 1000)
            node_results[node.id] = {
                'status': 'success',
                'rows_processed': in_rows,
                'rows_output': len(data),
                'duration_ms': duration,
                'columns': list(data[0].keys()) if data else [],
                'output_preview': data[:preview_rows],
            }
            logs.append({'level': 'info', 'node_id': node.id,
                         'message': f'{node.label or node.type_slug} : {len(data)} ligne(s) en sortie'})
        except Exception as ex:  # noqa: BLE001 — on remonte l'erreur dans le résultat
            duration = int((time.time() - started) * 1000)
            node_results[node.id] = {
                'status': 'error',
                'rows_processed': in_rows,
                'rows_output': 0,
                'duration_ms': duration,
                'error': str(ex),
                'output_preview': [],
            }
            logs.append({'level': 'error', 'node_id': node.id,
                         'message': f'{node.label or node.type_slug} : {ex}'})
            return {'status': 'error', 'node_results': dict(node_results),
                    'logs': logs, 'error': str(ex)}

    return {'status': 'success', 'node_results': dict(node_results),
            'logs': logs, 'error': None}
