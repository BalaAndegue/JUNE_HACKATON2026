from .auth import auth_bp
from .orgs import orgs_bp
from .pipelines import pipelines_bp
from .nodes import nodes_bp
from .runs import runs_bp
from .files import files_bp
from .transform import transform_bp
from .ai import ai_bp
from .results import results_bp
from .scheduling import scheduling_bp
from .webhooks import webhooks_bp
from .notifications import notifications_bp
from .analytics import analytics_bp
from .api_keys import api_keys_bp
from .health import health_bp
from .compat import compat_bp
from .telegram import telegram_bp


def register_blueprints(app):
    prefix = '/api/v1'
    app.register_blueprint(auth_bp,          url_prefix=f'{prefix}/auth')
    app.register_blueprint(orgs_bp,          url_prefix=f'{prefix}/orgs')
    app.register_blueprint(pipelines_bp,     url_prefix=f'{prefix}/pipelines')
    app.register_blueprint(nodes_bp,         url_prefix=f'{prefix}')
    app.register_blueprint(runs_bp,          url_prefix=f'{prefix}')
    app.register_blueprint(files_bp,         url_prefix=f'{prefix}')
    app.register_blueprint(transform_bp,     url_prefix=f'{prefix}/transform')
    app.register_blueprint(ai_bp,            url_prefix=f'{prefix}/ai')
    app.register_blueprint(results_bp,       url_prefix=f'{prefix}')
    app.register_blueprint(scheduling_bp,    url_prefix=f'{prefix}')
    app.register_blueprint(webhooks_bp,      url_prefix=f'{prefix}')
    app.register_blueprint(notifications_bp, url_prefix=f'{prefix}')
    app.register_blueprint(analytics_bp,     url_prefix=f'{prefix}')
    app.register_blueprint(api_keys_bp,      url_prefix=f'{prefix}')
    app.register_blueprint(health_bp,        url_prefix=f'{prefix}')
    app.register_blueprint(compat_bp,        url_prefix=f'{prefix}')
    app.register_blueprint(telegram_bp,      url_prefix=f'{prefix}')
