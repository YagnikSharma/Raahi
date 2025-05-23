"""
Comprehensive Mock Data Generator for Raahi Safety Platform
Generates realistic data for all database fields including cameras, incidents, zones, alerts, and users
"""

import random
import datetime
from app import app, db
from models import User, Camera, Incident, Zone, Alert
from werkzeug.security import generate_password_hash

def generate_comprehensive_mock_data():
    """Generate comprehensive mock data for all models"""
    with app.app_context():
        # Clear existing data
        print("🧹 Clearing existing data...")
        Alert.query.delete()
        Incident.query.delete()
        Camera.query.delete()
        Zone.query.delete()
        User.query.delete()
        
        # Generate Users (Admin accounts)
        print("👥 Creating admin users...")
        users = [
            {
                'username': 'admin',
                'email': 'admin@raahi.com',
                'password': 'admin123',
                'is_admin': True
            },
            {
                'username': 'safety_officer',
                'email': 'safety@raahi.com', 
                'password': 'safety123',
                'is_admin': True
            },
            {
                'username': 'operator1',
                'email': 'operator1@raahi.com',
                'password': 'operator123',
                'is_admin': True
            },
            {
                'username': 'emergency_coord',
                'email': 'emergency@raahi.com',
                'password': 'emergency123',
                'is_admin': True
            }
        ]
        
        created_users = []
        for user_data in users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                is_admin=user_data['is_admin'],
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 180)),
                last_login=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 7))
            )
            user.set_password(user_data['password'])
            created_users.append(user)
            db.session.add(user)
        
        db.session.commit()
        print(f"✅ Created {len(created_users)} admin users")
        
        # Generate CCTV Cameras with realistic locations
        print("📹 Creating CCTV cameras...")
        camera_locations = [
            {'name': 'Central Station - Main Entrance', 'location': 'New Delhi Railway Station, Platform 1', 'lat': 28.6434, 'lng': 77.2197},
            {'name': 'Metro Gate - Rajiv Chowk', 'location': 'Rajiv Chowk Metro Station, Connaught Place', 'lat': 28.6328, 'lng': 77.2197},
            {'name': 'Airport Terminal 3 - Departure', 'location': 'IGI Airport Terminal 3, Departure Gate', 'lat': 28.5562, 'lng': 77.1000},
            {'name': 'India Gate - Main Plaza', 'location': 'India Gate, Central Delhi', 'lat': 28.6129, 'lng': 77.2295},
            {'name': 'Red Fort - Entrance Gate', 'location': 'Red Fort, Chandni Chowk', 'lat': 28.6562, 'lng': 77.2410},
            {'name': 'Karol Bagh Market - Main Road', 'location': 'Karol Bagh Market, West Delhi', 'lat': 28.6519, 'lng': 77.1909},
            {'name': 'Nehru Place - Bus Terminal', 'location': 'Nehru Place Metro Station', 'lat': 28.5494, 'lng': 77.2519},
            {'name': 'Chandni Chowk - Market Area', 'location': 'Chandni Chowk Main Market', 'lat': 28.6506, 'lng': 77.2334},
            {'name': 'Khan Market - Central Plaza', 'location': 'Khan Market, Central Delhi', 'lat': 28.5984, 'lng': 77.2319},
            {'name': 'Lajpat Nagar - Market Junction', 'location': 'Lajpat Nagar Central Market', 'lat': 28.5653, 'lng': 77.2424}
        ]
        
        cameras = []
        statuses = ['active', 'active', 'active', 'inactive', 'maintenance']
        
        for cam_data in camera_locations:
            camera = Camera(
                name=cam_data['name'],
                location=cam_data['location'],
                latitude=cam_data['lat'],
                longitude=cam_data['lng'],
                status=random.choice(statuses),
                last_updated=datetime.datetime.utcnow() - datetime.timedelta(minutes=random.randint(1, 1440))
            )
            cameras.append(camera)
            db.session.add(camera)
        
        db.session.commit()
        print(f"✅ Created {len(cameras)} CCTV cameras")
        
        # Generate Safety Zones
        print("🛡️ Creating safety zones...")
        zone_locations = [
            {'lat': 28.6139, 'lng': 77.2090, 'safety_level': 0, 'details': 'Central Business District - Well patrolled area'},
            {'lat': 28.6328, 'lng': 77.2197, 'safety_level': 1, 'details': 'High traffic metro area - Exercise normal caution'},
            {'lat': 28.6562, 'lng': 77.2410, 'safety_level': 2, 'details': 'Tourist area - Pickpocketing incidents reported'},
            {'lat': 28.5494, 'lng': 77.2519, 'safety_level': 3, 'details': 'Market area - Multiple theft incidents'},
            {'lat': 28.6519, 'lng': 77.1909, 'safety_level': 1, 'details': 'Shopping district - Generally safe with crowds'},
            {'lat': 28.5653, 'lng': 77.2424, 'safety_level': 2, 'details': 'Market junction - Moderate safety concerns'},
            {'lat': 28.6129, 'lng': 77.2295, 'safety_level': 0, 'details': 'Monument area - High security presence'},
            {'lat': 28.5984, 'lng': 77.2319, 'safety_level': 1, 'details': 'Upscale market - Low crime rates'}
        ]
        
        zones = []
        for zone_data in zone_locations:
            zone = Zone(
                latitude=zone_data['lat'],
                longitude=zone_data['lng'],
                radius=random.uniform(0.005, 0.02),
                safety_level=zone_data['safety_level'],
                incident_count=random.randint(0, 8),
                last_updated=datetime.datetime.utcnow() - datetime.timedelta(hours=random.randint(1, 72)),
                details=zone_data['details']
            )
            zones.append(zone)
            db.session.add(zone)
        
        db.session.commit()
        print(f"✅ Created {len(zones)} safety zones")
        
        # Generate Realistic Incidents
        print("🚨 Creating incident reports...")
        incident_types = [
            'theft', 'assault', 'vandalism', 'suspicious_activity', 'fire', 
            'violence', 'explosion', 'robbery', 'harassment', 'drug_activity'
        ]
        
        incident_details = {
            'theft': ['Mobile phone snatching reported', 'Wallet stolen from pocket', 'Bag theft in crowded area'],
            'assault': ['Physical altercation between individuals', 'Harassment incident reported', 'Minor scuffle resolved'],
            'vandalism': ['Property damage to public infrastructure', 'Graffiti on walls', 'Damaged street furniture'],
            'suspicious_activity': ['Unattended bag reported', 'Individual loitering reported', 'Unusual behavior observed'],
            'fire': ['Small fire extinguished quickly', 'Smoke detected in building', 'Fire alarm activated'],
            'violence': ['Fight between groups', 'Domestic dispute in public', 'Aggressive behavior reported'],
            'explosion': ['Loud bang investigated - fireworks', 'Small blast from vehicle backfire', 'Construction blast nearby'],
            'robbery': ['Store robbery attempt', 'ATM robbery reported', 'Street robbery incident'],
            'harassment': ['Verbal harassment complaint', 'Inappropriate behavior reported', 'Harassment in public transport'],
            'drug_activity': ['Suspected drug dealing', 'Drug paraphernalia found', 'Substance abuse incident']
        }
        
        incidents = []
        for i in range(35):  # Generate 35 incidents
            incident_type = random.choice(incident_types)
            camera = random.choice(cameras) if random.random() > 0.3 else None
            verified_by = random.choice(created_users) if random.random() > 0.4 else None
            
            # Use camera location if available, otherwise random location near Delhi
            if camera:
                lat = camera.latitude + random.uniform(-0.01, 0.01)
                lng = camera.longitude + random.uniform(-0.01, 0.01)
            else:
                lat = 28.6139 + random.uniform(-0.1, 0.1)
                lng = 77.2090 + random.uniform(-0.1, 0.1)
            
            incident = Incident(
                incident_type=incident_type,
                latitude=lat,
                longitude=lng,
                confidence=random.uniform(0.6, 0.95),
                timestamp=datetime.datetime.utcnow() - datetime.timedelta(hours=random.randint(1, 168)),
                is_verified=random.random() > 0.3,
                details=random.choice(incident_details.get(incident_type, ['Incident reported'])),
                camera_id=camera.id if camera else None,
                verified_by=verified_by.id if verified_by else None
            )
            incidents.append(incident)
            db.session.add(incident)
        
        db.session.commit()
        print(f"✅ Created {len(incidents)} incident reports")
        
        # Generate Alerts (SOS, system alerts, detection alerts)
        print("🔔 Creating alert notifications...")
        alert_types = ['sos', 'system', 'detection']
        alert_messages = {
            'sos': [
                'Emergency SOS triggered by user',
                'Help requested - immediate assistance needed',
                'User reported feeling unsafe',
                'Emergency contact activated'
            ],
            'system': [
                'CCTV camera offline - maintenance required',
                'High incident rate detected in area',
                'System maintenance scheduled',
                'New safety zone created'
            ],
            'detection': [
                'AI detected suspicious activity',
                'Automated threat detection activated',
                'Unusual crowd behavior detected',
                'AI flagged potential safety concern'
            ]
        }
        
        alerts = []
        for i in range(25):  # Generate 25 alerts
            alert_type = random.choice(alert_types)
            incident = random.choice(incidents) if random.random() > 0.6 else None
            user = random.choice(created_users) if random.random() > 0.5 else None
            
            # Use incident location if available
            if incident:
                lat, lng = incident.latitude, incident.longitude
            else:
                lat = 28.6139 + random.uniform(-0.1, 0.1)
                lng = 77.2090 + random.uniform(-0.1, 0.1)
            
            alert = Alert(
                alert_type=alert_type,
                latitude=lat if random.random() > 0.2 else None,
                longitude=lng if random.random() > 0.2 else None,
                message=random.choice(alert_messages[alert_type]),
                timestamp=datetime.datetime.utcnow() - datetime.timedelta(hours=random.randint(1, 48)),
                is_active=random.random() > 0.3,
                is_read=random.random() > 0.4,
                user_id=user.id if user else None,
                incident_id=incident.id if incident else None
            )
            alerts.append(alert)
            db.session.add(alert)
        
        db.session.commit()
        print(f"✅ Created {len(alerts)} alert notifications")
        
        # Update zone incident counts based on actual incidents
        print("📊 Updating zone statistics...")
        for zone in zones:
            nearby_incidents = Incident.query.filter(
                Incident.latitude.between(zone.latitude - zone.radius, zone.latitude + zone.radius),
                Incident.longitude.between(zone.longitude - zone.radius, zone.longitude + zone.radius)
            ).count()
            zone.incident_count = nearby_incidents
            
            # Update safety level based on incident count
            if nearby_incidents == 0:
                zone.safety_level = 0
            elif nearby_incidents <= 2:
                zone.safety_level = 1
            elif nearby_incidents <= 5:
                zone.safety_level = 2
            else:
                zone.safety_level = 3
        
        db.session.commit()
        
        print("\n🎉 Comprehensive mock data generation completed!")
        print(f"📊 Generated:")
        print(f"   👥 {len(created_users)} admin users")
        print(f"   📹 {len(cameras)} CCTV cameras")
        print(f"   🛡️ {len(zones)} safety zones")
        print(f"   🚨 {len(incidents)} incident reports")
        print(f"   🔔 {len(alerts)} alert notifications")
        print("\n✨ Your Raahi safety platform is now fully populated with realistic data!")

if __name__ == "__main__":
    generate_comprehensive_mock_data()