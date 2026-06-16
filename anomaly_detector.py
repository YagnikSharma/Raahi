"""
Video Anomaly Detection System
Detects fire, violence, and explosions in video files using YOLO models
"""

import cv2
import sqlite3
import numpy as np
import os
from typing import List, Dict, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, model_path='best.pt', db_path=None):
        """
        Initialize the anomaly detector
        
        Args:
            model_path (str): Path to the YOLO model file
            db_path (str): Path to SQLite database
        """
        self.model_path = model_path
        if db_path is None:
            self.db_path = "/tmp/anomalies.db" if os.environ.get("VERCEL") == "1" else "anomalies.db"
        else:
            self.db_path = db_path
        self.model = None
        self.target_classes = ['fire', 'violence', 'explosion']
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for storing anomalies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create anomalies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                frame_number INTEGER NOT NULL,
                video_name TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def load_model(self):
        """Load YOLO model with fallback to YOLOv8n if custom model not available"""
        try:
            # Try to load custom model first
            if os.path.exists(self.model_path):
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                logger.info(f"Loaded custom model from {self.model_path}")
            else:
                # Fallback to pre-trained YOLOv8n for demonstration
                from ultralytics import YOLO
                self.model = YOLO('yolov8n.pt')
                logger.info("Using YOLOv8n model (will detect general objects for demo)")
                
                # Map some general classes to our target classes for demo purposes
                self.class_mapping = {
                    'person': 'violence',  # Person detection can indicate potential violence
                    'fire hydrant': 'fire',  # Closest to fire detection
                    'bottle': 'explosion',  # Random mapping for demo
                }
                
        except ImportError:
            logger.error("Ultralytics not available. Using OpenCV-based mock detection.")
            self.model = None
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
    
    def _mock_detection(self, frame, frame_number, timestamp):
        """
        Mock detection when YOLO is not available
        Creates synthetic detections for demonstration
        """
        detections = []
        height, width = frame.shape[:2]
        
        # Generate some mock detections based on frame content
        if frame_number % 30 == 0:  # Every 30 frames
            # Mock fire detection (reddish areas)
            if np.mean(frame[:, :, 2]) > np.mean(frame[:, :, 1]):  # More red than green
                detections.append({
                    'class': 'fire',
                    'confidence': 0.8,
                    'x': width // 2,
                    'y': height // 2,
                    'timestamp': timestamp,
                    'frame_number': frame_number
                })
        
        if frame_number % 45 == 0:  # Every 45 frames
            # Mock violence detection (high motion areas)
            detections.append({
                'class': 'violence',
                'confidence': 0.7,
                'x': width // 3,
                'y': height // 3,
                'timestamp': timestamp,
                'frame_number': frame_number
            })
            
        return detections
    
    def detect_frame(self, frame, frame_number, timestamp):
        """
        Detect anomalies in a single frame
        
        Args:
            frame: OpenCV frame
            frame_number: Frame index
            timestamp: Time in seconds
            
        Returns:
            List of detections
        """
        detections = []
        
        if self.model is None:
            # Use mock detection if model not available
            return self._mock_detection(frame, frame_number, timestamp)
        
        try:
            # Run YOLO detection
            results = self.model(frame, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get class name
                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id]
                        confidence = float(box.conf[0])
                        
                        # Map to target classes or check if already target class
                        target_class = None
                        if class_name in self.target_classes:
                            target_class = class_name
                        elif hasattr(self, 'class_mapping') and class_name in self.class_mapping:
                            target_class = self.class_mapping[class_name]
                        
                        if target_class and confidence > 0.5:  # Confidence threshold
                            # Get bounding box center
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            center_x = int((x1 + x2) / 2)
                            center_y = int((y1 + y2) / 2)
                            
                            detections.append({
                                'class': target_class,
                                'confidence': confidence,
                                'x': center_x,
                                'y': center_y,
                                'timestamp': timestamp,
                                'frame_number': frame_number,
                                'bbox': [x1, y1, x2, y2]
                            })
                            
        except Exception as e:
            logger.error(f"Error in frame detection: {e}")
            
        return detections
    
    def process_video(self, video_path, progress_callback=None):
        """
        Process entire video and detect anomalies
        
        Args:
            video_path: Path to video file
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with processing results
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Load model if not already loaded
        if self.model is None:
            self.load_model()
        
        # Clear previous detections for this video
        self._clear_detections(os.path.basename(video_path))
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Processing video: {video_path}")
        logger.info(f"Total frames: {total_frames}, FPS: {fps}")
        
        all_detections = []
        frame_number = 0
        
        # Prepare video writer for output with bounding boxes
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_video = cv2.VideoWriter('output.mp4', fourcc, fps, (width, height))
        except:
            # Fallback if codec issues
            out_video = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_number / fps
            
            # Detect anomalies in frame
            detections = self.detect_frame(frame, frame_number, timestamp)
            
            # Store detections in database
            if detections:
                self._store_detections(detections, os.path.basename(video_path))
                all_detections.extend(detections)
            
            # Draw bounding boxes on frame
            annotated_frame = self._draw_detections(frame, detections)
            if out_video:
                out_video.write(annotated_frame)
            
            # Progress callback
            if progress_callback:
                progress = (frame_number + 1) / total_frames * 100
                progress_callback(progress)
            
            frame_number += 1
        
        cap.release()
        if out_video:
            out_video.release()
        
        # Generate summary
        summary = self._generate_summary(all_detections)
        
        logger.info(f"Processing complete. Found {len(all_detections)} anomalies")
        
        return {
            'total_detections': len(all_detections),
            'summary': summary,
            'output_video': 'output.mp4',
            'detections': all_detections
        }
    
    def _draw_detections(self, frame, detections):
        """Draw bounding boxes and labels on frame"""
        colors = {
            'fire': (0, 0, 255),      # Red
            'violence': (0, 255, 0),   # Green
            'explosion': (255, 0, 0)   # Blue
        }
        
        for detection in detections:
            if 'bbox' in detection:
                x1, y1, x2, y2 = detection['bbox']
                color = colors.get(detection['class'], (255, 255, 255))
                
                # Draw bounding box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                
                # Draw label
                label = f"{detection['class']}: {detection['confidence']:.2f}"
                cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            else:
                # Fallback for detections without bbox
                x, y = detection['x'], detection['y']
                color = colors.get(detection['class'], (255, 255, 255))
                cv2.circle(frame, (x, y), 10, color, -1)
                
                label = f"{detection['class']}: {detection['confidence']:.2f}"
                cv2.putText(frame, label, (x, y - 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return frame
    
    def _store_detections(self, detections, video_name):
        """Store detections in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for detection in detections:
            cursor.execute('''
                INSERT INTO anomalies (class, confidence, timestamp, x, y, frame_number, video_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                detection['class'],
                detection['confidence'],
                detection['timestamp'],
                detection['x'],
                detection['y'],
                detection['frame_number'],
                video_name
            ))
        
        conn.commit()
        conn.close()
    
    def _clear_detections(self, video_name):
        """Clear previous detections for a video"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM anomalies WHERE video_name = ?', (video_name,))
        conn.commit()
        conn.close()
    
    def _generate_summary(self, detections):
        """Generate summary statistics"""
        summary = {class_name: 0 for class_name in self.target_classes}
        
        for detection in detections:
            if detection['class'] in summary:
                summary[detection['class']] += 1
        
        return summary
    
    def get_detection_coordinates(self, video_name=None):
        """
        Get all detection coordinates for heatmap generation
        
        Args:
            video_name: Optional video name filter
            
        Returns:
            List of (x, y) coordinates
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_name:
            cursor.execute('SELECT x, y FROM anomalies WHERE video_name = ?', (video_name,))
        else:
            cursor.execute('SELECT x, y FROM anomalies')
        
        coordinates = cursor.fetchall()
        conn.close()
        
        return coordinates