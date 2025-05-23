"""
Video Anomaly Detection Web Application for Raahi Platform
Complete Flask app with video upload, AI detection, and heatmap visualization
"""

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import sqlite3
import threading
import time
from werkzeug.utils import secure_filename
from anomaly_detector import AnomalyDetector
from heatmap_generator import HeatmapGenerator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'raahi-video-detection-2024'

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

# Global processing status
processing_status = {
    'is_processing': False,
    'progress': 0,
    'message': 'Ready',
    'current_video': None
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main upload page"""
    return render_template('video_upload.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    """Handle video file upload"""
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
        filename = secure_filename(file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(video_path)
        
        # Handle model file if uploaded
        model_path = 'yolov8n.pt'  # Default model
        if model_file and model_file.filename.endswith('.pt'):
            model_filename = secure_filename(model_file.filename)
            model_path = os.path.join(UPLOAD_FOLDER, model_filename)
            model_file.save(model_path)
        
        # Start processing in background thread
        processing_thread = threading.Thread(
            target=process_video_background,
            args=(video_path, filename, model_path)
        )
        processing_thread.start()
        
        flash('Video uploaded successfully! Processing started.', 'success')
        return redirect(url_for('processing'))
    else:
        flash('Invalid file type. Please upload MP4, AVI, MOV, or MKV files.', 'error')
        return redirect(url_for('index'))

@app.route('/processing')
def processing():
    """Processing status page"""
    return render_template('processing.html')

@app.route('/status')
def get_status():
    """API endpoint to get processing status"""
    return jsonify(processing_status)

@app.route('/results')
def results():
    """Results page showing detection results and heatmap"""
    global processing_status
    
    if processing_status['is_processing']:
        flash('Processing is still in progress', 'info')
        return redirect(url_for('processing'))
    
    if not processing_status['current_video']:
        flash('No video has been processed yet', 'warning')
        return redirect(url_for('index'))
    
    # Get detection statistics
    detector = AnomalyDetector()
    stats = detector.get_detection_stats(processing_status['current_video'])
    detections = detector.get_all_detections(processing_status['current_video'])
    
    return render_template('results.html', 
                         stats=stats, 
                         detections=detections,
                         video_file=processing_status['current_video'])

@app.route('/download/<file_type>')
def download_file(file_type):
    """Download processed files"""
    try:
        if file_type == 'heatmap':
            return send_file('static/heatmap.png', as_attachment=True, 
                           download_name='anomaly_heatmap.png')
        elif file_type == 'video':
            output_video = os.path.join(OUTPUT_FOLDER, 'output.mp4')
            if os.path.exists(output_video):
                return send_file(output_video, as_attachment=True, 
                               download_name='detected_anomalies.mp4')
            else:
                flash('Output video not found', 'error')
                return redirect(url_for('results'))
        elif file_type == 'database':
            return send_file('anomalies.db', as_attachment=True, 
                           download_name='anomaly_data.db')
    except Exception as e:
        logger.error(f"Download error: {e}")
        flash('Error downloading file', 'error')
        return redirect(url_for('results'))

@app.route('/api/detections')
def api_detections():
    """API endpoint to get all detections as JSON"""
    detector = AnomalyDetector()
    detections = detector.get_all_detections()
    
    # Convert to JSON-friendly format
    detection_list = []
    for detection in detections:
        detection_list.append({
            'id': detection[0],
            'class': detection[1],
            'confidence': detection[2],
            'timestamp': detection[3],
            'x': detection[4],
            'y': detection[5],
            'video_file': detection[6] if len(detection) > 6 else None
        })
    
    return jsonify(detection_list)

def process_video_background(video_path: str, filename: str, model_path: str):
    """Background task to process video"""
    global processing_status
    
    try:
        processing_status.update({
            'is_processing': True,
            'progress': 0,
            'message': 'Initializing AI model...',
            'current_video': filename
        })
        
        # Initialize detector
        detector = AnomalyDetector(model_path=model_path)
        
        processing_status.update({
            'progress': 10,
            'message': 'Starting video analysis...'
        })
        
        # Process video
        output_video_path = os.path.join(OUTPUT_FOLDER, 'output.mp4')
        results = detector.process_video(video_path, output_video_path)
        
        if results.get('error'):
            processing_status.update({
                'is_processing': False,
                'progress': 0,
                'message': f'Error: {results["error"]}'
            })
            return
        
        processing_status.update({
            'progress': 80,
            'message': 'Generating heatmap...'
        })
        
        # Generate heatmap
        heatmap_gen = HeatmapGenerator()
        video_info = results.get('video_info', {})
        
        heatmap_success = heatmap_gen.generate_heatmap(
            video_file=filename,
            output_path='static/heatmap.png',
            video_width=video_info.get('width', 1920),
            video_height=video_info.get('height', 1080)
        )
        
        processing_status.update({
            'progress': 100,
            'message': 'Processing complete!',
            'is_processing': False
        })
        
        logger.info(f"Video processing completed: {results['total_detections']} detections")
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        processing_status.update({
            'is_processing': False,
            'progress': 0,
            'message': f'Processing failed: {str(e)}'
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)