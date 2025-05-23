/**
 * Clean Voice Emergency System for Raahi
 * Single instance, no conflicts, working implementation
 */

class VoiceEmergency {
    constructor() {
        // Only run on non-admin pages
        if (window.location.pathname.startsWith('/admin')) return;
        
        this.recognition = null;
        this.isListening = false;
        this.currentLocation = null;
        this.speechToTextMode = false;
        this.speechCallback = null;
        
        this.emergencyWords = ['help', 'help me', 'save me', 'emergency', 'fire', 'danger', 'rescue'];
        
        this.initialize();
    }
    
    initialize() {
        console.log('🎤 Voice Emergency System starting...');
        
        // Get location
        this.getLocation();
        
        // Setup speech recognition
        this.setupSpeech();
        
        // Update nav
        this.updateNav('active', 'Voice Protection Active');
        
        // Start listening
        this.startListening();
        
        console.log('✅ Voice system ready');
    }
    
    getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    this.currentLocation = {
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude
                    };
                    console.log('📍 Location ready');
                },
                () => console.log('📍 Location unavailable'),
                { timeout: 3000, maximumAge: 60000 }
            );
        }
    }
    
    setupSpeech() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.updateNav('unavailable', 'Voice Not Supported');
            return;
        }
        
        const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new Speech();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            const text = result[0].transcript.toLowerCase().trim();
            
            // Speech-to-text mode
            if (this.speechToTextMode && this.speechCallback) {
                this.speechCallback(result[0].transcript, result.isFinal);
                if (result.isFinal) {
                    this.stopSpeechToText();
                }
                return;
            }
            
            // Emergency detection
            if (result.isFinal && this.isEmergency(text)) {
                this.handleEmergency(text);
            }
        };
        
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.log('Voice error:', event.error);
            }
            this.restartListening();
        };
        
        this.recognition.onend = () => {
            this.restartListening();
        };
    }
    
    isEmergency(text) {
        return this.emergencyWords.some(word => text.includes(word));
    }
    
    async handleEmergency(text) {
        console.log('🚨 EMERGENCY:', text);
        this.updateNav('emergency', 'EMERGENCY DETECTED!');
        
        try {
            const response = await fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `Voice Emergency: "${text}"`,
                    latitude: this.currentLocation?.latitude,
                    longitude: this.currentLocation?.longitude,
                    timestamp: new Date().toISOString(),
                    trigger_type: 'voice_emergency'
                })
            });
            
            if (response.ok) {
                this.showAlert('✅ Emergency alert sent!', 'success');
                this.updateNav('sent', 'Emergency Alert Sent');
            } else {
                throw new Error('Send failed');
            }
        } catch (error) {
            this.showAlert('❌ Could not send alert. Call 911!', 'error');
            this.updateNav('failed', 'Alert Failed - Call 911');
        }
        
        setTimeout(() => this.updateNav('active', 'Voice Protection Active'), 10000);
    }
    
    startListening() {
        if (!this.recognition || this.isListening || this.speechToTextMode) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
        } catch (error) {
            this.isListening = false;
        }
    }
    
    restartListening() {
        if (this.speechToTextMode) return;
        
        this.isListening = false;
        setTimeout(() => {
            if (!this.speechToTextMode) {
                this.startListening();
            }
        }, 2000);
    }
    
    // Speech-to-text functionality
    startSpeechToText(callback) {
        if (!this.recognition) {
            callback('Speech not available', true);
            return;
        }
        
        this.speechToTextMode = true;
        this.speechCallback = callback;
        this.isListening = false;
        
        try {
            this.recognition.stop();
            setTimeout(() => {
                this.recognition.start();
            }, 500);
        } catch (error) {
            this.speechToTextMode = false;
            callback('Speech error', true);
        }
    }
    
    stopSpeechToText() {
        this.speechToTextMode = false;
        this.speechCallback = null;
        
        try {
            this.recognition.stop();
        } catch (error) {
            // Ignore
        }
        
        setTimeout(() => this.startListening(), 1000);
    }
    
    updateNav(status, text) {
        const voice = document.getElementById('voice-status');
        const icon = document.getElementById('mic-icon');
        const label = document.getElementById('mic-status-text');
        
        if (!voice || !icon || !label) return;
        
        voice.className = 'nav-link';
        
        switch (status) {
            case 'active':
                voice.classList.add('text-success');
                icon.className = 'fas fa-microphone';
                break;
            case 'emergency':
                voice.classList.add('text-danger');
                icon.className = 'fas fa-exclamation-triangle';
                break;
            case 'sent':
                voice.classList.add('text-primary');
                icon.className = 'fas fa-check-circle';
                break;
            case 'failed':
                voice.classList.add('text-warning');
                icon.className = 'fas fa-times-circle';
                break;
            case 'unavailable':
                voice.classList.add('text-muted');
                icon.className = 'fas fa-microphone-slash';
                break;
        }
        
        label.textContent = text;
    }
    
    showAlert(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        alert.style.cssText = 'top: 80px; right: 20px; z-index: 9999; max-width: 300px;';
        alert.innerHTML = `${message} <button type="button" class="btn-close" onclick="this.remove()"></button>`;
        
        document.body.appendChild(alert);
        setTimeout(() => alert.remove(), 6000);
    }
}

// Add speech-to-text to textarea
function enableSpeechToText(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea || !window.voiceSystem) return;
    
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-outline-primary btn-sm mt-2';
    btn.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
    
    let recording = false;
    
    btn.onclick = () => {
        if (!recording) {
            recording = true;
            btn.innerHTML = '<i class="fas fa-stop"></i> Stop speaking';
            btn.className = 'btn btn-danger btn-sm mt-2';
            
            window.voiceSystem.startSpeechToText((text, final) => {
                textarea.value = text;
                if (final) {
                    recording = false;
                    btn.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
                    btn.className = 'btn btn-outline-primary btn-sm mt-2';
                }
            });
        } else {
            recording = false;
            btn.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
            btn.className = 'btn btn-outline-primary btn-sm mt-2';
            window.voiceSystem.stopSpeechToText();
        }
    };
    
    textarea.parentNode.appendChild(btn);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.voiceSystem = new VoiceEmergency();
        
        // Add to SOS form if exists
        if (document.getElementById('sosMessage')) {
            enableSpeechToText('sosMessage');
        }
    }, 1000);
});