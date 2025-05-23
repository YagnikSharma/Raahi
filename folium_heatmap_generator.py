"""
Folium-based Heatmap Generator for Video Detections
Integrates AI video analysis results with geographic heatmaps
"""

import folium
from folium.plugins import HeatMap
import sqlite3
import os
import json
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class FoliumHeatmapGenerator:
    def __init__(self, db_path='video_detections.db'):
        """
        Initialize Folium heatmap generator
        
        Args:
            db_path (str): Path to SQLite database with video detections
        """
        self.db_path = db_path
        
        # Default map center (Delhi)
        self.default_center = [28.6139, 77.2090]
        self.default_zoom = 12
        
        # Color mapping for different detection types
        self.detection_colors = {
            'fire': '#FF0000',      # Red
            'violence': '#FFA500',  # Orange  
            'explosion': '#8B0000'  # Dark Red
        }
    
    def get_detection_data(self, video_name=None):
        """
        Get detection data from database
        
        Args:
            video_name: Optional filter for specific video
            
        Returns:
            List of detection dictionaries
        """
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if video_name:
                cursor.execute('''
                    SELECT latitude, longitude, detection_type, confidence, 
                           description, timestamp, frame_number 
                    FROM video_detections 
                    WHERE video_name = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
                    ORDER BY timestamp
                ''', (video_name,))
            else:
                cursor.execute('''
                    SELECT latitude, longitude, detection_type, confidence, 
                           description, timestamp, frame_number 
                    FROM video_detections 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                    ORDER BY timestamp
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            detections = []
            for row in results:
                detections.append({
                    'lat': row[0],
                    'lng': row[1],
                    'type': row[2],
                    'confidence': row[3],
                    'description': row[4],
                    'timestamp': row[5],
                    'frame_number': row[6]
                })
            
            return detections
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.close()
            return []
    
    def generate_integrated_heatmap(self, video_name=None, output_path='integrated_heatmap.html'):
        """
        Generate integrated heatmap combining existing safety zones with video detections
        
        Args:
            video_name: Optional filter for specific video
            output_path: Path to save HTML file
            
        Returns:
            Tuple of (output_path, detection_count, map_center)
        """
        # Get video detections
        detections = self.get_detection_data(video_name)
        
        if not detections:
            # Create map with just existing safety zones
            return self._create_safety_only_map(output_path)
        
        # Calculate map center based on detections
        center_lat = sum(d['lat'] for d in detections) / len(detections)
        center_lng = sum(d['lng'] for d in detections) / len(detections)
        map_center = [center_lat, center_lng]
        
        # Create base map
        m = folium.Map(
            location=map_center,
            zoom_start=self.default_zoom,
            tiles='OpenStreetMap'
        )
        
        # Add existing safety zones from main database
        self._add_safety_zones(m)
        
        # Add existing incidents
        self._add_existing_incidents(m)
        
        # Prepare heatmap data for video detections
        heat_data = []
        for detection in detections:
            # Weight by confidence for better visualization
            weight = detection['confidence']
            heat_data.append([detection['lat'], detection['lng'], weight])
        
        # Add heatmap layer for video detections
        if heat_data:
            HeatMap(heat_data, 
                   radius=15, 
                   blur=10, 
                   max_zoom=1,
                   gradient={0.2: 'blue', 0.4: 'cyan', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}).add_to(m)
        
        # Add individual detection markers
        self._add_detection_markers(m, detections)
        
        # Add legend
        self._add_legend(m, detections)
        
        # Save map
        m.save(output_path)
        logger.info(f"Integrated heatmap saved to {output_path}")
        
        return output_path, len(detections), map_center
    
    def _add_safety_zones(self, map_obj):
        """Add existing safety zones from main Raahi database"""
        try:
            # Import here to avoid circular imports
            from models import Zone
            from app import db
            
            zones = Zone.query.all()
            
            for zone in zones:
                # Color based on safety level
                if zone.safety_level == 0:
                    color = 'green'
                    fillColor = 'lightgreen'
                elif zone.safety_level == 1:
                    color = 'yellow'
                    fillColor = 'lightyellow'
                elif zone.safety_level == 2:
                    color = 'orange'
                    fillColor = 'moccasin'
                else:
                    color = 'red'
                    fillColor = 'lightcoral'
                
                # Add circle for safety zone
                folium.Circle(
                    location=[zone.latitude, zone.longitude],
                    radius=zone.radius * 111000,  # Convert degrees to meters approximately
                    color=color,
                    fillColor=fillColor,
                    fillOpacity=0.3,
                    popup=folium.Popup(
                        f"""
                        <b>Safety Zone</b><br>
                        Level: {['Safe', 'Caution', 'High Caution', 'Unsafe'][zone.safety_level]}<br>
                        Incidents: {zone.incident_count}<br>
                        Updated: {zone.last_updated.strftime('%d %b %Y') if zone.last_updated else 'Unknown'}
                        """,
                        max_width=200
                    )
                ).add_to(map_obj)
                
        except Exception as e:
            logger.warning(f"Could not load safety zones: {e}")
    
    def _add_existing_incidents(self, map_obj):
        """Add existing incidents from main Raahi database"""
        try:
            from models import Incident
            from app import db
            
            incidents = Incident.query.limit(50).all()  # Limit for performance
            
            for incident in incidents:
                # Icon based on incident type
                if 'fire' in incident.incident_type.lower():
                    icon_color = 'red'
                    icon = 'fire'
                elif 'violence' in incident.incident_type.lower():
                    icon_color = 'orange'
                    icon = 'exclamation-triangle'
                else:
                    icon_color = 'darkred'
                    icon = 'warning-sign'
                
                folium.Marker(
                    location=[incident.latitude, incident.longitude],
                    popup=folium.Popup(
                        f"""
                        <b>{incident.incident_type.title()}</b><br>
                        Confidence: {int(incident.confidence * 100)}%<br>
                        Time: {incident.timestamp.strftime('%d %b %Y, %H:%M')}<br>
                        {f'Verified: {incident.is_verified}' if incident.is_verified else ''}
                        """,
                        max_width=200
                    ),
                    icon=folium.Icon(color=icon_color, icon=icon, prefix='fa')
                ).add_to(map_obj)
                
        except Exception as e:
            logger.warning(f"Could not load existing incidents: {e}")
    
    def _add_detection_markers(self, map_obj, detections):
        """Add individual video detection markers"""
        for detection in detections:
            color = self.detection_colors.get(detection['type'], '#000000')
            
            # Create marker with detection details
            folium.CircleMarker(
                location=[detection['lat'], detection['lng']],
                radius=8,
                popup=folium.Popup(
                    f"""
                    <b>AI Video Detection</b><br>
                    Type: {detection['type'].title()}<br>
                    Confidence: {int(detection['confidence'] * 100)}%<br>
                    Description: {detection['description']}<br>
                    Frame: {detection['frame_number']}<br>
                    Time: {detection['timestamp']:.1f}s
                    """,
                    max_width=250
                ),
                color=color,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(map_obj)
    
    def _add_legend(self, map_obj, detections):
        """Add legend to map"""
        # Count detections by type
        type_counts = {}
        for detection in detections:
            detection_type = detection['type']
            type_counts[detection_type] = type_counts.get(detection_type, 0) + 1
        
        # Create legend HTML
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>Detection Legend</h4>
        '''
        
        for detection_type, count in type_counts.items():
            color = self.detection_colors.get(detection_type, '#000000')
            legend_html += f'''
            <p><span style="color:{color}; font-size:18px;">●</span> {detection_type.title()}: {count}</p>
            '''
        
        legend_html += '''
        <p><span style="color:green; font-size:18px;">●</span> Safe Zones</p>
        <p><span style="color:red; font-size:18px;">●</span> Unsafe Zones</p>
        </div>
        '''
        
        map_obj.get_root().html.add_child(folium.Element(legend_html))
    
    def _create_safety_only_map(self, output_path):
        """Create map with only existing safety data when no video detections"""
        m = folium.Map(
            location=self.default_center,
            zoom_start=self.default_zoom,
            tiles='OpenStreetMap'
        )
        
        # Add existing safety zones and incidents
        self._add_safety_zones(m)
        self._add_existing_incidents(m)
        
        # Add message about no video detections
        folium.Marker(
            location=self.default_center,
            popup=folium.Popup(
                """
                <b>No Video Detections</b><br>
                Upload and analyze videos to see AI-powered detection results on this map.
                """,
                max_width=200
            ),
            icon=folium.Icon(color='blue', icon='info-sign', prefix='fa')
        ).add_to(m)
        
        m.save(output_path)
        return output_path, 0, self.default_center
    
    def generate_detection_summary(self, video_name=None):
        """Generate summary statistics for detections"""
        detections = self.get_detection_data(video_name)
        
        summary = {
            'total_detections': len(detections),
            'by_type': {},
            'avg_confidence': 0,
            'high_confidence_count': 0
        }
        
        if detections:
            # Count by type
            for detection in detections:
                detection_type = detection['type']
                summary['by_type'][detection_type] = summary['by_type'].get(detection_type, 0) + 1
            
            # Calculate average confidence
            confidences = [d['confidence'] for d in detections]
            summary['avg_confidence'] = sum(confidences) / len(confidences)
            
            # Count high confidence detections (>0.7)
            summary['high_confidence_count'] = sum(1 for c in confidences if c > 0.7)
        
        return summary