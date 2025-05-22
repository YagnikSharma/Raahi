/**
 * SOS functionality for Raahi safety platform
 * Handles emergency SOS triggers and location sharing
 */

class SOSSystem {
    constructor(options = {}) {
        // Default options
        this.options = {
            autoGetLocation: true,
            sendToServer: true,
            enableSound: true,
            ...options
        };
        
        // Internal state
        this.userLocation = null;
        this.locationStatus = 'unknown';
        this.isEmergency = false;
        
        // Initialize if requested
        if (this.options.autoGetLocation) {
            this.getUserLocation();
        }
    }
    
    // Initialize SOS button functionality
    initSOSButton(buttonElement, sosModal, locationStatusElement, sendButton) {
        // Store elements
        this.sosButton = buttonElement;
        this.sosModal = sosModal;
        this.locationStatusElement = locationStatusElement;
        this.sendButton = sendButton;
        
        // Configure button
        if (this.sosButton) {
            this.sosButton.addEventListener('click', () => {
                this.getUserLocation();
                if (this.sosModal && typeof bootstrap !== 'undefined') {
                    const modal = new bootstrap.Modal(this.sosModal);
                    modal.show();
                }
            });
        }
        
        // Configure send button
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => {
                this.triggerSOS();
            });
        }
    }
    
    // Get user's current location
    getUserLocation() {
        if (navigator.geolocation) {
            this.updateLocationStatus('Obtaining your location...', 'info');
            
            navigator.geolocation.getCurrentPosition(
                // Success callback
                position => {
                    this.userLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    this.locationStatus = 'available';
                    
                    this.updateLocationStatus(
                        `Location obtained: ${this.userLocation.latitude.toFixed(6)}, ${this.userLocation.longitude.toFixed(6)}`,
                        'success'
                    );
                    
                    if (this.sendButton) {
                        this.sendButton.disabled = false;
                    }
                },
                // Error callback
                error => {
                    console.error('Error getting location:', error);
                    this.locationStatus = 'error';
                    
                    this.updateLocationStatus(
                        `Error getting location: ${error.message}`,
                        'danger'
                    );
                    
                    if (this.sendButton) {
                        this.sendButton.disabled = true;
                    }
                }
            );
        } else {
            this.locationStatus = 'unsupported';
            this.updateLocationStatus('Geolocation is not supported by your browser', 'danger');
            if (this.sendButton) {
                this.sendButton.disabled = true;
            }
        }
    }
    
    // Update location status display
    updateLocationStatus(message, status) {
        if (this.locationStatusElement) {
            this.locationStatusElement.innerHTML = message;
            this.locationStatusElement.className = `alert alert-${status}`;
        }
    }
    
    // Trigger SOS alert
    triggerSOS(message = '') {
        if (!this.userLocation) {
            alert('Cannot send SOS: Location information is unavailable');
            return false;
        }
        
        // Get message if not provided
        if (!message && document.getElementById('sosMessage')) {
            message = document.getElementById('sosMessage').value;
        }
        
        if (!message) {
            message = 'Emergency SOS triggered';
        }
        
        // Set emergency state
        this.isEmergency = true;
        
        // Play emergency sound if enabled
        if (this.options.enableSound) {
            this.playEmergencySound();
        }
        
        // Send to server if enabled
        if (this.options.sendToServer) {
            return this.sendSOSToServer(message);
        }
        
        return true;
    }
    
    // Send SOS alert to server
    sendSOSToServer(message) {
        return fetch('/api/sos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                latitude: this.userLocation.latitude,
                longitude: this.userLocation.longitude,
                message: message
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.onSOSSent(true, 'SOS alert sent successfully! Emergency services have been notified.');
                    return true;
                } else {
                    this.onSOSSent(false, `Error sending SOS: ${data.message}`);
                    return false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.onSOSSent(false, 'Failed to send SOS alert. Please try again or call emergency services directly.');
                return false;
            });
    }
    
    // Callback when SOS is sent
    onSOSSent(success, message) {
        if (success) {
            alert(message);
            // Close the modal if open
            if (this.sosModal && typeof bootstrap !== 'undefined') {
                const modal = bootstrap.Modal.getInstance(this.sosModal);
                if (modal) {
                    modal.hide();
                }
            }
        } else {
            alert(message);
        }
    }
    
    // Play emergency sound
    playEmergencySound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Create oscillator for alarm sound
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.type = 'triangle';
            oscillator.frequency.setValueAtTime(780, audioContext.currentTime);
            
            // Create "wailing" effect for alarm
            oscillator.frequency.linearRampToValueAtTime(580, audioContext.currentTime + 0.2);
            oscillator.frequency.linearRampToValueAtTime(780, audioContext.currentTime + 0.4);
            oscillator.frequency.linearRampToValueAtTime(580, audioContext.currentTime + 0.6);
            oscillator.frequency.linearRampToValueAtTime(780, audioContext.currentTime + 0.8);
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.01, audioContext.currentTime + 1);
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 1);
        } catch (error) {
            console.error('Error playing emergency sound:', error);
        }
    }
    
    // Cancel active SOS
    cancelSOS() {
        this.isEmergency = false;
    }
}

// Export for use in other scripts
window.SOSSystem = SOSSystem;

// Initialize SOS system on page load
document.addEventListener('DOMContentLoaded', function() {
    const sos = new SOSSystem();
    
    // Initialize SOS button if elements exist
    const sosBtn = document.getElementById('sosBtn');
    const sosModal = document.getElementById('sosModal');
    const locationStatus = document.getElementById('locationStatus');
    const sendSosBtn = document.getElementById('sendSosBtn');
    
    if (sosBtn && sosModal && locationStatus && sendSosBtn) {
        sos.initSOSButton(sosBtn, sosModal, locationStatus, sendSosBtn);
    }
});
