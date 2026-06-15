import unittest
import json
import os
import sys

# Add root folder to sys path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, Camera, Incident, Zone, Alert

class RaahiTestCase(unittest.TestCase):
    def setUp(self):
        """Set up testing environment with an in-memory SQLite database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
        
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        
        db.create_all()
        
        # Seed test camera
        self.camera = Camera(
            name="Test-CCTV-1",
            location="Test Junction",
            latitude=28.6139,
            longitude=77.2090,
            status="active"
        )
        db.session.add(self.camera)
        
        # Seed test admin user
        self.admin_user = User(
            username="admin",
            email="admin@example.com",
            is_admin=True
        )
        self.admin_user.set_password("admin_password")
        db.session.add(self.admin_user)
        
        db.session.commit()
        
    def tearDown(self):
        """Tear down test database"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        
    def login_admin(self):
        """Helper to log in as admin user"""
        return self.client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin_password'
        }, follow_redirects=True)
        
    def test_database_camera_setup(self):
        """Verify database starts with our seeded camera"""
        cameras = Camera.query.all()
        self.assertEqual(len(cameras), 1)
        self.assertEqual(cameras[0].name, "Test-CCTV-1")
        
    def test_route_safety_planner_endpoint(self):
        """Verify route safety planner returns three distinct paths with safety scores"""
        response = self.client.get('/api/route-safety?start_lat=28.6139&start_lng=77.2090&end_lat=28.6200&end_lng=77.2150')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['routes']), 3)
        
        # Verify route types are present
        route_ids = [r['id'] for r in data['routes']]
        self.assertIn('direct', route_ids)
        self.assertIn('balanced', route_ids)
        self.assertIn('safest', route_ids)
        
        # Verify safety scores are within bounds
        for route in data['routes']:
            self.assertTrue(0 <= route['safety_score'] <= 100)
            self.assertIn('distance', route)
            self.assertIn('duration', route)
            
    def test_voice_emergency_log_saves_to_db(self):
        """Verify that hitting the voice emergency endpoint creates database Incident and Alert logs"""
        payload = {
            'keyword': 'help me',
            'latitude': 28.6139,
            'longitude': 77.2090,
            'timestamp': '2026-06-15T22:00:00Z'
        }
        
        response = self.client.post(
            '/api/emergency-log',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'logged')
        self.assertIsNotNone(data['alert_id'])
        
        # Check that Incident and Alert are added to database
        incidents = Incident.query.filter_by(incident_type='voice_trigger').all()
        self.assertEqual(len(incidents), 1)
        self.assertIn("Voice SOS: 'help me' detected.", incidents[0].details)
        
        alerts = Alert.query.filter_by(trigger_type='voice_keyword').all()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].severity, 'critical')
        
    def test_jwt_alerts_unauthenticated(self):
        """Verify that accessing the alerts endpoint without a valid JWT token returns unauthorized"""
        response = self.client.get('/api/alerts?unread=true')
        self.assertEqual(response.status_code, 401) # Unauthorized

    def test_jwt_alerts_authenticated(self):
        """Verify that accessing the alerts endpoint with a valid JWT token returns alerts"""
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=str(self.admin_user.id))
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # Add a dummy alert
        alert = Alert(
            alert_type="sos",
            trigger_type="manual",
            severity="medium",
            message="Test alert",
            is_read=False
        )
        db.session.add(alert)
        db.session.commit()
        
        response = self.client.get('/api/alerts?unread=true', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['message'], "Test alert")

    def test_cctv_analysis_status(self):
        """Verify that the cctv-analysis status endpoint returns the processing state structure"""
        self.login_admin()
        response = self.client.get('/admin/cctv-analysis/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('is_processing', data)
        self.assertIn('progress', data)
        self.assertIn('results', data)

if __name__ == '__main__':
    unittest.main()
