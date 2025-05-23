"""
Anomaly Detection Module for Raahi Platform
Detects fire, violence, and explosion in video using YOLO
"""

import cv2
import sqlite3
import numpy as np
from ultralytics import YOLO
import os
import logging
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, model_path='yolov8n.pt', db_path='anomalies.db'):
        """
        Initialize the anomaly detector
        
        Args:
            model_path: Path to YOLO model file
            db_path: Path to SQLite database
        """
        self.model_path = model_path
        self.db_path = db_path
        self.model = None
        self.target_classes = ['fire', 'violence', 'explosion']
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for storing anomalies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                video_file TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def load_model(self):
        """Load YOLO model"""
        try:
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                logger.info(f"Custom model loaded from {self.model_path}")
            else:
                # Fallback to pretrained model
                self.model = YOLO('yolov8n.pt')
                logger.info("Using pretrained YOLOv8n model")
            
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def clear_database(self, video_file=None):
        """Clear previous detections for a video file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_file:
            cursor.execute('DELETE FROM anomalies WHERE video_file = ?', (video_file,))
        else:
            cursor.execute('DELETE FROM anomalies')
        
        conn.commit()
        conn.close()
        logger.info(f"Cleared database for video: {video_file}")
    
    def process_video(self, video_path: str, output_path: str = None) -> Dict:
        """
        Process video for anomaly detection
        
        Args:
            video_path: Path to input video
            output_path: Path for output video with bounding boxes
            
        Returns:
            Dictionary with detection results and statistics
        """
        if not self.load_model():
            return {"error": "Failed to load model"}
        
        # Clear previous detections for this video
        video_filename = os.path.basename(video_path)
        self.clear_database(video_filename)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Could not open video file"}
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Processing video: {width}x{height}, {total_frames} frames, {fps} FPS")
        
        # Setup output video writer if output path provided
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        detections = []
        frame_count = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_time = frame_count / fps
                
                # Run YOLO detection
                results = self.model(frame, verbose=False)
                
                # Process detections
                for result in results:
                    if result.boxes is not None:
                        boxes = result.boxes
                        
                        for i in range(len(boxes)):
                            # Get detection info
                            conf = float(boxes.conf[i])
                            cls_id = int(boxes.cls[i])
                            class_name = self.model.names[cls_id].lower()
                            
                            # Check if it's one of our target classes
                            if any(target in class_name for target in self.target_classes):
                                # Get bounding box coordinates
                                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
                                center_x = int((x1 + x2) / 2)
                                center_y = int((y1 + y2) / 2)
                                
                                # Store in database
                                cursor.execute('''
                                    INSERT INTO anomalies 
                                    (class, confidence, timestamp, x, y, video_file)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (class_name, conf, frame_time, center_x, center_y, video_filename))
                                
                                detections.append({
                                    'class': class_name,
                                    'confidence': conf,
                                    'timestamp': frame_time,
                                    'x': center_x,
                                    'y': center_y
                                })
                                
                                # Draw bounding box on output frame
                                if out is not None:
                                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                                    label = f"{class_name}: {conf:.2f}"
                                    cv2.putText(frame, label, (int(x1), int(y1)-10), 
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                
                # Write frame to output video
                if out is not None:
                    out.write(frame)
                
                frame_count += 1
                
                # Log progress every 30 frames
                if frame_count % 30 == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"Processing: {progress:.1f}% complete")
        
        finally:
            cap.release()
            if out is not None:
                out.release()
            conn.commit()
            conn.close()
        
        # Generate statistics
        stats = self.get_detection_stats(video_filename)
        
        logger.info(f"Processing complete. Total detections: {len(detections)}")
        
        return {
            "success": True,
            "total_detections": len(detections),
            "detections": detections,
            "stats": stats,
            "video_info": {
                "width": width,
                "height": height,
                "fps": fps,
                "total_frames": total_frames
            }
        }
    
    def get_detection_stats(self, video_file=None) -> Dict:
        """Get detection statistics from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_file:
            cursor.execute('SELECT class, COUNT(*) FROM anomalies WHERE video_file = ? GROUP BY class', (video_file,))
        else:
            cursor.execute('SELECT class, COUNT(*) FROM anomalies GROUP BY class')
        
        stats = dict(cursor.fetchall())
        conn.close()
        
        return stats
    
    def get_all_detections(self, video_file=None) -> List[Tuple]:
        """Get all detections from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_file:
            cursor.execute('SELECT * FROM anomalies WHERE video_file = ?', (video_file,))
        else:
            cursor.execute('SELECT * FROM anomalies')
        
        detections = cursor.fetchall()
        conn.close()
        
        return detections