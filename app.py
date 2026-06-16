import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()
jwt = JWTManager()

# Create Flask application
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Load configuration
app.config.from_object('config.Config')

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
mail.init_app(app)
jwt.init_app(app)

# Create database tables
with app.app_context():
    from models import User, Incident, Zone, Alert, Camera
    from utils import initialize_admin_user
    db.create_all()
    logger.debug("Database tables created")
    
    # Initialize your admin account
    initialize_admin_user()
    
    # Initialize mock data for demonstration
    try:
        from detection.mock_data import initialize_mock_data
        initialize_mock_data()
        logger.debug("Mock data initialized")
    except Exception as e:
        logger.error(f"Error seeding mock data: {e}")
    
    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.public import public_bp
    from routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp)
    
    logger.debug("Blueprints registered")

# Context processor to inject JWT token for authenticated admins
@app.context_processor
def inject_jwt_token():
    from flask import session
    from flask_login import current_user
    from flask_jwt_extended import create_access_token
    if current_user and current_user.is_authenticated:
        token = session.get('jwt_token')
        if not token:
            try:
                token = create_access_token(identity=str(current_user.id))
                session['jwt_token'] = token
            except Exception as e:
                logger.error(f"Error creating JWT token: {e}")
                token = ""
        return {'jwt_token': token}
    return {'jwt_token': ''}

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Helper routes to serve uploads and processed files on serverless Vercel from /tmp
@app.route('/static/processed/<path:filename>')
def serve_processed(filename):
    from flask import send_from_directory
    tmp_processed = '/tmp/processed'
    if os.path.exists(os.path.join(tmp_processed, filename)):
        return send_from_directory(tmp_processed, filename)
    return send_from_directory(os.path.join(app.static_folder, 'processed'), filename)

@app.route('/static/uploads/<path:filename>')
def serve_uploads(filename):
    from flask import send_from_directory
    tmp_uploads = '/tmp/uploads'
    if os.path.exists(os.path.join(tmp_uploads, filename)):
        return send_from_directory(tmp_uploads, filename)
    return send_from_directory(os.path.join(app.static_folder, 'uploads'), filename)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    from flask import render_template
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    from flask import render_template
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500
