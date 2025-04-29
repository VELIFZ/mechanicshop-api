from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from application.extensions import ma, limiter, cache
from application.models import db
from application.blueprints.customer import customer_bp
from application.blueprints.employee import employee_bp
from application.blueprints.service_ticket import service_ticket_bp
from application.blueprints.inventory import inventory_bp
from application.blueprints.service_ import service_bp

def create_app(config_name="development"):
    
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Load configuration based on the environment
    if config_name == "development":
        app.config.from_object("config.DevelopmentConfig")
    elif config_name == "production":
        app.config.from_object("config.ProductionConfig")
    elif config_name == "testing":
        app.config.from_object("config.TestingConfig")
    else:
        app.logger.warning(f"Unknown configuration '{config_name}', defaulting to development")
        app.config.from_object("config.DevelopmentConfig")
    
    # Print the config to debug
    app.logger.info(f"Starting application in {config_name} mode")
    app.logger.info(f"SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"SECRET_KEY in app: {app.config['SECRET_KEY']}")

    
    # add extensions to app
    db.init_app(app)
    ma.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(customer_bp, url_prefix='/customers')
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(service_ticket_bp, url_prefix='/service-tickets')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(service_bp, url_prefix='/services')
    
    # Error handlers for production
    if config_name == "production":
        @app.errorhandler(Exception)
        def handle_error(e):
            return jsonify({"error": str(e)}), 500
            
        @app.errorhandler(404)
        def handle_not_found(e):
            return jsonify({"error": "Resource not found"}), 404
    
    with app.app_context():
        db.create_all()
    
    return app