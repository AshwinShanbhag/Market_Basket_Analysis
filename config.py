import os

SECRET_KEY = os.environ.get('SECRET_KEY') or 'my-secret-key'
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///myapp.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
