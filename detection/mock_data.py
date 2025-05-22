import random
import datetime
from app import db
from models import Camera, Incident, Zone, Alert
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def create_mock_cameras(count=4):
    """Create mock CCTV cameras for demonstration purposes"""
    # Default location (New Delhi)
    default_lat = current_app.config.get('DEFAULT_LAT', 28.6139)
    default_lng = current_app.config.get('DEFAULT_LNG', 77.2090)
    
    # Create cameras only if none exist
    if Camera.query.count() == 0:
        logger.info(f"Creating {count} mock cameras")
        
        locations = [
            ("Main Street Junction", "Traffic intersection with high pedestrian activity"),
            ("Central Park", "Public recreation area with walking paths"),
            ("Metro Station", "Public transportation hub"),
            ("Shopping District", "Retail area with high foot traffic")
        ]
        
        for i in range(min(count, len(locations))):
            # Create cameras with slightly different locations
            lat_offset = random.uniform(-0.02, 0.02)
            lng_offset = random.uniform(-0.02, 0.02)
            
            camera = Camera(
                name=f"CCTV-{i+1}",
                location=locations[i][0],
                latitude=default_lat + lat_offset,
                longitude=default_lng + lng_offset,
                status="active",
                last_updated=datetime.datetime.utcnow()
            )
            
            db.session.add(camera)
        
        db.session.commit()
        logger.info(f"Created {count} mock cameras")
        
        return True
    
    return False

def create_mock_incidents(count=20):
    """Create mock incidents for demonstration purposes"""
    # Only create if very few incidents exist
    if Incident.query.count() < 5:
        logger.info(f"Creating {count} mock incidents")
        
        cameras = Camera.query.all()
        if not cameras:
            create_mock_cameras()
            cameras = Camera.query.all()
        
        incident_types = [
            "fire", "smoke", "fight", "weapon", "darkness", "suspicious_activity"
        ]
        
        # Create incidents over the past 7 days
        now = datetime.datetime.utcnow()
        
        for i in range(count):
            # Select a random camera
            camera = random.choice(cameras)
            
            # Create the incident with slightly randomized location
            lat_offset = random.uniform(-0.005, 0.005)
            lng_offset = random.uniform(-0.005, 0.005)
            
            # Random time in the past week
            hours_ago = random.randint(0, 168)  # 0-7 days
            timestamp = now - datetime.timedelta(hours=hours_ago)
            
            incident = Incident(
                incident_type=random.choice(incident_types),
                latitude=camera.latitude + lat_offset,
                longitude=camera.longitude + lng_offset,
                confidence=random.uniform(0.3, 0.95),
                timestamp=timestamp,
                is_verified=random.choice([True, False]),
                details="Mock incident for demonstration",
                camera_id=camera.id
            )
            
            db.session.add(incident)
        
        db.session.commit()
        logger.info(f"Created {count} mock incidents")
        
        # Now create safety zones based on these incidents
        create_mock_zones()
        
        return True
    
    return False

def create_mock_zones():
    """Create safety zones based on incident data"""
    logger.info("Creating mock safety zones")
    
    # Get all incidents
    incidents = Incident.query.all()
    
    # Create a grid of zones covering the incident areas
    grid = {}
    grid_size = current_app.config.get('MAP_GRID_SIZE', 0.01)
    
    for incident in incidents:
        # Round to grid
        lat_grid = round(incident.latitude / grid_size) * grid_size
        lng_grid = round(incident.longitude / grid_size) * grid_size
        
        # Create grid key
        key = f"{lat_grid},{lng_grid}"
        
        if key not in grid:
            grid[key] = {
                'latitude': lat_grid,
                'longitude': lng_grid,
                'count': 0,
                'incidents': []
            }
        
        grid[key]['count'] += 1
        grid[key]['incidents'].append(incident)
    
    # Create zone objects
    for key, data in grid.items():
        # Check if zone already exists
        zone = Zone.query.filter_by(
            latitude=data['latitude'],
            longitude=data['longitude']
        ).first()
        
        if not zone:
            zone = Zone(
                latitude=data['latitude'],
                longitude=data['longitude'],
                radius=grid_size,
                incident_count=data['count'],
                last_updated=datetime.datetime.utcnow()
            )
            db.session.add(zone)
        else:
            zone.incident_count = data['count']
            zone.last_updated = datetime.datetime.utcnow()
        
        # Set safety level based on incident count
        if data['count'] == 0:
            zone.safety_level = 0  # Safe
        elif data['count'] <= 2:
            zone.safety_level = 1  # Caution
        elif data['count'] <= 5:
            zone.safety_level = 2  # High Caution
        else:
            zone.safety_level = 3  # Unsafe
    
    db.session.commit()
    logger.info(f"Created safety zones for {len(grid)} grid areas")
    
    return True

def create_mock_alerts(count=10):
    """Create mock alerts for demonstration purposes"""
    if Alert.query.count() < 3:
        logger.info(f"Creating {count} mock alerts")
        
        alert_types = ["sos", "detection", "system"]
        alert_messages = [
            "SOS triggered by user",
            "Fire detected in camera view",
            "Smoke detected in camera view",
            "Fight detected in camera view",
            "Weapon detected in camera view",
            "Unusual activity detected",
            "System maintenance alert",
            "Camera offline",
            "Low lighting conditions detected"
        ]
        
        # Get incidents and cameras for reference
        incidents = Incident.query.all()
        cameras = Camera.query.all()
        
        for i in range(count):
            alert_type = random.choice(alert_types)
            message = random.choice(alert_messages)
            
            if alert_type == "sos" or alert_type == "detection":
                # Use incident or camera location
                if incidents and random.choice([True, False]):
                    incident = random.choice(incidents)
                    lat = incident.latitude
                    lng = incident.longitude
                    incident_id = incident.id
                elif cameras:
                    camera = random.choice(cameras)
                    lat = camera.latitude
                    lng = camera.longitude
                    incident_id = None
                else:
                    # Default location
                    lat = current_app.config.get('DEFAULT_LAT', 28.6139)
                    lng = current_app.config.get('DEFAULT_LNG', 77.2090)
                    incident_id = None
            else:
                # System alerts don't need location
                lat = None
                lng = None
                incident_id = None
            
            # Random time in the past week
            hours_ago = random.randint(0, 72)  # 0-3 days
            timestamp = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)
            
            alert = Alert(
                alert_type=alert_type,
                message=message,
                latitude=lat,
                longitude=lng,
                timestamp=timestamp,
                is_active=random.choice([True, False]),
                is_read=random.choice([True, False]),
                incident_id=incident_id
            )
            
            db.session.add(alert)
        
        db.session.commit()
        logger.info(f"Created {count} mock alerts")
        
        return True
    
    return False

def initialize_mock_data():
    """Initialize all mock data for demonstration"""
    logger.info("Initializing mock data for demonstration")
    create_mock_cameras()
    create_mock_incidents(20)
    create_mock_alerts(10)
    logger.info("Mock data initialization complete")
