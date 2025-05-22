/**
 * Map functionality for Raahi safety platform
 * Handles map initialization, safety zones, and incident markers
 */

class SafetyMap {
    constructor(mapElementId, options = {}) {
        this.mapElementId = mapElementId;
        this.map = null;
        this.zonesLayer = null;
        this.incidentsLayer = null;
        this.camerasLayer = null;
        this.userMarker = null;
        
        // Default options
        this.options = {
            defaultLat: 28.6139,  // New Delhi
            defaultLng: 77.2090,
            defaultZoom: 13,
            enableUserLocation: true,
            showCameras: true,
            showIncidents: true,
            ...options
        };
        
        // Initialize the map
        this.initialize();
    }
    
    initialize() {
        // Create the map with default center
        this.map = L.map(this.mapElementId).setView(
            [this.options.defaultLat, this.options.defaultLng], 
            this.options.defaultZoom
        );
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);
        
        // Create layer groups
        this.zonesLayer = L.layerGroup().addTo(this.map);
        this.incidentsLayer = L.layerGroup().addTo(this.map);
        this.camerasLayer = L.layerGroup().addTo(this.map);
        
        // Add layer controls
        const overlays = {
            "Safety Zones": this.zonesLayer,
            "Incidents": this.incidentsLayer,
            "Cameras": this.camerasLayer
        };
        
        L.control.layers(null, overlays).addTo(this.map);
        
        // Get user location if enabled
        if (this.options.enableUserLocation) {
            this.getUserLocation();
        }
    }
    
    loadSafetyZones() {
        // Clear existing zones
        this.zonesLayer.clearLayers();
        
        // Fetch zones from API
        fetch('/api/heatmap')
            .then(response => response.json())
            .then(zones => {
                zones.forEach(zone => {
                    const zoneCircle = L.circle([zone.latitude, zone.longitude], {
                        color: zone.color,
                        fillColor: zone.color,
                        fillOpacity: 0.3,
                        radius: 500  // in meters
                    }).addTo(this.zonesLayer);
                    
                    // Safety level labels
                    const safetyLabels = ['Safe', 'Caution', 'High Caution', 'Unsafe'];
                    
                    // Add popup
                    zoneCircle.bindPopup(`
                        <h6>Safety Zone</h6>
                        <p>Safety Level: 
                            <span class="badge ${this.getSafetyBadgeClass(zone.safety_level)}">
                                ${safetyLabels[zone.safety_level]}
                            </span>
                        </p>
                        <p>Incident Count: ${zone.incident_count}</p>
                        <p>Last Updated: ${new Date(zone.last_updated).toLocaleString()}</p>
                    `);
                });
            })
            .catch(error => {
                console.error('Error loading safety zones:', error);
            });
    }
    
    loadIncidents() {
        // Clear existing incidents
        this.incidentsLayer.clearLayers();
        
        // Custom marker icon for incidents
        const incidentIcon = L.divIcon({
            html: '<i class="fas fa-exclamation-circle"></i>',
            className: 'incident-marker',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        // Fetch incidents from API
        fetch('/api/incidents')
            .then(response => response.json())
            .then(incidents => {
                incidents.forEach(incident => {
                    const incidentMarker = L.marker([incident.latitude, incident.longitude], {
                        icon: incidentIcon
                    }).addTo(this.incidentsLayer);
                    
                    // Add popup
                    incidentMarker.bindPopup(`
                        <h6>${this.capitalizeFirst(incident.type)}</h6>
                        <p>Detected: ${new Date(incident.timestamp).toLocaleString()}</p>
                        <p>Confidence: ${Math.round(incident.confidence * 100)}%</p>
                        <p>Status: ${incident.is_verified ? 'Verified' : 'Unverified'}</p>
                    `);
                });
            })
            .catch(error => {
                console.error('Error loading incidents:', error);
            });
    }
    
    loadCameras() {
        // Clear existing cameras
        this.camerasLayer.clearLayers();
        
        // Custom marker icon for cameras
        const cameraIcon = L.divIcon({
            html: '<i class="fas fa-video"></i>',
            className: 'camera-marker',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        // Fetch cameras from API
        fetch('/api/cameras')
            .then(response => response.json())
            .then(cameras => {
                cameras.forEach(camera => {
                    const cameraMarker = L.marker([camera.latitude, camera.longitude], {
                        icon: cameraIcon
                    }).addTo(this.camerasLayer);
                    
                    // Add popup
                    cameraMarker.bindPopup(`
                        <h6>${camera.name}</h6>
                        <p>Location: ${camera.location}</p>
                        <p>Status: ${camera.status}</p>
                    `);
                });
            })
            .catch(error => {
                console.error('Error loading cameras:', error);
            });
    }
    
    getUserLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                // Success callback
                position => {
                    const userLat = position.coords.latitude;
                    const userLng = position.coords.longitude;
                    
                    // Add user marker
                    const userIcon = L.divIcon({
                        html: '<i class="fas fa-user-circle"></i>',
                        className: 'user-marker',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    });
                    
                    // Remove existing user marker if any
                    if (this.userMarker) {
                        this.map.removeLayer(this.userMarker);
                    }
                    
                    this.userMarker = L.marker([userLat, userLng], {
                        icon: userIcon
                    }).addTo(this.map);
                    
                    // Pan to user location
                    this.map.panTo([userLat, userLng]);
                    
                    // Get safety information for user location
                    this.checkLocationSafety(userLat, userLng, 'Your Location');
                },
                // Error callback
                error => {
                    console.error('Error getting user location:', error);
                }
            );
        }
    }
    
    checkLocationSafety(lat, lng, locationName = 'Selected Location') {
        fetch(`/api/safety/${lat}/${lng}`)
            .then(response => response.json())
            .then(data => {
                // If we have a user marker, update its popup
                if (locationName === 'Your Location' && this.userMarker) {
                    this.userMarker.bindPopup(`
                        <h6>${locationName}</h6>
                        <p>Safety Level: 
                            <span class="badge ${this.getSafetyBadgeClass(data.safety_level)}">
                                ${data.safety_label}
                            </span>
                        </p>
                        <p>${data.incident_count} recent incidents in this area.</p>
                    `).openPopup();
                } else {
                    // Add a temporary marker for searched locations
                    const marker = L.marker([lat, lng]).addTo(this.map);
                    marker.bindPopup(`
                        <h6>${locationName}</h6>
                        <p>Safety Level: 
                            <span class="badge ${this.getSafetyBadgeClass(data.safety_level)}">
                                ${data.safety_label}
                            </span>
                        </p>
                        <p>${data.incident_count} recent incidents in this area.</p>
                    `).openPopup();
                    
                    // Remove marker after 10 seconds
                    setTimeout(() => {
                        this.map.removeLayer(marker);
                    }, 10000);
                }
                
                // Return data for external use
                return data;
            })
            .catch(error => {
                console.error('Error checking location safety:', error);
            });
    }
    
    searchLocation(location) {
        if (!location) return;
        
        // In a real implementation, this would use a geocoding service
        // For demo purposes, we'll simulate with a location near the map center
        const mapCenter = this.map.getCenter();
        const lat = mapCenter.lat + (Math.random() * 0.01 - 0.005);
        const lng = mapCenter.lng + (Math.random() * 0.01 - 0.005);
        
        // Pan map to location
        this.map.panTo([lat, lng]);
        
        // Check safety of the location
        return this.checkLocationSafety(lat, lng, location);
    }
    
    // Helper methods
    capitalizeFirst(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
    
    getSafetyBadgeClass(safetyLevel) {
        const classes = [
            'bg-success',   // Safe (0)
            'bg-warning',   // Caution (1)
            'bg-orange',    // High Caution (2)
            'bg-danger'     // Unsafe (3)
        ];
        return classes[Math.min(safetyLevel, 3)];
    }
}

// Export for use in other scripts
window.SafetyMap = SafetyMap;
