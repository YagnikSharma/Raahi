/**
 * Working Microphone SOS System for Raahi Safety Platform
 * This will actually use the laptop microphone and detect help calls
 */

class WorkingMicrophoneSystem {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.micStream = null;
        this.audioContext = null;
        this.microphone = null;
        this.analyser = null;

        // Emergency keywords that will trigger instant SOS
        this.emergencyKeywords = [
            'help', 'help me', 'i need help',
            'save me', 'save', 'rescue me',
            'emergency', 'urgent',
            'fire', 'call police', 'ambulance'
        ];

        this.currentLocation = null;
        this.init();
    }

    async init() {
        console.log('🎤 Initializing Working Microphone System...');

        // Request microphone permission immediately
        await this.requestMicrophonePermission();

        // Initialize speech recognition
        this.initSpeechRecognition();

        // Start location tracking
        this.startLocationTracking();

        // Add visual indicator
        this.addMicrophoneIndicator();

        // Auto-start listening
        setTimeout(() => this.startListening(), 1000);
    }

    async requestMicrophonePermission() {
        try {
            console.log('📢 Requesting microphone permission...');

            // Request microphone access
            this.micStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });

            console.log('✅ Microphone permission granted!');

            // Set up audio visualization
            this.setupAudioVisualization();

            return true;
        } catch (error) {
            console.error('❌ Microphone permission denied:', error);
            this.showMicrophoneError();
            return false;
        }
    }

    setupAudioVisualization() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.microphone = this.audioContext.createMediaStreamSource(this.micStream);
            this.analyser = this.audioContext.createAnalyser();

            this.analyser.fftSize = 256;
            this.microphone.connect(this.analyser);

            // Start audio level monitoring
            this.monitorAudioLevel();

            console.log('🎵 Audio visualization setup complete');
        } catch (error) {
            console.error('Audio context error:', error);
        }
    }

    monitorAudioLevel() {
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const checkAudioLevel = () => {
            if (!this.isListening) return;

            this.analyser.getByteFrequencyData(dataArray);

            // Calculate average audio level
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            const average = sum / bufferLength;

            // Update visual indicator based on audio level
            this.updateMicrophoneIndicator(average);

            requestAnimationFrame(checkAudioLevel);
        };

        checkAudioLevel();
    }

    initSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('❌ Speech recognition not supported');
            this.showSpeechRecognitionError();
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        // Configure for emergency detection
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.recognition.maxAlternatives = 1;

        // Handle speech results
        this.recognition.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript.toLowerCase().trim();
                const confidence = event.results[i][0].confidence || 0.8;

                console.log(`🎤 Heard: "${transcript}" (confidence: ${confidence})`);

                // Check for emergency keywords
                if (this.detectEmergency(transcript)) {
                    console.log('🚨 EMERGENCY DETECTED!');
                    this.triggerInstantSOS(transcript);
                }
            }
        };

        // Handle errors and restart
        this.recognition.onerror = (event) => {
            console.log(`Speech recognition error: ${event.error}`);

            if (event.error === 'not-allowed') {
                this.showMicrophoneError();
            } else if (event.error !== 'no-speech') {
                // Restart recognition for other errors
                setTimeout(() => {
                    if (this.isListening) {
                        this.recognition.start();
                    }
                }, 1000);
            }
        };

        // Auto-restart when it ends
        this.recognition.onend = () => {
            if (this.isListening) {
                setTimeout(() => {
                    try {
                        if (this.recognition && this.isListening) {
                            this.recognition.start();
                        }
                    } catch (error) {
                        console.log('Recognition restart error:', error);
                        this.isListening = false;
                    }
                }, 1000);
            }
        };

        console.log('🎤 Speech recognition initialized');
    }

    detectEmergency(transcript) {
        // Check for emergency keywords
        for (const keyword of this.emergencyKeywords) {
            if (transcript.includes(keyword)) {
                return true;
            }
        }
        return false;
    }

    async triggerInstantSOS(detectedPhrase) {
        console.log('🚨 TRIGGERING INSTANT SOS!');

        // Show immediate visual feedback
        this.showEmergencyAlert(detectedPhrase);

        // Get current location if available
        let location = this.currentLocation;
        if (!location) {
            try {
                const position = await this.getCurrentLocationFast();
                location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
            } catch (error) {
                console.log('Could not get location for emergency');
            }
        }

        // Send instant SOS without description
        const sosData = {
            message: `VOICE EMERGENCY: "${detectedPhrase}"`,
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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sosData)
            });

            if (response.ok) {
                this.showSOSSuccess();

                // Offer speech-to-text for additional details
                this.offerSpeechToText();
            } else {
                this.showSOSError();
            }
        } catch (error) {
            console.error('SOS send error:', error);
            this.showSOSError();
        }
    }

    getCurrentLocationFast() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                resolve,
                reject,
                { enableHighAccuracy: true, timeout: 3000, maximumAge: 10000 }
            );
        });
    }

    startLocationTracking() {
        if (navigator.geolocation) {
            // Get immediate location
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        timestamp: new Date().toISOString()
                    };
                    console.log('📍 Location obtained:', this.currentLocation);
                },
                (error) => console.log('Location error:', error),
                { enableHighAccuracy: true, timeout: 5000, maximumAge: 30000 }
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
                (error) => console.log('Location tracking error:', error),
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
            );
        }
    }

    startListening() {
        if (!this.recognition || !this.micStream) {
            console.error('❌ Cannot start listening - microphone not ready');
            return;
        }

        try {
            this.isListening = true;
            this.recognition.start();
            this.updateIndicatorStatus('LISTENING FOR EMERGENCIES');
            console.log('🎤 Started listening for emergency keywords');
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
        }
    }

    stopListening() {
        this.isListening = false;
        if (this.recognition) {
            this.recognition.stop();
        }
        this.updateIndicatorStatus('MICROPHONE INACTIVE');
        console.log('🎤 Stopped listening');
    }

    addMicrophoneIndicator() {
        // Remove existing indicator
        const existing = document.getElementById('mic-indicator');
        if (existing) existing.remove();

        // Create new indicator
        const indicator = document.createElement('div');
        indicator.id = 'mic-indicator';
        indicator.innerHTML = `
            <div class="mic-status">
                <div class="mic-icon">🎤</div>
                <div class="mic-text">INITIALIZING MICROPHONE...</div>
                <div class="mic-level-bar">
                    <div class="mic-level-fill"></div>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            #mic-indicator {
                position: fixed;
                top: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 15px;
                border-radius: 10px;
                z-index: 10000;
                font-family: Arial, sans-serif;
                min-width: 250px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
            .mic-status {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
            }
            .mic-icon {
                font-size: 2rem;
                margin-bottom: 5px;
                animation: pulse 2s infinite;
            }
            .mic-text {
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            .mic-level-bar {
                width: 100%;
                height: 4px;
                background: #333;
                border-radius: 2px;
                overflow: hidden;
            }
            .mic-level-fill {
                height: 100%;
                background: linear-gradient(90deg, #00ff00, #ffff00, #ff0000);
                width: 0%;
                transition: width 0.1s ease;
            }
            .mic-listening {
                color: #00ff00 !important;
            }
            .mic-emergency {
                color: #ff0000 !important;
                animation: flash 0.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
            @keyframes flash {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(indicator);
    }

    updateMicrophoneIndicator(audioLevel) {
        const indicator = document.getElementById('mic-indicator');
        if (!indicator) return;

        const levelFill = indicator.querySelector('.mic-level-fill');
        if (levelFill) {
            // Convert audio level to percentage
            const percentage = Math.min((audioLevel / 128) * 100, 100);
            levelFill.style.width = `${percentage}%`;
        }
    }

    updateIndicatorStatus(status) {
        const indicator = document.getElementById('mic-indicator');
        if (!indicator) return;

        const textElement = indicator.querySelector('.mic-text');
        const iconElement = indicator.querySelector('.mic-icon');

        if (textElement) textElement.textContent = status;

        if (status.includes('LISTENING')) {
            indicator.classList.add('mic-listening');
            indicator.classList.remove('mic-emergency');
        } else if (status.includes('EMERGENCY')) {
            indicator.classList.add('mic-emergency');
            indicator.classList.remove('mic-listening');
        } else {
            indicator.classList.remove('mic-listening', 'mic-emergency');
        }
    }

    showEmergencyAlert(phrase) {
        this.updateIndicatorStatus('🚨 EMERGENCY DETECTED!');

        // Create emergency overlay
        const alertDiv = document.createElement('div');
        alertDiv.id = 'emergency-overlay';
        alertDiv.innerHTML = `
            <div class="emergency-content">
                <div class="emergency-icon">🚨</div>
                <h2>EMERGENCY DETECTED!</h2>
                <p><strong>"${phrase}"</strong></p>
                <p>Sending SOS alert automatically...</p>
                <div class="emergency-spinner"></div>
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            #emergency-overlay {
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(255, 0, 0, 0.95);
                z-index: 20000;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-family: Arial, sans-serif;
                animation: emergency-flash 1s infinite;
            }
            .emergency-content {
                text-align: center;
                background: rgba(0, 0, 0, 0.8);
                padding: 2rem;
                border-radius: 15px;
                max-width: 400px;
            }
            .emergency-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
                animation: emergency-pulse 0.5s infinite;
            }
            .emergency-spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #ff0000;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes emergency-flash {
                0%, 50% { opacity: 1; }
                25%, 75% { opacity: 0.8; }
            }
            @keyframes emergency-pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.3); }
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(alertDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 5000);
    }

    showSOSSuccess() {
        // Remove emergency overlay
        const overlay = document.getElementById('emergency-overlay');
        if (overlay) overlay.remove();

        this.showNotification('✅ Emergency SOS sent successfully!', 'success');
        this.updateIndicatorStatus('SOS SENT - HELP IS COMING');
    }

    showSOSError() {
        this.showNotification('❌ Failed to send SOS. Please call emergency services directly!', 'error');
    }

    offerSpeechToText() {
        const offerDiv = document.createElement('div');
        offerDiv.innerHTML = `
            <div class="speech-to-text-offer">
                <h3>Additional Details</h3>
                <p>Would you like to provide more details about your emergency?</p>
                <button onclick="window.workingMic.startSpeechToText()" class="btn btn-primary">
                    🎤 Speak Details
                </button>
                <button onclick="this.parentElement.parentElement.remove()" class="btn btn-secondary">
                    Skip
                </button>
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            .speech-to-text-offer {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: white;
                color: black;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 15000;
                max-width: 300px;
            }
            .speech-to-text-offer button {
                margin: 5px;
                padding: 10px 15px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            .btn-primary { background: #007bff; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
        `;
        document.head.appendChild(style);
        document.body.appendChild(offerDiv);
    }

    startSpeechToText() {
        // Implementation for speech-to-text details
        console.log('Starting speech-to-text for emergency details');
        // This would capture additional details and send them as follow-up
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        const style = document.createElement('style');
        style.textContent = `
            .notification {
                position: fixed;
                top: 100px;
                right: 20px;
                padding: 15px;
                border-radius: 5px;
                color: white;
                z-index: 15000;
                max-width: 300px;
                font-weight: bold;
            }
            .notification-success { background: #28a745; }
            .notification-error { background: #dc3545; }
        `;
        document.head.appendChild(style);
        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    showMicrophoneError() {
        this.updateIndicatorStatus('❌ MICROPHONE ACCESS DENIED');
        this.showNotification('Please allow microphone access for emergency detection', 'error');
    }

    showSpeechRecognitionError() {
        this.updateIndicatorStatus('❌ SPEECH RECOGNITION NOT SUPPORTED');
        this.showNotification('Speech recognition not supported in this browser', 'error');
    }
}

// Initialize the working microphone system when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Working Microphone SOS System...');
    window.workingMic = new WorkingMicrophoneSystem();
});

window.WorkingMicrophoneSystem = WorkingMicrophoneSystem;