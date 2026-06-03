from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import random

from ..utils import validate_required

transform_bp = Blueprint('transform', __name__)

SQL_HISTORY = []

SQL_FUNCTIONS = [
    {'name': 'SUM', 'category': 'Aggregate', 'description': 'Sum of values', 'syntax': 'SUM(column)'},
    {'name': 'AVG', 'category': 'Aggregate', 'description': 'Average of values', 'syntax': 'AVG(column)'},
    {'name': 'COUNT', 'category': 'Aggregate', 'description': 'Count rows', 'syntax': 'COUNT(*)'},
    {'name': 'MAX', 'category': 'Aggregate', 'description': 'Maximum value', 'syntax': 'MAX(column)'},
    {'name': 'MIN', 'category': 'Aggregate', 'description': 'Minimum value', 'syntax': 'MIN(column)'},
    {'name': 'GROUP BY', 'category': 'Grouping', 'description': 'Group results', 'syntax': 'GROUP BY column'},
    {'name': 'ROUND', 'category': 'Math', 'description': 'Round a number', 'syntax': 'ROUND(value, decimals)'},
    {'name': 'UPPER', 'category': 'String', 'description': 'Convert to uppercase', 'syntax': 'UPPER(column)'},
    {'name': 'LOWER', 'category': 'String', 'description': 'Convert to lowercase', 'syntax': 'LOWER(column)'},
    {'name': 'TRIM', 'category': 'String', 'description': 'Remove whitespace', 'syntax': 'TRIM(column)'},
    {'name': 'CAST', 'category': 'Type', 'description': 'Convert data type', 'syntax': 'CAST(value AS type)'},
    {'name': 'COALESCE', 'category': 'Null', 'description': 'Return first non-null', 'syntax': 'COALESCE(a, b, ...)'},
    {'name': 'DATE_TRUNC', 'category': 'Date', 'description': 'Truncate to period', 'syntax': "DATE_TRUNC('month', column)"},
    {'name': 'EXTRACT', 'category': 'Date', 'description': 'Extract date part', 'syntax': "EXTRACT(YEAR FROM column)"},
    {'name': 'STRFTIME', 'category': 'Date', 'description': 'Format date', 'syntax': "STRFTIME('%Y-%m', column)"},
]

SQL_TEMPLATES = [
    {'id': 'monthly_agg', 'name': 'Agrégation mensuelle', 'description': 'Agréger par mois et catégorie',
     'query': "SELECT STRFTIME('%Y-%m', date_transaction) as mois, type, SUM(montant) as total, COUNT(*) as nb_transactions FROM {input} GROUP BY mois, type ORDER BY mois DESC"},
    {'id': 'top_transactions', 'name': 'Top transactions', 'description': 'Les N plus grosses transactions',
     'query': 'SELECT * FROM {input} ORDER BY montant DESC LIMIT 100'},
    {'id': 'dedup', 'name': 'Dédoublonnage', 'description': 'Supprimer les doublons sur un champ clé',
     'query': 'SELECT * FROM {input} WHERE rowid IN (SELECT MIN(rowid) FROM {input} GROUP BY id)'},
    {'id': 'anomalies', 'name': 'Détection d\'anomalies simples', 'description': 'Transactions hors norme (> 3 écarts types)',
     'query': 'SELECT * FROM {input} WHERE ABS(montant - (SELECT AVG(montant) FROM {input})) > 3 * (SELECT SQRT(AVG((montant - (SELECT AVG(montant) FROM {input})) * (montant - (SELECT AVG(montant) FROM {input})))) FROM {input})'},
    {'id': 'pivot_status', 'name': 'Pivot par statut', 'description': 'Compter par statut',
     'query': "SELECT statut, COUNT(*) as total, SUM(montant) as montant_total FROM {input} GROUP BY statut"},
]


@transform_bp.route('/sql/validate', methods=['POST'])
@jwt_required()
def validate_sql():
    data = request.get_json()
    err = validate_required(data, ['query'])
    if err:
        return jsonify({'error': err}), 400

    query = data['query'].strip().upper()
    is_valid = True
    issues = []

    dangerous = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    for kw in dangerous:
        if kw in query:
            issues.append({'severity': 'error', 'message': f'Keyword {kw} not allowed in transform queries'})
            is_valid = False

    if not any(q in query for q in ['SELECT', 'WITH']):
        issues.append({'severity': 'warning', 'message': 'Query should start with SELECT or WITH'})

    return jsonify({'valid': is_valid, 'issues': issues, 'query': data['query']})


@transform_bp.route('/sql/execute', methods=['POST'])
@jwt_required()
def execute_sql():
    user_id = get_jwt_identity()
    data = request.get_json()
    err = validate_required(data, ['query'])
    if err:
        return jsonify({'error': err}), 400

    SQL_HISTORY.append({
        'user_id': user_id,
        'query': data['query'],
        'executed_at': datetime.utcnow().isoformat() + 'Z',
    })

    mock_result = [
        {'mois': '2026-06', 'type': 'virement', 'total': 458750.00, 'nb_transactions': 127},
        {'mois': '2026-06', 'type': 'retrait', 'total': 89200.00, 'nb_transactions': 43},
        {'mois': '2026-05', 'type': 'virement', 'total': 392100.00, 'nb_transactions': 109},
        {'mois': '2026-05', 'type': 'retrait', 'total': 71500.00, 'nb_transactions': 38},
    ]
    return jsonify({
        'rows': mock_result,
        'rows_count': len(mock_result),
        'columns': list(mock_result[0].keys()) if mock_result else [],
        'duration_ms': random.randint(30, 200),
        'query': data['query'],
    })


@transform_bp.route('/sql/history', methods=['GET'])
@jwt_required()
def sql_history():
    user_id = get_jwt_identity()
    history = [h for h in SQL_HISTORY if h['user_id'] == user_id]
    return jsonify({'history': history[-20:][::-1]})


@transform_bp.route('/functions', methods=['GET'])
@jwt_required()
def list_functions():
    category = request.args.get('category')
    funcs = SQL_FUNCTIONS
    if category:
        funcs = [f for f in funcs if f['category'] == category]
    return jsonify({'functions': funcs})


@transform_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_transform():
    data = request.get_json()
    err = validate_required(data, ['query', 'sample_data'])
    if err:
        return jsonify({'error': err}), 400

    sample = data['sample_data'][:5] if isinstance(data['sample_data'], list) else []
    return jsonify({
        'input_rows': len(data['sample_data']) if isinstance(data['sample_data'], list) else 0,
        'output_rows': len(sample),
        'preview': sample,
        'query': data['query'],
    })


@transform_bp.route('/chain', methods=['POST'])
@jwt_required()
def chain_transforms():
    data = request.get_json()
    err = validate_required(data, ['transforms'])
    if err:
        return jsonify({'error': err}), 400

    transforms = data['transforms']
    result = {
        'steps': len(transforms),
        'chain': [{'step': i + 1, 'query': t.get('query', ''), 'status': 'valid'} for i, t in enumerate(transforms)],
        'estimated_duration_ms': len(transforms) * 150,
    }
    return jsonify(result)


@transform_bp.route('/templates', methods=['GET'])
@jwt_required()
def list_transform_templates():
    return jsonify({'templates': SQL_TEMPLATES})


@transform_bp.route('/templates/<template_id>/apply', methods=['POST'])
@jwt_required()
def apply_template(template_id):
    tpl = next((t for t in SQL_TEMPLATES if t['id'] == template_id), None)
    if not tpl:
        return jsonify({'error': 'Template not found'}), 404
    data = request.get_json() or {}
    input_ref = data.get('input_ref', 'input_dataset')
    query = tpl['query'].replace('{input}', input_ref)
    return jsonify({'template_id': template_id, 'query': query, 'name': tpl['name']})


@transform_bp.route('/mock-data/generate', methods=['POST'])
@jwt_required()
def generate_mock_data():
    data = request.get_json() or {}
    schema = data.get('schema', {})
    count = min(data.get('count', 10), 1000)
    domain = data.get('domain', 'banking')

    rows = []
    for i in range(count):
        if domain == 'banking':
            row = {
                'id': i + 1,
                'reference': f"TXN{100000 + i}",
                'montant': round(random.uniform(100, 500000), 2),
                'devise': random.choice(['XAF', 'EUR', 'USD']),
                'type': random.choice(['virement', 'retrait', 'depot', 'paiement']),
                'statut': random.choice(['traite', 'en_attente', 'rejete']),
                'date_transaction': f"2026-0{random.randint(1,6)}-{random.randint(1,28):02d}",
                'compte_source': f"CI{random.randint(10000000, 99999999)}",
                'compte_dest': f"CI{random.randint(10000000, 99999999)}",
            }
        else:
            row = {f"field_{j}": f"value_{i}_{j}" for j in range(len(schema) or 3)}
            row['id'] = i + 1
        rows.append(row)

    return jsonify({
        'count': len(rows),
        'domain': domain,
        'data': rows,
        'columns': list(rows[0].keys()) if rows else [],
    })
