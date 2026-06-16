import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from models import User, Incident, Zone, Alert, Camera
from utils import create_alert

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Check if user is admin for all admin_bp routes
@admin_bp.before_request
@login_required
def check_admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('public.index'))

@admin_bp.route('/')
def dashboard():
    # Get statistics for dashboard
    total_incidents = Incident.query.count()
    recent_incidents = Incident.query.filter(
        Incident.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).count()
    
    cameras = Camera.query.all()
    active_cameras = Camera.query.filter_by(status='active').count()
    
    zones = Zone.query.all()
    unsafe_zones = Zone.query.filter(Zone.safety_level >= 2).count()
    
    unread_alerts = Alert.query.filter_by(is_read=False).count()
    
    return render_template(
        'admin/dashboard.html',
        total_incidents=total_incidents,
        recent_incidents=recent_incidents,
        cameras=cameras,
        active_cameras=active_cameras,
        total_cameras=len(cameras),
        zones=zones,
        unsafe_zones=unsafe_zones,
        unread_alerts=unread_alerts
    )

@admin_bp.route('/incidents')
def incidents():
    # Get all incidents with pagination
    page = request.args.get('page', 1, type=int)
    incidents = Incident.query.order_by(Incident.timestamp.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/incidents.html', incidents=incidents)

@admin_bp.route('/incident/<int:incident_id>', methods=['GET', 'POST'])
def incident_detail(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'verify':
            incident.is_verified = True
            incident.verified_by = current_user.id
            db.session.commit()
            flash('Incident verified.', 'success')
        elif action == 'delete':
            db.session.delete(incident)
            db.session.commit()
            flash('Incident deleted.', 'success')
            return redirect(url_for('admin.incidents'))
    
    return render_template('admin/incident_detail.html', incident=incident)

@admin_bp.route('/alerts')
def alerts():
    # Get all alerts with pagination
    page = request.args.get('page', 1, type=int)
    alerts = Alert.query.order_by(Alert.timestamp.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/alerts.html', alerts=alerts)

@admin_bp.route('/alert/<int:alert_id>/mark-read', methods=['POST'])
def mark_alert_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    alert.user_id = current_user.id
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/cameras')
def cameras():
    cameras = Camera.query.all()
    return render_template('admin/cameras.html', cameras=cameras)

@admin_bp.route('/camera/<int:camera_id>', methods=['GET', 'POST'])
def camera_detail(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'status_update':
            camera.status = request.form.get('status')
            db.session.commit()
            flash(f'Camera status updated to {camera.status}.', 'success')
    
    # Get recent incidents from this camera
    incidents = Incident.query.filter_by(camera_id=camera.id).order_by(Incident.timestamp.desc()).limit(5).all()
    
    return render_template('admin/camera_detail.html', camera=camera, incidents=incidents)

@admin_bp.route('/map')
def map():
    zones = Zone.query.all()
    incidents = Incident.query.order_by(Incident.timestamp.desc()).limit(100).all()
    cameras = Camera.query.all()
    
    return render_template(
        'admin/map.html', 
        zones=zones, 
        incidents=incidents, 
        cameras=cameras,
        default_lat=current_app.config.get('DEFAULT_LAT'),
        default_lng=current_app.config.get('DEFAULT_LNG'),
        default_zoom=current_app.config.get('DEFAULT_ZOOM')
    )

@admin_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Update username
        if username and username != current_user.username:
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
            else:
                current_user.username = username
                db.session.commit()
                flash('Username updated successfully.', 'success')
        
        # Update password
        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully.', 'success')
    
    return render_template('admin/profile.html')

# CCTV Video Hub processing imports
import os
import threading
import shutil
import random
from werkzeug.utils import secure_filename

# Global processing status
video_processing_status = {
    'is_processing': False,
    'progress': 0,
    'current_video': None,
    'results': None,
    'error': None
}

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def update_progress(progress):
    video_processing_status['progress'] = int(progress)

def process_video_async(flask_app, video_path, model_path=None):
    global video_processing_status
    
    with flask_app.app_context():
        try:
            video_processing_status['is_processing'] = True
            video_processing_status['progress'] = 0
            video_processing_status['error'] = None
            
            # Create directories under static
            uploads_dir = os.path.join(flask_app.static_folder, 'uploads')
            processed_dir = os.path.join(flask_app.static_folder, 'processed')
            os.makedirs(uploads_dir, exist_ok=True)
            os.makedirs(processed_dir, exist_ok=True)
            
            # Initialize detector
            from anomaly_detector import AnomalyDetector
            detector = AnomalyDetector(model_path=model_path or 'best.pt')
            
            # Process video
            results = detector.process_video(video_path, progress_callback=update_progress)
            
            # Initialize heatmap generator
            from heatmap_generator import HeatmapGenerator
            heatmap_gen = HeatmapGenerator()
            
            # Get video dimensions
            cap = cv2.VideoCapture(video_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            video_filename = os.path.basename(video_path)
            
            # Generate heatmaps in root, then move them
            heatmap_path, detection_count = heatmap_gen.generate_heatmap(
                video_name=video_filename,
                video_width=width,
                video_height=height
            )
            
            class_heatmaps = heatmap_gen.generate_class_heatmaps(
                video_name=video_filename,
                video_width=width,
                video_height=height
            )
            
            summary = heatmap_gen.get_detection_summary(video_filename)
            
            # Move generated outputs to static/processed folder
            safe_video_name = video_filename.rsplit('.', 1)[0]
            
            target_video = f"processed_{video_filename}"
            target_video_path = os.path.join(processed_dir, target_video)
            if os.path.exists('output.mp4'):
                shutil.move('output.mp4', target_video_path)
                
            target_heatmap = f"heatmap_{safe_video_name}.png"
            target_heatmap_path = os.path.join(processed_dir, target_heatmap)
            if os.path.exists('heatmap.png'):
                shutil.move('heatmap.png', target_heatmap_path)
                
            processed_class_heatmaps = {}
            for class_name, temp_path in class_heatmaps.items():
                if os.path.exists(temp_path):
                    target_ch = f"heatmap_{safe_video_name}_{class_name}.png"
                    shutil.move(temp_path, os.path.join(processed_dir, target_ch))
                    processed_class_heatmaps[class_name] = f"processed/{target_ch}"
            
            # Create Mock Incidents & Alerts in safety database
            camera = Camera.query.first()
            if not camera:
                # Create default camera if none exists
                default_lat = current_app.config.get('DEFAULT_LAT', 28.6139)
                default_lng = current_app.config.get('DEFAULT_LNG', 77.2090)
                camera = Camera(
                    name="CCTV-1",
                    location="Main Boulevard Intersection",
                    latitude=default_lat,
                    longitude=default_lng,
                    status="active"
                )
                db.session.add(camera)
                db.session.commit()
                
            # Log incidents to the DB to dynamically populate the citizen maps
            for anomaly_type, count in summary.items():
                if count > 0:
                    for _ in range(min(count, 3)): # cap at 3 per type to avoid clustering too densely
                        lat_offset = random.uniform(-0.005, 0.005)
                        lng_offset = random.uniform(-0.005, 0.005)
                        lat = camera.latitude + lat_offset
                        lng = camera.longitude + lng_offset
                        
                        incident = Incident(
                            incident_type=anomaly_type,
                            latitude=lat,
                            longitude=lng,
                            confidence=random.uniform(0.72, 0.94),
                            camera_id=camera.id,
                            details=f"Offline YOLO detection from CCTV video upload: {video_filename}"
                        )
                        db.session.add(incident)
                        db.session.commit()
                        
                        create_alert(
                            alert_type='detection',
                            message=f"Offline YOLO: {anomaly_type.replace('_', ' ').capitalize()} identified in camera recordings",
                            latitude=lat,
                            longitude=lng,
                            incident_id=incident.id,
                            trigger_type='offline_video',
                            severity='high',
                            source=video_filename
                        )
                        
                        update_zone_safety(lat, lng, anomaly_type)
            
            # Store results
            video_processing_status['results'] = {
                'total_detections': results['total_detections'],
                'summary': summary,
                'heatmap_path': f"processed/{target_heatmap}",
                'class_heatmaps': processed_class_heatmaps,
                'output_video': f"processed/{target_video}",
                'detection_count': detection_count,
                'original_name': video_filename
            }
            
            video_processing_status['progress'] = 100
            
        except Exception as e:
            flask_app.logger.error(f"Error processing video in thread: {e}")
            video_processing_status['error'] = str(e)
        finally:
            video_processing_status['is_processing'] = False

@admin_bp.route('/cctv-analysis')
def cctv_analysis():
    """Admin page for CCTV offline video upload and processing"""
    return render_template('admin/video_hub.html', status=video_processing_status)

@admin_bp.route('/cctv-analysis/upload', methods=['POST'])
def cctv_upload():
    """Handle video uploads and launch background processing thread"""
    global video_processing_status
    
    if video_processing_status['is_processing']:
        flash('Another video is currently being processed. Please wait.', 'warning')
        return redirect(url_for('admin.cctv_analysis'))
        
    if 'video' not in request.files:
        flash('No video file selected', 'danger')
        return redirect(url_for('admin.cctv_analysis'))
        
    file = request.files['video']
    if file.filename == '':
        flash('No video file selected', 'danger')
        return redirect(url_for('admin.cctv_analysis'))
        
    if file and allowed_file(file.filename):
        if os.environ.get("VERCEL") == "1":
            # Serverless deployment: run quick synchronous mock processing
            tmp_uploads = '/tmp/uploads'
            tmp_processed = '/tmp/processed'
            os.makedirs(tmp_uploads, exist_ok=True)
            os.makedirs(tmp_processed, exist_ok=True)
            
            filename = secure_filename(file.filename)
            video_path = os.path.join(tmp_uploads, filename)
            file.save(video_path)
            
            # Setup simulated anomaly data
            summary = {
                'violence': random.randint(1, 4),
                'fire': random.randint(1, 2),
                'explosion': random.randint(0, 1)
            }
            total = sum(summary.values())
            
            # Save mock coordinates to anomalies.db for HeatmapGenerator
            from anomaly_detector import AnomalyDetector
            detector = AnomalyDetector(db_path='/tmp/anomalies.db')
            detector._clear_detections(filename)
            
            mock_coords = []
            for class_name, count in summary.items():
                for i in range(count):
                    x = random.randint(100, 1800)
                    y = random.randint(100, 900)
                    mock_coords.append({
                        'class': class_name,
                        'confidence': random.uniform(0.75, 0.95),
                        'x': x,
                        'y': y,
                        'frame_number': i * 30,
                        'timestamp': i * 1.5
                    })
            detector._store_detections(mock_coords, filename)
            
            # Generate heatmap using Matplotlib
            from heatmap_generator import HeatmapGenerator
            heatmap_gen = HeatmapGenerator(db_path='/tmp/anomalies.db')
            
            target_heatmap = f"heatmap_{filename.rsplit('.', 1)[0]}.png"
            heatmap_gen.generate_heatmap(
                video_name=filename,
                output_path=os.path.join(tmp_processed, target_heatmap)
            )
            
            # Create Database incidents/alerts for dashboard simulation
            camera = Camera.query.first()
            if not camera:
                camera = Camera(
                    name="CCTV-1",
                    location="Times Square Rooftop",
                    latitude=28.6139,
                    longitude=77.2090,
                    status="active"
                )
                db.session.add(camera)
                db.session.commit()
                
            for anomaly_type, count in summary.items():
                if count > 0:
                    for _ in range(count):
                        lat = camera.latitude + random.uniform(-0.005, 0.005)
                        lng = camera.longitude + random.uniform(-0.005, 0.005)
                        incident = Incident(
                            incident_type=anomaly_type,
                            latitude=lat,
                            longitude=lng,
                            confidence=random.uniform(0.72, 0.94),
                            camera_id=camera.id,
                            details=f"Vercel simulated YOLO detection from video: {filename}"
                        )
                        db.session.add(incident)
                        db.session.commit()
                        
                        create_alert(
                            alert_type='detection',
                            message=f"Offline YOLO: {anomaly_type.capitalize()} identified in camera recordings",
                            latitude=lat,
                            longitude=lng,
                            incident_id=incident.id,
                            trigger_type='offline_video',
                            severity='high',
                            source=filename
                        )
            
            # Set results
            video_processing_status = {
                'is_processing': False,
                'progress': 100,
                'current_video': filename,
                'results': {
                    'total_detections': total,
                    'summary': summary,
                    'heatmap_path': f"processed/{target_heatmap}",
                    'class_heatmaps': {},
                    'output_video': 'https://assets.mixkit.co/videos/preview/mixkit-security-camera-monitoring-a-parking-lot-43187-large.mp4',
                    'detection_count': total,
                    'original_name': filename
                },
                'error': None
            }
            flash(f'Video "{filename}" uploaded and analyzed successfully (Vercel Serverless mode)!', 'success')
            return redirect(url_for('admin.cctv_analysis'))

        uploads_dir = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        video_path = os.path.join(uploads_dir, filename)
        file.save(video_path)
        
        # Reset status
        video_processing_status = {
            'is_processing': True,
            'progress': 0,
            'current_video': filename,
            'results': None,
            'error': None
        }
        
        # Get active Flask app reference for context in thread
        flask_app = current_app._get_current_object()
        
        # Start thread
        thread = threading.Thread(target=process_video_async, args=(flask_app, video_path))
        thread.start()
        
        flash(f'Video "{filename}" uploaded successfully! Anomaly processing started in the background.', 'success')
        return redirect(url_for('admin.cctv_analysis'))
    else:
        flash('Invalid video format. Allowed formats: MP4, AVI, MOV, MKV', 'danger')
        return redirect(url_for('admin.cctv_analysis'))

@admin_bp.route('/cctv-analysis/status')
def cctv_status():
    """API endpoint to fetch real-time video processing progress"""
    return jsonify(video_processing_status)

@admin_bp.route('/cctv-analysis/reset')
def cctv_reset():
    """Reset processing state and clear current results cache"""
    global video_processing_status
    if video_processing_status['is_processing']:
        flash('Cannot reset while video processing is active.', 'warning')
    else:
        video_processing_status = {
            'is_processing': False,
            'progress': 0,
            'current_video': None,
            'results': None,
            'error': None
        }
        flash('Video analysis workspace reset successfully.', 'success')
    return redirect(url_for('admin.cctv_analysis'))
