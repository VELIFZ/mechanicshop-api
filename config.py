import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_TOKEN_EXPIRY = 3600  # Token expiry time in seconds (1 hour)

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI', 'sqlite:///app.db')
    DEBUG = True
    JWT_TOKEN_EXPIRY = 86400  # 24 hours for development

class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI', 'sqlite:///test.db')
    TESTING = True
    DEBUG = True
    JWT_TOKEN_EXPIRY = 300  # 5 minutes for testing

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    DEBUG = False
    JWT_TOKEN_EXPIRY = 3600  # 1 hour for production

class Constants:
    TAX_RATE = 1.08  # 8% tax rate