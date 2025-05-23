/**
 * Enhanced SOS System for Raahi Safety Platform
 * Real-time voice detection and emergency response
 */

class EnhancedSOSSystem {
    constructor(options = {}) {
        this.isListening = false;
        this.recognition = null;
        this.currentLocation = null;
        this.locationWatcher = null;
        
        // Enhanced emergency keywords with variations
        this.emergencyKeywords = [
            'help', 'help me', 'i need help', 'please help',
            'save me', 'save', 'rescue me', 'rescue',
            'emergency', 'urgent', 'crisis',
            'fire', 'burning', 'smoke',
            'police', 'call police', 'need police',
            'ambulance', 'medical emergency', 'heart attack',
            'attack', 'robbery', 'thief', 'danger',
            'accident', 'crash', 'injured', 'hurt',
            'trapped', 'stuck', 'can\'t move'
        ];
        
        this.init();
    }
    
    init() {
        this.initSpeechRecognition();
        this.startLocationTracking();
        this.setupAutoStart();
    }
    
    initSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('Speech recognition not supported in this browser');
            this.showFallbackSOS();
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Enhanced configuration for better detection
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.recognition.maxAlternatives = 5;
        this.recognition.serviceURI = null; // Use default service
        
        this.recognition.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                
                // Check all alternatives for emergency keywords
                for (let j = 0; j < result.length; j++) {
                    const transcript = result[j].transcript.toLowerCase().trim();
                    const confidence = result[j].confidence;
                    
                    console.log(`Voice detected: "${transcript}" (confidence: ${confidence})`);
                    
                    if (this.detectEmergencyKeywords(transcript, confidence)) {
                        this.handleEmergencyDetected(transcript, confidence);
                        break;
                    }
                }
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'not-allowed') {
                this.showMicrophonePermissionError();
            } else {
                // Restart recognition automatically
                setTimeout(() => {
                    if (this.isListening) {
                        this.startListening();
                    }
                }, 1000);
            }
        };
        
        this.recognition.onend = () => {
            // Only restart if still supposed to be listening and not already starting
            if (this.isListening && this.recognition.readyState !== 'running') {
                setTimeout(() => {
                    if (this.isListening && this.recognition.readyState !== 'running') {
                        try {
                            this.recognition.start();
                        } catch (error) {
                            console.log('Recognition restart failed:', error);
                            this.isListening = false;
                        }
                    }
                }, 1000);
            }
        };
    }
    
    detectEmergencyKeywords(transcript, confidence = 1) {
        // Enhanced keyword matching with fuzzy logic
        for (const keyword of this.emergencyKeywords) {
            if (transcript.includes(keyword)) {
                // Higher confidence for exact matches
                if (confidence > 0.6 || keyword.length <= 4) { // Short words like "help" need less confidence
                    return true;
                }
            }
        }
        
        // Check for partial matches with high confidence
        if (confidence > 0.8) {
            const urgentWords = ['help', 'save', 'emergency', 'fire', 'police'];
            for (const word of urgentWords) {
                if (transcript.includes(word.substring(0, 3))) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    handleEmergencyDetected(transcript, confidence) {
        console.log(`🚨 EMERGENCY DETECTED: "${transcript}" (${Math.round(confidence * 100)}%)`);
        
        // Show immediate visual feedback
        this.showEmergencyAlert(transcript, confidence);
        
        // Auto-trigger SOS with enhanced data
        this.triggerEnhancedSOS(transcript, confidence);
        
        // Play emergency sound
        this.playEmergencySound();
    }
    
    startLocationTracking() {
        if (!navigator.geolocation) {
            console.warn('Geolocation not supported');
            return;
        }
        
        // Get immediate location
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date().toISOString()
                };
                console.log('Location obtained:', this.currentLocation);
            },
            (error) => {
                console.error('Location error:', error);
            },
            { 
                enableHighAccuracy: true, 
                timeout: 5000, 
                maximumAge: 10000 
            }
        );
        
        // Continuous location tracking for emergencies
        this.locationWatcher = navigator.geolocation.watchPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date().toISOString()
                };
            },
            (error) => {
                console.error('Location tracking error:', error);
            },
            { 
                enableHighAccuracy: true, 
                timeout: 10000, 
                maximumAge: 30000 
            }
        );
    }
    
    setupAutoStart() {
        // Don't auto-start to avoid conflicts - let user manually activate
        console.log('🎤 Voice emergency detection ready - click to activate');
        this.showNotification('🎤 Voice emergency detection is ready! Click the microphone button to activate.', 'info');
    }
    
    startListening() {
        if (!this.recognition) {
            this.showFallbackSOS();
            return;
        }
        
        // Don't start if already listening
        if (this.isListening) {
            console.log('🎤 Already listening for emergencies');
            return;
        }
        
        try {
            this.isListening = true;
            this.recognition.start();
            this.updateUI();
            console.log('🎤 Voice emergency detection started');
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
            this.isListening = false;
            this.showMicrophonePermissionError();
        }
    }
    
    stopListening() {
        if (this.recognition && this.isListening) {
            this.isListening = false;
            this.recognition.stop();
            this.updateUI();
            console.log('🎤 Voice emergency detection stopped');
        }
    }
    
    async triggerEnhancedSOS(triggerPhrase = '', confidence = 1) {
        try {
            // Gather comprehensive emergency data
            const emergencyData = {
                // Core emergency info
                message: `VOICE EMERGENCY DETECTED: "${triggerPhrase}" (${Math.round(confidence * 100)}% confidence)`,
                trigger_type: 'voice_detection',
                trigger_phrase: triggerPhrase,
                detection_confidence: confidence,
                
                // Location data
                latitude: this.currentLocation?.latitude,
                longitude: this.currentLocation?.longitude,
                location_accuracy: this.currentLocation?.accuracy,
                location_timestamp: this.currentLocation?.timestamp,
                
                // System data
                timestamp: new Date().toISOString(),
                user_agent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                
                // Emergency context
                auto_triggered: true,
                priority: 'CRITICAL',
                response_required: true,
                
                // Additional data
                page_url: window.location.href,
                session_duration: Date.now() - performance.timing.navigationStart,
                battery_level: await this.getBatteryLevel(),
                connection_type: this.getConnectionType()
            };
            
            console.log('Sending enhanced SOS data:', emergencyData);
            
            // Send to server
            const response = await fetch('/api/sos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(emergencyData)
            });
            
            if (response.ok) {
                this.showSOSSuccess();
                console.log('✅ Emergency SOS sent successfully');
            } else {
                throw new Error('SOS request failed');
            }
            
        } catch (error) {
            console.error('❌ Failed to send SOS:', error);
            this.showSOSError();
        }
    }
    
    async getBatteryLevel() {
        try {
            if ('getBattery' in navigator) {
                const battery = await navigator.getBattery();
                return Math.round(battery.level * 100);
            }
        } catch (error) {
            console.log('Battery API not available');
        }
        return null;
    }
    
    getConnectionType() {
        try {
            if ('connection' in navigator) {
                return navigator.connection.effectiveType || navigator.connection.type;
            }
        } catch (error) {
            console.log('Connection API not available');
        }
        return 'unknown';
    }
    
    showEmergencyAlert(phrase, confidence) {
        // Create prominent emergency overlay
        const alertDiv = document.createElement('div');
        alertDiv.className = 'emergency-alert-overlay';
        alertDiv.innerHTML = `
            <div class="emergency-alert-content">
                <div class="emergency-icon">🚨</div>
                <h2>EMERGENCY DETECTED!</h2>
                <p><strong>"${phrase}"</strong></p>
                <p>Confidence: ${Math.round(confidence * 100)}%</p>
                <p>Sending SOS alert to emergency services...</p>
                <div class="emergency-countdown">
                    <span id="countdown">5</span> seconds to cancel
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="btn btn-warning">
                    Cancel Alert
                </button>
            </div>
        `;
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .emergency-alert-overlay {
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(255, 0, 0, 0.9);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-family: Arial, sans-serif;
                animation: flash 1s infinite;
            }
            .emergency-alert-content {
                text-align: center;
                background: rgba(0, 0, 0, 0.8);
                padding: 2rem;
                border-radius: 10px;
                max-width: 400px;
            }
            .emergency-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
                animation: pulse 0.5s infinite;
            }
            .emergency-countdown {
                font-size: 1.5rem;
                margin: 1rem 0;
                color: yellow;
            }
            @keyframes flash {
                0%, 50% { opacity: 1; }
                25%, 75% { opacity: 0.7; }
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.2); }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(alertDiv);
        
        // Countdown timer
        let countdown = 5;
        const countdownElement = document.getElementById('countdown');
        const countdownInterval = setInterval(() => {
            countdown--;
            if (countdownElement) {
                countdownElement.textContent = countdown;
            }
            if (countdown <= 0) {
                clearInterval(countdownInterval);
                // Auto-remove after countdown
                if (alertDiv.parentElement) {
                    alertDiv.remove();
                }
            }
        }, 1000);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 10000);
    }
    
    showSOSSuccess() {
        this.showNotification('✅ Emergency alert sent successfully!', 'success');
    }
    
    showSOSError() {
        this.showNotification('❌ Failed to send emergency alert. Please call emergency services directly.', 'error');
    }
    
    showMicrophonePermissionError() {
        this.showNotification('🎤 Microphone access denied. Please enable microphone permissions for voice emergency detection.', 'warning');
    }
    
    showFallbackSOS() {
        console.log('Voice detection not available, showing manual SOS options');
        // You can add a visible SOS button here
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `sos-notification sos-${type}`;
        notification.textContent = message;
        
        const style = document.createElement('style');
        style.textContent = `
            .sos-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 1rem;
                border-radius: 5px;
                color: white;
                z-index: 9999;
                max-width: 300px;
                font-weight: bold;
            }
            .sos-success { background: #28a745; }
            .sos-error { background: #dc3545; }
            .sos-warning { background: #ffc107; color: black; }
            .sos-info { background: #17a2b8; }
        `;
        document.head.appendChild(style);
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    playEmergencySound() {
        try {
            // Create emergency sound
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1);
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime + 0.2);
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0, audioContext.currentTime + 1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 1);
        } catch (error) {
            console.log('Audio context not available');
        }
    }
    
    updateUI() {
        // Update any UI elements to show voice detection status
        const statusElements = document.querySelectorAll('.voice-status');
        statusElements.forEach(element => {
            if (this.isListening) {
                element.innerHTML = '🎤 <span style="color: #28a745;">LISTENING FOR EMERGENCIES</span>';
                element.style.animation = 'pulse 2s infinite';
            } else {
                element.innerHTML = '🎤 Voice detection inactive';
                element.style.animation = 'none';
            }
        });
    }
    
    // Public methods for manual control
    toggle() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    manualSOS(customMessage = '') {
        this.triggerEnhancedSOS(customMessage || 'Manual SOS triggered', 1.0);
    }
    
    // Cleanup
    destroy() {
        this.stopListening();
        if (this.locationWatcher) {
            navigator.geolocation.clearWatch(this.locationWatcher);
        }
    }
}

// Auto-initialize enhanced SOS system
document.addEventListener('DOMContentLoaded', function() {
    window.enhancedSOS = new EnhancedSOSSystem();
    
    // Add voice status indicator to page
    const statusDiv = document.createElement('div');
    statusDiv.className = 'voice-status';
    statusDiv.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 1000;
    `;
    document.body.appendChild(statusDiv);
    
    console.log('🚀 Enhanced SOS System initialized and ready!');
});

// Export for use in other scripts
window.EnhancedSOSSystem = EnhancedSOSSystem;