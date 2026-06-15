import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    """Admin user model for the Raahi platform"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)
    reset_token = db.Column(db.String(100))
    reset_token_expiry = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Camera(db.Model):
    """CCTV camera model with location and status information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="active")  # active, inactive, maintenance
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    incidents = db.relationship('Incident', backref='camera', lazy=True)
    
    def __repr__(self):
        return f'<Camera {self.name} at {self.location}>'

class Incident(db.Model):
    """Model to store detected safety incidents"""
    id = db.Column(db.Integer, primary_key=True)
    incident_type = db.Column(db.String(50), nullable=False)  # fire, explosion, assault, etc.
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, default=0.0)  # Detection confidence score
    image_path = db.Column(db.String(200))  # Path to stored image if available
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)  # Admin verified flag
    details = db.Column(db.Text)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    def __repr__(self):
        return f'<Incident {self.incident_type} at {self.timestamp}>'

class Zone(db.Model):
    """Safety zone model with classification"""
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Float, default=0.01)  # Zone radius in degrees
    safety_level = db.Column(db.Integer, default=0)  # 0=safe, 1=caution, 2=high caution, 3=unsafe
    incident_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    details = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Zone at ({self.latitude},{self.longitude}) - Level {self.safety_level}>'
    
    @property
    def color(self):
        """Returns the color code based on safety level"""
        colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]  # green, yellow, orange, red
        return colors[min(self.safety_level, 3)]

class Alert(db.Model):
    """SOS and system alerts model"""
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)  # sos, system, detection
    trigger_type = db.Column(db.String(50), default="manual")  # sos_button, voice_keyword, cctv_yolo, offline_video, manual
    severity = db.Column(db.String(20), default="medium")  # low, medium, high, critical
    source = db.Column(db.String(100), default="system")  # cctv name, video file name, system
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # User who marked as read/resolved
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=True)  # Related incident if any
    
    def __repr__(self):
        return f'<Alert {self.alert_type} ({self.trigger_type}) at {self.timestamp}>'
