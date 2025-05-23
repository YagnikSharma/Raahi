"""
Video Anomaly Detection Web Application
Flask app for uploading and analyzing videos for fire, violence, and explosions
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import threading
from werkzeug.utils import secure_filename
import cv2
from anomaly_detector import AnomalyDetector
from heatmap_generator import HeatmapGenerator

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables for processing status
processing_status = {
    'is_processing': False,
    'progress': 0,
    'current_video': None,
    'results': None,
    'error': None
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_progress(progress):
    """Callback function to update processing progress"""
    processing_status['progress'] = progress

def process_video_async(video_path, model_path=None):
    """Process video in background thread"""
    global processing_status
    
    try:
        processing_status['is_processing'] = True
        processing_status['progress'] = 0
        processing_status['error'] = None
        
        # Initialize detector
        detector = AnomalyDetector(model_path=model_path or 'best.pt')
        
        # Process video
        results = detector.process_video(video_path, progress_callback=update_progress)
        
        # Generate heatmap
        heatmap_gen = HeatmapGenerator()
        
        # Get video dimensions
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        heatmap_path, detection_count = heatmap_gen.generate_heatmap(
            video_name=os.path.basename(video_path),
            video_width=width,
            video_height=height
        )
        
        # Generate class-specific heatmaps
        class_heatmaps = heatmap_gen.generate_class_heatmaps(
            video_name=os.path.basename(video_path),
            video_width=width,
            video_height=height
        )
        
        # Get detection summary
        summary = heatmap_gen.get_detection_summary(os.path.basename(video_path))
        
        # Store results
        processing_status['results'] = {
            'total_detections': results['total_detections'],
            'summary': summary,
            'heatmap_path': heatmap_path,
            'class_heatmaps': class_heatmaps,
            'output_video': results['output_video'],
            'detection_count': detection_count
        }
        
        processing_status['progress'] = 100
        
    except Exception as e:
        processing_status['error'] = str(e)
    finally:
        processing_status['is_processing'] = False

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('video_upload.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    """Handle video upload and start processing"""
    global processing_status
    
    if processing_status['is_processing']:
        flash('Another video is currently being processed. Please wait.', 'warning')
        return redirect(url_for('index'))
    
    if 'video' not in request.files:
        flash('No video file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['video']
    model_file = request.files.get('model')
    
    if file.filename == '':
        flash('No video file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Save video file
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(video_path)
        
        # Save model file if provided
        model_path = None
        if model_file and model_file.filename and model_file.filename.endswith('.pt'):
            model_filename = secure_filename(model_file.filename)
            model_path = os.path.join(app.config['UPLOAD_FOLDER'], model_filename)
            model_file.save(model_path)
        
        # Reset processing status
        processing_status = {
            'is_processing': False,
            'progress': 0,
            'current_video': filename,
            'results': None,
            'error': None
        }
        
        # Start processing in background thread
        thread = threading.Thread(target=process_video_async, args=(video_path, model_path))
        thread.start()
        
        flash(f'Video "{filename}" uploaded successfully! Processing started.', 'success')
        return redirect(url_for('processing'))
    
    else:
        flash('Invalid file type. Please upload MP4, AVI, MOV, or MKV files.', 'error')
        return redirect(url_for('index'))

@app.route('/processing')
def processing():
    """Processing status page"""
    return render_template('processing.html')

@app.route('/api/status')
def get_status():
    """API endpoint to get processing status"""
    return jsonify(processing_status)

@app.route('/results')
def results():
    """Results page showing detection summary and heatmap"""
    if not processing_status['results']:
        flash('No results available. Please upload and process a video first.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('results.html', results=processing_status['results'])

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed files"""
    try:
        return send_file(filename, as_attachment=True)
    except FileNotFoundError:
        flash('File not found', 'error')
        return redirect(url_for('results'))

@app.route('/heatmap')
def view_heatmap():
    """View heatmap image"""
    try:
        return send_file('heatmap.png')
    except FileNotFoundError:
        flash('Heatmap not found', 'error')
        return redirect(url_for('results'))

@app.route('/heatmap/<class_name>')
def view_class_heatmap(class_name):
    """View class-specific heatmap"""
    try:
        return send_file(f'heatmap_{class_name}.png')
    except FileNotFoundError:
        flash(f'Heatmap for {class_name} not found', 'error')
        return redirect(url_for('results'))

@app.route('/reset')
def reset():
    """Reset processing status and clear results"""
    global processing_status
    
    if not processing_status['is_processing']:
        processing_status = {
            'is_processing': False,
            'progress': 0,
            'current_video': None,
            'results': None,
            'error': None
        }
        flash('System reset successfully', 'success')
    else:
        flash('Cannot reset while processing is in progress', 'warning')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)