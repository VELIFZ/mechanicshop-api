class Config:
    SECRET_KEY = 'secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    DEBUG = True

class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    TESTING = True
    DEBUG = True

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:<YOUR PASSWORD>@localhost/<the data base>'
    DEBUG = False