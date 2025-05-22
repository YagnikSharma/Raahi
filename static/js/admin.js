/**
 * Admin functionality for Raahi safety platform
 * Handles admin dashboard, alerts, and incident management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers
    initializeTooltips();
    
    // Initialize alert system
    initializeAlerts();
    
    // Initialize charts if they exist
    initializeCharts();
    
    // Initialize incident verification
    initializeIncidentVerification();
    
    // Initialize camera controls
    initializeCameraControls();
});

function initializeTooltips() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

function initializeAlerts() {
    // Check for unread alerts periodically
    const alertBadge = document.getElementById('alertBadge');
    const alertsList = document.getElementById('alertsList');
    
    if (alertBadge || alertsList) {
        fetchUnreadAlerts();
        
        // Update alerts every 30 seconds
        setInterval(fetchUnreadAlerts, 30000);
    }
    
    // Mark as read buttons
    document.querySelectorAll('.mark-read-btn').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            markAlertAsRead(alertId);
        });
    });
    
    // Alert sound toggle
    const alertSoundToggle = document.getElementById('alertSoundToggle');
    if (alertSoundToggle) {
        alertSoundToggle.addEventListener('change', function() {
            localStorage.setItem('alertSoundEnabled', this.checked);
        });
        
        // Load saved preference
        const soundEnabled = localStorage.getItem('alertSoundEnabled');
        if (soundEnabled !== null) {
            alertSoundToggle.checked = (soundEnabled === 'true');
        }
    }
}

function fetchUnreadAlerts() {
    // Only run if we have a JWT token (for authenticated endpoints)
    const token = localStorage.getItem('jwt_token');
    if (!token) return;
    
    fetch('/api/alerts?unread=true', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
        .then(response => response.json())
        .then(alerts => {
            updateAlertBadge(alerts.length);
            updateAlertsList(alerts);
        })
        .catch(error => {
            console.error('Error fetching alerts:', error);
        });
}

function updateAlertBadge(count) {
    const alertBadge = document.getElementById('alertBadge');
    if (alertBadge) {
        alertBadge.textContent = count;
        alertBadge.style.display = count > 0 ? 'inline-block' : 'none';
        
        // Play sound if new alerts arrived and sound is enabled
        const prevCount = parseInt(alertBadge.getAttribute('data-prev-count') || '0');
        alertBadge.setAttribute('data-prev-count', count.toString());
        
        if (count > prevCount) {
            const soundEnabled = localStorage.getItem('alertSoundEnabled');
            if (soundEnabled === 'true' || soundEnabled === null) {
                playAlertSound();
            }
        }
    }
}

function updateAlertsList(alerts) {
    const alertsList = document.getElementById('alertsList');
    if (!alertsList) return;
    
    if (alerts.length === 0) {
        alertsList.innerHTML = '<div class="text-center py-4">No unread alerts</div>';
        return;
    }
    
    // Sort alerts by timestamp (newest first)
    alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Update alerts list
    let alertsHtml = '';
    
    alerts.forEach(alert => {
        const alertTime = new Date(alert.timestamp).toLocaleString();
        const alertTypeClass = getAlertTypeClass(alert.type);
        
        alertsHtml += `
            <div class="alert ${alertTypeClass} alert-dismissible fade show" role="alert">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="alert-heading">${formatAlertType(alert.type)}</h6>
                        <p class="mb-0">${alert.message}</p>
                        <small>${alertTime}</small>
                    </div>
                    <div>
                        <button type="button" class="btn-close mark-read-btn" data-alert-id="${alert.id}" aria-label="Mark as read"></button>
                    </div>
                </div>
            </div>
        `;
    });
    
    alertsList.innerHTML = alertsHtml;
    
    // Re-attach mark as read event listeners
    document.querySelectorAll('.mark-read-btn').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            markAlertAsRead(alertId);
        });
    });
}

function markAlertAsRead(alertId) {
    fetch(`/admin/alert/${alertId}/mark-read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update alerts
                fetchUnreadAlerts();
            }
        })
        .catch(error => {
            console.error('Error marking alert as read:', error);
        });
}

function getAlertTypeClass(alertType) {
    switch (alertType.toLowerCase()) {
        case 'sos':
            return 'alert-danger';
        case 'detection':
            return 'alert-warning';
        case 'system':
            return 'alert-info';
        default:
            return 'alert-secondary';
    }
}

function formatAlertType(alertType) {
    switch (alertType.toLowerCase()) {
        case 'sos':
            return 'SOS Emergency';
        case 'detection':
            return 'Anomaly Detected';
        case 'system':
            return 'System Alert';
        default:
            return alertType.charAt(0).toUpperCase() + alertType.slice(1);
    }
}

function playAlertSound() {
    // Create and play a notification sound
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A5
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.5);
}

function initializeCharts() {
    // Initialize dashboard charts if they exist
    const incidentTrendChart = document.getElementById('incidentTrendChart');
    if (incidentTrendChart) {
        createIncidentTrendChart(incidentTrendChart);
    }
    
    const incidentTypesChart = document.getElementById('incidentTypesChart');
    if (incidentTypesChart) {
        createIncidentTypesChart(incidentTypesChart);
    }
    
    const safetyDistributionChart = document.getElementById('safetyDistributionChart');
    if (safetyDistributionChart) {
        createSafetyDistributionChart(safetyDistributionChart);
    }
}

function createIncidentTrendChart(canvas) {
    // Sample data - in real implementation, this would be fetched from the API
    const labels = [];
    const data = [];
    
    // Generate last 7 days
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
    }
    
    // Random data for demonstration
    for (let i = 0; i < 7; i++) {
        data.push(Math.floor(Math.random() * 10));
    }
    
    // Create chart
    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Incidents',
                data: data,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function createIncidentTypesChart(canvas) {
    fetch('/api/incidents?limit=100')
        .then(response => response.json())
        .then(incidents => {
            // Count incidents by type
            const typeCounts = {};
            incidents.forEach(incident => {
                typeCounts[incident.type] = (typeCounts[incident.type] || 0) + 1;
            });
            
            // Prepare data for chart
            const labels = Object.keys(typeCounts).map(type => 
                type.charAt(0).toUpperCase() + type.slice(1)
            );
            
            const data = Object.values(typeCounts);
            
            // Set colors based on incident types
            const colors = labels.map(label => {
                const lowerLabel = label.toLowerCase();
                if (lowerLabel === 'fire' || lowerLabel === 'explosion') {
                    return '#dc3545'; // danger
                } else if (lowerLabel === 'fight' || lowerLabel === 'weapon') {
                    return '#ffc107'; // warning
                } else if (lowerLabel === 'darkness') {
                    return '#6c757d'; // secondary
                } else {
                    return '#0d6efd'; // primary
                }
            });
            
            // Create chart
            new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: colors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching incident data for chart:', error);
        });
}

function createSafetyDistributionChart(canvas) {
    fetch('/api/heatmap')
        .then(response => response.json())
        .then(zones => {
            // Count zones by safety level
            const safetyLevels = [0, 0, 0, 0]; // [Safe, Caution, High Caution, Unsafe]
            
            zones.forEach(zone => {
                safetyLevels[zone.safety_level]++;
            });
            
            // Create chart
            new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: ['Safe', 'Caution', 'High Caution', 'Unsafe'],
                    datasets: [{
                        label: 'Number of Zones',
                        data: safetyLevels,
                        backgroundColor: [
                            '#28a745', // success
                            '#ffc107', // warning
                            '#fd7e14', // orange
                            '#dc3545'  // danger
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching safety zone data for chart:', error);
        });
}

function initializeIncidentVerification() {
    // Incident verification buttons
    const verifyButtons = document.querySelectorAll('.verify-incident-btn');
    
    verifyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const incidentId = this.getAttribute('data-incident-id');
            const verifyForm = document.getElementById(`verifyForm-${incidentId}`);
            
            if (verifyForm) {
                verifyForm.submit();
            }
        });
    });
}

function initializeCameraControls() {
    // Camera status update buttons
    const cameraStatusBtns = document.querySelectorAll('.camera-status-btn');
    
    cameraStatusBtns.forEach(button => {
        button.addEventListener('click', function() {
            const cameraId = this.getAttribute('data-camera-id');
            const statusValue = this.getAttribute('data-status');
            const statusForm = document.getElementById(`cameraStatusForm-${cameraId}`);
            
            if (statusForm) {
                const statusInput = statusForm.querySelector('input[name="status"]');
                statusInput.value = statusValue;
                statusForm.submit();
            }
        });
    });
}

function getCsrfToken() {
    // Get CSRF token from meta tag
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    return '';
}
