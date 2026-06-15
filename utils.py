import os
import secrets
import datetime
import logging
from flask import current_app
from flask_mail import Message
from app import mail, db
from models import User, Zone, Incident, Alert

logger = logging.getLogger(__name__)

def generate_token(length=32):
    """Generate a secure random token for password reset"""
    return secrets.token_hex(length)

def send_password_reset_email(user):
    """Send password reset email to user"""
    token = generate_token()
    user.reset_token = token
    user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    db.session.commit()
    
    reset_url = f"http://localhost:5000/admin/reset-password/{token}"
    
    try:
        msg = Message(
            subject="Raahi - Password Reset Request",
            recipients=[user.email],
            body=f"Click the link to reset your password: {reset_url}\nThis link will expire in 1 hour.",
            html=f"<p>Click the link to reset your password:</p><p><a href='{reset_url}'>Reset Password</a></p><p>This link will expire in 1 hour.</p>"
        )
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return False

def update_zone_safety(latitude, longitude, incident_type=None):
    """Update safety level of a zone based on incident count"""
    # Find or create the zone
    zone = Zone.query.filter(
        Zone.latitude >= latitude - 0.01,
        Zone.latitude <= latitude + 0.01,
        Zone.longitude >= longitude - 0.01,
        Zone.longitude <= longitude + 0.01
    ).first()
    
    if not zone:
        zone = Zone(
            latitude=round(latitude * 100) / 100,  # Round to grid
            longitude=round(longitude * 100) / 100,
            safety_level=0,
            incident_count=0
        )
        db.session.add(zone)
    
    # Ensure zone has a radius value
    if zone.radius is None:
        zone.radius = 0.01
    
    # Get the number of incidents in the zone in the last 24 hours
    recent_incidents = Incident.query.filter(
        Incident.latitude >= zone.latitude - zone.radius,
        Incident.latitude <= zone.latitude + zone.radius,
        Incident.longitude >= zone.longitude - zone.radius,
        Incident.longitude <= zone.longitude + zone.radius,
        Incident.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).count()
    
    zone.incident_count = recent_incidents
    
    # Update safety level based on incident count
    if recent_incidents == 0:
        zone.safety_level = 0  # Safe - Green
    elif recent_incidents <= 2:
        zone.safety_level = 1  # Caution - Yellow
    elif recent_incidents <= 5:
        zone.safety_level = 2  # High Caution - Orange
    else:
        zone.safety_level = 3  # Unsafe - Red
    
    zone.last_updated = datetime.datetime.utcnow()
    db.session.commit()
    
    return zone

def create_alert(alert_type, message, latitude=None, longitude=None, incident_id=None, trigger_type='manual', severity='medium', source='system'):
    """Create a new alert in the system"""
    alert = Alert(
        alert_type=alert_type,
        trigger_type=trigger_type,
        severity=severity,
        source=source,
        latitude=latitude,
        longitude=longitude,
        incident_id=incident_id,
        message=message
    )
    db.session.add(alert)
    db.session.commit()
    
    logger.info(f"New alert created: {alert_type} ({trigger_type}) - {message}")
    return alert

def initialize_admin_user():
    """Initialize the default admin user if none exists"""
    from models import User
    from app import db
    
    # Set up your specific admin account
    admin_email = 'yagniksharma47@gmail.com'
    admin_username = 'yagniksharma47'
    admin_password = 'ynk@123'
    
    if User.query.filter_by(email=admin_email).first() is None:
        admin = User(
            username=admin_username,
            email=admin_email,
            is_admin=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        logger.info(f"Primary admin user created: {admin_email}")

def send_admin_confirmation_email(new_admin_email, admin_name):
    """Send email to primary admin for new admin account confirmation"""
    from flask_mail import Message
    from app import mail
    
    try:
        msg = Message(
            'New Admin Account Request - Raahi Safety Platform',
            recipients=['yagniksharma47@gmail.com'],
            sender='noreply@raahi.com'
        )
        
        msg.body = f"""
        New Admin Account Request
        
        A new admin account has been requested for the Raahi Safety Platform:
        
        Email: {new_admin_email}
        Name: {admin_name}
        Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
        
        Please review and approve this request in the admin dashboard.
        
        Best regards,
        Raahi Safety Platform
        Team Garun
        """
        
        mail.send(msg)
        logger.info(f"Admin confirmation email sent for: {new_admin_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send admin confirmation email: {str(e)}")
        return False
