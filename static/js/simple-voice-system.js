/**
 * Simple Voice System for Raahi - No Conflicts
 * Clean implementation with proper speech recognition integration
 */

class SimpleVoiceSystem {
    constructor() {
        this.recognition = null;
        this.isActive = false;
        this.emergencyKeywords = ['help', 'help me', 'save me', 'emergency', 'fire', 'danger'];
        this.speechCallback = null;
        this.currentLocation = null;
        
        // Only initialize on non-admin pages
        if (!window.location.pathname.startsWith('/admin')) {
            this.init();
        }
    }
    
    async init() {
        console.log('🎤 Starting Simple Voice System...');
        
        try {
            // Get location
            this.getCurrentLocation();
            
            // Setup speech recognition
            this.setupSpeechRecognition();
            
            // Update nav indicator
            this.updateNavStatus('active', 'Voice Protection Active');
            
            // Start listening
            this.startListening();
            
            console.log('✅ Voice System Ready');
            
        } catch (error) {
            console.log('Voice unavailable:', error.message);
            this.updateNavStatus('unavailable', 'Voice Protection Unavailable');
        }
    }
    
    getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    console.log('📍 Location obtained');
                },
                () => console.log('📍 Location unavailable'),
                { enableHighAccuracy: false, timeout: 3000, maximumAge: 60000 }
            );
        }
    }
    
    setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            throw new Error('Speech recognition not supported');
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false; // Changed to false to avoid conflicts
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onresult = (event) => {
            const lastResult = event.results[event.results.length - 1];
            const transcript = lastResult[0].transcript.toLowerCase().trim();
            
            // Handle speech-to-text callback
            if (this.speechCallback) {
                this.speechCallback(transcript, lastResult.isFinal);
                return;
            }
            
            // Handle emergency detection (only for final results)
            if (lastResult.isFinal && this.isEmergencyCall(transcript)) {
                this.handleEmergency(transcript);
            }
        };
        
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.log('Voice error:', event.error);
            }
            this.restartIfNeeded();
        };
        
        this.recognition.onend = () => {
            this.restartIfNeeded();
        };
    }
    
    startListening() {
        if (this.isActive || !this.recognition) return;
        
        try {
            this.isActive = true;
            this.recognition.start();
            console.log('🎤 Listening started');
        } catch (error) {
            console.log('Could not start listening');
            this.isActive = false;
        }
    }
    
    restartIfNeeded() {
        if (this.isActive && !this.speechCallback) {
            setTimeout(() => {
                if (this.isActive && !this.speechCallback) {
                    try {
                        this.recognition.start();
                    } catch (error) {
                        // Ignore restart errors
                    }
                }
            }, 2000);
        }
    }
    
    isEmergencyCall(text) {
        return this.emergencyKeywords.some(keyword => text.includes(keyword));
    }
    
    async handleEmergency(transcript) {
        console.log('🚨 EMERGENCY:', transcript);
        
        this.updateNavStatus('emergency', 'EMERGENCY DETECTED!');
        
        const data = {
            message: `Voice Emergency: "${transcript}"`,
            latitude: this.currentLocation?.latitude,
            longitude: this.currentLocation?.longitude,
            timestamp: new Date().toISOString(),
            trigger_type: 'voice_emergency'
        };
        
        try {
            const response = await fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                this.showAlert('✅ Emergency alert sent!', 'success');
                this.updateNavStatus('sent', 'Emergency Alert Sent');
            } else {
                throw new Error('Send failed');
            }
        } catch (error) {
            this.showAlert('❌ Could not send alert. Call 911!', 'error');
            this.updateNavStatus('failed', 'Alert Failed - Call 911');
        }
        
        setTimeout(() => {
            this.updateNavStatus('active', 'Voice Protection Active');
        }, 10000);
    }
    
    // Speech-to-text for forms
    startSpeechToText(callback) {
        if (!this.recognition) {
            callback('Speech not available', true);
            return;
        }
        
        this.speechCallback = callback;
        this.isActive = false; // Stop emergency listening
        
        try {
            this.recognition.stop(); // Stop current recognition
            setTimeout(() => {
                this.recognition.start(); // Start new session for speech-to-text
                console.log('🎤 Speech-to-text started');
            }, 500);
        } catch (error) {
            console.log('Speech-to-text error');
        }
    }
    
    stopSpeechToText() {
        this.speechCallback = null;
        this.recognition.stop();
        
        // Restart emergency listening
        setTimeout(() => {
            this.startListening();
        }, 1000);
        
        console.log('🎤 Speech-to-text stopped');
    }
    
    updateNavStatus(status, text) {
        const voiceStatus = document.getElementById('voice-status');
        const micIcon = document.getElementById('mic-icon');
        const statusText = document.getElementById('mic-status-text');
        
        if (!voiceStatus || !micIcon || !statusText) return;
        
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
        alert.style.cssText = 'top: 80px; right: 20px; z-index: 9999; max-width: 300px;';
        alert.innerHTML = `${message} <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>`;
        
        document.body.appendChild(alert);
        setTimeout(() => alert.remove(), 6000);
    }
}

// Helper function to add speech-to-text to any textarea
function addSpeechToText(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea || !window.simpleVoice) return;
    
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline-primary btn-sm mt-2';
    button.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
    
    let recording = false;
    
    button.onclick = function() {
        if (!recording) {
            recording = true;
            button.innerHTML = '<i class="fas fa-stop"></i> Stop speaking';
            button.className = 'btn btn-danger btn-sm mt-2';
            
            window.simpleVoice.startSpeechToText((text, isFinal) => {
                textarea.value = text;
                if (isFinal) {
                    recording = false;
                    button.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
                    button.className = 'btn btn-outline-primary btn-sm mt-2';
                    window.simpleVoice.stopSpeechToText();
                }
            });
        } else {
            recording = false;
            button.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
            button.className = 'btn btn-outline-primary btn-sm mt-2';
            window.simpleVoice.stopSpeechToText();
        }
    };
    
    textarea.parentNode.appendChild(button);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        window.simpleVoice = new SimpleVoiceSystem();
        
        // Add speech-to-text to SOS message if it exists
        if (document.getElementById('sosMessage')) {
            addSpeechToText('sosMessage');
        }
    }, 1000);
});