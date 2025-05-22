import os
from datetime import timedelta

class Config:
    # Flask configuration
    DEBUG = True
    SECRET_KEY = os.environ.get("SESSION_SECRET", "dev-secret-key")
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///raahi.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Mail configuration for password reset
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@raahi.com')
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Application specific configuration
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@raahi.com')
    DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
    
    # Mock CCTV configuration
    MOCK_CCTV_CAMERAS = 4
    CCTV_UPDATE_INTERVAL = 5  # seconds
    
    # YOLO model configuration
    YOLO_MODEL_PATH = "detection/models/yolov8n.pt"
    DETECTION_CONFIDENCE = 0.25
    
    # Safety zones configuration
    DEFAULT_LAT = 28.6139  # New Delhi
    DEFAULT_LNG = 77.2090
    DEFAULT_ZOOM = 13
    MAP_GRID_SIZE = 0.01  # grid size in degrees for safety zones
