/**
 * Clean Voice Emergency System for Raahi
 * Simple, conflict-free emergency voice detection
 */

class CleanVoiceEmergency {
    constructor() {
        this.recognition = null;
        this.isActive = false;
        this.currentLocation = null;
        
        this.emergencyWords = ['help', 'help me', 'save me', 'emergency', 'fire', 'danger'];
        
        this.init();
    }
    
    async init() {
        console.log('🎤 Starting Clean Voice Emergency System...');
        
        try {
            // Get location immediately
            await this.getLocationFast();
            
            // Setup speech recognition
            this.setupVoiceDetection();
            
            // Update nav status
            this.updateNavStatus('active', 'Voice Protection Active');
            
            console.log('✅ Voice Emergency System Ready');
        } catch (error) {
            console.log('Voice system unavailable:', error.message);
            this.updateNavStatus('unavailable', 'Voice Protection Unavailable');
        }
    }
    
    async getLocationFast() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Location not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    console.log('📍 Location ready');
                    resolve(this.currentLocation);
                },
                (error) => {
                    console.log('Location unavailable');
                    resolve(null);
                },
                { enableHighAccuracy: false, timeout: 3000, maximumAge: 60000 }
            );
        });
    }
    
    setupVoiceDetection() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            throw new Error('Speech recognition not supported');
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';
        
        this.recognition.onresult = (event) => {
            const lastResult = event.results[event.results.length - 1];
            if (lastResult.isFinal) {
                const transcript = lastResult[0].transcript.toLowerCase().trim();
                console.log('🎤 Heard:', transcript);
                
                if (this.isEmergencyCall(transcript)) {
                    this.handleEmergency(transcript);
                }
            }
        };
        
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech') {
                console.log('Voice detection error:', event.error);
                setTimeout(() => this.restartVoiceDetection(), 2000);
            }
        };
        
        this.recognition.onend = () => {
            if (this.isActive) {
                setTimeout(() => this.restartVoiceDetection(), 1000);
            }
        };
        
        this.startVoiceDetection();
    }
    
    isEmergencyCall(text) {
        return this.emergencyWords.some(word => text.includes(word));
    }
    
    async handleEmergency(transcript) {
        console.log('🚨 EMERGENCY DETECTED:', transcript);
        
        this.updateNavStatus('emergency', 'EMERGENCY DETECTED!');
        
        const emergencyData = {
            message: `Voice Emergency: "${transcript}"`,
            latitude: this.currentLocation?.latitude,
            longitude: this.currentLocation?.longitude,
            timestamp: new Date().toISOString(),
            trigger_type: 'voice_emergency'
        };
        
        try {
            const response = await fetch('/api/sos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(emergencyData)
            });
            
            if (response.ok) {
                this.showAlert('✅ Emergency alert sent to authorities!', 'success');
                this.updateNavStatus('sent', 'Emergency Alert Sent');
            } else {
                throw new Error('Failed to send');
            }
        } catch (error) {
            console.error('Emergency send failed:', error);
            this.showAlert('❌ Could not send alert. Please call 911!', 'error');
            this.updateNavStatus('failed', 'Alert Failed - Call 911');
        }
        
        // Reset status after 15 seconds
        setTimeout(() => {
            this.updateNavStatus('active', 'Voice Protection Active');
        }, 15000);
    }
    
    startVoiceDetection() {
        if (this.isActive) return;
        
        try {
            this.isActive = true;
            this.recognition.start();
            console.log('🎤 Voice detection started');
        } catch (error) {
            console.log('Could not start voice detection:', error.message);
            this.isActive = false;
        }
    }
    
    restartVoiceDetection() {
        if (!this.isActive) return;
        
        try {
            this.recognition.start();
        } catch (error) {
            // Ignore restart errors
        }
    }
    
    updateNavStatus(status, text) {
        const voiceStatus = document.getElementById('voice-status');
        const micIcon = document.getElementById('mic-icon');
        const statusText = document.getElementById('mic-status-text');
        
        if (!voiceStatus || !micIcon || !statusText) return;
        
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
                voiceStatus.classList.add('text-primary');
                micIcon.className = 'fas fa-check-circle';
                break;
            case 'failed':
                voiceStatus.classList.add('text-warning');
                micIcon.className = 'fas fa-times-circle';
                break;
            case 'unavailable':
                voiceStatus.classList.add('text-muted');
                micIcon.className = 'fas fa-microphone-slash';
                break;
        }
        
        statusText.textContent = text;
    }
    
    showAlert(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        alert.style.cssText = 'top: 80px; right: 20px; z-index: 9999; max-width: 350px; font-weight: bold;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(alert);
        
        setTimeout(() => {
            if (alert.parentElement) alert.remove();
        }, 8000);
    }
}

// Initialize when page loads (only for non-admin pages)
document.addEventListener('DOMContentLoaded', function() {
    if (!window.location.pathname.startsWith('/admin')) {
        setTimeout(() => {
            window.voiceEmergency = new CleanVoiceEmergency();
        }, 1000);
    }
});