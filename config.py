import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration for all environments."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # Database configuration with thread-safe pooling
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'soporte.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Default: SQLite options (no pooling needed for development)
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # email settings (console backend for development)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@localhost')
    
    # Security: Session & Cookie Configuration
    SESSION_COOKIE_SECURE = True      # Only send cookie over HTTPS
    SESSION_COOKIE_HTTPONLY = True    # No JavaScript access to cookie
    SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF protection
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes timeout
    
    # Security: Flask-Talisman Headers (CSP, X-Frame-Options, etc)
    TALISMAN_FORCE_HTTPS = False  # Set per environment
    TALISMAN_HSTS_MAX_AGE = 31536000  # 1 year in seconds
    TALISMAN_HSTS_INCLUDE_SUBDOMAINS = True
    TALISMAN_HSTS_PRELOAD = True
    TALISMAN_CONTENT_SECURITY_POLICY = {
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],  # Allow Bootstrap inline
        'style-src': ["'self'", "'unsafe-inline'", "fonts.googleapis.com"],
        'font-src': ["'self'", "fonts.gstatic.com"],
        'img-src': ["'self'", "data:"],
    }


class DevelopmentConfig(Config):
    """Development configuration - uses SQLite."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = False
    
    # SQLite doesn't need pool configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 15}
    }


class ProductionConfig(Config):
    """Production configuration - uses PostgreSQL."""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    
    # Security: Force HTTPS in production
    TALISMAN_FORCE_HTTPS = True
    SESSION_COOKIE_SECURE = True
    
    # In production, prefer PostgreSQL URL from env vars.
    # Render usually provides DATABASE_URL; some platforms use SQLALCHEMY_DATABASE_URI.
    # Fallback to SQLite only to avoid startup crash during initial setup.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or os.environ.get('SQLALCHEMY_DATABASE_URI')
        or 'sqlite:///' + os.path.join(basedir, 'instance', 'soporte.db')
    )
    
    # PostgreSQL connection pool configuration for production
    # NOTE: connect_args timeout is for SQLite only, not PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,              # Number of connections to maintain in pool
        'pool_recycle': 1800,         # Recycle connections after 30 minutes
        'pool_pre_ping': True,        # Test connection before reusing
        'max_overflow': 40,           # Additional connections allowed
    }


class TestingConfig(Config):
    """Testing configuration - uses in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    MAIL_SUPPRESS_SEND = True
    WTF_CSRF_ENABLED = False
    
    # In-memory SQLite for testing (no pooling needed)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 1}
    }

