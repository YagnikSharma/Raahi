/**
 * Admin functionality for Raahi safety platform
 * Handles admin dashboard, alerts, and incident management
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeAlerts();
    initializeCharts();
    initializeIncidentVerification();
    initializeCameraControls();
});

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

function initializeAlerts() {
    const alertBadge = document.getElementById('alertBadge');
    const alertsList = document.getElementById('alertsList');
    
    if (alertBadge || alertsList) {
        fetchUnreadAlerts();
        // Check for new notifications every 10 seconds
        setInterval(fetchUnreadAlerts, 10000);
    }
    
    // Bind click handlers for existing alerts
    document.querySelectorAll('.mark-read-btn').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.getAttribute('data-alert-id');
            markAlertAsRead(alertId);
        });
    });
    
    const alertSoundToggle = document.getElementById('alertSoundToggle');
    if (alertSoundToggle) {
        alertSoundToggle.addEventListener('change', function() {
            localStorage.setItem('alertSoundEnabled', this.checked);
        });
        
        const soundEnabled = localStorage.getItem('alertSoundEnabled');
        if (soundEnabled !== null) {
            alertSoundToggle.checked = (soundEnabled === 'true');
        }
    }
}

function fetchUnreadAlerts() {
    const token = localStorage.getItem('jwt_token');
    if (!token) return;
    
    fetch('/api/alerts?unread=true', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(alerts => {
        updateAlertBadge(alerts.length, alerts);
        updateAlertsList(alerts);
    })
    .catch(error => {
        console.error('Error fetching alerts:', error);
    });
}

function updateAlertBadge(count, alerts = []) {
    const alertBadge = document.getElementById('alertBadge');
    const unresolvedCounter = document.getElementById('unresolvedAlertsCount');
    
    if (unresolvedCounter) {
        unresolvedCounter.textContent = count;
    }
    
    if (alertBadge) {
        alertBadge.textContent = count;
        alertBadge.style.display = count > 0 ? 'inline-block' : 'none';
        
        const prevCount = parseInt(alertBadge.getAttribute('data-prev-count') || '0');
        alertBadge.setAttribute('data-prev-count', count.toString());
        
        // Check if new alerts have arrived
        if (count > prevCount && prevCount > 0) {
            const newAlerts = alerts.slice(0, count - prevCount);
            newAlerts.forEach(alert => {
                // Determine style badge
                let style = 'info';
                if (alert.type === 'sos') style = 'danger';
                else if (alert.type === 'detection') style = 'warning';
                
                // Fire a real-time toaster notification
                if (typeof showGlobalToast === 'function') {
                    showGlobalToast(
                        `🚨 SYSTEM DISPATCH: ${alert.type.toUpperCase()}`,
                        alert.message,
                        style
                    );
                }
            });
            
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
        alertsList.innerHTML = `
            <div class="text-center py-4 text-muted">
                <i class="fas fa-circle-check text-success fa-2x mb-2"></i>
                <p class="mb-0 small">Surveillance clear. No unread alerts.</p>
            </div>
        `;
        return;
    }
    
    alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    let alertsHtml = '';
    alerts.forEach(alert => {
        const alertTime = new Date(alert.timestamp).toLocaleTimeString();
        const alertTypeClass = getAlertTypeClass(alert.type);
        
        alertsHtml += `
            <div class="alert ${alertTypeClass} border-0 card mb-3 p-3" role="alert">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-danger rounded-pill small">${formatAlertType(alert.type)}</span>
                            <small class="text-muted" style="font-size: 0.75rem;">${alertTime}</small>
                        </div>
                        <p class="mb-0 text-white small">${alert.message}</p>
                    </div>
                    <button type="button" class="btn-close mark-read-btn" data-alert-id="${alert.id}" aria-label="Mark read"></button>
                </div>
            </div>
        `;
    });
    
    alertsList.innerHTML = alertsHtml;
    
    // Re-attach listener handlers
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
            return 'alert-danger bg-danger bg-opacity-10';
        case 'detection':
            return 'alert-warning bg-warning bg-opacity-10';
        case 'system':
            return 'alert-info bg-info bg-opacity-10';
        default:
            return 'alert-secondary bg-secondary bg-opacity-10';
    }
}

function formatAlertType(alertType) {
    switch (alertType.toLowerCase()) {
        case 'sos':
            return 'SOS';
        case 'detection':
            return 'YOLO';
        case 'system':
            return 'SYS';
        default:
            return alertType.toUpperCase();
    }
}

function playAlertSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.type = 'sawtooth';
    oscillator.frequency.setValueAtTime(520, audioContext.currentTime); // C5 alert
    
    gainNode.gain.setValueAtTime(0.15, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.4);
}

function initializeCharts() {
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
    const labels = [];
    const data = [];
    
    // Generate dates for the last 7 days
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
    }
    
    // Seed sample timeline counts
    for (let i = 0; i < 7; i++) {
        data.push(4 + Math.floor(Math.random() * 8));
    }
    
    const ctx = canvas.getContext('2d');
    
    // Create modern premium gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(79, 70, 229, 0.4)');
    gradient.addColorStop(1, 'rgba(79, 70, 229, 0.0)');
    
    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Surveillance Reports',
                data: data,
                borderColor: '#4f46e5',
                backgroundColor: gradient,
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#4f46e5',
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', precision: 0 },
                    beginAtZero: true
                }
            }
        }
    });
}

function createIncidentTypesChart(canvas) {
    fetch('/api/incidents?limit=100')
    .then(response => response.json())
    .then(incidents => {
        const typeCounts = {};
        incidents.forEach(incident => {
            const key = incident.type || 'unknown';
            typeCounts[key] = (typeCounts[key] || 0) + 1;
        });
        
        const labels = Object.keys(typeCounts).map(type => 
            type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')
        );
        const data = Object.values(typeCounts);
        
        // Elegant obsidian chart colors
        const colors = [
            '#ef4444', // Red (fire, emergency)
            '#f97316', // Orange (violence, weapon)
            '#f59e0b', // Yellow (visibility, low light)
            '#4f46e5', // Indigo (others)
            '#06b6d4'  // Cyan (system triggers)
        ];
        
        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderColor: '#0f1117',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                cutout: '70%'
            }
        });
    })
    .catch(error => console.error('Types chart error:', error));
}

function createSafetyDistributionChart(canvas) {
    fetch('/api/heatmap')
    .then(response => response.json())
    .then(zones => {
        const safetyLevels = [0, 0, 0, 0];
        zones.forEach(zone => {
            safetyLevels[zone.safety_level]++;
        });
        
        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Safe', 'Caution', 'Caution+', 'Unsafe'],
                datasets: [{
                    data: safetyLevels,
                    backgroundColor: [
                        '#10b981', // green
                        '#f59e0b', // yellow
                        '#f97316', // orange
                        '#ef4444'  // red
                    ],
                    borderRadius: 6,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#9ca3af' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af', precision: 0 },
                        beginAtZero: true
                    }
                }
            }
        });
    })
    .catch(error => console.error('Safety distribution error:', error));
}

function initializeIncidentVerification() {
    const verifyButtons = document.querySelectorAll('.verify-incident-btn');
    verifyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const incidentId = this.getAttribute('data-incident-id');
            const verifyForm = document.getElementById(`verifyForm-${incidentId}`);
            if (verifyForm) verifyForm.submit();
        });
    });
}

function initializeCameraControls() {
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
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    return '';
}
