"""
Heatmap Generation Module for Raahi Platform
Creates visual heatmaps from anomaly detection data
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import seaborn as sns
import sqlite3
from typing import List, Tuple
import logging
import os

logger = logging.getLogger(__name__)

class HeatmapGenerator:
    def __init__(self, db_path='anomalies.db'):
        """
        Initialize heatmap generator
        
        Args:
            db_path: Path to SQLite database containing anomaly data
        """
        self.db_path = db_path
        
    def generate_heatmap(self, video_file=None, output_path='heatmap.png', 
                        video_width=1920, video_height=1080) -> bool:
        """
        Generate heatmap from anomaly detection data
        
        Args:
            video_file: Specific video file to generate heatmap for (None for all)
            output_path: Path to save heatmap image
            video_width: Width of original video
            video_height: Height of original video
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get detection coordinates from database
            coords = self.get_detection_coordinates(video_file)
            
            if not coords:
                logger.warning("No detection data found for heatmap generation")
                self.create_empty_heatmap(output_path, video_width, video_height)
                return True
            
            # Separate x and y coordinates
            x_coords = [coord[0] for coord in coords]
            y_coords = [coord[1] for coord in coords]
            
            # Create figure with dark theme to match Raahi
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Create 2D histogram for heatmap
            bins_x = min(50, video_width // 40)  # Adaptive bin size
            bins_y = min(50, video_height // 40)
            
            heatmap, xedges, yedges = np.histogram2d(
                x_coords, y_coords, 
                bins=[bins_x, bins_y],
                range=[[0, video_width], [0, video_height]]
            )
            
            # Create the heatmap using seaborn
            sns.heatmap(
                heatmap.T,  # Transpose to match image coordinates
                cmap='Reds',
                cbar=True,
                cbar_kws={'label': 'Anomaly Density'},
                xticklabels=False,
                yticklabels=False,
                ax=ax
            )
            
            # Customize the plot
            ax.set_title('🚨 Anomaly Detection Heatmap - Raahi Platform', 
                        fontsize=16, color='white', pad=20)
            ax.set_xlabel('Video Width (pixels)', fontsize=12, color='white')
            ax.set_ylabel('Video Height (pixels)', fontsize=12, color='white')
            
            # Add detection statistics as text overlay
            stats = self.get_detection_stats(video_file)
            stats_text = self.format_stats_text(stats)
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8),
                   color='white')
            
            # Invert y-axis to match video coordinate system
            ax.invert_yaxis()
            
            # Save the heatmap
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                       facecolor='black', edgecolor='none')
            plt.close()
            
            logger.info(f"Heatmap generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating heatmap: {e}")
            return False
    
    def create_empty_heatmap(self, output_path: str, width: int, height: int):
        """Create empty heatmap when no detections found"""
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create empty grid
        empty_grid = np.zeros((height//40, width//40))
        
        sns.heatmap(
            empty_grid,
            cmap='Reds',
            cbar=True,
            cbar_kws={'label': 'Anomaly Density'},
            xticklabels=False,
            yticklabels=False,
            ax=ax
        )
        
        ax.set_title('🚨 No Anomalies Detected - Raahi Platform', 
                    fontsize=16, color='white', pad=20)
        ax.set_xlabel('Video Width (pixels)', fontsize=12, color='white')
        ax.set_ylabel('Video Height (pixels)', fontsize=12, color='white')
        
        # Add "No detections" message
        ax.text(0.5, 0.5, 'No Anomalies Detected\n✅ Area appears safe', 
               transform=ax.transAxes, fontsize=14,
               ha='center', va='center',
               bbox=dict(boxstyle='round', facecolor='green', alpha=0.7),
               color='white')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                   facecolor='black', edgecolor='none')
        plt.close()
    
    def get_detection_coordinates(self, video_file=None) -> List[Tuple[int, int]]:
        """Get all detection coordinates from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_file:
            cursor.execute('SELECT x, y FROM anomalies WHERE video_file = ?', (video_file,))
        else:
            cursor.execute('SELECT x, y FROM anomalies')
        
        coords = cursor.fetchall()
        conn.close()
        
        return coords
    
    def get_detection_stats(self, video_file=None) -> dict:
        """Get detection statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if video_file:
            cursor.execute('''
                SELECT class, COUNT(*), AVG(confidence) 
                FROM anomalies 
                WHERE video_file = ? 
                GROUP BY class
            ''', (video_file,))
        else:
            cursor.execute('''
                SELECT class, COUNT(*), AVG(confidence) 
                FROM anomalies 
                GROUP BY class
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        stats = {}
        for class_name, count, avg_conf in results:
            stats[class_name] = {
                'count': count,
                'avg_confidence': avg_conf
            }
        
        return stats
    
    def format_stats_text(self, stats: dict) -> str:
        """Format detection statistics as text"""
        if not stats:
            return "No anomalies detected ✅"
        
        lines = ["🚨 Anomaly Detection Results:"]
        total_detections = 0
        
        for class_name, data in stats.items():
            count = data['count']
            confidence = data['avg_confidence']
            total_detections += count
            
            emoji = self.get_class_emoji(class_name)
            lines.append(f"{emoji} {class_name.title()}: {count} ({confidence:.1%} confidence)")
        
        lines.insert(1, f"Total Detections: {total_detections}")
        return "\n".join(lines)
    
    def get_class_emoji(self, class_name: str) -> str:
        """Get emoji for detection class"""
        emoji_map = {
            'fire': '🔥',
            'violence': '⚡',
            'explosion': '💥',
            'weapon': '🔫',
            'person': '👤'
        }
        
        for key, emoji in emoji_map.items():
            if key in class_name.lower():
                return emoji
        
        return '🚨'
    
    def generate_class_specific_heatmap(self, class_name: str, video_file=None, 
                                      output_path=None, video_width=1920, video_height=1080) -> bool:
        """Generate heatmap for specific anomaly class"""
        if output_path is None:
            output_path = f'heatmap_{class_name}.png'
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if video_file:
                cursor.execute(
                    'SELECT x, y FROM anomalies WHERE class = ? AND video_file = ?', 
                    (class_name, video_file)
                )
            else:
                cursor.execute('SELECT x, y FROM anomalies WHERE class = ?', (class_name,))
            
            coords = cursor.fetchall()
            conn.close()
            
            if not coords:
                logger.warning(f"No {class_name} detections found")
                return False
            
            # Generate heatmap similar to main method but with class-specific title
            x_coords = [coord[0] for coord in coords]
            y_coords = [coord[1] for coord in coords]
            
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8))
            
            bins_x = min(50, video_width // 40)
            bins_y = min(50, video_height // 40)
            
            heatmap, xedges, yedges = np.histogram2d(
                x_coords, y_coords,
                bins=[bins_x, bins_y],
                range=[[0, video_width], [0, video_height]]
            )
            
            sns.heatmap(
                heatmap.T,
                cmap='Reds',
                cbar=True,
                cbar_kws={'label': f'{class_name.title()} Density'},
                xticklabels=False,
                yticklabels=False,
                ax=ax
            )
            
            emoji = self.get_class_emoji(class_name)
            ax.set_title(f'{emoji} {class_name.title()} Detection Heatmap - Raahi Platform', 
                        fontsize=16, color='white', pad=20)
            ax.set_xlabel('Video Width (pixels)', fontsize=12, color='white')
            ax.set_ylabel('Video Height (pixels)', fontsize=12, color='white')
            
            ax.text(0.02, 0.98, f'{class_name.title()} Detections: {len(coords)}', 
                   transform=ax.transAxes, fontsize=12, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8),
                   color='white')
            
            ax.invert_yaxis()
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                       facecolor='black', edgecolor='none')
            plt.close()
            
            logger.info(f"Class-specific heatmap generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating {class_name} heatmap: {e}")
            return False