#!/usr/bin/env python3
"""
Video Anomaly Detection System - Main Runner
Launch the complete video analysis web application
"""

from video_app import app

if __name__ == '__main__':
    print("🚀 Starting Video Anomaly Detection System...")
    print("📹 Upload videos to detect: Fire, Violence, Explosions")
    print("🌐 Open your browser to: http://localhost:5000")
    print("")
    
    app.run(host='0.0.0.0', port=5000, debug=True)