/**
 * Single Voice Emergency System for Raahi
 * Clean implementation with microphone indicator
 */

let voiceSystem = null;

class VoiceSystem {
    constructor() {
        // Only run on non-admin pages
        if (window.location.pathname.startsWith('/admin')) return;
        
        this.recognition = null;
        this.isListening = false;
        this.currentLocation = null;
        this.speechMode = false;
        this.speechCallback = null;
        
        this.emergencyWords = ['help', 'help me', 'emergency', 'fire', 'danger', 'rescue', 'save me'];
        
        this.init();
    }
    
    init() {
        console.log('Voice system starting...');
        
        // Get location first
        this.getLocation();
        
        // Setup speech recognition
        if (this.setupSpeech()) {
            this.updateIndicator('active', 'Voice Protection Active');
            this.startListening();
        } else {
            this.updateIndicator('unavailable', 'Voice Not Supported');
        }
    }
    
    getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    this.currentLocation = {
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude
                    };
                },
                () => console.log('Location unavailable'),
                { timeout: 5000, maximumAge: 60000 }
            );
        }
    }
    
    setupSpeech() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            return false;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';
        
        this.recognition.onresult = (event) => {
            const text = event.results[0][0].transcript.toLowerCase().trim();
            
            if (this.speechMode && this.speechCallback) {
                this.speechCallback(event.results[0][0].transcript);
                this.stopSpeechToText();
                return;
            }
            
            // Check for emergency words
            if (this.isEmergency(text)) {
                this.handleEmergency(text);
            }
        };
        
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.log('Speech error:', event.error);
            }
            this.restartListening();
        };
        
        this.recognition.onend = () => {
            this.restartListening();
        };
        
        return true;
    }
    
    isEmergency(text) {
        return this.emergencyWords.some(word => text.includes(word));
    }
    
    async handleEmergency(text) {
        console.log('EMERGENCY DETECTED:', text);
        this.updateIndicator('emergency', 'Emergency Detected!');
        
        try {
            const response = await fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `Voice Emergency: "${text}"`,
                    latitude: this.currentLocation?.latitude,
                    longitude: this.currentLocation?.longitude,
                    timestamp: new Date().toISOString(),
                    trigger_type: 'voice_detection'
                })
            });
            
            if (response.ok) {
                this.showAlert('Emergency alert sent successfully!', 'success');
                this.updateIndicator('sent', 'Alert Sent');
            } else {
                throw new Error('Failed to send');
            }
        } catch (error) {
            this.showAlert('Failed to send alert. Please call 911!', 'danger');
            this.updateIndicator('failed', 'Alert Failed');
        }
        
        // Reset after 10 seconds
        setTimeout(() => {
            this.updateIndicator('active', 'Voice Protection Active');
        }, 10000);
    }
    
    startListening() {
        if (!this.recognition || this.isListening || this.speechMode) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
        } catch (error) {
            this.isListening = false;
        }
    }
    
    restartListening() {
        if (this.speechMode) return;
        
        this.isListening = false;
        setTimeout(() => {
            if (!this.speechMode) {
                this.startListening();
            }
        }, 1000);
    }
    
    // Speech-to-text for forms
    startSpeechToText(callback) {
        if (!this.recognition) {
            callback('Speech not available');
            return;
        }
        
        this.speechMode = true;
        this.speechCallback = callback;
        this.isListening = false;
        
        this.recognition.stop();
        
        setTimeout(() => {
            try {
                this.recognition.start();
            } catch (error) {
                this.speechMode = false;
                callback('Speech error');
            }
        }, 500);
    }
    
    stopSpeechToText() {
        this.speechMode = false;
        this.speechCallback = null;
        this.recognition.stop();
        
        setTimeout(() => {
            this.startListening();
        }, 1000);
    }
    
    updateIndicator(status, text) {
        const indicator = document.getElementById('voice-status');
        const icon = document.getElementById('mic-icon');
        const label = document.getElementById('mic-status-text');
        
        if (!indicator || !icon || !label) return;
        
        // Reset classes
        indicator.className = 'nav-link';
        
        switch (status) {
            case 'active':
                indicator.classList.add('text-success');
                icon.className = 'fas fa-microphone';
                break;
            case 'emergency':
                indicator.classList.add('text-danger');
                icon.className = 'fas fa-exclamation-triangle';
                break;
            case 'sent':
                indicator.classList.add('text-primary');
                icon.className = 'fas fa-check-circle';
                break;
            case 'failed':
                indicator.classList.add('text-warning');
                icon.className = 'fas fa-times-circle';
                break;
            case 'unavailable':
                indicator.classList.add('text-muted');
                icon.className = 'fas fa-microphone-slash';
                break;
        }
        
        label.textContent = text;
    }
    
    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible position-fixed`;
        alertDiv.style.cssText = 'top: 80px; right: 20px; z-index: 9999; max-width: 400px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Add speech-to-text to any textarea
function addSpeechToText(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea || !voiceSystem || !voiceSystem.recognition) return;
    
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline-primary btn-sm mt-2';
    button.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
    
    let isRecording = false;
    
    button.onclick = () => {
        if (!isRecording) {
            isRecording = true;
            button.innerHTML = '<i class="fas fa-stop"></i> Stop recording';
            button.className = 'btn btn-danger btn-sm mt-2';
            
            voiceSystem.startSpeechToText((text) => {
                textarea.value = text;
                isRecording = false;
                button.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
                button.className = 'btn btn-outline-primary btn-sm mt-2';
            });
        } else {
            isRecording = false;
            button.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
            button.className = 'btn btn-outline-primary btn-sm mt-2';
            voiceSystem.stopSpeechToText();
        }
    };
    
    textarea.parentNode.appendChild(button);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for page to fully load
    setTimeout(() => {
        voiceSystem = new VoiceSystem();
        
        // Add speech-to-text to SOS message field if it exists
        if (document.getElementById('sosMessage')) {
            addSpeechToText('sosMessage');
        }
    }, 1000);
});