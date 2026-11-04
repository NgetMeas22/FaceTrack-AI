/**
 * FaceTrack AI — Live Animated Face Scanner Client Engine
 */

class LiveFaceScanner {
  constructor(config = {}) {
    this.video = document.getElementById(config.videoId || 'webcam-feed');
    this.overlayCanvas = document.getElementById(config.canvasId || 'face-canvas');
    this.statusBadge = document.getElementById('scanner-status');
    this.resultCard = document.getElementById('match-result-card');
    this.directionToggle = document.getElementById('direction-select');
    this.deviceSelect = document.getElementById('camera-select');
    this.laserBeam = document.getElementById('scanner-laser');

    this.stream = null;
    this.isScanning = false;
    this.isProcessingFrame = false;
    this.scanInterval = null;
    this.direction = 'CHECK_IN';
    this.lastMatchId = null;
    this.lastMatchTime = 0;

    this.audioCtx = null;

    this.init();
  }

  init() {
    this.initAudio();
    this.setupEventListeners();
    this.populateCameraDevices().then(() => {
      this.startCamera();
    });
  }

  initAudio() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AudioContext();
    } catch (e) {
      console.warn('Web Audio not supported');
    }
  }

  playChime(type = 'success') {
    if (!this.audioCtx) return;
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }

    const now = this.audioCtx.currentTime;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    osc.connect(gain);
    gain.connect(this.audioCtx.destination);

    if (type === 'success') {
      // Pleasant two-tone chime (C5 to E5)
      osc.type = 'sine';
      osc.frequency.setValueAtTime(523.25, now);
      osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.12);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    } else if (type === 'unknown') {
      // Low dual warning tone
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(260, now);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    }
  }

  setupEventListeners() {
    if (this.directionToggle) {
      this.directionToggle.addEventListener('change', (e) => {
        this.direction = e.target.value;
      });
    }

    if (this.deviceSelect) {
      this.deviceSelect.addEventListener('change', () => {
        this.startCamera(this.deviceSelect.value);
      });
    }
  }

  async populateCameraDevices() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter((d) => d.kind === 'videoinput');

      if (this.deviceSelect && videoDevices.length > 0) {
        this.deviceSelect.innerHTML = '';
        videoDevices.forEach((dev, idx) => {
          const opt = document.createElement('option');
          opt.value = dev.deviceId;
          opt.textContent = dev.label || `Camera ${idx + 1}`;
          this.deviceSelect.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn('Could not enumerate video devices:', err);
    }
  }

  async startCamera(deviceId = null) {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
    }

    const constraints = {
      video: deviceId
        ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
        : { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    };

    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.stream;
      await this.video.play();

      this.video.onloadedmetadata = () => {
        this.overlayCanvas.width = this.video.videoWidth;
        this.overlayCanvas.height = this.video.videoHeight;
        this.startScanningLoop();
      };

      this.setStatus('Scanning actively...', 'cyan');
    } catch (err) {
      console.error('Camera access error:', err);
      this.setStatus('Camera permission denied or camera unavailable', 'rose');
    }
  }

  setStatus(text, color = 'cyan') {
    if (!this.statusBadge) return;
    this.statusBadge.textContent = text;
    this.statusBadge.className = `px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-1.5 shadow-sm text-${color}-400 bg-${color}-950/40 border-${color}-800/60`;
  }

  startScanningLoop() {
    if (this.scanInterval) clearInterval(this.scanInterval);
    // Process a frame every 700ms for fast recognition without saturating the server
    this.scanInterval = setInterval(() => {
      this.captureAndRecognize();
    }, 700);
  }

  async captureAndRecognize() {
    if (this.isProcessingFrame || !this.video || this.video.readyState !== 4) return;
    this.isProcessingFrame = true;

    try {
      // Offscreen canvas for frame extraction
      const offscreen = document.createElement('canvas');
      offscreen.width = this.video.videoWidth;
      offscreen.height = this.video.videoHeight;
      const ctx = offscreen.getContext('2d');
      ctx.drawImage(this.video, 0, 0, offscreen.width, offscreen.height);

      const dataUrl = offscreen.toDataURL('image/jpeg', 0.82);

      const response = await fetch('/api/scan/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: dataUrl,
          direction: this.direction,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const res = await response.json();
      this.handleScanResult(res);
    } catch (err) {
      console.warn('Scan request error:', err);
    } finally {
      this.isProcessingFrame = false;
    }
  }

  handleScanResult(res) {
    const ctx = this.overlayCanvas.getContext('2d');
    ctx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);

    if (res.outcome === 'MATCH') {
      const b = res.box;
      if (b) {
        this.drawTargetBox(ctx, b, '#10b981', res.employee.name, `${res.confidence}%`);
      }

      const now = Date.now();
      // Only chime and trigger banner animation if not an immediate duplicate repeat
      if (this.lastMatchId !== res.employee.id || now - this.lastMatchTime > 15000) {
        this.playChime('success');
        this.showMatchCard(res);
        this.triggerFlashEffect();
        this.lastMatchId = res.employee.id;
        this.lastMatchTime = now;
      }
      this.setStatus(`Matched: ${res.employee.name} (${res.confidence}%)`, 'emerald');

    } else if (res.outcome === 'UNKNOWN') {
      const b = res.box;
      if (b) {
        this.drawTargetBox(ctx, b, '#f43f5e', 'Unknown Person', '');
      }
      this.setStatus('Unregistered face detected', 'rose');

    } else if (res.outcome === 'NO_FACE') {
      this.setStatus('Looking for faces in camera view...', 'cyan');
    }
  }

  drawTargetBox(ctx, box, color, title, score) {
    const isVideoMirrored = this.video && (
      this.video.classList.contains('scale-x-[-1]') ||
      (this.video.className && this.video.className.indexOf('scale-x-[-1]') !== -1)
    );
    const x = isVideoMirrored ? (this.overlayCanvas.width - (box.x + box.width)) : box.x;
    const y = box.y;
    const width = box.width;
    const height = box.height;

    ctx.strokeStyle = color;
    ctx.lineWidth = 3;

    // Corner targeting lines
    const lineLen = Math.min(24, width * 0.25);

    ctx.beginPath();
    // Top-left
    ctx.moveTo(x, y + lineLen);
    ctx.lineTo(x, y);
    ctx.lineTo(x + lineLen, y);
    // Top-right
    ctx.moveTo(x + width - lineLen, y);
    ctx.lineTo(x + width, y);
    ctx.lineTo(x + width, y + lineLen);
    // Bottom-left
    ctx.moveTo(x, y + height - lineLen);
    ctx.lineTo(x, y + height);
    ctx.lineTo(x + lineLen, y + height);
    // Bottom-right
    ctx.moveTo(x + width - lineLen, y + height);
    ctx.lineTo(x + width, y + height);
    ctx.lineTo(x + width, y + height - lineLen);
    ctx.stroke();

    // Name / confidence tag
    if (title) {
      ctx.fillStyle = color;
      ctx.font = 'bold 15px Inter, sans-serif';
      const label = score ? `${title} [${score}]` : title;
      const textWidth = ctx.measureText(label).width;

      ctx.fillRect(x, Math.max(0, y - 28), textWidth + 16, 26);
      ctx.fillStyle = '#0b0f19';
      ctx.fillText(label, x + 8, Math.max(18, y - 9));
    }
  }

  showMatchCard(res) {
    if (!this.resultCard) return;

    const emp = res.employee;
    const avatarEl = document.getElementById('match-avatar');
    const nameEl = document.getElementById('match-name');
    const deptEl = document.getElementById('match-dept');
    const timeEl = document.getElementById('match-time');
    const directionEl = document.getElementById('match-direction');
    const confidenceEl = document.getElementById('match-confidence');

    if (avatarEl) {
      if (emp.photo_path) {
        avatarEl.src = emp.photo_path;
      } else {
        avatarEl.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(emp.name)}&background=06b6d4&color=fff&size=128`;
      }
    }
    if (nameEl) nameEl.textContent = emp.name;
    if (deptEl) deptEl.textContent = `${emp.department} • ${emp.position}`;
    if (timeEl) timeEl.textContent = res.timestamp;
    if (directionEl) {
      directionEl.textContent = res.direction === 'CHECK_IN' ? 'Check In' : 'Check Out';
      directionEl.className = res.direction === 'CHECK_IN'
        ? 'px-2 py-0.5 text-xs font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-800'
        : 'px-2 py-0.5 text-xs font-semibold rounded bg-cyan-950 text-cyan-400 border border-cyan-800';
    }
    if (confidenceEl) confidenceEl.textContent = `${res.confidence}% Match`;

    this.resultCard.classList.remove('opacity-0', 'translate-y-4', 'pointer-events-none');
    this.resultCard.classList.add('opacity-100', 'translate-y-0');

    // Auto fade after 5 seconds
    clearTimeout(this.fadeTimer);
    this.fadeTimer = setTimeout(() => {
      this.resultCard.classList.add('opacity-0', 'translate-y-4', 'pointer-events-none');
      this.resultCard.classList.remove('opacity-100', 'translate-y-0');
    }, 5000);
  }

  triggerFlashEffect() {
    const flashEl = document.getElementById('scanner-flash');
    if (flashEl) {
      flashEl.classList.add('flash-success');
      setTimeout(() => flashEl.classList.remove('flash-success'), 800);
    }
  }
}

// Auto-initialize when scanner page is loaded
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('webcam-feed')) {
    window.faceScanner = new LiveFaceScanner();
  }
});

