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
    {'id': 'claude-3-5-haiku-20241022', 'name': 'Claude 3.5 Haiku', 'provider': 'anthropic', 'description': 'Most capable and fast Anthropic model', 'max_tokens': 2048, 'available': True},
    {'id': 'gemini-2.0-flash', 'name': 'Gemini 2.0 Flash', 'provider': 'google', 'description': 'Fast Google model, generous free tier', 'max_tokens': 8192, 'available': True},
    {'id': 'llama-3.3-70b-versatile', 'name': 'Llama 3.3 70B (Groq)', 'provider': 'groq', 'description': 'Ultra-fast inference via Groq, OpenAI-compatible', 'max_tokens': 8192, 'available': True},
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
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json',
                     'User-Agent': 'DataPipe/1.0'},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            AI_USAGE['tokens_used'] += result.get('usage', {}).get('total_tokens', 0)
            AI_USAGE['requests'] += 1
            return result['choices'][0]['message']['content']
    except Exception as e:
        return None


def _call_claude(system, messages, model=None, max_tokens=2048):
    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None

    if not model:
        model = current_app.config.get('CLAUDE_MODEL', 'claude-3-5-haiku-20241022')

    try:
        import urllib.request
        import json as _json

        payload = _json.dumps({
            'model': model,
            'messages': messages,
            'system': system,
            'max_tokens': max_tokens,
            'temperature': 0.3,
        }).encode()

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
                'User-Agent': 'DataPipe/1.0',
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            AI_USAGE['tokens_used'] += result.get('usage', {}).get('total_tokens', 0)
            AI_USAGE['requests'] += 1
            return result['content'][0]['text']
    except Exception as e:
        current_app.logger.error(f"Claude API Error: {e}")
        return None



def _call_gemini(system, messages, model=None, max_tokens=2048):
    api_key = current_app.config.get('GEMINI_API_KEY', '')
    if not api_key:
        return None

    if not model:
        model = current_app.config.get('GEMINI_MODEL', 'gemini-2.0-flash')

    try:
        import urllib.request
        import json as _json

        # Gemini: roles are 'user' / 'model', system goes in systemInstruction.
        contents = [{
            'role': 'model' if m.get('role') == 'assistant' else 'user',
            'parts': [{'text': m.get('content', '')}],
        } for m in messages]

        payload = _json.dumps({
            'contents': contents,
            'systemInstruction': {'parts': [{'text': system}]},
            'generationConfig': {'temperature': 0.3, 'maxOutputTokens': max_tokens},
        }).encode()

        url = (f'https://generativelanguage.googleapis.com/v1beta/models/'
               f'{model}:generateContent?key={api_key}')
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'DataPipe/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            usage = result.get('usageMetadata', {})
            AI_USAGE['tokens_used'] += usage.get('totalTokenCount', 0)
            AI_USAGE['requests'] += 1
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        current_app.logger.error(f"Gemini API Error: {e}")
        return None


def _call_groq(system, messages, max_tokens=2048):
    """Groq — OpenAI-compatible chat completions, very fast inference."""
    api_key = current_app.config.get('GROQ_API_KEY', '')
    if not api_key:
        return None
    model = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    try:
        import urllib.request
        import json as _json
        payload = _json.dumps({
            'model': model,
            'messages': [{'role': 'system', 'content': system}] + list(messages),
            'max_tokens': max_tokens,
            'temperature': 0.3,
        }).encode()
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json',
                     'User-Agent': 'DataPipe/1.0'},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            AI_USAGE['tokens_used'] += result.get('usage', {}).get('total_tokens', 0)
            AI_USAGE['requests'] += 1
            return result['choices'][0]['message']['content']
    except Exception as e:
        current_app.logger.error(f"Groq API Error: {e}")
        return None


def _call_llm(system, messages, max_tokens=2048):
    """Unified LLM call with provider fallback: Claude -> Gemini -> Groq -> OpenAI."""
    resp = _call_claude(system=system, messages=messages, max_tokens=max_tokens)
    if not resp:
        resp = _call_gemini(system=system, messages=messages, max_tokens=max_tokens)
    if not resp:
        resp = _call_groq(system=system, messages=messages, max_tokens=max_tokens)
    if not resp:
        resp = _call_openai(
            [{'role': 'system', 'content': system}] + list(messages), max_tokens=max_tokens)
    return resp


def _llm_model_name():
    cfg = current_app.config
    if cfg.get('ANTHROPIC_API_KEY'):
        return 'claude-3-5-haiku-20241022'
    if cfg.get('GEMINI_API_KEY'):
        return cfg.get('GEMINI_MODEL', 'gemini-2.0-flash')
    if cfg.get('GROQ_API_KEY'):
        return cfg.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
    if cfg.get('OPENAI_API_KEY'):
        return 'gpt-4o-mini'
    return 'datapipe-analyst'


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

    sql = _call_llm(
        system="Tu es un expert SQL pour l'ETL bancaire.",
        messages=[{'role': 'user', 'content': f"Génère une requête SQL pour : \"{description}\". Colonnes disponibles : {', '.join(columns)}. Utilise {{input}} pour référencer le dataset d'entrée. Réponds avec UNIQUEMENT la requête SQL, sans explication."}]
    )

    used_mock = False
    if not sql:
        used_mock = True
        sql_map = {
            'somme': f"SELECT SUM(montant) as total, COUNT(*) as nb FROM {{input}}",
            'agreg': f"SELECT STRFTIME('%Y-%m', date_transaction) as mois, SUM(montant) as total FROM {{input}} GROUP BY mois ORDER BY mois DESC",
            'filtr': f"SELECT * FROM {{input}} WHERE statut = 'traite' AND montant > 10000",
            'anomal': f"SELECT * FROM {{input}} WHERE montant > (SELECT AVG(montant) + 3 * SQRT(AVG(montant * montant) - AVG(montant)*AVG(montant)) FROM {{input}})",
        }
        desc_lower = description.lower()
        sql = next((v for k, v in sql_map.items() if k in desc_lower),
                   f"SELECT * FROM {{input}} -- TODO: implement: {description}")

    # Clean potential markdown wrappers
    import re
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql)
    sql = sql.strip()

    model_used = 'datapipe-analyst'
    if not used_mock:
        model_used = _llm_model_name()

    return jsonify({
        'query': sql,
        'description': description,
        'model': model_used,
        'confidence': 0.95 if not used_mock else 0.80,
    })


# ─── Agent IA contrôlé : génère → explique → teste sur échantillon ──────────────

def _agent_sql_and_explanation(description, columns):
    """Ask the LLM for SQL + a plain-language explanation in one JSON call.
    Falls back to a safe heuristic when no API key is configured."""
    system = ("Tu es un expert SQL DuckDB pour l'ETL bancaire. "
              "Tu génères des requêtes SELECT uniquement (jamais de mutation).")
    user = (f"Génère une transformation SQL DuckDB pour : \"{description}\".\n"
            f"Colonnes disponibles : {', '.join(columns)}.\n"
            "Utilise {input} comme nom de table d'entrée.\n"
            "Réponds en JSON STRICT : {\"sql\": \"...\", \"explanation\": "
            "\"explication en français en 1-2 phrases de ce que fait la requête\"}.")
    raw = _call_llm(system=system, messages=[{'role': 'user', 'content': user}])
    if raw:
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
            parsed = _json.loads(cleaned)
            if parsed.get('sql'):
                return parsed['sql'].strip(), parsed.get('explanation', ''), False
        except Exception:
            pass

    # Heuristic fallback (no API key) — column-aware so the generated SQL runs
    # against the actual dataset (e.g. `amount` vs `montant`).
    desc = description.lower()
    cols_lower = {c.lower(): c for c in columns}

    def pick(*candidates, contains=None):
        for cand in candidates:
            if cand in cols_lower:
                return cols_lower[cand]
        if contains:
            for low, orig in cols_lower.items():
                if any(k in low for k in contains):
                    return orig
        return None

    amount = pick('montant', 'amount', 'value', 'total', contains=['montant', 'amount', 'mont']) or (columns[0] if columns else 'montant')
    group = pick('transaction_type', 'type', 'statut', 'status', 'category', 'region',
                 contains=['type', 'categ', 'statut', 'region'])

    if 'anomal' in desc or 'suspect' in desc:
        sql = (f"SELECT * FROM {{input}} WHERE TRY_CAST({amount} AS DOUBLE) < 0 "
               f"OR TRY_CAST({amount} AS DOUBLE) > 5000000")
        expl = f"Sélectionne les transactions où {amount} est négatif ou supérieur à 5 000 000."
    elif 'doublon' in desc or 'dédoublon' in desc or 'duplicat' in desc:
        sql = "SELECT DISTINCT * FROM {input}"
        expl = "Supprime les lignes en double."
    elif 'somme' in desc or 'total' in desc or 'agrég' in desc or 'mois' in desc or 'group' in desc:
        if group:
            sql = (f"SELECT {group}, SUM(TRY_CAST({amount} AS DOUBLE)) AS total, "
                   f"COUNT(*) AS nb FROM {{input}} GROUP BY {group} ORDER BY total DESC")
            expl = f"Agrège la somme de {amount} et le nombre de lignes par {group}."
        else:
            sql = f"SELECT SUM(TRY_CAST({amount} AS DOUBLE)) AS total, COUNT(*) AS nb FROM {{input}}"
            expl = f"Calcule la somme de {amount} et le nombre total de lignes."
    else:
        sql = f"SELECT * FROM {{input}} WHERE TRY_CAST({amount} AS DOUBLE) > 0"
        expl = f"Filtre les lignes où {amount} est positif."
    return sql, expl, True


@ai_bp.route('/agent/transform', methods=['POST'])
@jwt_required()
def agent_transform():
    """
    Controlled AI agent for banking data.

    Pipeline of trust:
      1. The agent proposes SQL from a natural-language request.
      2. It explains, in plain language, what the SQL does.
      3. The SQL is validated (no data-mutating statements allowed).
      4. It is dry-run on a SAMPLE of the real data via the engine.
      5. Before/after preview + quality are returned for human approval.

    Nothing is committed: the user reviews the sample, then runs the pipeline.
    """
    from ..engine.executor import ExecutionContext, DANGEROUS_SQL
    from ..engine import quality as q
    import pandas as pd

    data = request.get_json()
    err = validate_required(data, ['description'])
    if err:
        return jsonify({'error': err}), 400

    description = data['description']
    file_id = data.get('file_id')
    sample_rows = data.get('sample_rows') or data.get('data')
    sample_limit = int(data.get('limit', 200))

    ctx = ExecutionContext(current_app.config['UPLOAD_FOLDER'])

    # Resolve the sample DataFrame (real file > posted rows > empty).
    if file_id:
        df = ctx.load_csv(file_id, {})
        if df.empty:
            df = ctx.load_json(file_id, {})
    elif isinstance(sample_rows, list) and sample_rows:
        df = pd.DataFrame(sample_rows)
    else:
        df = pd.DataFrame()

    sample_df = df.head(sample_limit)
    columns = list(sample_df.columns) or data.get('columns') or [
        'transaction_id', 'montant', 'devise', 'date_transaction', 'transaction_type', 'statut']

    sql, explanation, used_mock = _agent_sql_and_explanation(description, columns)
    sql = re.sub(r"```sql\s*|```\s*", "", sql).strip()

    # Step 3 — validation.
    issues = []
    safe = True
    if DANGEROUS_SQL.search(sql):
        safe = False
        issues.append("La requête contient une instruction de modification interdite.")

    response = {
        'description': description,
        'generated_sql': sql,
        'explanation': explanation,
        'model': _llm_model_name() if not used_mock else 'datapipe-analyst',
        'validation': {'safe': safe, 'issues': issues},
        'status': 'rejected' if not safe else 'pending_confirmation',
    }

    # Step 4 — dry-run on the sample (only if safe and we have data).
    if safe and not sample_df.empty:
        try:
            out = ctx.run_sql(sql, sample_df)
            response['sample'] = {
                'rows_in': len(sample_df),
                'rows_out': len(out),
                'columns_before': q.df_columns(sample_df),
                'columns_after': q.df_columns(out),
                'preview_before': q.df_to_records(sample_df, 10),
                'preview_after': q.df_to_records(out, 10),
                'quality_before': q.compute_quality(sample_df),
                'quality_after': q.compute_quality(out),
            }
        except Exception as exc:  # noqa: BLE001
            response['validation']['safe'] = False
            response['status'] = 'error'
            response['validation']['issues'].append(f"Échec du test sur échantillon : {exc}")
    elif safe:
        response['sample'] = {'rows_in': 0, 'note': "Aucune donnée échantillon fournie — "
                              "associez un fichier (file_id) pour tester avant exécution."}

    return jsonify(response)


# ─── Chat « mode action » : l'assistant propose une action, l'utilisateur confirme ──

# Catalogue des actions que l'agent peut proposer. Chaque exécution se fait via les
# endpoints existants côté front APRÈS confirmation de l'utilisateur.
ACTION_CATALOG = {
    'create_pipeline':  {'params': ['name'],            'warn': None},
    'add_node':         {'params': ['node_type', 'label'], 'warn': None},
    'connect_nodes':    {'params': ['source', 'target'], 'warn': None},
    'configure_node':   {'params': ['node', 'config'],   'warn': None},
    'attach_file':      {'params': ['file_id'],          'warn': None},
    'generate_sql':     {'params': ['description'],      'warn': None},
    'run_pipeline':     {'params': [],                   'warn': "L'exécution traitera les données réelles du pipeline."},
    'delete_node':      {'params': ['node'],             'warn': "Cette action supprime un nœud et ses connexions."},
    'export_pipeline':  {'params': ['format'],           'warn': None},
    'audit_report':     {'params': [],                   'warn': None},
}

_NODE_KEYWORDS = {
    'mask_pii': ['masqu', 'anonymis', 'rgpd', 'pii', 'confidentia'],
    'detect_anomalies': ['anomal', 'suspect', 'fraud', 'atypiqu'],
    'quality_report': ['qualité', 'quality'],
    'filter': ['filtre', 'filtrer', 'garde', 'supérieur', 'inférieur', 'where'],
    'aggregate': ['agrég', 'somme', 'total', 'groupe', 'moyenne', 'count'],
    'dedup': ['doublon', 'dédoublon', 'duplicat'],
    'join': ['jointure', 'join', 'fusionne'],
    'csv_reader': ['csv', 'importe un fichier', 'charge un csv'],
    'file_export': ['exporte en csv', 'export csv'],
}


def _plan_heuristic(message):
    """Fallback sans LLM : déduit une action proposée à partir de mots-clés."""
    m = (message or '').lower()

    if any(k in m for k in ['crée', 'créer', 'nouveau pipeline', 'new pipeline']):
        name = 'Nouveau pipeline'
        mt = re.search(r'(?:appel|nomm)[^\s]*\s+["\']?([\w \-]{3,40})', m)
        if mt:
            name = mt.group(1).strip()
        return {'type': 'action', 'action': 'create_pipeline', 'params': {'name': name},
                'message': f"Je vais créer un pipeline « {name} »."}

    if any(k in m for k in ['exécute', 'execute', 'lance', 'run ', 'lancer']):
        return {'type': 'action', 'action': 'run_pipeline', 'params': {},
                'message': "Je vais exécuter le pipeline courant sur les données réelles."}

    if any(k in m for k in ['audit', 'conformité', 'rapport']):
        return {'type': 'action', 'action': 'audit_report', 'params': {},
                'message': "Je peux générer le rapport d'audit de conformité du dernier run."}

    if any(k in m for k in ['exporte', 'télécharge', 'export', 'yaml', 'déployable']):
        fmt = 'yaml' if 'yaml' in m else 'json'
        return {'type': 'action', 'action': 'export_pipeline', 'params': {'format': fmt},
                'message': f"Je vais exporter le pipeline en {fmt.upper()} déployable."}

    if any(k in m for k in ['sql', 'requête', 'transforme', 'transformation']):
        return {'type': 'action', 'action': 'generate_sql', 'params': {'description': message},
                'message': "Je vais générer une transformation SQL, la tester sur un échantillon, puis tu valideras."}

    # Détection d'un type de nœud à ajouter
    for node_type, kws in _NODE_KEYWORDS.items():
        if any(k in m for k in kws):
            labels = {'mask_pii': 'Masquage RGPD', 'detect_anomalies': 'Détection anomalies',
                      'quality_report': 'Rapport qualité', 'filter': 'Filtre', 'aggregate': 'Agrégation',
                      'dedup': 'Dédoublonnage', 'join': 'Jointure', 'csv_reader': 'Source CSV',
                      'file_export': 'Export'}
            return {'type': 'action', 'action': 'add_node',
                    'params': {'node_type': node_type, 'label': labels.get(node_type, node_type)},
                    'message': f"Je vais ajouter un nœud « {labels.get(node_type, node_type)} » au pipeline."}

    return {'type': 'reply', 'message': _get_fallback_response(message)}


@ai_bp.route('/agent/plan', methods=['POST'])
@jwt_required()
def agent_plan():
    """
    Chat « mode action » : transforme un message en proposition d'action structurée
    (ou réponse texte). N'EXÉCUTE RIEN — le front affiche l'action, l'utilisateur
    confirme, puis l'exécution se fait via les endpoints existants.
    """
    data = request.get_json() or {}
    message = data.get('message')
    if not message and isinstance(data.get('messages'), list):
        message = next((m.get('content') for m in reversed(data['messages'])
                        if m.get('role') == 'user'), None)
    if not message:
        return jsonify({'error': 'message is required'}), 400

    context = data.get('context') or {}
    columns = context.get('columns') or []

    system = (
        "Tu es DataPipe Agent, un assistant qui PILOTE une plateforme ETL bancaire. "
        "À partir du message de l'utilisateur, tu réponds en JSON STRICT.\n"
        "Soit une réponse texte : {\"type\":\"reply\",\"message\":\"...\"}.\n"
        "Soit UNE action à proposer : {\"type\":\"action\",\"action\":\"<nom>\","
        "\"params\":{...},\"message\":\"explication en français\",\"warning\":\"... ou null\"}.\n"
        f"Actions possibles : {', '.join(ACTION_CATALOG.keys())}.\n"
        "Types de nœuds pour add_node : csv_reader, json_reader, sql_query, filter, map, "
        "aggregate, join, sort, dedup, sql_transform, validate, mask_pii, detect_anomalies, "
        "quality_report, file_export.\n"
        f"Colonnes connues : {', '.join(columns) if columns else 'inconnues'}.\n"
        "Tu ne fais qu'UNE action à la fois. Tu n'exécutes jamais : tu proposes."
    )
    raw = _call_llm(system=system, messages=[{'role': 'user', 'content': message}])

    plan = None
    if raw:
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
            parsed = _json.loads(cleaned)
            if parsed.get('type') in ('reply', 'action'):
                plan = parsed
        except Exception:
            pass
    if plan is None:
        plan = _plan_heuristic(message)

    # Validation + garde-fous serveur
    if plan.get('type') == 'action':
        action = plan.get('action')
        if action not in ACTION_CATALOG:
            plan = {'type': 'reply', 'message': plan.get('message')
                    or "Je n'ai pas compris l'action demandée."}
        else:
            spec = ACTION_CATALOG[action]
            plan.setdefault('params', {})
            if not plan.get('warning'):
                plan['warning'] = spec['warn']
            plan['requires_confirmation'] = True

    plan['model'] = _llm_model_name() if raw else 'datapipe-analyst'
    return jsonify(plan)


# ─── Mock Intelligent Constantes & Helpers ─────────────────────────────────────
import re
import json as _json

_SOURCE_KEYWORDS = {
    "csvImport":  ["csv", "fichier", "transactions", "importe", "charge", "upload", "données"],
    "jsonLoader": ["json", "clients", "loader", "api", "url", "endpoint"],
    "sqlQuery":   ["sql", "requête", "base de données", "query", "db", "database"],
}

_TRANSFORM_KEYWORDS = {
    "filter":      ["filtre", "filter", "où", "supérieur", "inférieur", "égal", "where",
                    ">", "<", "montant", "condition", "sélectionne", "garde", "retient"],
    "join":        ["join", "fusionne", "combine", "relie", "merge", "associe", "lien"],
    "aggregation": ["groupe", "agrège", "sum", "somme", "count", "compte", "moyenne",
                    "average", "group by", "par région", "par mois", "par agence", "total",
                    "max", "min", "calcule"],
    "renameCols":  ["renomme", "colonne", "rename", "supprime col", "réordonne"],
    "cleanup":     ["nettoie", "doublon", "null", "vide", "propre", "clean", "supprime doublon"],
    "aiTransform": ["ia transform", "transformation ia", "sql depuis texte", "générer sql"],
}

_OUTPUT_KEYWORDS = {
    "tablePreview": ["tableau", "aperçu", "preview", "affiche", "visualise", "table", "résultat"],
    "chart":        ["graphique", "chart", "bar", "courbe", "pie", "camembert", "histogramme",
                    "visualise", "trace", "diagramme"],
    "csvExport":    ["exporte", "télécharge", "download", "export", "csv export", "enregistre"],
}

_OPERATOR_KEYWORDS = {
    ">":  ["supérieur", ">", "plus grand", "plus de", "dépasse"],
    "<":  ["inférieur", "<", "moins de", "en dessous"],
    ">=": ["supérieur ou égal", ">=", "au moins"],
    "<=": ["inférieur ou égal", "<=", "au plus"],
    "=":  ["égal", "=", "exactement", "vaut"],
    "!=": ["différent", "!=", "pas égal"],
}

_BANKING_COLUMNS = ["montant", "date", "region", "agence", "client_id", "type_transaction", "statut", "id"]
_BANKING_AGGS = {
    "somme": "SUM", "sum": "SUM", "total": "SUM",
    "count": "COUNT", "compte": "COUNT", "nombre": "COUNT",
    "moyenne": "AVG", "average": "AVG", "avg": "AVG",
    "max": "MAX", "maximum": "MAX",
    "min": "MIN", "minimum": "MIN",
}

_GROUP_BY_KEYWORDS = {
    "region": ["région", "region", "zone"],
    "agence": ["agence", "branch", "succursale"],
    "date":   ["mois", "month", "date", "jour", "année", "an"],
    "type_transaction": ["type", "catégorie", "category"],
}

def _detect_nodes(prompt: str) -> list:
    p = prompt.lower()
    detected = []

    # Sources
    for node_type, keywords in _SOURCE_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            if node_type not in detected:
                detected.append(node_type)

    if not any(t in detected for t in _SOURCE_KEYWORDS.keys()):
        detected.append("csvImport")

    if "join" in [t for t in _TRANSFORM_KEYWORDS.keys() if any(kw in p for kw in _TRANSFORM_KEYWORDS[t])]:
        if "jsonLoader" not in detected and any(kw in p for kw in ["clients", "json"]):
            detected.append("jsonLoader")

    # Transformations
    for node_type, keywords in _TRANSFORM_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            if node_type not in detected:
                detected.append(node_type)

    # Outputs
    for node_type, keywords in _OUTPUT_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            if node_type not in detected:
                detected.append(node_type)

    if not any(t in detected for t in _OUTPUT_KEYWORDS.keys()):
        detected.append("tablePreview")

    return detected

def _extract_filter_config(prompt: str) -> dict:
    p = prompt.lower()
    config = {"column": "montant", "operator": ">", "value": 50000}

    for col in _BANKING_COLUMNS:
        if col in p:
            config["column"] = col
            break

    for op, keywords in _OPERATOR_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            config["operator"] = op
            break

    numbers = re.findall(r'\b(\d[\d\s]*(?:\.\d+)?)\b', p)
    if numbers:
        try:
            val = float(numbers[0].replace(" ", ""))
            config["value"] = int(val) if val.is_integer() else val
        except ValueError:
            pass

    return config

def _extract_aggregation_config(prompt: str) -> dict:
    p = prompt.lower()

    group_by = []
    for col, keywords in _GROUP_BY_KEYWORDS.items():
        if any(kw in p for kw in keywords):
            group_by.append(col)
    if not group_by:
        group_by = ["region"]

    aggregates = []
    for kw, func in _BANKING_AGGS.items():
        if kw in p:
            agg_col = "montant"
            if "transaction" in p:
                agg_col = "id" if func == "COUNT" else "montant"
            alias_map = {"SUM": "total_montant", "COUNT": "nb_transactions", "AVG": "moy_montant",
                         "MAX": "max_montant", "MIN": "min_montant"}
            entry = {"func": func, "column": agg_col, "alias": alias_map.get(func, f"{func.lower()}_{agg_col}")}
            if entry not in aggregates:
                aggregates.append(entry)

    if not aggregates:
        aggregates = [{"func": "SUM", "column": "montant", "alias": "total_montant"}]

    return {"groupBy": group_by, "aggregates": aggregates}

def _extract_chart_config(prompt: str, agg_config: dict = None) -> dict:
    p = prompt.lower()
    chart_type = "bar"
    if any(kw in p for kw in ["courbe", "line", "ligne", "évolution", "tendance"]):
        chart_type = "line"
    elif any(kw in p for kw in ["pie", "camembert", "circulaire", "secteur"]):
        chart_type = "pie"

    x_axis = "region"
    y_axis = "total_montant"

    if agg_config:
        if agg_config.get("groupBy"):
            x_axis = agg_config["groupBy"][0]
        if agg_config.get("aggregates"):
            y_axis = agg_config["aggregates"][0].get("alias", "valeur")

    axis_labels = {"region": "Région", "agence": "Agence", "date": "Date",
                   "type_transaction": "Type de transaction"}
    agg_labels = {"total_montant": "Total montant (FCFA)", "nb_transactions": "Nombre de transactions",
                   "moy_montant": "Montant moyen (FCFA)"}

    title = f"{agg_labels.get(y_axis, y_axis)} par {axis_labels.get(x_axis, x_axis)}"
    return {"type": chart_type, "xAxis": x_axis, "yAxis": y_axis, "title": title}

def _build_nodes_and_edges(node_types: list, prompt: str) -> tuple:
    nodes = []
    edges = []
    counter = 1
    x = 100
    y_main = 200
    y_secondary = 420
    last_main_id = None

    filter_config = _extract_filter_config(prompt)
    agg_config = _extract_aggregation_config(prompt)
    chart_config = _extract_chart_config(prompt, agg_config)

    for node_type in node_types:
        node_id = f"ai-{counter}"
        label_map = {
            "csvImport": "CSV Import", "jsonLoader": "JSON Loader", "sqlQuery": "SQL Query",
            "filter": "Filtre", "join": "Join", "aggregation": "Agrégation",
            "renameCols": "Rename Cols", "cleanup": "Nettoyage", "aiTransform": "IA Transform",
            "tablePreview": "Table Preview", "chart": "Chart", "csvExport": "Export CSV",
        }

        config_map = {
            "csvImport":    {"filename": "transactions_banque.csv", "separator": ",", "encoding": "utf-8"},
            "jsonLoader":   {"filename": "clients.json", "rootKey": None},
            "sqlQuery":     {"query": "SELECT * FROM transactions LIMIT 100"},
            "filter":       filter_config,
            "join":         {"leftKey": "client_id", "rightKey": "client_id", "type": "LEFT"},
            "aggregation":  agg_config,
            "renameCols":   {"renames": {}, "drops": []},
            "cleanup":      {"removeDuplicates": True, "dropNulls": False, "trimStrings": True},
            "aiTransform":  {"prompt": "", "generatedSql": ""},
            "tablePreview": {"pageSize": 25, "sortable": True},
            "chart":        chart_config,
            "csvExport":    {"filename": "resultat_datapipe.csv"},
        }

        if node_type == "jsonLoader" and "join" in node_types:
            node_y = y_secondary
        else:
            node_y = y_main

        node = {
            "id": node_id,
            "type": node_type,
            "position": {"x": float(x), "y": float(node_y)},
            "data": {
                "label": label_map.get(node_type, node_type),
                "nodeType": node_type,
                "config": config_map.get(node_type, {}),
            }
        }
        nodes.append(node)

        if node_type != "jsonLoader" and last_main_id:
            edge_id = f"ai-e{last_main_id.split('-')[-1]}-{counter}"
            edge = {
                "id": edge_id,
                "source": last_main_id,
                "target": node_id,
                "animated": True,
                "style": {"stroke": "#00d4ff", "strokeWidth": 2}
            }
            edges.append(edge)
        elif node_type == "join" and "jsonLoader" in node_types:
            json_node = next((n for n in nodes if n["type"] == "jsonLoader"), None)
            if json_node:
                edges.append({
                    "id": f"ai-ejson-{counter}",
                    "source": json_node["id"],
                    "target": node_id,
                    "animated": True,
                    "style": {"stroke": "#00d4ff", "strokeWidth": 2}
                })

        if node_type not in ("jsonLoader",):
            last_main_id = node_id
            x += 280

        counter += 1

    return nodes, edges

def _build_explanation(node_types: list) -> str:
    steps = []
    step_labels = {
        "csvImport": "import CSV", "jsonLoader": "chargement JSON",
        "filter": "filtrage des données", "join": "jointure des datasets",
        "aggregation": "agrégation", "renameCols": "renommage des colonnes",
        "cleanup": "nettoyage", "aiTransform": "transformation IA",
        "tablePreview": "aperçu tableau", "chart": "visualisation graphique",
        "csvExport": "export CSV",
    }
    for nt in node_types:
        if nt in step_labels:
            steps.append(step_labels[nt])

    pipeline_str = " → ".join(steps)
    return f"Pipeline généré ({len(node_types)} nœuds) : {pipeline_str}. Cliquez sur 'Exécuter' pour lancer le pipeline."


# ─── Endpoints de Suggestion / Génération de Pipelines ──────────────────────────────────────

@ai_bp.route('/suggest-pipeline', methods=['POST'])
@jwt_required()
def suggest_pipeline():
    data = request.get_json()
    err = validate_required(data, ['goal'])
    if err:
        return jsonify({'error': err}), 400

    goal = data['goal']
    
    # Tentative Claude
    system_prompt = "Tu es un expert en ETL bancaire."
    user_prompt = f"""Suggère une structure de pipeline pour : "{goal}"
Réponds en JSON avec : name, description, nodes (liste de {{type, label}}), edges (liste de {{source_idx, target_idx}}).
Types disponibles : csv_reader, json_reader, sql_query, filter, map, aggregate, join, sort, dedup, sql_transform, ai_transform, sql_write, file_export, notification_send."""
    
    ai_response = _call_llm(
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_prompt}]
    )

    if ai_response:
        try:
            # Nettoyer le markdown potentiel
            ai_response = re.sub(r"```json\s*", "", ai_response)
            ai_response = re.sub(r"```\s*", "", ai_response)
            ai_response = ai_response.strip()
            parsed = _json.loads(ai_response)
            parsed['mock'] = False
            return jsonify(parsed)
        except Exception:
            pass

    # Fallback sur notre mock intelligent enrichi adapté au format attendu par Bala
    node_types = _detect_nodes(goal)
    nodes_simple = []
    edges_simple = []
    
    type_conversion = {
        "csvImport": "csv_reader",
        "jsonLoader": "json_reader",
        "sqlQuery": "sql_query",
        "filter": "filter",
        "join": "join",
        "aggregation": "aggregate",
        "renameCols": "map",
        "cleanup": "dedup",
        "aiTransform": "ai_transform",
        "tablePreview": "map",
        "chart": "file_export",
        "csvExport": "file_export"
    }
    
    for i, nt in enumerate(node_types):
        nodes_simple.append({
            'type': type_conversion.get(nt, 'filter'),
            'label': nt.capitalize()
        })
        if i > 0:
            edges_simple.append({
                'source_idx': i - 1,
                'target_idx': i
            })
            
    return jsonify({
        'name': f'Pipeline: {goal[:50]}',
        'description': f'Pipeline suggéré pour: {goal}',
        'confidence': 0.85,
        'nodes': nodes_simple,
        'edges': edges_simple,
        'mock': True
    })


@ai_bp.route('/generate-pipeline', methods=['POST'])
@jwt_required()
def generate_pipeline():
    """
    Génère un pipeline complet au format React Flow (nodes + edges).
    Compatible avec notre hook useAIPipeline et le store React Flow.
    """
    data = request.get_json()
    err = validate_required(data, ['prompt'])
    if err:
        return jsonify({'error': err}), 400

    prompt = data['prompt']
    
    # Prompt Système pour React Flow JSON
    system_prompt = """Tu es DataPipe AI, un expert en pipelines de données ETL visuels.
Tu génères des pipelines JSON pour l'application DataPipe, compatibles avec React Flow.

NŒUDS DISPONIBLES :
- csvImport    : importe un fichier CSV (SOURCE, couleur verte)
- jsonLoader   : charge un fichier JSON ou URL API (SOURCE, couleur verte)
- sqlQuery     : exécute une requête SQL sur une DB (SOURCE, couleur verte)
- filter       : filtre les données selon une condition (TRANSFORM)
- join         : fusionne 2 DataFrames (TRANSFORM)
- aggregation  : agrège avec GROUP BY + fonctions (TRANSFORM)
- renameCols   : renomme/supprime/réordonne les colonnes (TRANSFORM)
- cleanup      : nettoie les données - doublons, nulls, trim (TRANSFORM)
- aiTransform  : transformation IA SQL DuckDB (IA, couleur violette)
- tablePreview : affiche un tableau interactif (OUTPUT, couleur ambre)
- chart        : affiche un graphique Recharts (OUTPUT, couleur ambre)
- csvExport    : exporte le résultat en CSV téléchargeable (OUTPUT, couleur ambre)

RÈGLES DE POSITIONNEMENT :
- x débute à 100, incrémente de 280 par nœud de gauche à droite
- y = 200 par défaut (flux principal horizontal)
- Pour les join : la 2ème source est positionnée à y = 420
- Ne jamais dépasser x = 2200

FORMAT DE RÉPONSE (JSON STRICT, aucun texte autour) :
{
  "nodes": [
    {
      "id": "ai-1",
      "type": "csvImport",
      "position": {"x": 100, "y": 200},
      "data": {
        "label": "CSV Import",
        "nodeType": "csvImport",
        "config": {}
      }
    }
  ],
  "edges": [
    {"id": "ai-e1-2", "source": "ai-1", "target": "ai-2", "animated": true}
  ],
  "explanation": "Description courte du pipeline généré (1-2 sentences, in French)"
}

Réponds UNIQUEMENT avec le JSON valide."""

    ai_response = _call_llm(
        system=system_prompt,
        messages=[{'role': 'user', 'content': f"Génère un pipeline pour : {prompt}"}],
        max_tokens=3000
    )

    if ai_response:
        try:
            ai_response = re.sub(r"```json\s*", "", ai_response)
            ai_response = re.sub(r"```\s*", "", ai_response)
            ai_response = ai_response.strip()
            parsed = _json.loads(ai_response)
            parsed['mock'] = False
            parsed['node_count'] = len(parsed.get('nodes', []))
            return jsonify(parsed)
        except Exception:
            pass

    # Fallback mock intelligent React Flow
    node_types = _detect_nodes(prompt)
    nodes, edges = _build_nodes_and_edges(node_types, prompt)
    explanation = _build_explanation(node_types)

    return jsonify({
        "nodes": nodes,
        "edges": edges,
        "explanation": explanation,
        "mock": True,
        "node_count": len(nodes)
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
    data = request.get_json() or {}

    # Accept both the simple {message} shape and the frontend's {messages:[...]} shape.
    message = data.get('message')
    if not message and isinstance(data.get('messages'), list):
        message = next((m.get('content') for m in reversed(data['messages'])
                        if m.get('role') == 'user'), None)
    if not message:
        return jsonify({'error': 'message is required'}), 400

    session_id = data.get('session_id') or f"chat_{user_id}_{int(datetime.utcnow().timestamp())}"
    if session_id not in AI_SESSIONS:
        AI_SESSIONS[session_id] = []

    system_prompt = """Tu es DataPipe Assistant, un expert en ETL et pipelines de données bancaires.
Tu aides les utilisateurs à construire des pipelines, écrire des requêtes SQL, et analyser leurs données.
Réponds en français de manière concise et pratique."""

    AI_SESSIONS[session_id].append({'role': 'user', 'content': message})

    ai_response = _call_llm(system=system_prompt, messages=AI_SESSIONS[session_id][-10:])

    used_mock = False
    if not ai_response:
        used_mock = True
        ai_response = _get_fallback_response(message)

    AI_SESSIONS[session_id].append({'role': 'assistant', 'content': ai_response})

    model_used = 'datapipe-analyst'
    if not used_mock:
        model_used = _llm_model_name()

    return jsonify({
        'session_id': session_id,
        'message': {'role': 'assistant', 'content': ai_response},  # frontend shape
        'response': ai_response,  # legacy shape (kept for existing tests)
        'model': model_used,
        'tokens_used': AI_USAGE.get('tokens_used', 0),
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
