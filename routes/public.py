from flask import Blueprint, render_template, current_app, redirect, url_for, request
from models import Zone, Incident, Camera
from utils import create_alert, update_zone_safety
from app import db
import datetime

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index():
    return render_template('index.html')

@public_bp.route('/map')
def map():
    # Get all safety zones for the map
    zones = Zone.query.all()
    
    # Get recent incidents (last 24 hours)
    recent_incidents = Incident.query.filter(
        Incident.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).order_by(Incident.timestamp.desc()).limit(10).all()
    
    return render_template(
        'public/map.html',
        zones=zones,
        incidents=recent_incidents,
        default_lat=current_app.config.get('DEFAULT_LAT'),
        default_lng=current_app.config.get('DEFAULT_LNG'),
        default_zoom=current_app.config.get('DEFAULT_ZOOM')
    )

@public_bp.route('/incidents')
def incidents():
    # Get all incidents with pagination
    page = request.args.get('page', 1, type=int)
    
    # Filter by incident type if provided
    incident_type = request.args.get('type')
    if incident_type:
        incidents_query = Incident.query.filter_by(incident_type=incident_type)
    else:
        incidents_query = Incident.query
    
    # Get the incidents, ordered by most recent first
    incidents = incidents_query.order_by(Incident.timestamp.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Get all unique incident types for the filter dropdown
    incident_types = db.session.query(Incident.incident_type).distinct().all()
    incident_types = [t[0] for t in incident_types]
    
    return render_template(
        'public/incidents.html',
        incidents=incidents,
        incident_types=incident_types,
        selected_type=incident_type
    )

@public_bp.route('/sos', methods=['POST'])
def sos():
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    message = request.form.get('message', 'Emergency SOS triggered')
    
    if latitude and longitude:
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            
            # Create alert
            alert = create_alert('sos', message, latitude, longitude)
            
            # Update zone to mark as unsafe
            zone = update_zone_safety(latitude, longitude)
            zone.safety_level = 3  # Force to unsafe (red)
            db.session.commit()
            
            return {'success': True, 'message': 'SOS alert sent successfully'}
        except Exception as e:
            return {'success': False, 'message': f'Error processing SOS: {str(e)}'}
    else:
        return {'success': False, 'message': 'Location information is required'}

@public_bp.route('/cameras')
def cameras():
    # Get all active cameras
    cameras = Camera.query.filter_by(status='active').all()
    return render_template('public/cameras.html', cameras=cameras)

@public_bp.route('/safety-info')
def safety_info():
    # Information about safety levels and what they mean
    return render_template('public/safety_info.html')

@public_bp.route('/about')
def about():
    # About page with information about Team Garun and the Raahi project
    return render_template('public/about.html')

@public_bp.route('/live-detection')
def live_detection():
    """Live CCTV detection page with real-time AI analysis"""
    return render_template('live_detection.html')
