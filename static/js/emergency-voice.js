/**
 * Emergency Voice Recognition System for Raahi Homepage
 * Clean implementation following user specifications
 */

class EmergencyVoiceSystem {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentLocation = null;
        
        // Emergency keywords as specified
        this.emergencyKeywords = ["help", "help me", "save me"];
        
        this.initialize();
    }
    
    initialize() {
        console.log('🔴 Emergency Voice System: Initializing...');
        
        // Get location first
        this.getCurrentLocation();
        
        // Setup speech recognition
        if (this.setupSpeechRecognition()) {
            this.startListening();
            this.showStatus('🎤 Voice Protection: Listening for emergencies', 'success');
        } else {
            this.showStatus('❌ Voice not supported on this browser', 'warning');
        }
    }
    
    setupSpeechRecognition() {
        // Check for browser support
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            return false;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';
        
        // Handle speech results
        this.recognition.onresult = (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
            console.log('🎤 Heard:', transcript);
            
            // Check for emergency keywords
            if (this.isEmergencyCall(transcript)) {
                this.handleEmergency(transcript);
            }
        };
        
        // Handle errors gracefully
        this.recognition.onerror = (event) => {
            if (event.error !== 'no-speech' && event.error !== 'aborted') {
                console.log('Voice error:', event.error);
                // Restart after error
                setTimeout(() => this.restartListening(), 2000);
            }
        };
        
        // Restart when ended
        this.recognition.onend = () => {
            if (this.isListening) {
                this.restartListening();
            }
        };
        
        return true;
    }
    
    getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    console.log('📍 Location ready for emergencies');
                },
                (error) => {
                    console.log('📍 Location unavailable:', error.message);
                },
                { timeout: 10000, maximumAge: 300000, enableHighAccuracy: true }
            );
        }
    }
    
    isEmergencyCall(transcript) {
        return this.emergencyKeywords.some(keyword => transcript.includes(keyword));
    }
    
    async handleEmergency(transcript) {
        console.log('🚨 EMERGENCY DETECTED:', transcript);
        
        // Stop listening temporarily to avoid multiple triggers
        this.stopListening();
        
        // Show immediate feedback
        this.showStatus('🚨 EMERGENCY DETECTED! Sending alert...', 'danger');
        
        try {
            // Send emergency alert to admin
            await this.sendAlertToAdmin(transcript);
            
            // Log emergency instance
            await this.logEmergencyInstance(transcript);
            
            // Show success
            this.showStatus('✅ Emergency alert sent successfully!', 'success');
            
        } catch (error) {
            console.error('Failed to send emergency alert:', error);
            this.showStatus('❌ Alert failed - Please call 911 immediately!', 'danger');
        }
        
        // Resume listening after 10 seconds
        setTimeout(() => {
            this.startListening();
            this.showStatus('🎤 Voice Protection: Listening for emergencies', 'success');
        }, 10000);
    }
    
    async sendAlertToAdmin(keyword) {
        const alertData = {
            message: `Voice Emergency: "${keyword}" detected`,
            latitude: this.currentLocation?.latitude,
            longitude: this.currentLocation?.longitude,
            timestamp: new Date().toISOString(),
            trigger_type: 'voice_emergency'
        };
        
        const response = await fetch('/api/sos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(alertData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    }
    
    async logEmergencyInstance(keyword) {
        const logData = {
            keyword: keyword,
            latitude: this.currentLocation?.latitude,
            longitude: this.currentLocation?.longitude,
            timestamp: new Date().toISOString(),
            user_agent: navigator.userAgent
        };
        
        // Log to database via API (optional - for analytics)
        try {
            await fetch('/api/emergency-log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(logData)
            });
        } catch (error) {
            // Logging failure shouldn't stop emergency response
            console.log('Emergency logged locally only');
        }
    }
    
    startListening() {
        if (!this.recognition || this.isListening) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
        } catch (error) {
            console.log('Start listening error:', error);
            this.isListening = false;
        }
    }
    
    stopListening() {
        if (!this.recognition || !this.isListening) return;
        
        this.isListening = false;
        try {
            this.recognition.stop();
        } catch (error) {
            // Ignore stop errors
        }
    }
    
    restartListening() {
        this.stopListening();
        setTimeout(() => {
            this.startListening();
        }, 1000);
    }
    
    showStatus(message, type) {
        // Create or update status indicator
        let statusElement = document.getElementById('voice-status-indicator');
        
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = 'voice-status-indicator';
            statusElement.style.cssText = `
                position: fixed;
                top: 70px;
                right: 20px;
                z-index: 9999;
                max-width: 300px;
                padding: 10px 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            `;
            document.body.appendChild(statusElement);
        }
        
        // Set colors based on type
        const colors = {
            success: { bg: '#d4edda', text: '#155724', border: '#c3e6cb' },
            danger: { bg: '#f8d7da', text: '#721c24', border: '#f5c6cb' },
            warning: { bg: '#fff3cd', text: '#856404', border: '#ffeaa7' }
        };
        
        const color = colors[type] || colors.success;
        statusElement.style.backgroundColor = color.bg;
        statusElement.style.color = color.text;
        statusElement.style.border = `1px solid ${color.border}`;
        statusElement.textContent = message;
        
        // Auto-hide non-critical messages
        if (type !== 'danger') {
            setTimeout(() => {
                if (statusElement.textContent === message) {
                    statusElement.style.opacity = '0.7';
                }
            }, 5000);
        }
    }
}

// Initialize emergency voice system when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Only run on homepage/landing page (not admin pages)
    if (!window.location.pathname.startsWith('/admin')) {
        setTimeout(() => {
            window.emergencyVoice = new EmergencyVoiceSystem();
        }, 1000);
    }
});