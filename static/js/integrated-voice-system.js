/**
 * Integrated Voice Emergency System for Raahi
 * Clean, efficient voice detection integrated into navigation
 */

class IntegratedVoiceSystem {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.currentLocation = null;
        this.isInitialized = false;
        
        // Emergency keywords
        this.emergencyKeywords = [
            'help', 'help me', 'save me', 'emergency', 'fire', 
            'rescue', 'urgent', 'police', 'ambulance', 'danger'
        ];
        
        this.init();
    }
    
    async init() {
        if (this.isInitialized) return;
        
        console.log('🎤 Initializing Voice Emergency System...');
        
        try {
            // Request permissions
            await this.requestPermissions();
            
            // Setup speech recognition
            this.setupSpeechRecognition();
            
            // Start location tracking
            this.startLocationTracking();
            
            // Update navigation indicator
            this.updateNavIndicator('active', 'Voice Protection Active');
            
            // Start listening
            this.startListening();
            
            this.isInitialized = true;
            console.log('✅ Voice Emergency System Ready');
            
        } catch (error) {
            console.error('❌ Voice system initialization failed:', error);
            this.updateNavIndicator('error', 'Voice Protection Unavailable');
        }
    }
    
    async requestPermissions() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop()); // Stop immediately, we just needed permission
            return true;
        } catch (error) {
            throw new Error('Microphone permission denied');
        }
    }
    
    setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            throw new Error('Speech recognition not supported');
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript.toLowerCase().trim();
                
                if (event.results[i].isFinal && this.detectEmergency(transcript)) {
                    console.log('🚨 Emergency detected:', transcript);
                    this.triggerEmergencyResponse(transcript);
                }
            }
        };
        
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.log('Speech recognition error:', event.error);
                this.restartRecognition();
            }
        };
        
        this.recognition.onend = () => {
            if (this.isListening) {
                this.restartRecognition();
            }
        };
    }
    
    detectEmergency(transcript) {
        return this.emergencyKeywords.some(keyword => transcript.includes(keyword));
    }
    
    async triggerEmergencyResponse(transcript) {
        this.updateNavIndicator('emergency', 'EMERGENCY DETECTED!');
        
        // Get fast location
        const location = await this.getFastLocation();
        
        // Send emergency alert
        const emergencyData = {
            message: `VOICE EMERGENCY: "${transcript}"`,
            latitude: location?.latitude,
            longitude: location?.longitude,
            timestamp: new Date().toISOString(),
            trigger_type: 'voice_detection',
            auto_triggered: true,
            priority: 'CRITICAL'
        };
        
        try {
            const response = await fetch('/api/sos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(emergencyData)
            });
            
            if (response.ok) {
                this.showSuccessNotification('Emergency alert sent successfully!');
                this.updateNavIndicator('sent', 'Emergency Alert Sent');
                
                // Offer additional description
                setTimeout(() => this.offerDescriptionCapture(), 2000);
            } else {
                throw new Error('Failed to send emergency alert');
            }
        } catch (error) {
            console.error('Emergency alert failed:', error);
            this.showErrorNotification('Failed to send emergency alert. Please call 911 directly!');
            this.updateNavIndicator('error', 'Alert Failed - Call 911');
        }
        
        // Reset after 10 seconds
        setTimeout(() => {
            this.updateNavIndicator('active', 'Voice Protection Active');
        }, 10000);
    }
    
    async getFastLocation() {
        // Use cached location if recent
        if (this.currentLocation && 
            (Date.now() - new Date(this.currentLocation.timestamp).getTime() < 60000)) {
            return this.currentLocation;
        }
        
        // Try to get fresh location with short timeout
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    resolve,
                    reject,
                    { enableHighAccuracy: true, timeout: 2000, maximumAge: 30000 }
                );
            });
            
            this.currentLocation = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                timestamp: new Date().toISOString()
            };
            
            return this.currentLocation;
        } catch (error) {
            console.log('Could not get fresh location, using cached or default');
            return this.currentLocation;
        }
    }
    
    startLocationTracking() {
        if (!navigator.geolocation) return;
        
        // Get initial location
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    timestamp: new Date().toISOString()
                };
                console.log('📍 Location obtained');
            },
            (error) => console.log('Location unavailable:', error.message),
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
        );
        
        // Continuous tracking
        navigator.geolocation.watchPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    timestamp: new Date().toISOString()
                };
            },
            (error) => console.log('Location tracking error:', error.message),
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 120000 }
        );
    }
    
    startListening() {
        if (!this.recognition || this.isListening) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
            console.log('🎤 Voice detection started');
        } catch (error) {
            console.error('Failed to start voice detection:', error);
            this.isListening = false;
        }
    }
    
    restartRecognition() {
        if (!this.isListening) return;
        
        setTimeout(() => {
            try {
                if (this.recognition && this.isListening) {
                    this.recognition.start();
                }
            } catch (error) {
                // Ignore restart errors
            }
        }, 1000);
    }
    
    updateNavIndicator(status, text) {
        const micIcon = document.getElementById('mic-icon');
        const statusText = document.getElementById('mic-status-text');
        const voiceStatus = document.getElementById('voice-status');
        
        if (!micIcon || !statusText || !voiceStatus) return;
        
        // Reset classes
        voiceStatus.className = 'nav-link';
        
        switch (status) {
            case 'active':
                voiceStatus.classList.add('text-success');
                micIcon.className = 'fas fa-microphone';
                break;
            case 'emergency':
                voiceStatus.classList.add('text-danger');
                micIcon.className = 'fas fa-exclamation-triangle';
                break;
            case 'sent':
                voiceStatus.classList.add('text-info');
                micIcon.className = 'fas fa-check-circle';
                break;
            case 'error':
                voiceStatus.classList.add('text-warning');
                micIcon.className = 'fas fa-exclamation-triangle';
                break;
        }
        
        statusText.textContent = text;
    }
    
    offerDescriptionCapture() {
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div class="modal fade show" style="display: block; background: rgba(0,0,0,0.5);" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-info text-white">
                            <h5 class="modal-title">Additional Details</h5>
                            <button type="button" class="btn-close btn-close-white" onclick="this.closest('.modal').remove()"></button>
                        </div>
                        <div class="modal-body">
                            <p>Would you like to provide more details about your emergency?</p>
                            <button class="btn btn-primary me-2" onclick="window.voiceSystem.startDescriptionCapture()">
                                🎤 Speak Details
                            </button>
                            <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">
                                Skip
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Auto-remove after 15 seconds
        setTimeout(() => {
            if (modal.parentElement) modal.remove();
        }, 15000);
    }
    
    startDescriptionCapture() {
        const modal = document.querySelector('.modal');
        if (modal) modal.remove();
        
        // Create description capture interface
        const captureModal = document.createElement('div');
        captureModal.innerHTML = `
            <div class="modal fade show" style="display: block; background: rgba(0,0,0,0.5);" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">🎤 Describing Emergency...</h5>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-3">
                                <div class="spinner-border text-primary" role="status"></div>
                                <p class="mt-2">Listening for details...</p>
                                <p id="captured-text" class="text-muted small"></p>
                            </div>
                            <button class="btn btn-success" onclick="window.voiceSystem.finishDescriptionCapture()">
                                Stop & Send
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(captureModal);
        
        // Start description capture
        this.captureDescription();
    }
    
    captureDescription() {
        // Implementation for capturing additional description
        console.log('Starting description capture...');
        // This would use speech recognition to capture additional details
    }
    
    finishDescriptionCapture() {
        const modal = document.querySelector('.modal');
        if (modal) modal.remove();
        
        this.showSuccessNotification('Additional details captured successfully!');
    }
    
    showSuccessNotification(message) {
        this.showNotification(message, 'success');
    }
    
    showErrorNotification(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        notification.innerHTML = `
            <strong>${type === 'success' ? '✅' : '❌'}</strong> ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) notification.remove();
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if not admin page
    if (!window.location.pathname.startsWith('/admin')) {
        window.voiceSystem = new IntegratedVoiceSystem();
    }
});