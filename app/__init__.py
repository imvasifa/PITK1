import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from .filters import register_template_filters

# Configure logging
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize CSRF protection
csrf = CSRFProtect()

# Import license manager after db is initialized to avoid circular imports
from .licensing import license_manager, check_license_statuses

# Initialize migrate after db is created
migrate = Migrate()

def create_app(config_class='config'):
    """Create and configure the Flask application."""
    # Set the template and static folders to the root directories
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    app = Flask(__name__, 
               template_folder=template_dir,
               static_folder=static_dir)
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Load configuration
    if isinstance(config_class, str):
        app.config.from_object(config_class)
    else:
        # If it's a config class, initialize it and update config
        config = config_class()
        app.config.from_object(config)
    
    # Ensure secret key is set
    if 'SECRET_KEY' in os.environ:
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    
    # Ensure required config values are set
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'app.db')
    
    # Configure logging
    from .utils.logging import setup_logging
    setup_logging(app)
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Flask-Migrate after db is initialized
    migrate.init_app(app, db)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Import and register the user_loader
    from .auth import load_user
    login_manager.user_loader(load_user)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize database manager (for Redis)
    from .db_utils import Database
    db_manager = Database()
    db_manager.init_app(app)
    
    # Initialize license manager
    license_manager.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")
        
        # Test database connection
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
    
    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.admin import admin_bp
    from .routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register error handlers
    from .utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Register context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    # Register template filters
    register_template_filters(app)
    
    # Log application startup
    app.logger.info('Strong application startup')
    app.logger.info(f"Environment: {app.config.get('ENV', 'production')}")
    app.logger.info(f"Debug mode: {app.debug}")
    
    return app
