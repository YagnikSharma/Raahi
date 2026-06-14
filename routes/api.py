from flask import Blueprint, jsonify, request, current_app
from models import Zone, Incident, Camera, Alert
from app import db
import datetime
from utils import update_zone_safety, create_alert
from detection.yolo import detect_objects
from flask_jwt_extended import jwt_required
import json
import base64
import os
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/heatmap', methods=['GET'])
def get_heatmap():
    """Public API endpoint for fetching safety zone data for the heatmap"""
    zones = Zone.query.all()
    
    zone_data = []
    for zone in zones:
        zone_data.append({
            'id': zone.id,
            'latitude': zone.latitude,
            'longitude': zone.longitude,
            'radius': zone.radius,
            'safety_level': zone.safety_level,
            'incident_count': zone.incident_count,
            'color': zone.color,
            'last_updated': zone.last_updated.isoformat() if zone.last_updated else None
        })
    
    return jsonify(zone_data)

@api_bp.route('/incidents', methods=['GET'])
def get_incidents():
    """Public API endpoint for fetching recent incidents"""
    # Parse filters
    hours = request.args.get('hours', 24, type=int)
    incident_type = request.args.get('type')
    limit = request.args.get('limit', 100, type=int)
    
    # Base query
    query = Incident.query.filter(
        Incident.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    )
    
    # Apply type filter if provided
    if incident_type:
        query = query.filter_by(incident_type=incident_type)
    
    # Get results
    incidents = query.order_by(Incident.timestamp.desc()).limit(limit).all()
    
    incident_data = []
    for incident in incidents:
        incident_data.append({
            'id': incident.id,
            'type': incident.incident_type,
            'latitude': incident.latitude,
            'longitude': incident.longitude,
            'confidence': incident.confidence,
            'timestamp': incident.timestamp.isoformat(),
            'is_verified': incident.is_verified
        })
    
    return jsonify(incident_data)

@api_bp.route('/safety/<float:lat>/<float:lng>', methods=['GET'])
def get_safety(lat, lng):
    """Public API endpoint for getting safety information for a specific location"""
    # Find nearby zones
    radius = current_app.config.get('MAP_GRID_SIZE', 0.01)
    zones = Zone.query.filter(
        Zone.latitude >= lat - radius,
        Zone.latitude <= lat + radius,
        Zone.longitude >= lng - radius,
        Zone.longitude <= lng + radius
    ).all()
    
    # If no zones found, create a new one with default safety level
    if not zones:
        zone = update_zone_safety(lat, lng)
        zones = [zone]
    
    # Find the worst safety level of nearby zones
    worst_safety = 0
    nearest_zone = None
    min_distance = float('inf')
    
    for zone in zones:
        # Calculate distance to determine nearest zone
        distance = ((zone.latitude - lat) ** 2 + (zone.longitude - lng) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest_zone = zone
        
        # Track worst safety level
        if zone.safety_level > worst_safety:
            worst_safety = zone.safety_level
    
    safety_labels = ["Safe", "Caution", "High Caution", "Unsafe"]
    
    response = {
        'latitude': lat,
        'longitude': lng,
        'safety_level': worst_safety,
        'safety_label': safety_labels[worst_safety],
        'color': nearest_zone.color if nearest_zone else "#28a745",
        'nearest_zone_id': nearest_zone.id if nearest_zone else None,
        'incident_count': nearest_zone.incident_count if nearest_zone else 0
    }
    
    return jsonify(response)

@api_bp.route('/cameras', methods=['GET'])
def get_cameras():
    """Public API endpoint for getting camera information"""
    cameras = Camera.query.filter_by(status='active').all()
    
    camera_data = []
    for camera in cameras:
        camera_data.append({
            'id': camera.id,
            'name': camera.name,
            'location': camera.location,
            'latitude': camera.latitude,
            'longitude': camera.longitude,
            'status': camera.status,
            'last_updated': camera.last_updated.isoformat() if camera.last_updated else None
        })
    
    return jsonify(camera_data)

@api_bp.route('/detect', methods=['POST'])
def detect():
    """API endpoint for processing image data from cameras"""
    try:
        # Handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            data = request.json
        else:
            data = request.form.to_dict()
            
        if not data or 'image' not in data or 'camera_id' not in data:
            return jsonify({'error': 'Missing required data'}), 400
        
        # Get camera information
        camera_id = data.get('camera_id')
        camera = Camera.query.get(camera_id)
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404
        
        # Process the image
        image_data = data.get('image')
        # Remove 'data:image/jpeg;base64,' prefix if it exists
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            return jsonify({'error': f'Invalid image data: {str(e)}'}), 400
        
        # Detect objects in the image
        detections = detect_objects(image_bytes)
        
        # Process detections
        incidents = []
        for detection in detections:
            if detection['confidence'] >= current_app.config.get('DETECTION_CONFIDENCE', 0.25):
                # Create incident record
                incident = Incident(
                    incident_type=detection['class'],
                    latitude=camera.latitude,
                    longitude=camera.longitude,
                    confidence=detection['confidence'],
                    camera_id=camera.id,
                    details=json.dumps(detection)
                )
                db.session.add(incident)
                incidents.append(incident)
                
                # Create alert for high confidence detections
                if detection['confidence'] >= 0.5:
                    create_alert(
                        'detection',
                        f"{detection['class']} detected at {camera.location} with {detection['confidence']:.2f} confidence",
                        camera.latitude,
                        camera.longitude,
                        None  # Will be updated after incident is committed
                    )
        
        # Update camera last_updated timestamp
        camera.last_updated = datetime.datetime.utcnow()
        db.session.commit()
        
        # Update related alerts with incident IDs
        for incident in incidents:
            # Update zone safety level
            update_zone_safety(incident.latitude, incident.longitude, incident.incident_type)
        
        return jsonify({
            'success': True,
            'detections': len(detections),
            'incidents_created': len(incidents)
        })
    except Exception as e:
        logger.error(f"Error in detection API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/sos', methods=['POST'])
def sos_api():
    """API endpoint for SOS triggers"""
    try:
        data = request.json
        if not data or 'latitude' not in data or 'longitude' not in data:
            return jsonify({'error': 'Missing location data'}), 400
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        message = data.get('message', 'Emergency SOS triggered')
        
        # Create alert
        alert = create_alert('sos', message, latitude, longitude)
        
        # Update zone to mark as unsafe
        zone = update_zone_safety(latitude, longitude)
        zone.safety_level = 3  # Force to unsafe (red)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'alert_id': alert.id,
            'message': 'SOS alert created successfully'
        })
    except Exception as e:
        logger.error(f"Error in SOS API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/emergency-log', methods=['POST'])
def emergency_log():
    """API endpoint for logging emergency voice detections"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Log emergency detection for analytics
        current_app.logger.info(f"Emergency voice detection: {data.get('keyword')} at {data.get('timestamp')}")
        
        return jsonify({
            'status': 'logged',
            'message': 'Emergency instance recorded'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging emergency: {e}")
        return jsonify({'error': 'Logging failed'}), 500

@api_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    """API endpoint for getting alerts (requires authentication)"""
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    alert_type = request.args.get('type')
    limit = request.args.get('limit', 100, type=int)
    
    # Base query
    query = Alert.query
    
    # Apply filters
    if unread_only:
        query = query.filter_by(is_read=False)
    
    if alert_type:
        query = query.filter_by(alert_type=alert_type)
    
    # Get results
    alerts = query.order_by(Alert.timestamp.desc()).limit(limit).all()
    
    alert_data = []
    for alert in alerts:
        alert_data.append({
            'id': alert.id,
            'type': alert.alert_type,
            'message': alert.message,
            'latitude': alert.latitude,
            'longitude': alert.longitude,
            'timestamp': alert.timestamp.isoformat(),
            'is_read': alert.is_read,
            'is_active': alert.is_active,
            'incident_id': alert.incident_id
        })
    
    return jsonify(alert_data)
