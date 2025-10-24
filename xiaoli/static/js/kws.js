/**
 * KWS Application JavaScript
 * Handles real-time keyword spotting functionality
 */

class KWSApp {
    constructor(elements) {
        this.elements = elements;
        this.isRunning = false;
        this.audioContext = null;
        this.mediaStream = null;
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
        this.detectionCount = 0;
        this.successCount = 0;
        this.ws = null;
        
        // Configuration
        this.config = {
            sampleRate: 16000,
            channels: 1,
            chunkSize: 1024,
            threshold: 0.25,
            score: 1.0
        };
    }

    init() {
        this.setupEventListeners();
        this.updateCurrentTime();
        this.initializeAudioVisualizer();
        this.loadSettings();
    }

    setupEventListeners() {
        // Start/Stop buttons
        this.elements.startBtn.addEventListener('click', () => this.startDetection());
        this.elements.stopBtn.addEventListener('click', () => this.stopDetection());

        // WebSocket connection
        this.connectWebSocket();

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !this.isRunning) {
                e.preventDefault();
                this.startDetection();
            } else if (e.code === 'Escape' && this.isRunning) {
                e.preventDefault();
                this.stopDetection();
            }
        });

        // Page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isRunning) {
                this.pauseDetection();
            } else if (!document.hidden && this.isRunning) {
                this.resumeDetection();
            }
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/kws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected to FastAPI');
            this.showToast('WebSocket连接已建立', 'success');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleDetectionResult(data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.showToast('WebSocket连接已断开', 'warning');
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showToast('WebSocket连接错误', 'danger');
        };
    }

    async startDetection() {
        try {
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.config.sampleRate,
                    channelCount: this.config.channels,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.config.sampleRate
            });

            // Create audio source
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            // Create analyser for visualization
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            source.connect(this.analyser);

            // Start audio processing
            this.startAudioProcessing();

            // Send start command to server
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'start_detection'
                }));
            }

            // Update UI
            this.updateStatus('active', '检测中', '正在监听唤醒词...');
            this.elements.startBtn.disabled = true;
            this.elements.stopBtn.disabled = false;
            this.isRunning = true;

            this.showToast('语音检测已启动', 'success');

        } catch (error) {
            console.error('Error starting detection:', error);
            this.showToast('无法启动语音检测: ' + error.message, 'danger');
        }
    }

    stopDetection() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        // Send stop command to server
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'stop_detection'
            }));
        }

        // Update UI
        this.updateStatus('inactive', '已停止', '点击开始按钮启动检测');
        this.elements.startBtn.disabled = false;
        this.elements.stopBtn.disabled = true;
        this.isRunning = false;

        this.showToast('语音检测已停止', 'info');
    }

    pauseDetection() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.enabled = false);
        }
        this.updateStatus('paused', '已暂停', '页面不可见，检测已暂停');
    }

    resumeDetection() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.enabled = true);
        }
        this.updateStatus('active', '检测中', '正在监听唤醒词...');
    }

    startAudioProcessing() {
        const processAudio = () => {
            if (!this.analyser) return;

            this.analyser.getByteFrequencyData(this.dataArray);
            this.updateVisualizer();

            // Send audio data to server
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                // Get raw audio data from MediaStream
                const audioData = this.dataArray.slice();
                
                // Convert to base64 for transmission
                const audioBuffer = new Uint8Array(audioData);
                const base64Audio = btoa(String.fromCharCode(...audioBuffer));
                
                this.ws.send(JSON.stringify({
                    type: 'audio_data',
                    audio_data: base64Audio,
                    sample_rate: 16000,
                    channels: 1,
                    timestamp: Date.now()
                }));
            }

            this.animationId = requestAnimationFrame(processAudio);
        };

        processAudio();
    }

    updateVisualizer() {
        const canvas = this.elements.audioVisualizer;
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        ctx.fillStyle = '#f8f9fa';
        ctx.fillRect(0, 0, width, height);

        const barWidth = width / this.dataArray.length;
        let x = 0;

        for (let i = 0; i < this.dataArray.length; i++) {
            const barHeight = (this.dataArray[i] / 255) * height;
            
            const gradient = ctx.createLinearGradient(0, height, 0, height - barHeight);
            gradient.addColorStop(0, '#007bff');
            gradient.addColorStop(1, '#0056b3');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(x, height - barHeight, barWidth, barHeight);
            
            x += barWidth;
        }
    }

    handleDetectionResult(data) {
        if (data.type === 'detection') {
            this.detectionCount++;
            this.successCount++;
            
            // Update statistics
            this.elements.totalDetections.textContent = this.detectionCount;
            const successRate = this.detectionCount > 0 ? 
                Math.round((this.successCount / this.detectionCount) * 100) : 0;
            this.elements.successRate.textContent = successRate + '%';

            // Add detection result to UI
            this.addDetectionResult(data);
            
            // Show notification
            this.showToast(`检测到唤醒词: ${data.keyword}`, 'success');
            
            // Visual feedback
            this.elements.statusCircle.classList.add('active');
            setTimeout(() => {
                this.elements.statusCircle.classList.remove('active');
            }, 1000);
        } else if (data.type === 'detection_started') {
            this.showToast('检测已启动', 'info');
        } else if (data.type === 'detection_stopped') {
            this.showToast('检测已停止', 'info');
        } else if (data.type === 'error') {
            this.showToast('检测错误: ' + data.message, 'danger');
        }
    }

    addDetectionResult(data) {
        const resultsContainer = this.elements.detectionResults;
        
        // Remove "no results" message if present
        const noResultsMsg = resultsContainer.querySelector('.text-muted');
        if (noResultsMsg) {
            noResultsMsg.remove();
        }

        const detectionItem = document.createElement('div');
        detectionItem.className = 'detection-item fade-in';
        detectionItem.innerHTML = `
            <div class="detection-timestamp">${new Date().toLocaleString()}</div>
            <div class="detection-keyword">${data.keyword}</div>
            <div class="detection-confidence">置信度: ${(data.confidence * 100).toFixed(1)}%</div>
        `;

        resultsContainer.insertBefore(detectionItem, resultsContainer.firstChild);

        // Keep only last 10 results
        const items = resultsContainer.querySelectorAll('.detection-item');
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }

    updateStatus(state, text, description) {
        const circle = this.elements.statusCircle;
        const statusText = this.elements.statusText;
        const statusDescription = this.elements.statusDescription;

        // Remove all state classes
        circle.classList.remove('active', 'error', 'paused');

        if (state === 'active') {
            circle.classList.add('active');
        } else if (state === 'error') {
            circle.classList.add('error');
        } else if (state === 'paused') {
            circle.classList.add('paused');
        }

        statusText.textContent = text;
        statusDescription.textContent = description;
    }

    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();

        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    updateCurrentTime() {
        const updateTime = () => {
            const now = new Date();
            const timeString = now.toLocaleString('zh-CN');
            const timeElement = document.getElementById('current-time');
            if (timeElement) {
                timeElement.textContent = timeString;
            }
        };

        updateTime();
        setInterval(updateTime, 1000);
    }

    initializeAudioVisualizer() {
        const canvas = this.elements.audioVisualizer;
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        
        // Draw initial empty state
        ctx.fillStyle = '#f8f9fa';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('音频可视化', canvas.width / 2, canvas.height / 2);
    }

    loadSettings() {
        // Load settings from localStorage or server
        const savedSettings = localStorage.getItem('kws-settings');
        if (savedSettings) {
            this.config = { ...this.config, ...JSON.parse(savedSettings) };
        }
    }

    saveSettings() {
        localStorage.setItem('kws-settings', JSON.stringify(this.config));
    }
}

/**
 * Settings Application JavaScript
 */
class SettingsApp {
    constructor() {
        this.form = document.getElementById('general-settings-form');
        this.keywordsTextarea = document.getElementById('keywords-textarea');
    }

    init() {
        this.setupEventListeners();
        this.updateRangeValues();
    }

    setupEventListeners() {
        // Range inputs
        document.getElementById('threshold').addEventListener('input', (e) => {
            document.getElementById('threshold-value').textContent = e.target.value;
        });

        document.getElementById('score').addEventListener('input', (e) => {
            document.getElementById('score-value').textContent = e.target.value;
        });

        // Save buttons
        document.getElementById('save-settings-btn').addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('reset-settings-btn').addEventListener('click', () => {
            this.resetSettings();
        });

        document.getElementById('save-keywords-btn').addEventListener('click', () => {
            this.saveKeywords();
        });

        document.getElementById('reset-keywords-btn').addEventListener('click', () => {
            this.resetKeywords();
        });
    }

    updateRangeValues() {
        const thresholdValue = document.getElementById('threshold').value;
        const scoreValue = document.getElementById('score').value;
        
        document.getElementById('threshold-value').textContent = thresholdValue;
        document.getElementById('score-value').textContent = scoreValue;
    }

    async saveSettings() {
        const settings = {
            threshold: document.getElementById('threshold').value,
            score: document.getElementById('score').value,
            max_active_paths: document.getElementById('max-active-paths').value,
            num_trailing_blanks: document.getElementById('num-trailing-blanks').value,
            num_threads: document.getElementById('num-threads').value,
            provider: document.getElementById('provider').value,
            sample_rate: document.getElementById('sample-rate').value,
            channels: document.getElementById('channels').value,
            chunk_size: document.getElementById('chunk-size').value,
            device_index: document.getElementById('device-index').value
        };

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            if (response.ok) {
                this.showToast('设置保存成功', 'success');
            } else {
                throw new Error('保存失败');
            }
        } catch (error) {
            this.showToast('设置保存失败: ' + error.message, 'danger');
        }
    }

    async saveKeywords() {
        const keywords = this.keywordsTextarea.value.split('\n')
            .map(k => k.trim())
            .filter(k => k.length > 0);

        try {
            const response = await fetch('/api/keywords', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ keywords })
            });

            if (response.ok) {
                this.showToast('唤醒词保存成功', 'success');
            } else {
                throw new Error('保存失败');
            }
        } catch (error) {
            this.showToast('唤醒词保存失败: ' + error.message, 'danger');
        }
    }

    resetSettings() {
        if (confirm('确定要重置所有设置为默认值吗？')) {
            // Reset form to default values
            document.getElementById('threshold').value = 0.25;
            document.getElementById('score').value = 1.0;
            document.getElementById('max-active-paths').value = 4;
            document.getElementById('num-trailing-blanks').value = 1;
            document.getElementById('num-threads').value = 2;
            document.getElementById('provider').value = 'cpu';
            
            this.updateRangeValues();
            this.showToast('设置已重置', 'info');
        }
    }

    resetKeywords() {
        if (confirm('确定要重置唤醒词吗？')) {
            this.keywordsTextarea.value = '';
            this.showToast('唤醒词已重置', 'info');
        }
    }

    showToast(message, type = 'info') {
        // Reuse the toast functionality from KWSApp
        const toastContainer = document.querySelector('.toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
}

/**
 * Logs Application JavaScript
 */
class LogsApp {
    constructor() {
        this.logContainer = document.getElementById('log-container');
        this.autoScroll = document.getElementById('auto-scroll');
    }

    init() {
        this.setupEventListeners();
        this.setupWebSocket();
    }

    setupEventListeners() {
        // Filter controls
        document.getElementById('log-level').addEventListener('change', () => {
            this.filterLogs();
        });

        document.getElementById('log-source').addEventListener('change', () => {
            this.filterLogs();
        });

        document.getElementById('time-range').addEventListener('change', () => {
            this.filterLogs();
        });

        document.getElementById('search-logs').addEventListener('input', () => {
            this.filterLogs();
        });

        // Action buttons
        document.getElementById('refresh-logs-btn').addEventListener('click', () => {
            this.refreshLogs();
        });

        document.getElementById('export-logs-btn').addEventListener('click', () => {
            this.exportLogs();
        });

        document.getElementById('clear-logs-btn').addEventListener('click', () => {
            this.clearLogs();
        });
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onmessage = (event) => {
            const logData = JSON.parse(event.data);
            this.addLogEntry(logData);
        };
    }

    filterLogs() {
        const level = document.getElementById('log-level').value;
        const source = document.getElementById('log-source').value;
        const searchTerm = document.getElementById('search-logs').value.toLowerCase();
        
        const logEntries = this.logContainer.querySelectorAll('.log-entry');
        
        logEntries.forEach(entry => {
            const entryLevel = entry.dataset.level;
            const entrySource = entry.dataset.source;
            const entryText = entry.textContent.toLowerCase();
            
            let show = true;
            
            if (level !== 'all' && entryLevel !== level) {
                show = false;
            }
            
            if (source !== 'all' && entrySource !== source) {
                show = false;
            }
            
            if (searchTerm && !entryText.includes(searchTerm)) {
                show = false;
            }
            
            entry.style.display = show ? 'block' : 'none';
        });
    }

    addLogEntry(logData) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${logData.level}`;
        logEntry.dataset.timestamp = logData.timestamp;
        logEntry.dataset.source = logData.source;
        logEntry.dataset.level = logData.level;
        
        logEntry.innerHTML = `
            <div class="log-header">
                <span class="log-timestamp">${new Date(logData.timestamp).toLocaleString()}</span>
                <span class="log-level badge bg-${this.getLevelColor(logData.level)}">${logData.level.toUpperCase()}</span>
                <span class="log-source">${logData.source}</span>
            </div>
            <div class="log-message">${logData.message}</div>
            ${logData.details ? `
                <div class="log-details">
                    <details>
                        <summary>详细信息</summary>
                        <pre>${logData.details}</pre>
                    </details>
                </div>
            ` : ''}
        `;
        
        this.logContainer.insertBefore(logEntry, this.logContainer.firstChild);
        
        // Auto scroll if enabled
        if (this.autoScroll.checked) {
            this.logContainer.scrollTop = 0;
        }
        
        // Keep only last 100 entries
        const entries = this.logContainer.querySelectorAll('.log-entry');
        if (entries.length > 100) {
            entries[entries.length - 1].remove();
        }
    }

    getLevelColor(level) {
        const colors = {
            'debug': 'secondary',
            'info': 'primary',
            'warning': 'warning',
            'error': 'danger'
        };
        return colors[level] || 'secondary';
    }

    async refreshLogs() {
        try {
            const response = await fetch('/api/logs');
            const logs = await response.json();
            
            this.logContainer.innerHTML = '';
            logs.forEach(log => this.addLogEntry(log));
            
            this.showToast('日志已刷新', 'success');
        } catch (error) {
            this.showToast('刷新日志失败: ' + error.message, 'danger');
        }
    }

    exportLogs() {
        const logEntries = this.logContainer.querySelectorAll('.log-entry');
        const logs = Array.from(logEntries).map(entry => ({
            timestamp: entry.dataset.timestamp,
            level: entry.dataset.level,
            source: entry.dataset.source,
            message: entry.querySelector('.log-message').textContent
        }));
        
        const dataStr = JSON.stringify(logs, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `kws-logs-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        this.showToast('日志已导出', 'success');
    }

    async clearLogs() {
        if (confirm('确定要清空所有日志吗？')) {
            try {
                const response = await fetch('/api/logs', {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    this.logContainer.innerHTML = '';
                    this.showToast('日志已清空', 'success');
                } else {
                    throw new Error('清空失败');
                }
            } catch (error) {
                this.showToast('清空日志失败: ' + error.message, 'danger');
            }
        }
    }

    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
}
