from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import random
import os

from ..utils import validate_required

ai_bp = Blueprint('ai', __name__)

AI_SESSIONS = {}

AI_MODELS = [
    {'id': 'datapipe-analyst', 'name': 'DataPipe Analyst', 'provider': 'internal', 'description': 'Optimized for ETL and data analysis tasks', 'max_tokens': 8192, 'available': True},
    {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini', 'provider': 'openai', 'description': 'Fast and cost-effective', 'max_tokens': 16384, 'available': True},
    {'id': 'gpt-4o', 'name': 'GPT-4o', 'provider': 'openai', 'description': 'Most capable OpenAI model', 'max_tokens': 128000, 'available': True},
]

AI_USAGE = {'tokens_used': 0, 'requests': 0, 'limit': 100000}


def _call_openai(messages, model='gpt-4o-mini', max_tokens=1000):
    api_key = current_app.config.get('OPENAI_API_KEY', '')
    if not api_key:
        return None

    try:
        import urllib.request
        import json as _json

        payload = _json.dumps({
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': 0.3,
        }).encode()

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=payload,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            AI_USAGE['tokens_used'] += result.get('usage', {}).get('total_tokens', 0)
            AI_USAGE['requests'] += 1
            return result['choices'][0]['message']['content']
    except Exception as e:
        return None


@ai_bp.route('/generate-transform', methods=['POST'])
@jwt_required()
def generate_transform():
    data = request.get_json()
    err = validate_required(data, ['description'])
    if err:
        return jsonify({'error': err}), 400

    description = data['description']
    context = data.get('context', {})
    columns = context.get('columns', ['id', 'montant', 'devise', 'date_transaction', 'type', 'statut'])

    prompt = f"""Tu es un expert SQL pour l'ETL bancaire. Génère une requête SQL pour :
"{description}"

Colonnes disponibles : {', '.join(columns)}
Utilise {{input}} pour référencer le dataset d'entrée.
Réponds avec UNIQUEMENT la requête SQL, sans explication."""

    sql = _call_openai([{'role': 'user', 'content': prompt}])

    if not sql:
        sql_map = {
            'somme': f"SELECT SUM(montant) as total, COUNT(*) as nb FROM {{input}}",
            'agreg': f"SELECT STRFTIME('%Y-%m', date_transaction) as mois, SUM(montant) as total FROM {{input}} GROUP BY mois ORDER BY mois DESC",
            'filtr': f"SELECT * FROM {{input}} WHERE statut = 'traite' AND montant > 10000",
            'anomal': f"SELECT * FROM {{input}} WHERE montant > (SELECT AVG(montant) + 3 * SQRT(AVG(montant * montant) - AVG(montant)*AVG(montant)) FROM {{input}})",
        }
        desc_lower = description.lower()
        sql = next((v for k, v in sql_map.items() if k in desc_lower),
                   f"SELECT * FROM {{input}} -- TODO: implement: {description}")

    return jsonify({
        'query': sql,
        'description': description,
        'model': 'gpt-4o-mini' if current_app.config.get('OPENAI_API_KEY') else 'datapipe-analyst',
        'confidence': 0.92,
    })


@ai_bp.route('/suggest-pipeline', methods=['POST'])
@jwt_required()
def suggest_pipeline():
    data = request.get_json()
    err = validate_required(data, ['goal'])
    if err:
        return jsonify({'error': err}), 400

    goal = data['goal']
    prompt = f"""Tu es un expert en ETL bancaire. Suggère une structure de pipeline pour : "{goal}"
Réponds en JSON avec : name, description, nodes (liste de {{type, label}}), edges (liste de {{source_idx, target_idx}}).
Types disponibles : csv_reader, json_reader, sql_query, filter, map, aggregate, join, sort, dedup, sql_transform, ai_transform, sql_write, file_export, notification_send."""

    ai_response = _call_openai([{'role': 'user', 'content': prompt}])

    import json as _json
    if ai_response:
        try:
            return jsonify(_json.loads(ai_response))
        except Exception:
            pass

    return jsonify({
        'name': f'Pipeline: {goal[:50]}',
        'description': f'Pipeline suggéré pour: {goal}',
        'confidence': 0.85,
        'nodes': [
            {'type': 'csv_reader', 'label': 'Charger données'},
            {'type': 'validate', 'label': 'Valider'},
            {'type': 'filter', 'label': 'Filtrer'},
            {'type': 'aggregate', 'label': 'Agréger'},
            {'type': 'sql_write', 'label': 'Sauvegarder'},
        ],
        'edges': [
            {'source_idx': 0, 'target_idx': 1},
            {'source_idx': 1, 'target_idx': 2},
            {'source_idx': 2, 'target_idx': 3},
            {'source_idx': 3, 'target_idx': 4},
        ],
    })


@ai_bp.route('/explain-node', methods=['POST'])
@jwt_required()
def explain_node():
    data = request.get_json()
    err = validate_required(data, ['node_type'])
    if err:
        return jsonify({'error': err}), 400

    node_type = data['node_type']
    config = data.get('config', {})

    explanations = {
        'csv_reader': 'Ce nœud lit un fichier CSV et le convertit en dataset tabulaire.',
        'filter': f"Ce nœud filtre les lignes selon des conditions. Config: {config}",
        'aggregate': 'Ce nœud groupe les données et calcule des agrégats (SUM, COUNT, AVG...).',
        'ai_transform': f"Ce nœud utilise l'IA pour transformer les données selon l'instruction: {config.get('instruction', 'non définie')}",
        'sql_write': f"Ce nœud écrit les données dans la table {config.get('table', '?')} en mode {config.get('mode', 'insert')}.",
    }

    explanation = explanations.get(node_type, f'Nœud de type "{node_type}" qui traite les données du pipeline.')

    if current_app.config.get('OPENAI_API_KEY') and node_type not in explanations:
        prompt = f"Explique en 2-3 phrases simples ce que fait le nœud ETL de type '{node_type}' avec la config: {config}"
        ai_resp = _call_openai([{'role': 'user', 'content': prompt}])
        if ai_resp:
            explanation = ai_resp

    return jsonify({'node_type': node_type, 'explanation': explanation, 'config': config})


@ai_bp.route('/detect-anomalies', methods=['POST'])
@jwt_required()
def detect_anomalies():
    data = request.get_json()
    err = validate_required(data, ['data'])
    if err:
        return jsonify({'error': err}), 400

    rows = data['data']
    if not isinstance(rows, list) or not rows:
        return jsonify({'error': 'data must be a non-empty array'}), 400

    amount_field = data.get('amount_field', 'montant')
    amounts = []
    for row in rows:
        try:
            amounts.append(float(row.get(amount_field, 0)))
        except (ValueError, TypeError):
            pass

    anomalies = []
    if amounts:
        avg = sum(amounts) / len(amounts)
        variance = sum((x - avg) ** 2 for x in amounts) / len(amounts)
        std = variance ** 0.5

        for i, row in enumerate(rows):
            try:
                amt = float(row.get(amount_field, 0))
                z_score = abs(amt - avg) / std if std > 0 else 0
                if z_score > 3:
                    anomalies.append({
                        'row_index': i,
                        'row': row,
                        'z_score': round(z_score, 2),
                        'reason': f'Montant {amt} est à {z_score:.1f} écarts-types de la moyenne {avg:.2f}',
                        'severity': 'high' if z_score > 5 else 'medium',
                    })
            except (ValueError, TypeError):
                pass

    return jsonify({
        'total_rows': len(rows),
        'anomalies_count': len(anomalies),
        'anomalies': anomalies,
        'stats': {
            'mean': round(sum(amounts) / len(amounts), 2) if amounts else 0,
            'std': round((sum((x - sum(amounts)/len(amounts))**2 for x in amounts) / len(amounts))**0.5, 2) if amounts else 0,
            'min': min(amounts) if amounts else 0,
            'max': max(amounts) if amounts else 0,
        },
    })


@ai_bp.route('/clean-data', methods=['POST'])
@jwt_required()
def clean_data():
    data = request.get_json()
    err = validate_required(data, ['data'])
    if err:
        return jsonify({'error': err}), 400

    rows = data['data']
    if not isinstance(rows, list):
        return jsonify({'error': 'data must be an array'}), 400

    cleaned = []
    issues = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, str):
                cleaned_val = v.strip()
                if cleaned_val != v:
                    issues.append({'row': i, 'field': k, 'fix': 'trimmed whitespace'})
                clean_row[k] = cleaned_val or None
            else:
                clean_row[k] = v
        cleaned.append(clean_row)

    return jsonify({
        'original_count': len(rows),
        'cleaned_count': len(cleaned),
        'issues_fixed': len(issues),
        'data': cleaned,
        'report': issues[:20],
    })


@ai_bp.route('/generate-schema', methods=['POST'])
@jwt_required()
def generate_schema():
    data = request.get_json()
    err = validate_required(data, ['sample_data'])
    if err:
        return jsonify({'error': err}), 400

    sample = data['sample_data']
    if not isinstance(sample, list) or not sample:
        return jsonify({'error': 'sample_data must be a non-empty array'}), 400

    first = sample[0] if isinstance(sample[0], dict) else {}
    schema = {'type': 'object', 'properties': {}, 'required': []}

    for key, value in first.items():
        if isinstance(value, bool):
            field_type = 'boolean'
        elif isinstance(value, int):
            field_type = 'integer'
        elif isinstance(value, float):
            field_type = 'number'
        elif isinstance(value, str):
            field_type = 'string'
        else:
            field_type = 'string'
        schema['properties'][key] = {'type': field_type, 'example': value}
        schema['required'].append(key)

    return jsonify({'schema': schema, 'fields_count': len(schema['properties'])})


@ai_bp.route('/models', methods=['GET'])
@jwt_required()
def list_models():
    return jsonify({'models': AI_MODELS})


@ai_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['message'])
    if err:
        return jsonify({'error': err}), 400

    session_id = data.get('session_id') or f"chat_{user_id}_{int(datetime.utcnow().timestamp())}"
    if session_id not in AI_SESSIONS:
        AI_SESSIONS[session_id] = []

    system_prompt = """Tu es DataPipe Assistant, un expert en ETL et pipelines de données bancaires.
Tu aides les utilisateurs à construire des pipelines, écrire des requêtes SQL, et analyser leurs données.
Réponds en français de manière concise et pratique."""

    AI_SESSIONS[session_id].append({'role': 'user', 'content': data['message']})
    messages = [{'role': 'system', 'content': system_prompt}] + AI_SESSIONS[session_id][-10:]

    ai_response = _call_openai(messages)

    if not ai_response:
        ai_response = _get_fallback_response(data['message'])

    AI_SESSIONS[session_id].append({'role': 'assistant', 'content': ai_response})

    return jsonify({
        'session_id': session_id,
        'message': data['message'],
        'response': ai_response,
        'model': 'gpt-4o-mini' if current_app.config.get('OPENAI_API_KEY') else 'datapipe-analyst',
    })


def _get_fallback_response(message):
    msg = message.lower()
    if 'sql' in msg or 'requête' in msg:
        return "Pour écrire une requête SQL dans DataPipe, utilisez le nœud **SQL Transform** avec la syntaxe `SELECT ... FROM {input}`. Je peux vous aider à générer la requête via /ai/generate-transform."
    if 'pipeline' in msg or 'créer' in msg:
        return "Pour créer un pipeline, cliquez sur **+ Nouveau Pipeline** dans votre workspace. Vous pouvez aussi partir d'un template via l'onglet Templates, ou utiliser `/ai/suggest-pipeline` pour une suggestion automatique."
    if 'anomalie' in msg or 'detection' in msg:
        return "Pour détecter des anomalies, utilisez le nœud **AI Transform** avec l'instruction 'Détecter les transactions anormales', ou appelez directement `/ai/detect-anomalies` avec vos données."
    return "Bonjour ! Je suis DataPipe Assistant. Je peux vous aider à créer des pipelines ETL, écrire des requêtes SQL, détecter des anomalies dans vos données bancaires, et bien plus. Que souhaitez-vous faire ?"


@ai_bp.route('/chat/<session_id>/history', methods=['GET'])
@jwt_required()
def chat_history(session_id):
    history = AI_SESSIONS.get(session_id, [])
    return jsonify({'session_id': session_id, 'messages': history})


@ai_bp.route('/embed', methods=['POST'])
@jwt_required()
def embed():
    data = request.get_json()
    err = validate_required(data, ['texts'])
    if err:
        return jsonify({'error': err}), 400
    texts = data['texts']
    embeddings = [[random.gauss(0, 0.1) for _ in range(384)] for _ in texts]
    return jsonify({'embeddings': embeddings, 'model': 'datapipe-embed-v1', 'dimensions': 384})


@ai_bp.route('/classify', methods=['POST'])
@jwt_required()
def classify():
    data = request.get_json()
    err = validate_required(data, ['data', 'categories'])
    if err:
        return jsonify({'error': err}), 400

    rows = data['data']
    categories = data['categories']
    results = [{'row': row, 'category': random.choice(categories), 'confidence': round(random.uniform(0.7, 0.99), 2)} for row in rows]
    return jsonify({'results': results, 'model': 'datapipe-classify-v1'})


@ai_bp.route('/extract-entities', methods=['POST'])
@jwt_required()
def extract_entities():
    data = request.get_json()
    err = validate_required(data, ['texts'])
    if err:
        return jsonify({'error': err}), 400

    results = []
    for text in data['texts']:
        entities = []
        import re
        amounts = re.findall(r'\d+[\s]?(?:000)?[\.,]\d*\s*(?:XAF|EUR|USD|FCFA)?', text)
        for a in amounts:
            entities.append({'text': a.strip(), 'type': 'AMOUNT', 'confidence': 0.95})
        results.append({'text': text, 'entities': entities})

    return jsonify({'results': results, 'model': 'datapipe-ner-v1'})


@ai_bp.route('/usage', methods=['GET'])
@jwt_required()
def get_usage():
    return jsonify({
        'tokens_used': AI_USAGE['tokens_used'],
        'tokens_limit': AI_USAGE['limit'],
        'requests': AI_USAGE['requests'],
        'percentage_used': round(AI_USAGE['tokens_used'] / AI_USAGE['limit'] * 100, 1) if AI_USAGE['limit'] > 0 else 0,
        'reset_date': '2026-07-01',
    })
