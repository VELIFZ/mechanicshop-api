import os

# Only load .env in development or local testing
if os.environ.get("FLASK_ENV") != "production":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_TOKEN_EXPIRY = 3600  # Token expiry time in seconds 

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI', 'sqlite:///app.db')
    DEBUG = True
    JWT_TOKEN_EXPIRY = 86400  # 24 hours 
    # Redis cache for development
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    CACHE_DEFAULT_TIMEOUT = 300

class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI', 'sqlite:///test.db')
    TESTING = True
    DEBUG = True
    JWT_TOKEN_EXPIRY = 300  # 5 minutes 
    RATELIMIT_ENABLED = False  # Disable rate limiting for tests 
    # Simple cache for testing (no Redis dependency)
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///test.db'
    DEBUG = False
    JWT_TOKEN_EXPIRY = 3600  # 1 hour 
    # Redis cache for production
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    CACHE_DEFAULT_TIMEOUT = 300
