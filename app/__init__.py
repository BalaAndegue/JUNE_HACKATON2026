from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger
from .extensions import db, jwt, bcrypt
from .swagger_spec import SWAGGER_TEMPLATE, SWAGGER_CONFIG
from config import Config
import os


def create_app(testing=False):
    app = Flask(__name__)
    app.config.from_object(Config)

    if testing:
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['JWT_SECRET_KEY'] = 'test-secret'
        app.config['WTF_CSRF_ENABLED'] = False

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)

    from .routes import register_blueprints
    register_blueprints(app)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    with app.app_context():
        db.create_all()
        from .models import seed_node_types, seed_marketplace_nodes, seed_templates
        seed_node_types()
        seed_marketplace_nodes()
        seed_templates()

    return app
