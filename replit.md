# Raahi: AI-Powered Public Safety Platform

## Overview

Raahi is an intelligent public safety platform that leverages computer vision and AI to detect emergencies in urban environments. The system monitors CCTV camera feeds to identify various safety incidents (fires, assaults, etc.), classifies urban areas by safety levels, and visualizes this data through an interactive safety map.

The platform consists of a Flask-based web application with both public-facing components (safety maps, incident reports) and an administrative dashboard for monitoring and managing the system.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

Raahi uses a modern web application architecture with clear separation of concerns:

1. **Backend Framework**: Flask serves as the primary web framework, organized using the Blueprint pattern to separate different functional areas (public, admin, auth, API).

2. **Database**: SQLAlchemy ORM with a flexible database configuration that can work with SQLite for development and PostgreSQL for production.

3. **Authentication**: Uses Flask-Login for session management and JWT for API authentication, providing both traditional web session security and token-based API access.

4. **Frontend**: Server-side rendered HTML templates using Jinja2, enhanced with Bootstrap CSS framework and client-side JavaScript for interactive components.

5. **AI Detection**: A modular computer vision system based on YOLO for incident detection from CCTV feeds (currently mocked for demonstration).

This layered architecture allows for separation of concerns, making the codebase easier to maintain and extend.

## Key Components

### Models

The system uses the following key data models:

1. **User**: Administrators who can access the dashboard and verify incidents
2. **Camera**: CCTV cameras with location information
3. **Incident**: Detected safety incidents with location, confidence, and status
4. **Zone**: Geographic areas classified by safety level based on incident history
5. **Alert**: System notifications for administrators

### Routes and Views

The application is organized into distinct functional areas:

1. **Public Routes** (`routes/public.py`): 
   - Home page
   - Safety map visualization
   - Public incident browsing

2. **Admin Routes** (`routes/admin.py`):
   - Administrative dashboard
   - Incident verification and management
   - Camera monitoring
   - Alert management

3. **Auth Routes** (`routes/auth.py`):
   - User authentication
   - Password management

4. **API Routes** (`routes/api.py`):
   - Data endpoints for maps and incidents
   - Detection endpoints for processing video feeds

### Detection System

The detection system is modularized into:

1. **YOLO Detection** (`detection/yolo.py`): 
   - Uses YOLOv8 for object and incident detection
   - Currently mocked for demonstration purposes

2. **Audio Processing** (`detection/audio.py`):
   - Detects emergency keywords in audio streams
   - Also mocked for demonstration

### Frontend Components

The frontend utilizes several JavaScript modules:

1. **Map Visualization** (`static/js/map.js`):
   - Displays safety zones and incidents using Leaflet.js

2. **Admin Dashboard** (`static/js/admin.js`):
   - Manages administrative functions

3. **Detection Visualization** (`static/js/detection.js`):
   - Processes and visualizes detection results on camera feeds

4. **SOS System** (`static/js/sos.js`):
   - Handles emergency alerts and geolocation

## Data Flow

1. **Incident Detection Flow**:
   - CCTV cameras capture footage
   - Frames are processed through the YOLO model
   - Detected incidents are stored in the database
   - Safety zones are updated based on incident density
   - Administrators are alerted for verification

2. **User Interaction Flow**:
   - Public users can view the safety map and incidents
   - Administrators log in to access the dashboard
   - Administrators can verify incidents and manage alerts
   - API endpoints provide data for external applications

## External Dependencies

The system relies on the following key external libraries and frameworks:

1. **Flask & Extensions**:
   - Flask-SQLAlchemy for database ORM
   - Flask-Login for authentication
   - Flask-JWT-Extended for API authentication
   - Flask-Mail for sending password reset emails

2. **Frontend Libraries**:
   - Bootstrap CSS framework for UI components
   - Leaflet.js for map visualization
   - Font Awesome for icons

3. **AI & Computer Vision**:
   - YOLOv8 model for object detection (currently mocked)
   - Potential future integration with real CCTV systems

## Deployment Strategy

The application is configured for deployment on the Replit platform:

1. **Web Server**: Gunicorn serves as the WSGI server for handling HTTP requests in production.

2. **Database**: While the system can use SQLite for development, it's configured to optionally connect to PostgreSQL for production use via environment variables.

3. **Environment Configuration**: The application uses environment variables for configuration, making it easy to secure sensitive information like API keys and database credentials.

4. **Scaling**: The application is designed to scale horizontally with stateless application servers and a shared database.

5. **Static Assets**: CSS and JavaScript files are served directly by the web server for performance.

The deployment workflow involves:
- Starting the Gunicorn server to handle HTTP requests
- Automatic database table creation on startup
- Configurable logging for monitoring and debugging