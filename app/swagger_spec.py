"""OpenAPI 2.0 (Swagger) spec — DataPipe API v1.0"""
import os


SWAGGER_HOST = os.getenv('SWAGGER_HOST', 'https://datapipe.duckdns.org')
SWAGGER_SCHEMES = [
    scheme.strip()
    for scheme in os.getenv('SWAGGER_SCHEMES', 'https').split(',')
    if scheme.strip()
]

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "DataPipe API",
        "description": (
            "## DataPipe — ETL Visuel pour Pipelines Bancaires\n\n"
            "API REST complète pour concevoir, exécuter et monitorer des pipelines "
            "de transformation de données. Hackathon J.U.I.N 2026 — Thème 9.\n\n"
            "**Auth :** Toutes les routes (sauf `/auth/login`, `/auth/register`, "
            "`/health`) nécessitent un header `Authorization: Bearer <access_token>`."
        ),
        "version": "1.0.0",
        "contact": {"email": "balaandeguefrancoislionnel@gmail.com"},
        "license": {"name": "MIT"},
    },
    "host": SWAGGER_HOST,
    "basePath": "/api/v1",
    "schemes": SWAGGER_SCHEMES,
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT access token. Format : **Bearer &lt;token&gt;**",
        }
    },
    "security": [{"Bearer": []}],
    "tags": [
        {"name": "Auth", "description": "Inscription, connexion, sessions et profil"},
        {"name": "Organisations", "description": "Gestion des organisations et membres"},
        {"name": "Workspaces", "description": "Espaces de travail par org"},
        {"name": "Pipelines", "description": "CRUD pipelines, versioning, templates, import/export"},
        {"name": "Nodes", "description": "Nœuds, arêtes et types de nœuds"},
        {"name": "Runs", "description": "Exécution et monitoring des pipelines"},
        {"name": "Files", "description": "Upload et gestion des fichiers"},
        {"name": "Datasources", "description": "Connexions aux bases de données"},
        {"name": "Transform", "description": "Transformations SQL et mock data"},
        {"name": "AI", "description": "Intelligence artificielle : génération, détection, chat"},
        {"name": "Results", "description": "Résultats et exports"},
        {"name": "Scheduling", "description": "Planification des runs"},
        {"name": "Webhooks", "description": "Webhooks sortants et entrants"},
        {"name": "Notifications", "description": "Notifications et alertes"},
        {"name": "Analytics", "description": "Analytiques, audit et métriques"},
        {"name": "API Keys", "description": "Clés API et intégrations"},
        {"name": "Health", "description": "Santé, ops et marketplace"},
    ],

    # ─── DEFINITIONS / SCHEMAS ───────────────────────────────────────────────
    "definitions": {
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Resource not found"}
            },
        },
        "Message": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "example": "Operation successful"}
            },
        },
        "Pagination": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "page": {"type": "integer"},
                "per_page": {"type": "integer"},
                "pages": {"type": "integer"},
            },
        },
        "User": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "usr_abc123def456"},
                "email": {"type": "string", "format": "email"},
                "name": {"type": "string"},
                "verified": {"type": "boolean"},
                "avatar_url": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "orgs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "role": {"type": "string", "enum": ["viewer", "editor", "admin", "owner"]},
                        },
                    },
                },
            },
        },
        "LoginResponse": {
            "type": "object",
            "properties": {
                "access_token": {"type": "string"},
                "refresh_token": {"type": "string"},
                "expires_in": {"type": "integer", "example": 900},
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "org_id": {"type": "string"},
                    },
                },
            },
        },
        "Session": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "ip": {"type": "string"},
                "device": {"type": "string"},
                "created_at": {"type": "string"},
                "current": {"type": "boolean"},
            },
        },
        "Org": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "org_abc123"},
                "name": {"type": "string"},
                "slug": {"type": "string"},
                "plan": {"type": "string", "enum": ["free", "pro", "enterprise"]},
                "members_count": {"type": "integer"},
                "storage_used_mb": {"type": "integer"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "OrgMember": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "name": {"type": "string"},
                "email": {"type": "string"},
                "role": {"type": "string", "enum": ["viewer", "editor", "admin", "owner"]},
                "joined_at": {"type": "string"},
            },
        },
        "Workspace": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "ws_abc123"},
                "org_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "color": {"type": "string", "example": "#3b82f6"},
                "pipelines_count": {"type": "integer"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "Pipeline": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "pip_abc123"},
                "workspace_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": ["active", "archived", "deleted"]},
                "is_public": {"type": "boolean"},
                "nodes_count": {"type": "integer"},
                "last_run_at": {"type": "string", "format": "date-time"},
                "last_run_status": {"type": "string", "enum": ["success", "error", "running"]},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
            },
        },
        "PipelineWithGraph": {
            "allOf": [
                {"$ref": "#/definitions/Pipeline"},
                {
                    "type": "object",
                    "properties": {
                        "nodes": {"type": "array", "items": {"$ref": "#/definitions/Node"}},
                        "edges": {"type": "array", "items": {"$ref": "#/definitions/Edge"}},
                    },
                },
            ]
        },
        "Node": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "nod_abc123"},
                "pipeline_id": {"type": "string"},
                "type": {"type": "string", "example": "csv_reader"},
                "label": {"type": "string"},
                "config": {"type": "object"},
                "position": {
                    "type": "object",
                    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                },
                "has_pinned_data": {"type": "boolean"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "Edge": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "edg_abc123"},
                "pipeline_id": {"type": "string"},
                "source": {"type": "string"},
                "target": {"type": "string"},
                "sourceHandle": {"type": "string", "default": "output"},
                "targetHandle": {"type": "string", "default": "input"},
            },
        },
        "NodeType": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "example": "csv_reader"},
                "name": {"type": "string"},
                "category": {"type": "string", "enum": ["Input", "Transform", "Output", "AI", "Control", "Trigger"]},
                "description": {"type": "string"},
                "icon": {"type": "string"},
                "color": {"type": "string"},
                "inputs": {"type": "integer"},
                "outputs": {"type": "integer"},
            },
        },
        "Run": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "run_abc123"},
                "pipeline_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "running", "success", "error", "cancelled"]},
                "trigger": {"type": "string", "enum": ["manual", "schedule", "webhook", "retry"]},
                "started_at": {"type": "string", "format": "date-time"},
                "finished_at": {"type": "string", "format": "date-time"},
                "duration_ms": {"type": "integer"},
                "error_message": {"type": "string"},
            },
        },
        "RunLog": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "run_id": {"type": "string"},
                "node_id": {"type": "string"},
                "level": {"type": "string", "enum": ["info", "warn", "error"]},
                "message": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
            },
        },
        "File": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "fil_abc123"},
                "workspace_id": {"type": "string"},
                "name": {"type": "string"},
                "size": {"type": "integer", "description": "Size in bytes"},
                "mime_type": {"type": "string"},
                "rows_count": {"type": "integer"},
                "columns_count": {"type": "integer"},
                "columns": {"type": "array", "items": {"type": "string"}},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "Datasource": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "example": "ds_abc123"},
                "workspace_id": {"type": "string"},
                "type": {"type": "string", "enum": ["postgresql", "mysql", "sqlite", "mongodb", "api", "s3"]},
                "name": {"type": "string"},
                "config": {"type": "object"},
                "active": {"type": "boolean"},
                "sync_status": {"type": "string", "enum": ["idle", "syncing", "error"]},
                "last_synced_at": {"type": "string", "format": "date-time"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "Schedule": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "pipeline_id": {"type": "string"},
                "cron": {"type": "string", "example": "0 9 * * 1-5"},
                "timezone": {"type": "string", "example": "Africa/Abidjan"},
                "active": {"type": "boolean"},
                "next_run_at": {"type": "string", "format": "date-time"},
                "last_run_at": {"type": "string", "format": "date-time"},
            },
        },
        "Webhook": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "pipeline_id": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
                "events": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["run.success", "run.error", "run.started", "run.cancelled"]},
                },
                "active": {"type": "boolean"},
                "inbound_token": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "Notification": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string"},
                "title": {"type": "string"},
                "message": {"type": "string"},
                "read": {"type": "boolean"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "Alert": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "pipeline_id": {"type": "string"},
                "name": {"type": "string"},
                "condition": {"type": "string", "example": "run.status == error"},
                "channel": {"type": "string", "enum": ["email", "slack", "sms"]},
                "active": {"type": "boolean"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "ApiKey": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "key_prefix": {"type": "string", "example": "dp_abc123..."},
                "last_used_at": {"type": "string", "format": "date-time"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "PipelineVersion": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "pipeline_id": {"type": "string"},
                "version_num": {"type": "integer"},
                "label": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "PipelineTemplate": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string"},
                "icon": {"type": "string"},
                "nodes_count": {"type": "integer"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
    },

    # ─── PATHS ───────────────────────────────────────────────────────────────
    "paths": {

        # ── 01 AUTH ───────────────────────────────────────────────────────────
        "/auth/register": {
            "post": {
                "tags": ["Auth"],
                "summary": "Créer un compte",
                "description": "Enregistre un nouvel utilisateur. Envoie un email de vérification.",
                "security": [],
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["email", "name", "password"],
                    "properties": {
                        "email": {"type": "string", "format": "email", "example": "john@banque.ci"},
                        "name": {"type": "string", "example": "John Kouassi"},
                        "password": {"type": "string", "minLength": 8, "example": "Secure2026!"},
                        "org_name": {"type": "string", "example": "Banque CI"},
                    },
                }}],
                "responses": {
                    "201": {"description": "Compte créé", "schema": {
                        "type": "object",
                        "properties": {
                            "user": {"$ref": "#/definitions/User"},
                            "message": {"type": "string"},
                        },
                    }},
                    "400": {"description": "Données invalides", "schema": {"$ref": "#/definitions/Error"}},
                    "409": {"description": "Email déjà utilisé", "schema": {"$ref": "#/definitions/Error"}},
                },
            }
        },
        "/auth/login": {
            "post": {
                "tags": ["Auth"],
                "summary": "Se connecter",
                "description": "Retourne un access_token (15min) et un refresh_token (30j).",
                "security": [],
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["email", "password"],
                    "properties": {
                        "email": {"type": "string", "format": "email", "example": "john@banque.ci"},
                        "password": {"type": "string", "example": "Secure2026!"},
                    },
                }}],
                "responses": {
                    "200": {"description": "Connexion réussie", "schema": {"$ref": "#/definitions/LoginResponse"}},
                    "401": {"description": "Identifiants invalides", "schema": {"$ref": "#/definitions/Error"}},
                },
            }
        },
        "/auth/refresh-token": {
            "post": {
                "tags": ["Auth"],
                "summary": "Rafraîchir le token d'accès",
                "description": "Échange un refresh_token valide contre un nouvel access_token (rotation).",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["refresh_token"],
                    "properties": {"refresh_token": {"type": "string"}},
                }}],
                "responses": {
                    "200": {"description": "Nouveau token", "schema": {
                        "type": "object",
                        "properties": {
                            "access_token": {"type": "string"},
                            "refresh_token": {"type": "string"},
                            "expires_in": {"type": "integer"},
                        },
                    }},
                    "401": {"description": "Refresh token invalide"},
                },
            }
        },
        "/auth/logout": {
            "post": {
                "tags": ["Auth"],
                "summary": "Se déconnecter",
                "description": "Invalide la session courante. Le refresh_token est blacklisté.",
                "parameters": [{"in": "body", "name": "body", "schema": {
                    "type": "object",
                    "properties": {"refresh_token": {"type": "string"}},
                }}],
                "responses": {
                    "200": {"description": "Déconnecté", "schema": {"$ref": "#/definitions/Message"}},
                },
            }
        },
        "/auth/forgot-password": {
            "post": {
                "tags": ["Auth"],
                "summary": "Demander une réinitialisation",
                "security": [],
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["email"],
                    "properties": {"email": {"type": "string", "format": "email"}},
                }}],
                "responses": {
                    "200": {"description": "Email envoyé (réponse identique si compte inexistant)", "schema": {"$ref": "#/definitions/Message"}},
                },
            }
        },
        "/auth/reset-password": {
            "post": {
                "tags": ["Auth"],
                "summary": "Réinitialiser le mot de passe",
                "security": [],
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["token", "new_password"],
                    "properties": {
                        "token": {"type": "string"},
                        "new_password": {"type": "string", "minLength": 8},
                    },
                }}],
                "responses": {
                    "200": {"description": "Mot de passe réinitialisé", "schema": {"$ref": "#/definitions/Message"}},
                    "400": {"description": "Token invalide ou expiré"},
                },
            }
        },
        "/auth/verify-email": {
            "post": {
                "tags": ["Auth"],
                "summary": "Vérifier l'email",
                "security": [],
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["token"],
                    "properties": {"token": {"type": "string"}},
                }}],
                "responses": {
                    "200": {"description": "Email vérifié, retourne un access_token"},
                },
            }
        },
        "/auth/me": {
            "get": {
                "tags": ["Auth"],
                "summary": "Profil de l'utilisateur connecté",
                "responses": {
                    "200": {"description": "Profil", "schema": {"$ref": "#/definitions/User"}},
                },
            },
            "patch": {
                "tags": ["Auth"],
                "summary": "Modifier son profil",
                "parameters": [{"in": "body", "name": "body", "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "avatar_url": {"type": "string"},
                    },
                }}],
                "responses": {
                    "200": {"description": "Profil mis à jour"},
                },
            },
            "delete": {
                "tags": ["Auth"],
                "summary": "Supprimer son compte",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["password"],
                    "properties": {"password": {"type": "string"}},
                }}],
                "responses": {
                    "200": {"description": "Compte supprimé", "schema": {"$ref": "#/definitions/Message"}},
                    "400": {"description": "Mot de passe incorrect"},
                },
            },
        },
        "/auth/change-password": {
            "post": {
                "tags": ["Auth"],
                "summary": "Changer le mot de passe",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["current_password", "new_password"],
                    "properties": {
                        "current_password": {"type": "string"},
                        "new_password": {"type": "string", "minLength": 8},
                    },
                }}],
                "responses": {
                    "200": {"description": "Mot de passe changé, toutes les sessions révoquées"},
                    "400": {"description": "Mot de passe actuel incorrect"},
                },
            }
        },
        "/auth/revoke-all-sessions": {
            "post": {
                "tags": ["Auth"],
                "summary": "Révoquer toutes les sessions",
                "parameters": [{"in": "body", "name": "body", "schema": {
                    "type": "object",
                    "properties": {"except_current": {"type": "boolean", "default": False}},
                }}],
                "responses": {
                    "200": {"description": "Sessions révoquées", "schema": {
                        "type": "object",
                        "properties": {"revoked_count": {"type": "integer"}, "message": {"type": "string"}},
                    }},
                },
            }
        },
        "/auth/sessions": {
            "get": {
                "tags": ["Auth"],
                "summary": "Lister les sessions actives",
                "responses": {
                    "200": {"description": "Sessions", "schema": {
                        "type": "object",
                        "properties": {
                            "sessions": {"type": "array", "items": {"$ref": "#/definitions/Session"}},
                        },
                    }},
                },
            }
        },
        "/auth/sessions/{session_id}": {
            "delete": {
                "tags": ["Auth"],
                "summary": "Révoquer une session",
                "parameters": [{"in": "path", "name": "session_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Session révoquée", "schema": {"$ref": "#/definitions/Message"}},
                    "404": {"description": "Session introuvable"},
                },
            }
        },

        # ── 02 ORGS ───────────────────────────────────────────────────────────
        "/orgs": {
            "post": {
                "tags": ["Organisations"],
                "summary": "Créer une organisation",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string", "example": "Banque Nationale CI"},
                        "slug": {"type": "string", "example": "banque-ci"},
                        "plan": {"type": "string", "enum": ["free", "pro", "enterprise"], "default": "free"},
                    },
                }}],
                "responses": {
                    "201": {"description": "Organisation créée", "schema": {"$ref": "#/definitions/Org"}},
                    "400": {"description": "Données invalides"},
                },
            },
            "get": {
                "tags": ["Organisations"],
                "summary": "Lister mes organisations",
                "responses": {
                    "200": {"description": "Liste des orgs", "schema": {
                        "type": "object",
                        "properties": {
                            "orgs": {"type": "array", "items": {"$ref": "#/definitions/Org"}},
                        },
                    }},
                },
            },
        },
        "/orgs/{org_id}": {
            "get": {
                "tags": ["Organisations"],
                "summary": "Détail d'une organisation",
                "parameters": [{"in": "path", "name": "org_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Organisation", "schema": {"$ref": "#/definitions/Org"}},
                    "403": {"description": "Accès refusé"},
                    "404": {"description": "Organisation introuvable"},
                },
            },
            "patch": {
                "tags": ["Organisations"],
                "summary": "Modifier l'organisation",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "settings": {"type": "object"},
                        },
                    }},
                ],
                "responses": {
                    "200": {"description": "Organisation mise à jour", "schema": {"$ref": "#/definitions/Org"}},
                },
            },
            "delete": {
                "tags": ["Organisations"],
                "summary": "Supprimer l'organisation",
                "parameters": [{"in": "path", "name": "org_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Organisation supprimée", "schema": {"$ref": "#/definitions/Message"}},
                    "403": {"description": "Rôle owner requis"},
                },
            },
        },
        "/orgs/{org_id}/members/invite": {
            "post": {
                "tags": ["Organisations"],
                "summary": "Inviter un membre",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["email", "role"],
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "role": {"type": "string", "enum": ["viewer", "editor", "admin", "owner"]},
                        },
                    }},
                ],
                "responses": {
                    "201": {"description": "Invitation envoyée"},
                    "403": {"description": "Rôle admin requis"},
                },
            }
        },
        "/orgs/{org_id}/members": {
            "get": {
                "tags": ["Organisations"],
                "summary": "Lister les membres",
                "parameters": [{"in": "path", "name": "org_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Membres", "schema": {
                        "type": "object",
                        "properties": {
                            "members": {"type": "array", "items": {"$ref": "#/definitions/OrgMember"}},
                        },
                    }},
                },
            }
        },
        "/orgs/{org_id}/members/{user_id}": {
            "patch": {
                "tags": ["Organisations"],
                "summary": "Changer le rôle d'un membre",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "path", "name": "user_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["role"],
                        "properties": {"role": {"type": "string", "enum": ["viewer", "editor", "admin"]}},
                    }},
                ],
                "responses": {"200": {"description": "Rôle mis à jour"}},
            },
            "delete": {
                "tags": ["Organisations"],
                "summary": "Retirer un membre",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "path", "name": "user_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Membre retiré", "schema": {"$ref": "#/definitions/Message"}}},
            },
        },
        "/orgs/{org_id}/members/accept-invite": {
            "post": {
                "tags": ["Organisations"],
                "summary": "Accepter une invitation",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["token"],
                        "properties": {"token": {"type": "string"}},
                    }},
                ],
                "responses": {"200": {"description": "Rejoint l'organisation"}},
            }
        },
        "/orgs/{org_id}/workspaces": {
            "get": {
                "tags": ["Workspaces"],
                "summary": "Lister les workspaces",
                "parameters": [{"in": "path", "name": "org_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Workspaces", "schema": {
                        "type": "object",
                        "properties": {
                            "workspaces": {"type": "array", "items": {"$ref": "#/definitions/Workspace"}},
                        },
                    }},
                },
            },
            "post": {
                "tags": ["Workspaces"],
                "summary": "Créer un workspace",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string", "example": "Production"},
                            "description": {"type": "string"},
                            "color": {"type": "string", "example": "#3b82f6"},
                        },
                    }},
                ],
                "responses": {
                    "201": {"description": "Workspace créé", "schema": {"$ref": "#/definitions/Workspace"}},
                },
            },
        },
        "/orgs/{org_id}/workspaces/{ws_id}": {
            "get": {
                "tags": ["Workspaces"],
                "summary": "Détail d'un workspace",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "path", "name": "ws_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Workspace", "schema": {"$ref": "#/definitions/Workspace"}}},
            },
            "patch": {
                "tags": ["Workspaces"],
                "summary": "Modifier un workspace",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "path", "name": "ws_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "color": {"type": "string"},
                        },
                    }},
                ],
                "responses": {"200": {"description": "Workspace mis à jour", "schema": {"$ref": "#/definitions/Workspace"}}},
            },
            "delete": {
                "tags": ["Workspaces"],
                "summary": "Supprimer un workspace",
                "parameters": [
                    {"in": "path", "name": "org_id", "required": True, "type": "string"},
                    {"in": "path", "name": "ws_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Workspace supprimé", "schema": {"$ref": "#/definitions/Message"}}},
            },
        },

        # ── 03 PIPELINES ─────────────────────────────────────────────────────
        "/pipelines": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Lister les pipelines",
                "parameters": [
                    {"in": "query", "name": "workspace_id", "required": True, "type": "string"},
                    {"in": "query", "name": "page", "type": "integer", "default": 1},
                    {"in": "query", "name": "per_page", "type": "integer", "default": 20},
                    {"in": "query", "name": "search", "type": "string"},
                    {"in": "query", "name": "status", "type": "string", "enum": ["active", "archived"]},
                    {"in": "query", "name": "sort", "type": "string", "enum": ["name", "updated_at", "last_run_at"]},
                ],
                "responses": {
                    "200": {"description": "Pipelines paginés", "schema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "items": {"$ref": "#/definitions/Pipeline"}},
                            "pagination": {"$ref": "#/definitions/Pagination"},
                        },
                    }},
                },
            },
            "post": {
                "tags": ["Pipelines"],
                "summary": "Créer un pipeline",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["name", "workspace_id"],
                    "properties": {
                        "name": {"type": "string", "example": "Pipeline Transactions Mensuelles"},
                        "workspace_id": {"type": "string"},
                        "description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                }}],
                "responses": {
                    "201": {"description": "Pipeline créé", "schema": {"$ref": "#/definitions/PipelineWithGraph"}},
                },
            },
        },
        "/pipelines/{pipeline_id}": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Charger un pipeline complet (avec nodes + edges)",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Pipeline", "schema": {"$ref": "#/definitions/PipelineWithGraph"}},
                    "404": {"description": "Pipeline introuvable"},
                },
            },
            "put": {
                "tags": ["Pipelines"],
                "summary": "Remplacer un pipeline",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    }},
                ],
                "responses": {"200": {"description": "Pipeline mis à jour", "schema": {"$ref": "#/definitions/Pipeline"}}},
            },
            "patch": {
                "tags": ["Pipelines"],
                "summary": "Mettre à jour partiellement un pipeline",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    }},
                ],
                "responses": {"200": {"description": "Pipeline mis à jour", "schema": {"$ref": "#/definitions/Pipeline"}}},
            },
            "delete": {
                "tags": ["Pipelines"],
                "summary": "Supprimer un pipeline",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Pipeline supprimé", "schema": {"$ref": "#/definitions/Message"}}},
            },
        },
        "/pipelines/{pipeline_id}/duplicate": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Dupliquer un pipeline",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }},
                ],
                "responses": {"201": {"description": "Pipeline dupliqué", "schema": {"$ref": "#/definitions/PipelineWithGraph"}}},
            }
        },
        "/pipelines/{pipeline_id}/archive": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Archiver un pipeline",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Pipeline archivé"}},
            }
        },
        "/pipelines/{pipeline_id}/restore": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Restaurer un pipeline archivé",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Pipeline restauré"}},
            }
        },
        "/pipelines/{pipeline_id}/publish": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Rendre un pipeline public",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Pipeline publié"}},
            }
        },
        "/pipelines/{pipeline_id}/unpublish": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Rendre un pipeline privé",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Pipeline dépublié"}},
            }
        },
        "/pipelines/{pipeline_id}/versions": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Lister les versions",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Versions", "schema": {
                        "type": "object",
                        "properties": {"versions": {"type": "array", "items": {"$ref": "#/definitions/PipelineVersion"}}},
                    }},
                },
            }
        },
        "/pipelines/{pipeline_id}/versions/snapshot": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Créer un snapshot manuel",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {"label": {"type": "string", "example": "Avant refactoring"}},
                    }},
                ],
                "responses": {"201": {"description": "Snapshot créé", "schema": {"$ref": "#/definitions/PipelineVersion"}}},
            }
        },
        "/pipelines/{pipeline_id}/versions/{version_id}": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Détail d'une version",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "version_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Version avec snapshot complet"}},
            }
        },
        "/pipelines/{pipeline_id}/versions/{version_id}/restore": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Restaurer une version",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "version_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Pipeline restauré à cette version"}},
            }
        },
        "/pipelines/templates": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Lister les templates",
                "parameters": [{"in": "query", "name": "category", "type": "string"}],
                "responses": {
                    "200": {"description": "Templates", "schema": {
                        "type": "object",
                        "properties": {"templates": {"type": "array", "items": {"$ref": "#/definitions/PipelineTemplate"}}},
                    }},
                },
            }
        },
        "/pipelines/templates/{template_id}": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Détail d'un template",
                "parameters": [{"in": "path", "name": "template_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Template avec nodes et edges"}},
            }
        },
        "/pipelines/templates/{template_id}/instantiate": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Créer un pipeline depuis un template",
                "parameters": [
                    {"in": "path", "name": "template_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["workspace_id"],
                        "properties": {
                            "workspace_id": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    }},
                ],
                "responses": {"201": {"description": "Pipeline créé depuis le template", "schema": {"$ref": "#/definitions/PipelineWithGraph"}}},
            }
        },
        "/pipelines/import": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Importer un pipeline (JSON/YAML)",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["workspace_id", "definition"],
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "definition": {"type": "object", "description": "Définition du pipeline exporté"},
                    },
                }}],
                "responses": {"201": {"description": "Pipeline importé", "schema": {"$ref": "#/definitions/PipelineWithGraph"}}},
            }
        },
        "/pipelines/{pipeline_id}/export": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Exporter un pipeline",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "query", "name": "format", "type": "string", "enum": ["json", "yaml"], "default": "json"},
                ],
                "responses": {"200": {"description": "Définition exportée (JSON ou YAML)"}},
            }
        },
        "/pipelines/{pipeline_id}/diff": {
            "get": {
                "tags": ["Pipelines"],
                "summary": "Diff entre deux versions",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "query", "name": "version_a", "required": True, "type": "string"},
                    {"in": "query", "name": "version_b", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Différences entre les deux versions"}},
            }
        },
        "/pipelines/merge": {
            "post": {
                "tags": ["Pipelines"],
                "summary": "Fusionner deux pipelines",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["source_id", "target_id"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "target_id": {"type": "string"},
                        "offset_x": {"type": "integer", "default": 200},
                    },
                }}],
                "responses": {"200": {"description": "Pipelines fusionnés"}},
            }
        },

        # ── 04 NODES ─────────────────────────────────────────────────────────
        "/pipelines/{pipeline_id}/nodes": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Lister les nœuds",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Nœuds", "schema": {
                        "type": "object",
                        "properties": {"nodes": {"type": "array", "items": {"$ref": "#/definitions/Node"}}},
                    }},
                },
            },
            "post": {
                "tags": ["Nodes"],
                "summary": "Créer un nœud",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {"type": "string", "example": "csv_reader"},
                            "label": {"type": "string"},
                            "config": {"type": "object"},
                            "position": {
                                "type": "object",
                                "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                            },
                        },
                    }},
                ],
                "responses": {"201": {"description": "Nœud créé", "schema": {"$ref": "#/definitions/Node"}}},
            },
        },
        "/pipelines/{pipeline_id}/nodes/bulk": {
            "post": {
                "tags": ["Nodes"],
                "summary": "Créer plusieurs nœuds d'un coup",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["nodes"],
                        "properties": {
                            "nodes": {"type": "array", "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "label": {"type": "string"},
                                    "position": {"type": "object"},
                                    "config": {"type": "object"},
                                },
                            }},
                        },
                    }},
                ],
                "responses": {"201": {"description": "Nœuds créés"}},
            }
        },
        "/pipelines/{pipeline_id}/nodes/{node_id}": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Détail d'un nœud",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Nœud", "schema": {"$ref": "#/definitions/Node"}}},
            },
            "put": {
                "tags": ["Nodes"],
                "summary": "Remplacer un nœud",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/Node"}},
                ],
                "responses": {"200": {"description": "Nœud mis à jour"}},
            },
            "patch": {
                "tags": ["Nodes"],
                "summary": "Mettre à jour un nœud",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "config": {"type": "object"},
                            "position": {"type": "object"},
                        },
                    }},
                ],
                "responses": {"200": {"description": "Nœud mis à jour", "schema": {"$ref": "#/definitions/Node"}}},
            },
            "delete": {
                "tags": ["Nodes"],
                "summary": "Supprimer un nœud (et ses arêtes)",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Nœud supprimé", "schema": {"$ref": "#/definitions/Message"}}},
            },
        },
        "/pipelines/{pipeline_id}/nodes/{node_id}/test-data": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Données de test d'un nœud (pinned ou mock)",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Données de test"}},
            }
        },
        "/pipelines/{pipeline_id}/nodes/{node_id}/pin-data": {
            "post": {
                "tags": ["Nodes"],
                "summary": "Épingler des données sur un nœud (feature n8n)",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["data"],
                        "properties": {"data": {"type": "array"}},
                    }},
                ],
                "responses": {"200": {"description": "Données épinglées"}},
            }
        },
        "/pipelines/{pipeline_id}/nodes/{node_id}/pinned-data": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Lire les données épinglées",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Données épinglées"}, "404": {"description": "Aucune donnée épinglée"}},
            },
            "delete": {
                "tags": ["Nodes"],
                "summary": "Supprimer les données épinglées",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Données désépinglées"}},
            },
        },
        "/pipelines/{pipeline_id}/edges": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Lister les arêtes",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Arêtes", "schema": {
                        "type": "object",
                        "properties": {"edges": {"type": "array", "items": {"$ref": "#/definitions/Edge"}}},
                    }},
                },
            },
            "post": {
                "tags": ["Nodes"],
                "summary": "Créer une arête",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "required": True, "schema": {
                        "type": "object",
                        "required": ["source", "target"],
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "sourceHandle": {"type": "string", "default": "output"},
                            "targetHandle": {"type": "string", "default": "input"},
                        },
                    }},
                ],
                "responses": {"201": {"description": "Arête créée", "schema": {"$ref": "#/definitions/Edge"}}},
            },
        },
        "/pipelines/{pipeline_id}/edges/{edge_id}": {
            "delete": {
                "tags": ["Nodes"],
                "summary": "Supprimer une arête",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "edge_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Arête supprimée"}},
            }
        },
        "/pipelines/{pipeline_id}/edges/validate": {
            "post": {
                "tags": ["Nodes"],
                "summary": "Valider le graphe (cycles, nœuds manquants)",
                "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Résultat de validation", "schema": {
                        "type": "object",
                        "properties": {
                            "valid": {"type": "boolean"},
                            "errors": {"type": "array", "items": {"type": "object"}},
                        },
                    }},
                },
            }
        },
        "/node-types": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Catalogue des types de nœuds",
                "parameters": [{"in": "query", "name": "category", "type": "string"}],
                "responses": {
                    "200": {"description": "Types de nœuds groupés par catégorie", "schema": {
                        "type": "object",
                        "properties": {
                            "node_types": {"type": "array", "items": {"$ref": "#/definitions/NodeType"}},
                            "by_category": {"type": "object"},
                        },
                    }},
                },
            }
        },
        "/node-types/{type_slug}": {
            "get": {
                "tags": ["Nodes"],
                "summary": "Détail d'un type de nœud",
                "parameters": [{"in": "path", "name": "type_slug", "required": True, "type": "string", "example": "csv_reader"}],
                "responses": {"200": {"description": "Type de nœud", "schema": {"$ref": "#/definitions/NodeType"}}},
            }
        },
        "/node-types/{type_slug}/schema": {
            "get": {
                "tags": ["Nodes"],
                "summary": "JSON Schema de la config d'un type de nœud",
                "parameters": [{"in": "path", "name": "type_slug", "required": True, "type": "string"}],
                "responses": {"200": {"description": "JSON Schema de la configuration"}},
            }
        },

        # ── 05 RUNS ───────────────────────────────────────────────────────────
        "/pipelines/{pipeline_id}/run": {
            "post": {
                "tags": ["Runs"],
                "summary": "Déclencher un run",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {
                        "type": "object",
                        "properties": {"trigger": {"type": "string", "default": "manual"}},
                    }},
                ],
                "responses": {"201": {"description": "Run démarré", "schema": {"$ref": "#/definitions/Run"}}},
            }
        },
        "/pipelines/{pipeline_id}/runs": {
            "get": {
                "tags": ["Runs"],
                "summary": "Historique des runs",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "query", "name": "status", "type": "string"},
                    {"in": "query", "name": "page", "type": "integer"},
                    {"in": "query", "name": "per_page", "type": "integer"},
                ],
                "responses": {"200": {"description": "Runs paginés"}},
            }
        },
        "/pipelines/{pipeline_id}/runs/{run_id}": {
            "get": {
                "tags": ["Runs"],
                "summary": "Détail d'un run",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "run_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Run avec résultats par nœud", "schema": {"$ref": "#/definitions/Run"}}},
            },
            "delete": {
                "tags": ["Runs"],
                "summary": "Supprimer un run",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "run_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Run supprimé"}},
            },
        },
        "/pipelines/{pipeline_id}/runs/{run_id}/cancel": {
            "post": {
                "tags": ["Runs"],
                "summary": "Annuler un run en cours",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "run_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Run annulé"}},
            }
        },
        "/pipelines/{pipeline_id}/runs/{run_id}/retry": {
            "post": {
                "tags": ["Runs"],
                "summary": "Relancer un run échoué",
                "parameters": [
                    {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                    {"in": "path", "name": "run_id", "required": True, "type": "string"},
                ],
                "responses": {"201": {"description": "Nouveau run créé"}},
            }
        },
        "/runs/{run_id}/logs": {
            "get": {
                "tags": ["Runs"],
                "summary": "Logs d'un run",
                "parameters": [{"in": "path", "name": "run_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Logs", "schema": {
                        "type": "object",
                        "properties": {
                            "logs": {"type": "array", "items": {"$ref": "#/definitions/RunLog"}},
                            "count": {"type": "integer"},
                        },
                    }},
                },
            }
        },
        "/runs/{run_id}/logs/stream": {
            "get": {
                "tags": ["Runs"],
                "summary": "Stream des logs en temps réel (SSE)",
                "description": "Server-Sent Events. Content-Type: text/event-stream",
                "parameters": [{"in": "path", "name": "run_id", "required": True, "type": "string"}],
                "produces": ["text/event-stream"],
                "responses": {"200": {"description": "Stream de logs SSE"}},
            }
        },
        "/runs/{run_id}/nodes/{node_id}/output": {
            "get": {
                "tags": ["Runs"],
                "summary": "Output d'un nœud pour un run donné",
                "parameters": [
                    {"in": "path", "name": "run_id", "required": True, "type": "string"},
                    {"in": "path", "name": "node_id", "required": True, "type": "string"},
                ],
                "responses": {"200": {"description": "Résultat du nœud"}},
            }
        },

        # ── 06 FILES ─────────────────────────────────────────────────────────
        "/files/upload": {
            "post": {
                "tags": ["Files"],
                "summary": "Uploader un fichier",
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {"in": "formData", "name": "file", "type": "file", "required": True},
                    {"in": "formData", "name": "workspace_id", "type": "string", "required": True},
                ],
                "responses": {"201": {"description": "Fichier uploadé", "schema": {"$ref": "#/definitions/File"}}},
            }
        },
        "/files": {
            "get": {
                "tags": ["Files"],
                "summary": "Lister les fichiers",
                "parameters": [
                    {"in": "query", "name": "workspace_id", "required": True, "type": "string"},
                    {"in": "query", "name": "page", "type": "integer"},
                ],
                "responses": {"200": {"description": "Fichiers paginés"}},
            }
        },
        "/files/{file_id}": {
            "get": {
                "tags": ["Files"],
                "summary": "Détail d'un fichier",
                "parameters": [{"in": "path", "name": "file_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Fichier", "schema": {"$ref": "#/definitions/File"}}},
            },
            "delete": {
                "tags": ["Files"],
                "summary": "Supprimer un fichier",
                "parameters": [{"in": "path", "name": "file_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Fichier supprimé"}},
            },
        },
        "/files/{file_id}/preview": {
            "get": {
                "tags": ["Files"],
                "summary": "Aperçu des données",
                "parameters": [
                    {"in": "path", "name": "file_id", "required": True, "type": "string"},
                    {"in": "query", "name": "limit", "type": "integer", "default": 20},
                ],
                "responses": {"200": {"description": "Aperçu des premières lignes"}},
            }
        },
        "/files/{file_id}/analyze": {
            "post": {
                "tags": ["Files"],
                "summary": "Analyser la qualité d'un fichier",
                "parameters": [{"in": "path", "name": "file_id", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Rapport de qualité des données"}},
            }
        },
        "/datasources": {
            "get": {
                "tags": ["Datasources"],
                "summary": "Lister les datasources",
                "parameters": [{"in": "query", "name": "workspace_id", "required": True, "type": "string"}],
                "responses": {
                    "200": {"description": "Datasources", "schema": {
                        "type": "object",
                        "properties": {"datasources": {"type": "array", "items": {"$ref": "#/definitions/Datasource"}}},
                    }},
                },
            },
            "post": {
                "tags": ["Datasources"],
                "summary": "Créer une datasource",
                "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                    "type": "object",
                    "required": ["workspace_id", "type", "name"],
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "type": {"type": "string", "enum": ["postgresql", "mysql", "sqlite", "mongodb", "api", "s3"]},
                        "name": {"type": "string"},
                        "config": {"type": "object", "example": {"host": "localhost", "port": 5432, "database": "banque"}},
                    },
                }}],
                "responses": {"201": {"description": "Datasource créée", "schema": {"$ref": "#/definitions/Datasource"}}},
            },
        },
        "/datasources/types": {
            "get": {
                "tags": ["Datasources"],
                "summary": "Types de datasources supportés",
                "responses": {"200": {"description": "Types avec leurs schemas de config"}},
            }
        },
        "/datasources/{ds_id}": {
            "get": {"tags": ["Datasources"], "summary": "Détail d'une datasource",
                    "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Datasource", "schema": {"$ref": "#/definitions/Datasource"}}}},
            "patch": {"tags": ["Datasources"], "summary": "Modifier une datasource",
                      "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"},
                                     {"in": "body", "name": "body", "schema": {"type": "object"}}],
                      "responses": {"200": {"description": "Datasource mise à jour"}}},
            "delete": {"tags": ["Datasources"], "summary": "Supprimer une datasource",
                       "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Datasource supprimée"}}},
        },
        "/datasources/{ds_id}/test": {
            "post": {"tags": ["Datasources"], "summary": "Tester la connexion",
                     "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Résultat du test de connexion"}}}
        },
        "/datasources/{ds_id}/schema": {
            "get": {"tags": ["Datasources"], "summary": "Schéma de la base de données",
                    "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Tables et colonnes"}}}
        },
        "/datasources/{ds_id}/sync": {
            "post": {"tags": ["Datasources"], "summary": "Synchroniser les métadonnées",
                     "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Sync complétée"}}}
        },
        "/datasources/{ds_id}/sync-status": {
            "get": {"tags": ["Datasources"], "summary": "Statut de la synchronisation",
                    "parameters": [{"in": "path", "name": "ds_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Statut sync"}}}
        },

        # ── 07 TRANSFORM ─────────────────────────────────────────────────────
        "/transform/sql/validate": {
            "post": {"tags": ["Transform"], "summary": "Valider une requête SQL",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["query"],
                         "properties": {"query": {"type": "string", "example": "SELECT SUM(montant) FROM {input}"}},
                     }}],
                     "responses": {"200": {"description": "Résultat de validation"}}}
        },
        "/transform/sql/execute": {
            "post": {"tags": ["Transform"], "summary": "Exécuter une requête SQL",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["query"],
                         "properties": {"query": {"type": "string"}},
                     }}],
                     "responses": {"200": {"description": "Résultats de la requête"}}}
        },
        "/transform/sql/history": {
            "get": {"tags": ["Transform"], "summary": "Historique des requêtes",
                    "responses": {"200": {"description": "20 dernières requêtes"}}}
        },
        "/transform/functions": {
            "get": {"tags": ["Transform"], "summary": "Fonctions SQL disponibles",
                    "parameters": [{"in": "query", "name": "category", "type": "string"}],
                    "responses": {"200": {"description": "Liste des fonctions"}}}
        },
        "/transform/preview": {
            "post": {"tags": ["Transform"], "summary": "Prévisualiser une transformation",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["query", "sample_data"],
                         "properties": {"query": {"type": "string"}, "sample_data": {"type": "array"}},
                     }}],
                     "responses": {"200": {"description": "Aperçu des données transformées"}}}
        },
        "/transform/templates": {
            "get": {"tags": ["Transform"], "summary": "Templates SQL pré-définis",
                    "responses": {"200": {"description": "Templates SQL bancaires"}}}
        },
        "/transform/templates/{template_id}/apply": {
            "post": {"tags": ["Transform"], "summary": "Appliquer un template SQL",
                     "parameters": [
                         {"in": "path", "name": "template_id", "required": True, "type": "string"},
                         {"in": "body", "name": "body", "schema": {
                             "type": "object",
                             "properties": {"input_ref": {"type": "string", "default": "input_dataset"}},
                         }},
                     ],
                     "responses": {"200": {"description": "Requête SQL générée"}}}
        },
        "/transform/mock-data/generate": {
            "post": {"tags": ["Transform"], "summary": "Générer des données fictives réalistes",
                     "parameters": [{"in": "body", "name": "body", "schema": {
                         "type": "object",
                         "properties": {
                             "count": {"type": "integer", "default": 10, "maximum": 1000},
                             "domain": {"type": "string", "enum": ["banking", "generic"], "default": "banking"},
                             "schema": {"type": "object"},
                         },
                     }}],
                     "responses": {"200": {"description": "Données générées"}}}
        },
        "/transform/chain": {
            "post": {"tags": ["Transform"], "summary": "Chaîner plusieurs transformations",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["transforms"],
                         "properties": {"transforms": {"type": "array", "items": {"type": "object"}}},
                     }}],
                     "responses": {"200": {"description": "Résumé de la chaîne"}}}
        },

        # ── 08 AI ─────────────────────────────────────────────────────────────
        "/ai/generate-transform": {
            "post": {"tags": ["AI"], "summary": "Générer une requête SQL depuis une description naturelle",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["description"],
                         "properties": {
                             "description": {"type": "string", "example": "Somme des transactions par mois et par type"},
                             "context": {"type": "object", "properties": {"columns": {"type": "array", "items": {"type": "string"}}}},
                         },
                     }}],
                     "responses": {"200": {"description": "Requête SQL générée avec score de confiance"}}}
        },
        "/ai/suggest-pipeline": {
            "post": {"tags": ["AI"], "summary": "Suggérer une structure de pipeline depuis un objectif",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["goal"],
                         "properties": {"goal": {"type": "string", "example": "Détecter les fraudes dans les transactions bancaires"}},
                     }}],
                     "responses": {"200": {"description": "Structure de pipeline suggérée"}}}
        },
        "/ai/generate-pipeline": {
            "post": {"tags": ["AI"], "summary": "Générer un pipeline React Flow complet depuis un prompt",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["prompt"],
                         "properties": {"prompt": {"type": "string", "example": "Créer un pipeline d'analyse des transactions avec filtre de montant > 50000 et export CSV"}},
                     }}],
                     "responses": {"200": {"description": "Pipeline React Flow (nodes + edges) généré"}}}
        },
        "/ai/explain-node": {
            "post": {"tags": ["AI"], "summary": "Expliquer ce que fait un nœud",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["node_type"],
                         "properties": {
                             "node_type": {"type": "string"},
                             "config": {"type": "object"},
                         },
                     }}],
                     "responses": {"200": {"description": "Explication en langage naturel"}}}
        },
        "/ai/detect-anomalies": {
            "post": {"tags": ["AI"], "summary": "Détecter les anomalies dans un dataset",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["data"],
                         "properties": {
                             "data": {"type": "array", "items": {"type": "object"}},
                             "amount_field": {"type": "string", "default": "montant"},
                         },
                     }}],
                     "responses": {"200": {"description": "Anomalies détectées avec z-score"}}}
        },
        "/ai/clean-data": {
            "post": {"tags": ["AI"], "summary": "Nettoyer automatiquement un dataset",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["data"],
                         "properties": {"data": {"type": "array"}},
                     }}],
                     "responses": {"200": {"description": "Dataset nettoyé avec rapport"}}}
        },
        "/ai/generate-schema": {
            "post": {"tags": ["AI"], "summary": "Inférer un schema JSON depuis des données",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["sample_data"],
                         "properties": {"sample_data": {"type": "array"}},
                     }}],
                     "responses": {"200": {"description": "Schema JSON inféré"}}}
        },
        "/ai/models": {
            "get": {"tags": ["AI"], "summary": "Modèles IA disponibles",
                    "responses": {"200": {"description": "Liste des modèles"}}}
        },
        "/ai/chat": {
            "post": {"tags": ["AI"], "summary": "Chat avec DataPipe Assistant",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["message"],
                         "properties": {
                             "message": {"type": "string", "example": "Comment détecter les anomalies dans mes transactions ?"},
                             "session_id": {"type": "string"},
                         },
                     }}],
                     "responses": {"200": {"description": "Réponse de l'assistant"}}}
        },
        "/ai/chat/{session_id}/history": {
            "get": {"tags": ["AI"], "summary": "Historique d'une session de chat",
                    "parameters": [{"in": "path", "name": "session_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Messages de la session"}}}
        },
        "/ai/detect-anomalies-batch": {"get": {"tags": ["AI"], "summary": "Batch anomaly detection", "responses": {"200": {}}}},
        "/ai/embed": {
            "post": {"tags": ["AI"], "summary": "Générer des embeddings vectoriels",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["texts"],
                         "properties": {"texts": {"type": "array", "items": {"type": "string"}}},
                     }}],
                     "responses": {"200": {"description": "Vecteurs d'embeddings"}}}
        },
        "/ai/classify": {
            "post": {"tags": ["AI"], "summary": "Classifier des lignes dans des catégories",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["data", "categories"],
                         "properties": {
                             "data": {"type": "array"},
                             "categories": {"type": "array", "items": {"type": "string"}},
                         },
                     }}],
                     "responses": {"200": {"description": "Résultats de classification"}}}
        },
        "/ai/extract-entities": {
            "post": {"tags": ["AI"], "summary": "Extraire des entités (montants, dates, noms)",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["texts"],
                         "properties": {"texts": {"type": "array", "items": {"type": "string"}}},
                     }}],
                     "responses": {"200": {"description": "Entités extraites"}}}
        },
        "/ai/usage": {
            "get": {"tags": ["AI"], "summary": "Utilisation des tokens IA",
                    "responses": {"200": {"description": "Tokens utilisés / limit"}}}
        },

        # ── 09 RESULTS ───────────────────────────────────────────────────────
        "/pipelines/{pipeline_id}/results": {
            "get": {"tags": ["Results"], "summary": "Résultats d'un pipeline",
                    "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Résultats des runs récents"}}}
        },
        "/runs/{run_id}/results": {
            "get": {"tags": ["Results"], "summary": "Résultats d'un run",
                    "parameters": [{"in": "path", "name": "run_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Données produites par le run"}}}
        },
        "/results/{result_id}": {
            "get": {"tags": ["Results"], "summary": "Détail d'un résultat",
                    "parameters": [{"in": "path", "name": "result_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Résultat"}}}
        },
        "/results/{result_id}/download": {
            "get": {"tags": ["Results"], "summary": "Télécharger un résultat",
                    "parameters": [
                        {"in": "path", "name": "result_id", "required": True, "type": "string"},
                        {"in": "query", "name": "format", "type": "string", "enum": ["csv", "json"], "default": "csv"},
                    ],
                    "produces": ["text/csv", "application/json"],
                    "responses": {"200": {"description": "Fichier téléchargé"}}}
        },
        "/results/{result_id}/export": {
            "post": {"tags": ["Results"], "summary": "Créer un export",
                     "parameters": [
                         {"in": "path", "name": "result_id", "required": True, "type": "string"},
                         {"in": "body", "name": "body", "schema": {
                             "type": "object",
                             "properties": {"format": {"type": "string", "enum": ["csv", "json", "excel"]}},
                         }},
                     ],
                     "responses": {"201": {"description": "Export créé"}}}
        },
        "/exports": {
            "get": {"tags": ["Results"], "summary": "Lister les exports",
                    "responses": {"200": {"description": "Exports"}}}
        },
        "/exports/{export_id}": {
            "get": {"tags": ["Results"], "summary": "Détail d'un export",
                    "parameters": [{"in": "path", "name": "export_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Export"}}},
            "delete": {"tags": ["Results"], "summary": "Supprimer un export",
                       "parameters": [{"in": "path", "name": "export_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Export supprimé"}}},
        },
        "/exports/{export_id}/retry": {
            "post": {"tags": ["Results"], "summary": "Relancer un export échoué",
                     "parameters": [{"in": "path", "name": "export_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Export relancé"}}}
        },
        "/exports/{export_id}/download": {
            "get": {"tags": ["Results"], "summary": "Télécharger un export",
                    "parameters": [{"in": "path", "name": "export_id", "required": True, "type": "string"}],
                    "produces": ["text/csv", "application/json"],
                    "responses": {"200": {"description": "Fichier"}}}
        },

        # ── 10 SCHEDULING ─────────────────────────────────────────────────────
        "/pipelines/{pipeline_id}/schedule": {
            "get": {"tags": ["Scheduling"], "summary": "Lire le planning",
                    "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Schedule", "schema": {"$ref": "#/definitions/Schedule"}}}},
            "post": {"tags": ["Scheduling"], "summary": "Créer un planning",
                     "parameters": [
                         {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                         {"in": "body", "name": "body", "required": True, "schema": {
                             "type": "object", "required": ["cron"],
                             "properties": {
                                 "cron": {"type": "string", "example": "0 8 * * 1-5"},
                                 "timezone": {"type": "string", "default": "Africa/Abidjan"},
                                 "active": {"type": "boolean", "default": True},
                             },
                         }},
                     ],
                     "responses": {"201": {"description": "Schedule créé", "schema": {"$ref": "#/definitions/Schedule"}}}},
            "patch": {"tags": ["Scheduling"], "summary": "Modifier le planning",
                      "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                                     {"in": "body", "name": "body", "schema": {"type": "object"}}],
                      "responses": {"200": {"description": "Schedule mis à jour"}}},
            "delete": {"tags": ["Scheduling"], "summary": "Supprimer le planning",
                       "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Schedule supprimé"}}},
        },
        "/pipelines/{pipeline_id}/schedule/pause": {
            "post": {"tags": ["Scheduling"], "summary": "Mettre en pause",
                     "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Planification suspendue"}}}
        },
        "/pipelines/{pipeline_id}/schedule/resume": {
            "post": {"tags": ["Scheduling"], "summary": "Reprendre la planification",
                     "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Planification reprise"}}}
        },
        "/schedules": {
            "get": {"tags": ["Scheduling"], "summary": "Tous les plannings actifs",
                    "parameters": [{"in": "query", "name": "workspace_id", "type": "string"}],
                    "responses": {"200": {"description": "Plannings"}}}
        },
        "/schedules/{schedule_id}/runs": {
            "get": {"tags": ["Scheduling"], "summary": "Runs déclenchés par un schedule",
                    "parameters": [{"in": "path", "name": "schedule_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Runs"}}}
        },
        "/schedules/{schedule_id}/trigger": {
            "post": {"tags": ["Scheduling"], "summary": "Déclencher manuellement un schedule",
                     "parameters": [{"in": "path", "name": "schedule_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Run déclenché"}}}
        },

        # ── 11 WEBHOOKS ───────────────────────────────────────────────────────
        "/pipelines/{pipeline_id}/webhooks": {
            "get": {"tags": ["Webhooks"], "summary": "Webhooks d'un pipeline",
                    "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Webhooks"}}},
            "post": {"tags": ["Webhooks"], "summary": "Créer un webhook",
                     "parameters": [
                         {"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                         {"in": "body", "name": "body", "required": True, "schema": {
                             "type": "object", "required": ["url"],
                             "properties": {
                                 "url": {"type": "string", "format": "uri"},
                                 "events": {"type": "array", "items": {"type": "string"}},
                                 "secret": {"type": "string"},
                             },
                         }},
                     ],
                     "responses": {"201": {"description": "Webhook créé", "schema": {"$ref": "#/definitions/Webhook"}}}},
        },
        "/pipelines/{pipeline_id}/webhooks/{webhook_id}": {
            "get": {"tags": ["Webhooks"], "summary": "Détail d'un webhook",
                    "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                                   {"in": "path", "name": "webhook_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Webhook"}}},
            "patch": {"tags": ["Webhooks"], "summary": "Modifier un webhook",
                      "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                                     {"in": "path", "name": "webhook_id", "required": True, "type": "string"},
                                     {"in": "body", "name": "body", "schema": {"type": "object"}}],
                      "responses": {"200": {"description": "Webhook mis à jour"}}},
            "delete": {"tags": ["Webhooks"], "summary": "Supprimer un webhook",
                       "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                                      {"in": "path", "name": "webhook_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Webhook supprimé"}}},
        },
        "/pipelines/{pipeline_id}/webhooks/{webhook_id}/test": {
            "post": {"tags": ["Webhooks"], "summary": "Envoyer un webhook de test",
                     "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"},
                                    {"in": "path", "name": "webhook_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Webhook de test envoyé"}}}
        },
        "/webhooks": {
            "get": {"tags": ["Webhooks"], "summary": "Tous les webhooks",
                    "responses": {"200": {"description": "Webhooks"}}}
        },
        "/webhooks/{webhook_id}/events": {
            "get": {"tags": ["Webhooks"], "summary": "Historique des événements",
                    "parameters": [{"in": "path", "name": "webhook_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Événements webhook"}}}
        },
        "/webhooks/inbound/{token}": {
            "post": {"tags": ["Webhooks"], "summary": "Réception d'un webhook entrant",
                     "security": [],
                     "parameters": [{"in": "path", "name": "token", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Webhook reçu"}, "404": {"description": "Token invalide"}}}
        },

        # ── 12 NOTIFICATIONS ──────────────────────────────────────────────────
        "/notifications": {
            "get": {"tags": ["Notifications"], "summary": "Mes notifications",
                    "parameters": [{"in": "query", "name": "read", "type": "boolean"}],
                    "responses": {"200": {"description": "Notifications avec unread_count"}}}
        },
        "/notifications/{notif_id}/read": {
            "patch": {"tags": ["Notifications"], "summary": "Marquer comme lue",
                      "parameters": [{"in": "path", "name": "notif_id", "required": True, "type": "string"}],
                      "responses": {"200": {"description": "Notification marquée"}}}
        },
        "/notifications/mark-all-read": {
            "post": {"tags": ["Notifications"], "summary": "Marquer toutes comme lues",
                     "responses": {"200": {"description": "Toutes marquées"}}}
        },
        "/notifications/{notif_id}": {
            "delete": {"tags": ["Notifications"], "summary": "Supprimer une notification",
                       "parameters": [{"in": "path", "name": "notif_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Notification supprimée"}}}
        },
        "/alerts": {
            "get": {"tags": ["Notifications"], "summary": "Lister les alertes",
                    "parameters": [{"in": "query", "name": "workspace_id", "type": "string"}],
                    "responses": {"200": {"description": "Alertes"}}},
            "post": {"tags": ["Notifications"], "summary": "Créer une alerte",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["name", "condition"],
                         "properties": {
                             "pipeline_id": {"type": "string"},
                             "name": {"type": "string"},
                             "condition": {"type": "string"},
                             "channel": {"type": "string", "enum": ["email", "slack", "sms"]},
                             "recipients": {"type": "array", "items": {"type": "string"}},
                         },
                     }}],
                     "responses": {"201": {"description": "Alerte créée", "schema": {"$ref": "#/definitions/Alert"}}}},
        },
        "/alerts/{alert_id}": {
            "get": {"tags": ["Notifications"], "summary": "Détail d'une alerte",
                    "parameters": [{"in": "path", "name": "alert_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Alerte"}}},
            "patch": {"tags": ["Notifications"], "summary": "Modifier une alerte",
                      "parameters": [{"in": "path", "name": "alert_id", "required": True, "type": "string"},
                                     {"in": "body", "name": "body", "schema": {"type": "object"}}],
                      "responses": {"200": {"description": "Alerte mise à jour"}}},
            "delete": {"tags": ["Notifications"], "summary": "Supprimer une alerte",
                       "parameters": [{"in": "path", "name": "alert_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Alerte supprimée"}}},
        },
        "/alerts/{alert_id}/test": {
            "post": {"tags": ["Notifications"], "summary": "Tester une alerte",
                     "parameters": [{"in": "path", "name": "alert_id", "required": True, "type": "string"}],
                     "responses": {"200": {"description": "Alerte de test envoyée"}}}
        },

        # ── 13 ANALYTICS ─────────────────────────────────────────────────────
        "/analytics/overview": {
            "get": {"tags": ["Analytics"], "summary": "Vue d'ensemble des métriques",
                    "parameters": [{"in": "query", "name": "workspace_id", "type": "string"}],
                    "responses": {"200": {"description": "KPIs globaux (runs, success rate, data processed)"}}}
        },
        "/analytics/pipelines/{pipeline_id}/stats": {
            "get": {"tags": ["Analytics"], "summary": "Statistiques d'un pipeline",
                    "parameters": [{"in": "path", "name": "pipeline_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Stats détaillées + historique quotidien"}}}
        },
        "/analytics/usage": {
            "get": {"tags": ["Analytics"], "summary": "Utilisation du mois courant",
                    "responses": {"200": {"description": "API calls, stockage, runs, tokens IA"}}}
        },
        "/analytics/runs/timeline": {
            "get": {"tags": ["Analytics"], "summary": "Timeline des runs",
                    "parameters": [
                        {"in": "query", "name": "workspace_id", "type": "string"},
                        {"in": "query", "name": "days", "type": "integer", "default": 30},
                    ],
                    "responses": {"200": {"description": "Runs par jour sur N jours"}}}
        },
        "/audit/logs": {
            "get": {"tags": ["Analytics"], "summary": "Logs d'audit",
                    "parameters": [
                        {"in": "query", "name": "org_id", "type": "string"},
                        {"in": "query", "name": "action", "type": "string"},
                        {"in": "query", "name": "resource_type", "type": "string"},
                        {"in": "query", "name": "page", "type": "integer"},
                    ],
                    "responses": {"200": {"description": "Logs d'audit paginés"}}}
        },
        "/audit/logs/{log_id}": {
            "get": {"tags": ["Analytics"], "summary": "Détail d'un log",
                    "parameters": [{"in": "path", "name": "log_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Log d'audit"}}}
        },

        # ── 14 API KEYS ───────────────────────────────────────────────────────
        "/api-keys": {
            "get": {"tags": ["API Keys"], "summary": "Mes clés API",
                    "responses": {"200": {"description": "Clés API", "schema": {
                        "type": "object",
                        "properties": {"api_keys": {"type": "array", "items": {"$ref": "#/definitions/ApiKey"}}},
                    }}}},
            "post": {"tags": ["API Keys"], "summary": "Créer une clé API",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["name"],
                         "properties": {
                             "name": {"type": "string", "example": "CI/CD Pipeline"},
                             "org_id": {"type": "string"},
                         },
                     }}],
                     "responses": {"201": {"description": "Clé créée — à sauvegarder maintenant (non ré-affichée)"}}}
        },
        "/api-keys/{key_id}": {
            "delete": {"tags": ["API Keys"], "summary": "Révoquer une clé",
                       "parameters": [{"in": "path", "name": "key_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Clé révoquée"}}}
        },
        "/integrations": {
            "get": {"tags": ["API Keys"], "summary": "Lister les intégrations",
                    "parameters": [{"in": "query", "name": "org_id", "type": "string"}],
                    "responses": {"200": {"description": "Intégrations"}}},
            "post": {"tags": ["API Keys"], "summary": "Créer une intégration",
                     "parameters": [{"in": "body", "name": "body", "required": True, "schema": {
                         "type": "object", "required": ["org_id", "type", "name"],
                         "properties": {
                             "org_id": {"type": "string"},
                             "type": {"type": "string", "enum": ["slack", "email", "pagerduty", "jira", "github", "teams"]},
                             "name": {"type": "string"},
                             "config": {"type": "object"},
                         },
                     }}],
                     "responses": {"201": {"description": "Intégration créée"}}}
        },
        "/integrations/{integration_id}": {
            "get": {"tags": ["API Keys"], "summary": "Détail d'une intégration",
                    "parameters": [{"in": "path", "name": "integration_id", "required": True, "type": "string"}],
                    "responses": {"200": {"description": "Intégration"}}},
            "patch": {"tags": ["API Keys"], "summary": "Modifier une intégration",
                      "parameters": [{"in": "path", "name": "integration_id", "required": True, "type": "string"},
                                     {"in": "body", "name": "body", "schema": {"type": "object"}}],
                      "responses": {"200": {"description": "Intégration mise à jour"}}},
            "delete": {"tags": ["API Keys"], "summary": "Supprimer une intégration",
                       "parameters": [{"in": "path", "name": "integration_id", "required": True, "type": "string"}],
                       "responses": {"200": {"description": "Intégration supprimée"}}},
        },

        # ── 15 HEALTH ─────────────────────────────────────────────────────────
        "/health": {
            "get": {"tags": ["Health"], "summary": "Santé globale de l'API", "security": [],
                    "responses": {"200": {"description": "Healthy"}, "503": {"description": "Degraded"}}}
        },
        "/health/ready": {
            "get": {"tags": ["Health"], "summary": "Readiness probe (DB connectée ?)", "security": [],
                    "responses": {"200": {"description": "Ready"}, "503": {"description": "Not ready"}}}
        },
        "/health/live": {
            "get": {"tags": ["Health"], "summary": "Liveness probe", "security": [],
                    "responses": {"200": {"description": "Alive"}}}
        },
        "/ops/metrics": {
            "get": {"tags": ["Health"], "summary": "Métriques ops",
                    "responses": {"200": {"description": "Counters users, pipelines, runs"}}}
        },
        "/ops/version": {
            "get": {"tags": ["Health"], "summary": "Version de l'API", "security": [],
                    "responses": {"200": {"description": "Version et build info"}}}
        },
        "/ops/maintenance": {
            "post": {"tags": ["Health"], "summary": "Toggle mode maintenance",
                     "responses": {"200": {"description": "Mode togglé"}}}
        },
        "/marketplace/nodes": {
            "get": {"tags": ["Health"], "summary": "Catalogue de nœuds communautaires",
                    "parameters": [
                        {"in": "query", "name": "category", "type": "string"},
                        {"in": "query", "name": "search", "type": "string"},
                    ],
                    "responses": {"200": {"description": "Nœuds marketplace triés par popularité"}}}
        },
    },
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/v1/openapi.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
    "title": "DataPipe API",
    "uiversion": 3,
}
