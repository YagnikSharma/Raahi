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
