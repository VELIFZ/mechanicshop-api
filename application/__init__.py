import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_compress import Compress
from application.extensions import ma, limiter, init_cache
from application.models import db
from application.blueprints.customer import customer_bp
from application.blueprints.employee import employee_bp
from application.blueprints.service_ticket import service_ticket_bp
from application.blueprints.inventory import inventory_bp
from application.blueprints.service_ import service_bp
from flask_swagger_ui import get_swaggerui_blueprint

SWAGGER_URL = '/api/docs'  # set the endpoint for documentation

# Base API URL configuration that will be updated in create_app based on environment
API_URL = '/static/swagger.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Mechanic Shop API"
    }
)

def create_app(config_name="None"):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    app = Flask(__name__, static_folder='static')
    
    # Enable compression for static files
    Compress(app)
    
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

    # add extensions to app
    db.init_app(app)
    ma.init_app(app)
    
    # Only initialize rate limiter if enabled (disabled for testing)
    if app.config.get('RATELIMIT_ENABLED', True):
        limiter.init_app(app)
    
    # Initialize cache with proper configuration
    init_cache(app)
    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(customer_bp, url_prefix='/customers')
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(service_ticket_bp, url_prefix='/service-tickets')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(service_bp, url_prefix='/services')
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL) 
    
    # Local dev DB init only
    if config_name == "development":
        with app.app_context():
            db.create_all()
    
    return app

