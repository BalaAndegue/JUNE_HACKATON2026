"""
Server-side execution of agent actions.

The web chat confirms then calls REST endpoints; the Telegram bot has no browser,
so it executes here directly against the DB, then publishes a real-time event so
any open web editor redraws live. One vocabulary of actions, two front-ends.
"""
import io
import os

from datetime import datetime

from .extensions import db
from .models import (User, OrgMember, Workspace, Pipeline, Node, Edge, File)
from . import realtime


def ingest_file(user_id, filename, content):
    """Enregistre un fichier (bytes) dans le workspace de l'utilisateur + parse le schéma.
    Renvoie l'objet File (ou None si pas de workspace)."""
    from flask import current_app
    import pandas as pd
    ws_id = _user_workspace_id(user_id)
    if not ws_id:
        return None
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], ws_id)
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, filename)
    with open(path, 'wb') as fp:
        fp.write(content)

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'csv'
    cols, rows, preview = [], 0, []
    try:
        if ext == 'json':
            df = pd.read_json(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content), on_bad_lines='skip')
        cols = [str(c) for c in df.columns]
        rows = len(df)
        preview = df.head(5).to_dict(orient='records')
    except Exception:
        pass

    f = File(workspace_id=ws_id, name=filename, original_name=filename,
             size=len(content), mime_type='text/csv' if ext != 'json' else 'application/json',
             path=path, rows_count=rows, columns_count=len(cols))
    f.columns = cols
    f.preview = preview
    db.session.add(f)
    db.session.commit()
    return f


def build_audit_report(run, pipeline):
    """Rapport de conformité bancaire d'un run (partagé par l'API et le bot Telegram)."""
    results = run.node_results
    node_by_id = {n.id: n for n in pipeline.nodes}
    steps, masked_columns, quality_scores = [], set(), []
    total_anomalies = 0
    for nid, res in results.items():
        node = node_by_id.get(nid)
        extra = res.get('extra') or {}
        masked = extra.get('masked_columns') or []
        for m in masked:
            masked_columns.add(m.get('column'))
        if isinstance(extra.get('anomalies'), int):
            total_anomalies += extra['anomalies']
        q = (res.get('quality') or {}).get('score')
        if q is not None:
            quality_scores.append(q)
        steps.append({
            'node': node.label if node else nid,
            'type': node.type_slug if node else None,
            'status': res.get('status'),
            'rows_in': res.get('rows_processed'), 'rows_out': res.get('rows_output'),
            'masked_columns': [m.get('column') for m in masked],
            'anomalies_detected': extra.get('anomalies'),
            'quality_score': q,
        })
    return {
        'report_type': 'compliance_audit',
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'pipeline': {'id': pipeline.id, 'name': pipeline.name},
        'run': {'id': run.id, 'status': run.status, 'duration_ms': run.duration_ms},
        'compliance': {
            'pii_anonymised': len(masked_columns) > 0,
            'anonymised_columns': sorted(c for c in masked_columns if c),
            'anomalies_detected': total_anomalies,
            'final_quality_score': quality_scores[-1] if quality_scores else None,
        },
        'steps': steps,
    }


def _user_workspace_id(user_id):
    member = OrgMember.query.filter_by(user_id=user_id).first()
    if not member:
        return None
    ws = Workspace.query.filter_by(org_id=member.org_id).first()
    return ws.id if ws else None


def _find_node(pipeline, ref):
    ref = str(ref or '').lower().strip()
    if not ref:
        return None
    for n in pipeline.nodes:
        if n.id == ref:
            return n
    for n in pipeline.nodes:
        if ref in (n.label or '').lower():
            return n
    return None


def run_action(user_id, action, params, pipeline_id=None):
    """Execute one agent action. Returns {ok, message, pipeline_id, data?}."""
    params = params or {}
    pipeline = Pipeline.query.get(pipeline_id) if pipeline_id else None

    if action == 'create_pipeline':
        ws_id = _user_workspace_id(user_id)
        if not ws_id:
            return {'ok': False, 'message': "Aucun workspace pour cet utilisateur."}
        p = Pipeline(workspace_id=ws_id, name=params.get('name') or 'Nouveau pipeline')
        db.session.add(p)
        db.session.commit()
        return {'ok': True, 'pipeline_id': p.id,
                'message': f"Pipeline « {p.name} » créé."}

    if pipeline is None:
        return {'ok': False, 'message': "Aucun pipeline cible."}

    if action == 'add_node':
        node = Node(pipeline_id=pipeline.id, type_slug=params.get('node_type', 'filter'),
                    label=params.get('label') or params.get('node_type', 'Nœud'),
                    position_x=params.get('x', 320), position_y=params.get('y', 320))
        node.config = params.get('config') or {}
        db.session.add(node)
        db.session.commit()
        realtime.publish(pipeline.id, 'pipeline.updated', {'added_node': node.id})
        return {'ok': True, 'pipeline_id': pipeline.id,
                'message': f"Nœud « {node.label} » ajouté."}

    if action == 'connect_nodes':
        src = _find_node(pipeline, params.get('source'))
        tgt = _find_node(pipeline, params.get('target'))
        if not src or not tgt:
            return {'ok': False, 'message': "Nœud source ou cible introuvable."}
        db.session.add(Edge(pipeline_id=pipeline.id, source_node_id=src.id, target_node_id=tgt.id))
        db.session.commit()
        realtime.publish(pipeline.id, 'pipeline.updated', {'connected': [src.id, tgt.id]})
        return {'ok': True, 'pipeline_id': pipeline.id,
                'message': f"« {src.label} » → « {tgt.label} » connectés."}

    if action == 'delete_node':
        n = _find_node(pipeline, params.get('node'))
        if not n:
            return {'ok': False, 'message': "Nœud introuvable."}
        Edge.query.filter(
            (Edge.source_node_id == n.id) | (Edge.target_node_id == n.id),
            Edge.pipeline_id == pipeline.id).delete(synchronize_session=False)
        label = n.label
        db.session.delete(n)
        db.session.commit()
        realtime.publish(pipeline.id, 'pipeline.updated', {'deleted_node': True})
        return {'ok': True, 'pipeline_id': pipeline.id, 'message': f"Nœud « {label} » supprimé."}

    if action == 'configure_node':
        n = _find_node(pipeline, params.get('node'))
        if not n:
            return {'ok': False, 'message': "Nœud introuvable."}
        cfg = n.config
        cfg.update(params.get('config') or {})
        n.config = cfg
        db.session.commit()
        realtime.publish(pipeline.id, 'pipeline.updated', {'configured_node': n.id})
        return {'ok': True, 'pipeline_id': pipeline.id, 'message': f"Nœud « {n.label} » configuré."}

    if action == 'run_pipeline':
        from .routes.runs import _execute
        from .models import Run
        if not pipeline.nodes:
            return {'ok': False, 'message': "Le pipeline n'a aucun nœud."}
        run = Run(pipeline_id=pipeline.id, trigger='telegram', status='pending')
        db.session.add(run)
        db.session.flush()
        _execute(pipeline, run, user_id)
        results = run.node_results
        total = sum((r.get('rows_output') or 0) for r in results.values())
        anomalies = sum((r.get('extra', {}) or {}).get('anomalies', 0)
                        for r in results.values() if isinstance(r.get('extra'), dict))
        realtime.publish(pipeline.id, 'run.finished',
                         {'run_id': run.id, 'status': run.status, 'node_results': results})
        return {'ok': True, 'pipeline_id': pipeline.id, 'run_id': run.id,
                'message': f"Exécution {run.status} : {total} ligne(s)"
                           + (f", 🚨 {anomalies} anomalie(s)" if anomalies else "")}

    if action == 'generate_sql':
        from flask import current_app  # noqa: F401
        from .routes import ai as ai_mod
        sql, expl, _ = ai_mod._agent_sql_and_explanation(params.get('description', ''), [])
        node = Node(pipeline_id=pipeline.id, type_slug='sql_transform', label='Transformation IA',
                    position_x=700, position_y=360)
        node.config = {'query': sql}
        db.session.add(node)
        db.session.commit()
        realtime.publish(pipeline.id, 'pipeline.updated', {'added_node': node.id})
        return {'ok': True, 'pipeline_id': pipeline.id,
                'message': f"Nœud SQL ajouté : {expl}\n{sql}"}

    return {'ok': False, 'message': f"Action « {action} » non exécutable côté serveur."}
