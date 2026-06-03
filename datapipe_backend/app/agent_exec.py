"""
Server-side execution of agent actions.

The web chat confirms then calls REST endpoints; the Telegram bot has no browser,
so it executes here directly against the DB, then publishes a real-time event so
any open web editor redraws live. One vocabulary of actions, two front-ends.
"""
from datetime import datetime

from .extensions import db
from .models import (User, OrgMember, Workspace, Pipeline, Node, Edge)
from . import realtime


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
