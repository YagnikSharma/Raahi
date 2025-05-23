/**
 * Simple Voice Emergency Detection for Raahi
 * Clean implementation without conflicts
 */

class SimpleVoiceDetection {
    constructor() {
        this.isActive = false;
        this.recognition = null;
        this.emergencyWords = ['help', 'help me', 'emergency', 'save me', 'fire', 'police'];
        this.init();
    }
    
    init() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.log('Speech recognition not supported');
            this.showStatus('Speech not supported', 'error');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';
        
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.toLowerCase();
            console.log('Heard:', transcript);
            
            if (this.checkForEmergency(transcript)) {
                this.triggerEmergency(transcript);
            } else {
                this.startListening(); // Continue listening
            }
        };
        
        this.recognition.onerror = (event) => {
            console.log('Speech error:', event.error);
            if (event.error !== 'no-speech') {
                setTimeout(() => this.startListening(), 2000);
            }
        };
        
        this.recognition.onend = () => {
            if (this.isActive) {
                setTimeout(() => this.startListening(), 1000);
            }
        };
        
        this.createUI();
        this.showStatus('Ready to listen', 'success');
    }
    
    checkForEmergency(transcript) {
        return this.emergencyWords.some(word => transcript.includes(word));
    }
    
    triggerEmergency(transcript) {
        console.log('🚨 EMERGENCY DETECTED:', transcript);
        
        // Show emergency alert
        this.showEmergencyAlert(transcript);
        
        // Get location and send SOS
        navigator.geolocation.getCurrentPosition((position) => {
            const sosData = {
                message: `VOICE EMERGENCY: "${transcript}"`,
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                timestamp: new Date().toISOString()
            };
            
            fetch('/api/sos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sosData)
            }).then(() => {
                this.showStatus('Emergency SOS sent!', 'success');
            });
        });
    }
    
    startListening() {
        if (!this.recognition || this.isActive) return;
        
        try {
            this.isActive = true;
            this.recognition.start();
            this.showStatus('Listening for emergencies...', 'listening');
        } catch (error) {
            console.log('Failed to start:', error);
            this.isActive = false;
        }
    }
    
    stopListening() {
        this.isActive = false;
        if (this.recognition) {
            this.recognition.stop();
        }
        this.showStatus('Voice detection stopped', 'stopped');
    }
    
    toggle() {
        if (this.isActive) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    createUI() {
        const ui = document.createElement('div');
        ui.id = 'voice-ui';
        ui.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: white; border: 2px solid #007bff; border-radius: 10px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 10000; min-width: 200px;">
                <div style="text-align: center; margin-bottom: 10px;">
                    <div style="font-size: 2rem;">🎤</div>
                    <div style="font-weight: bold; color: #007bff;">Voice Emergency</div>
                </div>
                <div id="voice-status" style="padding: 8px; border-radius: 5px; text-align: center; font-size: 12px; margin-bottom: 10px;">
                    Initializing...
                </div>
                <button id="voice-toggle" onclick="window.voiceDetection.toggle()" style="width: 100%; padding: 10px; border: none; border-radius: 5px; background: #007bff; color: white; cursor: pointer; font-weight: bold;">
                    Start Listening
                </button>
                <div style="font-size: 10px; color: #666; margin-top: 8px; text-align: center;">
                    Say: "help me", "emergency", "fire"
                </div>
            </div>
        `;
        document.body.appendChild(ui);
    }
    
    showStatus(message, type) {
        const statusEl = document.getElementById('voice-status');
        const toggleBtn = document.getElementById('voice-toggle');
        
        if (!statusEl) return;
        
        statusEl.textContent = message;
        
        // Update colors based on status
        switch (type) {
            case 'listening':
                statusEl.style.background = '#28a745';
                statusEl.style.color = 'white';
                toggleBtn.textContent = 'Stop Listening';
                toggleBtn.style.background = '#dc3545';
                break;
            case 'success':
                statusEl.style.background = '#28a745';
                statusEl.style.color = 'white';
                break;
            case 'error':
                statusEl.style.background = '#dc3545';
                statusEl.style.color = 'white';
                break;
            case 'stopped':
                statusEl.style.background = '#6c757d';
                statusEl.style.color = 'white';
                toggleBtn.textContent = 'Start Listening';
                toggleBtn.style.background = '#007bff';
                break;
            default:
                statusEl.style.background = '#f8f9fa';
                statusEl.style.color = '#333';
        }
    }
    
    showEmergencyAlert(transcript) {
        const alert = document.createElement('div');
        alert.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(220, 53, 69, 0.95); z-index: 20000; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; padding: 30px; border-radius: 15px; text-align: center; max-width: 400px;">
                    <div style="font-size: 4rem; color: #dc3545; margin-bottom: 20px;">🚨</div>
                    <h2 style="color: #dc3545; margin-bottom: 15px;">EMERGENCY DETECTED!</h2>
                    <p style="font-size: 18px; margin-bottom: 20px;"><strong>"${transcript}"</strong></p>
                    <p>Sending emergency alert with your location...</p>
                    <div style="margin-top: 20px;">
                        <div style="border: 4px solid #dc3545; border-top: 4px solid transparent; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                    </div>
                </div>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        document.body.appendChild(alert);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.voiceDetection = new SimpleVoiceDetection();
    console.log('🎤 Simple Voice Emergency Detection ready!');
});