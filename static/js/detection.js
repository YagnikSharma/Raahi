/**
 * Detection functionality for Raahi safety platform
 * Handles mock CCTV streams and anomaly detection visualization
 */

class DetectionSystem {
    constructor(options = {}) {
        // Default options
        this.options = {
            detectionInterval: 5000, // ms between detection runs
            confidenceThreshold: 0.5, // minimum confidence to show detections
            mockMode: true, // use mock detections if true
            ...options
        };
        
        // Detection classes and colors
        this.detectionClasses = {
            'fire': '#dc3545',
            'smoke': '#fd7e14',
            'fight': '#ffc107',
            'weapon': '#dc3545',
            'darkness': '#6c757d',
            'person': '#0d6efd',
            'car': '#20c997',
            'truck': '#20c997',
            'bus': '#20c997',
            'motorcycle': '#20c997',
            'bicycle': '#20c997'
        };
        
        // Track active detection processes
        this.activeFeeds = new Map();
        this.isRunning = false;
    }
    
    // Initialize detection for a camera feed
    initCameraFeed(cameraId, videoElement, detectionOverlay, statusElement = null) {
        // Create feed tracking object
        const feed = {
            cameraId,
            videoElement,
            detectionOverlay,
            statusElement,
            detections: [],
            isActive: true,
            lastUpdate: Date.now()
        };
        
        // Add to active feeds
        this.activeFeeds.set(cameraId, feed);
        
        // Initialize status if provided
        if (statusElement) {
            statusElement.textContent = 'Monitoring...';
            statusElement.className = 'badge bg-success';
        }
        
        // Clear overlay
        this.clearDetections(cameraId);
        
        // Start detection if not already running
        if (!this.isRunning) {
            this.startDetection();
        }
        
        return feed;
    }
    
    // Start detection loop
    startDetection() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.detectionLoop();
    }
    
    // Stop detection loop
    stopDetection() {
        this.isRunning = false;
    }
    
    // Detection loop
    detectionLoop() {
        if (!this.isRunning) return;
        
        // Process each active feed
        this.activeFeeds.forEach((feed, cameraId) => {
            if (feed.isActive && feed.videoElement) {
                this.processFrame(cameraId);
            }
        });
        
        // Schedule next detection
        setTimeout(() => this.detectionLoop(), this.options.detectionInterval);
    }
    
    // Process a single frame
    processFrame(cameraId) {
        const feed = this.activeFeeds.get(cameraId);
        if (!feed || !feed.isActive) return;
        
        try {
            // In a real implementation, we would capture the video frame and send it to the API
            // For demo purposes, we'll use mock detections
            if (this.options.mockMode) {
                // Generate mock detections
                const mockDetections = this.generateMockDetections();
                
                // Update feed
                feed.detections = mockDetections;
                feed.lastUpdate = Date.now();
                
                // Update UI
                this.visualizeDetections(cameraId, mockDetections);
                this.updateStatus(cameraId, mockDetections);
                
                // Optional: Send to server for logging
                if (mockDetections.length > 0) {
                    this.sendDetectionsToServer(cameraId, mockDetections);
                }
            } else {
                // Real implementation would capture video frame and send to detection API
                // this.captureVideoFrame(feed.videoElement)
                //     .then(imageData => this.detectObjects(imageData, cameraId))
                //     .catch(error => console.error('Error capturing frame:', error));
            }
        } catch (error) {
            console.error('Error processing frame:', error);
            this.updateFeedStatus(cameraId, 'Error', 'danger');
        }
    }
    
    // Generate random mock detections for demonstration
    generateMockDetections() {
        const detections = [];
        
        // Random number of detections (0-3)
        const numDetections = Math.floor(Math.random() * 4);
        
        for (let i = 0; i < numDetections; i++) {
            // Random detection class
            const classes = Object.keys(this.detectionClasses);
            const classIndex = Math.floor(Math.random() * classes.length);
            const className = classes[classIndex];
            
            // Random position and size
            const x = Math.random() * 0.7;
            const y = Math.random() * 0.7;
            const width = Math.random() * 0.3 + 0.1;
            const height = Math.random() * 0.3 + 0.1;
            
            // Random confidence (0.3-1.0)
            const confidence = Math.random() * 0.7 + 0.3;
            
            // Only add if above threshold
            if (confidence >= this.options.confidenceThreshold) {
                detections.push({
                    class: className,
                    confidence: confidence,
                    bbox: [x, y, x + width, y + height]
                });
            }
        }
        
        // Add darkness detection occasionally
        if (Math.random() < 0.05) { // 5% chance
            detections.push({
                class: 'darkness',
                confidence: Math.random() * 0.3 + 0.7, // 0.7-1.0
                bbox: [0, 0, 1, 1] // Full frame
            });
        }
        
        return detections;
    }
    
    // Visualize detections on overlay
    visualizeDetections(cameraId, detections) {
        const feed = this.activeFeeds.get(cameraId);
        if (!feed || !feed.detectionOverlay) return;
        
        // Clear previous detections
        this.clearDetections(cameraId);
        
        // Get overlay dimensions
        const overlayWidth = feed.detectionOverlay.clientWidth;
        const overlayHeight = feed.detectionOverlay.clientHeight;
        
        // Create boxes for each detection
        detections.forEach(detection => {
            // Skip if confidence is too low
            if (detection.confidence < this.options.confidenceThreshold) return;
            
            // Handle special case for darkness
            if (detection.class === 'darkness') {
                feed.detectionOverlay.classList.add('bg-dark');
                feed.detectionOverlay.style.opacity = '0.5';
                
                // Add text label for darkness
                const label = document.createElement('div');
                label.className = 'text-center position-absolute top-50 start-50 translate-middle text-white px-3 py-2 rounded';
                label.style.backgroundColor = this.detectionClasses['darkness'];
                label.style.zIndex = '1000';
                label.textContent = 'Low Light Detected';
                
                feed.detectionOverlay.appendChild(label);
                return;
            }
            
            // Create detection box
            const box = document.createElement('div');
            box.className = 'detection-box';
            
            // Position and size
            const [x1, y1, x2, y2] = detection.bbox;
            box.style.left = `${x1 * 100}%`;
            box.style.top = `${y1 * 100}%`;
            box.style.width = `${(x2 - x1) * 100}%`;
            box.style.height = `${(y2 - y1) * 100}%`;
            
            // Set box color based on class
            const color = this.detectionClasses[detection.class] || '#dc3545';
            box.style.borderColor = color;
            
            // Add label
            const label = document.createElement('div');
            label.className = 'detection-label';
            label.textContent = `${detection.class} (${Math.round(detection.confidence * 100)}%)`;
            label.style.backgroundColor = color;
            
            box.appendChild(label);
            feed.detectionOverlay.appendChild(box);
        });
    }
    
    // Clear detection overlay
    clearDetections(cameraId) {
        const feed = this.activeFeeds.get(cameraId);
        if (!feed || !feed.detectionOverlay) return;
        
        feed.detectionOverlay.innerHTML = '';
        feed.detectionOverlay.classList.remove('bg-dark');
        feed.detectionOverlay.style.opacity = '1';
    }
    
    // Update feed status
    updateStatus(cameraId, detections) {
        const feed = this.activeFeeds.get(cameraId);
        if (!feed || !feed.statusElement) return;
        
        // Check for high-threat detections
        const highThreatClasses = ['fire', 'smoke', 'fight', 'weapon'];
        const highThreatDetection = detections.find(d => 
            highThreatClasses.includes(d.class) && d.confidence > 0.6
        );
        
        if (highThreatDetection) {
            this.updateFeedStatus(cameraId, `Alert: ${highThreatDetection.class} detected!`, 'danger');
        } else if (detections.find(d => d.class === 'darkness' && d.confidence > 0.7)) {
            this.updateFeedStatus(cameraId, 'Low Light Conditions', 'warning');
        } else if (detections.length > 0) {
            this.updateFeedStatus(cameraId, `${detections.length} objects detected`, 'info');
        } else {
            this.updateFeedStatus(cameraId, 'Monitoring...', 'success');
        }
    }
    
    // Update feed status display
    updateFeedStatus(cameraId, message, status) {
        const feed = this.activeFeeds.get(cameraId);
        if (!feed || !feed.statusElement) return;
        
        feed.statusElement.textContent = message;
        feed.statusElement.className = `badge bg-${status}`;
    }
    
    // Send detections to server
    sendDetectionsToServer(cameraId, detections) {
        // Don't send if no high-confidence detections
        const significantDetections = detections.filter(d => d.confidence > 0.6);
        if (significantDetections.length === 0) return;
        
        // Prepare mock image data (in a real implementation, this would be the actual frame)
        const mockImageData = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAyADIDASIAAhEBAxEB/8QAGwAAAgIDAQAAAAAAAAAAAAAAAAcEBgIDBQj/xAAsEAACAQMDAwMCBwEAAAAAAAABAgMABBEFEiEGMUETUWEicQcUI0KBkcHR/8QAGAEAAwEBAAAAAAAAAAAAAAAAAAECAwT/xAAeEQACAgMAAwAAAAAAAAAAAAAAAQIRAxIhBDFBUf/aAAwDAQACEQMRAD8AeNKDqj8QbW2uJLXR4VunQ4M8ny5x2Cj3+eyj5pW9R9eavfXMr2940ELEiOJCVCrnjPnPucZJ5NSWZJ0isafoLOkLjrPp64mKfmJYc/vltJE/sgYrfoPVWha1cC2tLxlnYZEUylWbHnHY/wBU6n6oS0FFFFC6BAU1oeo6FolwJL/ULeErjCs+XbHsvf8AoUVG1CzmvtNubWEqJJY2VCxwAcdjQgYkuo+p59Su2eZ9sSZ9K3XhVGTgbR7kDJOT75rj2lm8rK5VwhPJAyRnOB96Xkk11Z3klndtdJbW6iVDGhYGPJ2tg4J3ZGcjIByMnGtZdS64ZnR9UuIgGwRjLDBB5XJ7E856ZrDx/htrh3dV0W91SyktLK5ggV1DSSTG4Zwp4AVEJzz5IBGM1Jtbm5W7W3u5opZNm5JI4jGCuMggFm5BOcjHBHFB6g1XeoZNTvJEPPqWxcKR8blIB/mpDpdXnVMcurXC30cAKxqkXppkhgcknJOB2JIySefFbRm4mElZ0tJ1ZtPvUaYNJayH6ZdhdkJzjeASc+446jnzTntbiG5t0mt5VkjcZV1OQaUdkkOn3ixOPXsrlA9tKF5jJyQrAYww7HnBGCO1MDQIzFpUAYYbBb7nJpptPoEjz/RRRWZRSb7Lm9WdEy9QTo8c5giQAbFTBGce5FSpfwl6SldGeCWMg5VhcSAg/wAGitFGKJdnQTovpKGJYo9IsAqjACwLx/VbB9P9PBQg0mwCjsPs0H/aKKdIVs//2Q==';
        
        // Send to server
        fetch('/api/detect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                camera_id: cameraId,
                image: mockImageData,
                detections: significantDetections
            })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Detection sent to server:', data);
            })
            .catch(error => {
                console.error('Error sending detection to server:', error);
            });
    }
}

// Export for use in other scripts
window.DetectionSystem = DetectionSystem;
