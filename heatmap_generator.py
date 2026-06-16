"""
Heatmap Generator for Video Anomaly Detection
Creates visualization of anomaly hotspots
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import sqlite3
from typing import List, Tuple
import os

class HeatmapGenerator:
    def __init__(self, db_path=None):
        """
        Initialize heatmap generator
        
        Args:
            db_path (str): Path to SQLite database
        """
        if db_path is None:
            self.db_path = "/tmp/anomalies.db" if os.environ.get("VERCEL") == "1" else "anomalies.db"
        else:
            self.db_path = db_path
    
    def generate_heatmap(self, video_name=None, video_width=1920, video_height=1080, output_path='heatmap.png'):
        """
        Generate heatmap from detection coordinates
        
        Args:
            video_name: Optional video name filter
            video_width: Width of video for scaling
            video_height: Height of video for scaling
            output_path: Path to save heatmap image
            
        Returns:
            Tuple of (output_path, detection_count)
        """
        # Get coordinates from database
        coordinates = self._get_coordinates(video_name)
        
        if not coordinates:
            # Create empty heatmap if no detections
            return self._create_empty_heatmap(output_path, video_width, video_height)
        
        # Convert to numpy arrays
        x_coords = np.array([coord[0] for coord in coordinates])
        y_coords = np.array([coord[1] for coord in coordinates])
        
        # Create heatmap
        plt.figure(figsize=(12, 8))
        
        # Create 2D histogram for heatmap
        heatmap, xedges, yedges = np.histogram2d(x_coords, y_coords, bins=50, 
                                                range=[[0, video_width], [0, video_height]])
        
        # Create the plot
        plt.imshow(heatmap.T, origin='lower', cmap='hot', interpolation='bilinear',
                  extent=[0, video_width, 0, video_height], alpha=0.8)
        
        # Add colorbar
        plt.colorbar(label='Detection Density')
        
        # Customize the plot
        plt.title('Anomaly Detection Heatmap', fontsize=16, fontweight='bold')
        plt.xlabel('X Coordinate (pixels)', fontsize=12)
        plt.ylabel('Y Coordinate (pixels)', fontsize=12)
        
        # Add grid
        plt.grid(True, alpha=0.3)
        
        # Add detection points
        plt.scatter(x_coords, y_coords, c='white', s=10, alpha=0.6, edgecolors='black', linewidth=0.5)
        
        # Add statistics text
        total_detections = len(coordinates)
        stats_text = f'Total Detections: {total_detections}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                fontsize=10, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Save the plot
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()  # Close to free memory
        
        return output_path, total_detections
    
    def generate_class_heatmaps(self, video_name=None, video_width=1920, video_height=1080):
        """
        Generate separate heatmaps for each anomaly class
        
        Returns:
            Dictionary with class names as keys and heatmap paths as values
        """
        classes = ['fire', 'violence', 'explosion']
        heatmaps = {}
        
        for class_name in classes:
            coordinates = self._get_coordinates_by_class(video_name, class_name)
            
            if coordinates:
                output_path = f'heatmap_{class_name}.png'
                
                # Convert to numpy arrays
                x_coords = np.array([coord[0] for coord in coordinates])
                y_coords = np.array([coord[1] for coord in coordinates])
                
                # Create heatmap
                plt.figure(figsize=(10, 6))
                
                # Create 2D histogram
                heatmap, xedges, yedges = np.histogram2d(x_coords, y_coords, bins=30,
                                                        range=[[0, video_width], [0, video_height]])
                
                # Color schemes for different classes
                color_maps = {
                    'fire': 'Reds',
                    'violence': 'Greens', 
                    'explosion': 'Blues'
                }
                
                plt.imshow(heatmap.T, origin='lower', cmap=color_maps.get(class_name, 'hot'),
                          interpolation='bilinear', extent=[0, video_width, 0, video_height], alpha=0.8)
                
                plt.colorbar(label='Detection Density')
                plt.title(f'{class_name.title()} Detection Heatmap', fontsize=14, fontweight='bold')
                plt.xlabel('X Coordinate (pixels)')
                plt.ylabel('Y Coordinate (pixels)')
                plt.grid(True, alpha=0.3)
                
                # Add detection points
                plt.scatter(x_coords, y_coords, c='white', s=8, alpha=0.7)
                
                plt.tight_layout()
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                heatmaps[class_name] = output_path
        
        return heatmaps
    
    def _get_coordinates(self, video_name=None):
        """Get all detection coordinates from database"""
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if video_name:
                cursor.execute('SELECT x, y FROM anomalies WHERE video_name = ?', (video_name,))
            else:
                cursor.execute('SELECT x, y FROM anomalies')
            
            coordinates = cursor.fetchall()
            conn.close()
            return coordinates
        except sqlite3.Error:
            conn.close()
            return []
    
    def _get_coordinates_by_class(self, video_name, class_name):
        """Get coordinates for specific anomaly class"""
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if video_name:
                cursor.execute('SELECT x, y FROM anomalies WHERE video_name = ? AND class = ?', 
                             (video_name, class_name))
            else:
                cursor.execute('SELECT x, y FROM anomalies WHERE class = ?', (class_name,))
            
            coordinates = cursor.fetchall()
            conn.close()
            return coordinates
        except sqlite3.Error:
            conn.close()
            return []
    
    def _create_empty_heatmap(self, output_path, video_width, video_height):
        """Create empty heatmap when no detections found"""
        plt.figure(figsize=(12, 8))
        
        # Create empty plot with video dimensions
        plt.xlim(0, video_width)
        plt.ylim(0, video_height)
        
        plt.title('Anomaly Detection Heatmap - No Detections Found', fontsize=16, fontweight='bold')
        plt.xlabel('X Coordinate (pixels)', fontsize=12)
        plt.ylabel('Y Coordinate (pixels)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Add text indicating no detections
        plt.text(video_width/2, video_height/2, 'No Anomalies Detected', 
                ha='center', va='center', fontsize=20, alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_path, 0
    
    def get_detection_summary(self, video_name=None):
        """Get summary of detections by class"""
        if not os.path.exists(self.db_path):
            return {}
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if video_name:
                cursor.execute('''
                    SELECT class, COUNT(*) as count 
                    FROM anomalies 
                    WHERE video_name = ? 
                    GROUP BY class
                ''', (video_name,))
            else:
                cursor.execute('''
                    SELECT class, COUNT(*) as count 
                    FROM anomalies 
                    GROUP BY class
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            summary = {row[0]: row[1] for row in results}
            return summary
        except sqlite3.Error:
            conn.close()
            return {}