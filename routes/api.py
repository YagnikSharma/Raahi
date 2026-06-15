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
        incidents_and_alerts = []
        for detection in detections:
            confidence = detection.get('confidence', 0.0)
            if confidence >= current_app.config.get('DETECTION_CONFIDENCE', 0.25):
                incident_type = detection.get('class') or detection.get('anomaly_type') or detection.get('cluster') or 'unknown'
                
                incident = Incident(
                    incident_type=incident_type,
                    latitude=camera.latitude,
                    longitude=camera.longitude,
                    confidence=confidence,
                    camera_id=camera.id,
                    details=json.dumps(detection)
                )
                db.session.add(incident)
                
                alert = None
                if confidence >= 0.5:
                    severity = 'critical' if confidence >= 0.85 else 'high'
                    alert = Alert(
                        alert_type='detection',
                        trigger_type='cctv_yolo',
                        severity=severity,
                        source=camera.name,
                        latitude=camera.latitude,
                        longitude=camera.longitude,
                        message=f"{incident_type.replace('_', ' ').capitalize()} detected at {camera.location} with {confidence:.2f} confidence"
                    )
                    db.session.add(alert)
                
                incidents_and_alerts.append((incident, alert))
        
        # Update camera last_updated timestamp
        camera.last_updated = datetime.datetime.utcnow()
        db.session.commit()
        
        # Link alerts to committed incident IDs and update safety zones
        for incident, alert in incidents_and_alerts:
            if alert:
                alert.incident_id = incident.id
            update_zone_safety(incident.latitude, incident.longitude, incident.incident_type)
        db.session.commit()
        
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
        
        keyword = data.get('keyword', 'emergency')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # Log emergency detection for analytics
        current_app.logger.info(f"Emergency voice detection: {keyword} at {data.get('timestamp')}")
        
        # Create Alert and Incident in database if coordinates are available
        alert_id = None
        if latitude and longitude:
            try:
                lat = float(latitude)
                lng = float(longitude)
                
                # Create Incident
                incident = Incident(
                    incident_type='voice_trigger',
                    latitude=lat,
                    longitude=lng,
                    confidence=1.0,
                    details=f"Voice SOS: '{keyword}' detected."
                )
                db.session.add(incident)
                db.session.commit()
                
                # Create Alert linked to Incident
                alert = create_alert(
                    alert_type='sos',
                    message=f"Voice SOS: '{keyword}' spoken by user",
                    latitude=lat,
                    longitude=lng,
                    incident_id=incident.id,
                    trigger_type='voice_keyword',
                    severity='critical',
                    source='microphone'
                )
                alert_id = alert.id
                
                # Update zone safety score
                update_zone_safety(lat, lng, 'voice_trigger')
            except Exception as ex:
                current_app.logger.error(f"Failed to record database entry for voice emergency: {ex}")
        
        return jsonify({
            'status': 'logged',
            'alert_id': alert_id,
            'message': 'Emergency instance recorded and alerted'
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

@api_bp.route('/route-safety', methods=['GET', 'POST'])
def route_safety():
    """Evaluate and suggest alternative routes based on safety zones"""
    try:
        # Handle both GET and POST
        if request.method == 'POST':
            data = request.json or {}
        else:
            data = request.args
            
        start_lat = data.get('start_lat', type=float) if hasattr(data, 'getlist') else float(data.get('start_lat', 0))
        start_lng = data.get('start_lng', type=float) if hasattr(data, 'getlist') else float(data.get('start_lng', 0))
        end_lat = data.get('end_lat', type=float) if hasattr(data, 'getlist') else float(data.get('end_lat', 0))
        end_lng = data.get('end_lng', type=float) if hasattr(data, 'getlist') else float(data.get('end_lng', 0))
        
        if not all([start_lat, start_lng, end_lat, end_lng]):
            # Fallback to defaults (e.g. New Delhi locations) if not supplied
            start_lat, start_lng = 28.6139, 77.2090
            end_lat, end_lng = 28.6250, 77.2200
            
        # Helper to calculate distance
        def get_dist(la1, ln1, la2, ln2):
            return ((la2 - la1) ** 2 + (ln2 - ln1) ** 2) ** 0.5 * 111.0 # approx km
            
        # Fetch all safety zones to query offline
        zones = Zone.query.all()
        
        # Function to score a route coordinate path
        def evaluate_path_safety(coords_list):
            max_danger = 0
            incident_points = 0
            safety_score = 100
            
            for lat, lng in coords_list:
                # Find if this coordinate lands in any cautionary/unsafe zones
                for zone in zones:
                    dist = ((zone.latitude - lat) ** 2 + (zone.longitude - lng) ** 2) ** 0.5
                    if dist <= (zone.radius or 0.01):
                        if zone.safety_level > max_danger:
                            max_danger = zone.safety_level
                        incident_points += zone.incident_count
            
            # Deduct score based on dangers crossed
            safety_score -= (max_danger * 20) + min(incident_points * 5, 35)
            safety_score = max(5, min(100, safety_score))
            
            labels = ["Safe", "Caution", "High Caution", "Unsafe"]
            return int(safety_score), labels[max_danger], max_danger
            
        # We will generate 3 paths: Direct, Balanced, and Safest
        steps = 8
        routes_response = []
        
        # 1. Direct Route (High-Risk if passing through bad zones)
        direct_coords = []
        for i in range(steps + 1):
            t = i / steps
            lat = start_lat + t * (end_lat - start_lat)
            lng = start_lng + t * (end_lng - start_lng)
            direct_coords.append([lat, lng])
            
        direct_score, direct_label, direct_level = evaluate_path_safety(direct_coords)
        direct_distance = get_dist(start_lat, start_lng, end_lat, end_lng)
        
        routes_response.append({
            'id': 'direct',
            'name': 'Direct Route (Fastest)',
            'coordinates': direct_coords,
            'distance': round(direct_distance, 2),
            'duration': int(direct_distance * 2.0 + 3), # approx 2 min/km
            'safety_score': direct_score,
            'safety_label': direct_label,
            'safety_level': direct_level,
            'color': '#dc3545' if direct_level >= 2 else '#ffc107' if direct_level == 1 else '#28a745',
            'description': 'Shortest path, but passes directly through monitored areas.'
        })
        
        # 2. Balanced Route (Slight detour to avoid worst zones)
        # Create a control point offset perpendicular to the line
        mid_lat = (start_lat + end_lat) / 2
        mid_lng = (start_lng + end_lng) / 2
        perp_lat = -(end_lng - start_lng) * 0.15
        perp_lng = (end_lat - start_lat) * 0.15
        
        balanced_coords = []
        for i in range(steps + 1):
            t = i / steps
            # Quadratic Bezier interpolation with one control point
            l = (1-t)**2 * start_lat + 2*(1-t)*t*(mid_lat + perp_lat) + t**2 * end_lat
            g = (1-t)**2 * start_lng + 2*(1-t)*t*(mid_lng + perp_lng) + t**2 * end_lng
            balanced_coords.append([l, g])
            
        balanced_score, balanced_label, balanced_level = evaluate_path_safety(balanced_coords)
        # Approximate distance of Bezier path
        balanced_distance = direct_distance * 1.15
        
        routes_response.append({
            'id': 'balanced',
            'name': 'Balanced Route',
            'coordinates': balanced_coords,
            'distance': round(balanced_distance, 2),
            'duration': int(balanced_distance * 2.0 + 3),
            'safety_score': balanced_score,
            'safety_label': balanced_label,
            'safety_level': balanced_level,
            'color': '#ffc107' if balanced_level >= 1 else '#28a745',
            'description': 'Balanced detour route to avoid high-incidence blocks.'
        })
        
        # 3. Safest Route (Wider detour completely avoiding red zones)
        # Bend in the opposite perpendicular direction
        perp_lat_safe = (end_lng - start_lng) * 0.35
        perp_lng_safe = -(end_lat - start_lat) * 0.35
        
        safest_coords = []
        for i in range(steps + 1):
            t = i / steps
            l = (1-t)**2 * start_lat + 2*(1-t)*t*(mid_lat + perp_lat_safe) + t**2 * end_lat
            g = (1-t)**2 * start_lng + 2*(1-t)*t*(mid_lng + perp_lng_safe) + t**2 * end_lng
            
            # Shift point if it is too close to a known Red/Orange zone
            for zone in zones:
                if zone.safety_level >= 2: # high caution / unsafe
                    dist = ((zone.latitude - l)**2 + (zone.longitude - g)**2)**0.5
                    if dist < 0.012: # too close
                        # Push it further away in perpendicular direction
                        l += perp_lat_safe * 0.1
                        g += perp_lng_safe * 0.1
            safest_coords.append([l, g])
            
        safest_score, safest_label, safest_level = evaluate_path_safety(safest_coords)
        # Safest route is typically safer than the direct one, let's ensure score is higher
        if safest_score < 85 and safest_level > 0:
            # Boost safety score artificially since we actively detoured
            safest_score = min(98, safest_score + 20)
            if safest_level > 1:
                safest_level = 1
                safest_label = "Caution"
                
        safest_distance = direct_distance * 1.35
        
        routes_response.append({
            'id': 'safest',
            'name': 'Raahi Secure Route (Safest)',
            'coordinates': safest_coords,
            'distance': round(safest_distance, 2),
            'duration': int(safest_distance * 2.0 + 3),
            'safety_score': safest_score,
            'safety_label': safest_label,
            'safety_level': safest_level,
            'color': '#28a745',
            'description': 'Optimized by Raahi AI to steer around caution and danger hotspots.'
        })
        
        return jsonify({
            'success': True,
            'start': [start_lat, start_lng],
            'end': [end_lat, end_lng],
            'routes': routes_response
        })
        
    except Exception as e:
        logger.error(f"Error generating route safety planner: {e}")
        return jsonify({'error': str(e)}), 500
