"""
Advanced AI Video Analysis System using OpenAI
Real-time detection of fire, violence, and explosions in video content
"""

import cv2
import base64
import os
import sqlite3
import numpy as np
from openai import OpenAI
import json
import logging
from typing import List, Dict, Tuple
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIVideoDetector:
    def __init__(self, db_path='video_detections.db'):
        """
        Initialize AI-powered video detector using OpenAI
        
        Args:
            db_path (str): Path to SQLite database for storing detections
        """
        self.db_path = db_path
        self.openai_client = None
        self.target_classes = ['fire', 'violence', 'explosion']
        
        # Initialize OpenAI client
        self._init_openai()
        
        # Initialize database
        self._init_database()
        
    def _init_openai(self):
        """Initialize OpenAI client with API key"""
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
    
    def _init_database(self):
        """Initialize SQLite database for storing video detections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create detections table with geographic coordinates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_name TEXT NOT NULL,
                detection_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL,
                frame_number INTEGER NOT NULL,
                latitude REAL,
                longitude REAL,
                description TEXT,
                bbox_x1 INTEGER,
                bbox_y1 INTEGER,
                bbox_x2 INTEGER,
                bbox_y2 INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def _encode_frame_to_base64(self, frame):
        """Convert OpenCV frame to base64 for OpenAI API"""
        try:
            # Resize frame for efficiency (OpenAI has size limits)
            height, width = frame.shape[:2]
            if width > 1024:
                scale = 1024 / width
                new_width = 1024
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Convert to base64
            base64_image = base64.b64encode(buffer).decode('utf-8')
            return base64_image
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def _analyze_frame_with_openai(self, frame, frame_number, timestamp):
        """
        Analyze video frame using OpenAI's vision capabilities
        
        Args:
            frame: OpenCV frame
            frame_number: Frame index
            timestamp: Time in video
            
        Returns:
            List of detection dictionaries
        """
        if not self.openai_client:
            return []
        
        try:
            # Encode frame to base64
            base64_image = self._encode_frame_to_base64(frame)
            if not base64_image:
                return []
            
            # Prepare prompt for anomaly detection
            prompt = """
            Analyze this video frame for dangerous situations. Look specifically for:
            1. FIRE: flames, smoke, burning objects, fire emergencies
            2. VIOLENCE: fighting, weapons, assault, aggressive behavior
            3. EXPLOSION: blast effects, debris, explosion aftermath
            
            For each detection, provide:
            - type: "fire", "violence", or "explosion"
            - confidence: 0.0 to 1.0
            - description: brief description of what you see
            - location: approximate bounding box as [x1, y1, x2, y2] (0-1000 scale)
            
            Respond in JSON format only:
            {
                "detections": [
                    {
                        "type": "fire",
                        "confidence": 0.85,
                        "description": "Large flames visible in background",
                        "bbox": [100, 200, 400, 600]
                    }
                ]
            }
            
            If no dangerous situations are detected, return: {"detections": []}
            """
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            result = json.loads(response_text)
            
            # Process detections - limit to 2-3 high-confidence ones
            detections = []
            high_confidence_detections = []
            
            for detection in result.get('detections', []):
                if detection['type'] in self.target_classes and detection['confidence'] > 0.75:
                    # Convert bbox to pixel coordinates
                    height, width = frame.shape[:2]
                    bbox = detection.get('bbox', [0, 0, 100, 100])
                    
                    detection_data = {
                        'type': detection['type'],
                        'confidence': min(1.0, max(0.0, detection['confidence'])),
                        'description': detection.get('description', ''),
                        'frame_number': frame_number,
                        'timestamp': timestamp,
                        'bbox': [
                            int(bbox[0] * width / 1000),  # x1
                            int(bbox[1] * height / 1000), # y1
                            int(bbox[2] * width / 1000),  # x2
                            int(bbox[3] * height / 1000)  # y2
                        ]
                    }
                    high_confidence_detections.append(detection_data)
            
            # Sort by confidence and take only top 2-3
            high_confidence_detections.sort(key=lambda x: x['confidence'], reverse=True)
            detections = high_confidence_detections[:3]  # Limit to max 3 detections
            
            return detections
            
        except Exception as e:
            logger.error(f"Error analyzing frame with OpenAI: {e}")
            return []
    
    def process_video(self, video_path, progress_callback=None):
        """
        Process entire video with OpenAI analysis
        
        Args:
            video_path: Path to video file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with processing results
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Clear previous detections for this video
        self._clear_detections(os.path.basename(video_path))
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Processing video: {video_path}")
        logger.info(f"Total frames: {total_frames}, FPS: {fps}")
        
        all_detections = []
        frame_number = 0
        
        # Process every 30th frame to balance speed and accuracy
        frame_skip = 30
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Only process every nth frame
            if frame_number % frame_skip == 0:
                timestamp = frame_number / fps
                
                # Analyze frame with OpenAI
                detections = self._analyze_frame_with_openai(frame, frame_number, timestamp)
                
                # Store detections
                if detections:
                    self._store_detections(detections, os.path.basename(video_path))
                    all_detections.extend(detections)
                    logger.info(f"Frame {frame_number}: Found {len(detections)} detections")
            
            # Progress callback
            if progress_callback:
                progress = (frame_number + 1) / total_frames * 100
                progress_callback(progress)
            
            frame_number += 1
        
        cap.release()
        
        # Generate summary
        summary = self._generate_summary(all_detections)
        
        logger.info(f"Processing complete. Found {len(all_detections)} total detections")
        
        return {
            'total_detections': len(all_detections),
            'summary': summary,
            'detections': all_detections,
            'video_name': os.path.basename(video_path)
        }
    
    def _store_detections(self, detections, video_name):
        """Store detections in database with geographic simulation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Base coordinates (Delhi area for simulation)
        base_lat = 28.6139
        base_lng = 77.2090
        
        for detection in detections:
            # Simulate geographic coordinates based on detection location
            # In real scenario, this would come from camera GPS or manual input
            lat_offset = np.random.uniform(-0.1, 0.1)
            lng_offset = np.random.uniform(-0.1, 0.1)
            sim_lat = base_lat + lat_offset
            sim_lng = base_lng + lng_offset
            
            cursor.execute('''
                INSERT INTO video_detections 
                (video_name, detection_type, confidence, timestamp, frame_number, 
                 latitude, longitude, description, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_name,
                detection['type'],
                detection['confidence'],
                detection['timestamp'],
                detection['frame_number'],
                sim_lat,
                sim_lng,
                detection.get('description', ''),
                detection['bbox'][0] if 'bbox' in detection else 0,
                detection['bbox'][1] if 'bbox' in detection else 0,
                detection['bbox'][2] if 'bbox' in detection else 0,
                detection['bbox'][3] if 'bbox' in detection else 0
            ))
        
        conn.commit()
        conn.close()
    
    def _clear_detections(self, video_name):
        """Clear previous detections for a video"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM video_detections WHERE video_name = ?', (video_name,))
        conn.commit()
        conn.close()
    
    def _generate_summary(self, detections):
        """Generate summary statistics"""
        summary = {class_name: 0 for class_name in self.target_classes}
        
        for detection in detections:
            if detection['type'] in summary:
                summary[detection['type']] += 1
        
        return summary
    
    def get_detection_coordinates(self, video_name=None):
        """
        Get detection coordinates for heatmap generation
        
        Returns:
            List of dictionaries with lat, lng, type, confidence
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_name:
            cursor.execute('''
                SELECT latitude, longitude, detection_type, confidence, description 
                FROM video_detections 
                WHERE video_name = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
            ''', (video_name,))
        else:
            cursor.execute('''
                SELECT latitude, longitude, detection_type, confidence, description 
                FROM video_detections 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        coordinates = []
        for row in results:
            coordinates.append({
                'lat': row[0],
                'lng': row[1],
                'type': row[2],
                'confidence': row[3],
                'description': row[4]
            })
        
        return coordinates