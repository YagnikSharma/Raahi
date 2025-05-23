/**
 * Raahi Voice Emergency System
 * Complete voice detection system for emergency calls and speech-to-text
 */

class RaahiVoiceSystem {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentLocation = null;
        this.speechToTextCallback = null;
        
        // Emergency keywords that trigger instant SOS
        this.emergencyKeywords = [
            'help', 'help me', 'save me', 'emergency', 'fire', 
            'danger', 'rescue', 'urgent', 'police', 'ambulance'
        ];
        
        this.init();
    }
    
    async init() {
        // Only initialize on non-admin pages
        if (window.location.pathname.startsWith('/admin')) {
            return;
        }
        
        console.log('🎤 Initializing Raahi Voice System...');
        
        try {
            // Get location first
            await this.setupLocation();
            
            // Setup speech recognition
            this.setupSpeechRecognition();
            
            // Start listening for emergencies
            this.startEmergencyListening();
            
            // Update navigation indicator
            this.updateNavIndicator('active', 'Voice Protection Active');
            
            console.log('✅ Raahi Voice System Ready');
            
        } catch (error) {
            console.log('Voice system unavailable:', error.message);
            this.updateNavIndicator('unavailable', 'Voice Protection Unavailable');
        }
    }
    
    async setupLocation() {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve(null);
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
                () => {
                    console.log('📍 Location unavailable');
                    resolve(null);
                },
                { enableHighAccuracy: false, timeout: 3000, maximumAge: 60000 }
            );
        });
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
            const lastResult = event.results[event.results.length - 1];
            const transcript = lastResult[0].transcript.toLowerCase().trim();
            
            // Handle emergency detection (only for final results)
            if (lastResult.isFinal && this.isEmergencyCall(transcript)) {
                this.handleEmergency(transcript);
            }
            
            // Handle speech-to-text callback (for interim and final results)
            if (this.speechToTextCallback) {
                this.speechToTextCallback(transcript, lastResult.isFinal);
            }
        };
        
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.log('Voice error:', event.error);
                this.restartListening();
            }
        };
        
        this.recognition.onend = () => {
            if (this.isListening) {
                this.restartListening();
            }
        };
    }
    
    isEmergencyCall(text) {
        return this.emergencyKeywords.some(keyword => text.includes(keyword));
    }
    
    async handleEmergency(transcript) {
        console.log('🚨 EMERGENCY DETECTED:', transcript);
        
        this.updateNavIndicator('emergency', 'EMERGENCY DETECTED!');
        
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
                this.showNotification('✅ Emergency alert sent to authorities!', 'success');
                this.updateNavIndicator('sent', 'Emergency Alert Sent');
            } else {
                throw new Error('Send failed');
            }
        } catch (error) {
            console.error('Emergency send failed:', error);
            this.showNotification('❌ Could not send alert. Please call 911!', 'error');
            this.updateNavIndicator('failed', 'Alert Failed - Call 911');
        }
        
        // Reset after 10 seconds
        setTimeout(() => {
            this.updateNavIndicator('active', 'Voice Protection Active');
        }, 10000);
    }
    
    startEmergencyListening() {
        if (this.isListening) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
            console.log('🎤 Emergency listening started');
        } catch (error) {
            console.log('Could not start listening:', error.message);
            this.isListening = false;
        }
    }
    
    restartListening() {
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
    
    // Speech-to-text functionality for forms
    startSpeechToText(callback) {
        if (!this.recognition) {
            callback('Speech recognition not available', true);
            return;
        }
        
        this.speechToTextCallback = callback;
        console.log('🎤 Speech-to-text started');
    }
    
    stopSpeechToText() {
        this.speechToTextCallback = null;
        console.log('🎤 Speech-to-text stopped');
    }
    
    updateNavIndicator(status, text) {
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
                voiceStatus.style.animation = 'blink 0.5s infinite';
                break;
            case 'sent':
                voiceStatus.classList.add('text-primary');
                micIcon.className = 'fas fa-check-circle';
                voiceStatus.style.animation = 'none';
                break;
            case 'failed':
                voiceStatus.classList.add('text-warning');
                micIcon.className = 'fas fa-times-circle';
                voiceStatus.style.animation = 'none';
                break;
            case 'unavailable':
                voiceStatus.classList.add('text-muted');
                micIcon.className = 'fas fa-microphone-slash';
                break;
        }
        
        statusText.textContent = text;
    }
    
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
        notification.style.cssText = 'top: 80px; right: 20px; z-index: 9999; max-width: 350px; font-weight: bold;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) notification.remove();
        }, 8000);
    }
}

// Helper function for speech-to-text in forms
function addSpeechToTextToTextarea(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea || !window.raahiVoice) return;
    
    const speechButton = document.createElement('button');
    speechButton.type = 'button';
    speechButton.className = 'btn btn-outline-primary btn-sm mt-2';
    speechButton.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
    
    let isRecording = false;
    
    speechButton.onclick = function() {
        if (!isRecording) {
            isRecording = true;
            speechButton.innerHTML = '<i class="fas fa-stop"></i> Stop speaking';
            speechButton.classList.remove('btn-outline-primary');
            speechButton.classList.add('btn-danger');
            
            window.raahiVoice.startSpeechToText((transcript, isFinal) => {
                textarea.value = transcript;
                if (isFinal) {
                    isRecording = false;
                    speechButton.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
                    speechButton.classList.remove('btn-danger');
                    speechButton.classList.add('btn-outline-primary');
                    window.raahiVoice.stopSpeechToText();
                }
            });
        } else {
            isRecording = false;
            speechButton.innerHTML = '<i class="fas fa-microphone"></i> Speak to type';
            speechButton.classList.remove('btn-danger');
            speechButton.classList.add('btn-outline-primary');
            window.raahiVoice.stopSpeechToText();
        }
    };
    
    textarea.parentNode.appendChild(speechButton);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        window.raahiVoice = new RaahiVoiceSystem();
        
        // Add speech-to-text to SOS message textarea if it exists
        if (document.getElementById('sosMessage')) {
            addSpeechToTextToTextarea('sosMessage');
        }
    }, 1000);
});

// Add CSS for blinking animation
const style = document.createElement('style');
style.textContent = `
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.5; }
    }
`;
document.head.appendChild(style);