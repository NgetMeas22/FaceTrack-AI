/**
 * FaceTrack AI — Live Animated Face Scanner Client Engine
 * Enterprise HUD Biometric Telemetry & Real-Time Face Recognition
 */

class LiveFaceScanner {
  constructor(config = {}) {
    this.video = document.getElementById(config.videoId || 'webcam-feed');
    this.overlayCanvas = document.getElementById(config.canvasId || 'face-canvas');
    this.statusBadge = document.getElementById('scanner-status');
    this.statusText = document.getElementById('scanner-status-text');
    this.statusDot = document.getElementById('scanner-status-dot');
    this.radar = document.getElementById('scanner-radar');
    this.loadingText = document.getElementById('scanner-loading-text');
    this.resultCard = document.getElementById('match-result-card');
    this.directionToggle = document.getElementById('direction-select');
    this.deviceSelect = document.getElementById('camera-select');
    this.laserBeam = document.getElementById('scanner-laser');
    this.latencyEl = document.getElementById('hud-latency');
    this.fpsEl = document.getElementById('hud-fps');

    this.stream = null;
    this.isScanning = false;
    this.isProcessingFrame = false;
    this.scanInterval = null;
    this.direction = 'CHECK_IN';
    this.lastMatchId = null;
    this.lastMatchTime = 0;
    this.lastBoxFound = false;

    // Performance telemetry
    this.fpsFrameCount = 0;
    this.lastFpsCalcTime = performance.now();

    this.audioCtx = null;
    this.init();
  }

  init() {
    this.initAudio();
    this.setupEventListeners();
    this.populateCameraDevices().then(() => {
      this.startCamera();
    });
    this.startFpsLoop();
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
      this.setStatus('Initializing optical sensor...', 'cyan');
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.stream;
      await this.video.play();

      const onVideoReady = () => {
        if (this.video.videoWidth > 0 && this.overlayCanvas) {
          this.overlayCanvas.width = this.video.videoWidth;
          this.overlayCanvas.height = this.video.videoHeight;
        }
        this.startScanningLoop();
      };

      if (this.video.readyState >= 2 && this.video.videoWidth > 0) {
        onVideoReady();
      } else {
        this.video.addEventListener('loadeddata', onVideoReady, { once: true });
        this.video.addEventListener('loadedmetadata', onVideoReady, { once: true });
        this.video.addEventListener('canplay', onVideoReady, { once: true });
      }

      this.setStatus('Scanning actively...', 'cyan');
    } catch (err) {
      console.error('Camera access error:', err);
      this.setStatus('Camera permission denied or camera unavailable', 'rose');
    }
  }

  setStatus(text, color = 'cyan') {
    if (this.statusText) {
      this.statusText.textContent = text.toUpperCase();
    } else if (this.statusBadge) {
      this.statusBadge.textContent = text;
    }

    if (this.statusDot) {
      this.statusDot.className = `w-1.5 h-1.5 rounded-full bg-${color}-400 animate-pulse`;
    }

    if (this.statusBadge) {
      this.statusBadge.className = `telemetry-chip text-${color}-300 bg-${color}-950/80 border-${color}-500/50 shadow-sm transition-colors`;
    }

    if (this.loadingText && (color === 'cyan' || color === 'sky')) {
      this.loadingText.textContent = text.toUpperCase();
    }
  }

  startFpsLoop() {
    const calcFps = () => {
      this.fpsFrameCount++;
      const now = performance.now();
      const delta = now - this.lastFpsCalcTime;
      if (delta >= 1000) {
        const fps = Math.round((this.fpsFrameCount * 1000) / delta);
        if (this.fpsEl) {
          this.fpsEl.textContent = `${Math.min(60, Math.max(24, fps))}.0`;
        }
        this.fpsFrameCount = 0;
        this.lastFpsCalcTime = now;
      }
      requestAnimationFrame(calcFps);
    };
    requestAnimationFrame(calcFps);
  }

  startScanningLoop() {
    if (this.scanInterval) clearInterval(this.scanInterval);
    // Process a frame every 450ms for responsive recognition without lag
    this.scanInterval = setInterval(() => {
      this.captureAndRecognize();
    }, 450);
  }

  async captureAndRecognize() {
    if (this.isProcessingFrame || !this.video || this.video.readyState < 2) return;
    this.isProcessingFrame = true;
    const t0 = performance.now();

    // Show active analyzing indicator when searching
    if (this.loadingText && !this.lastBoxFound) {
      this.loadingText.textContent = 'AI ANALYZING...';
    }

    try {
      // Sync canvas dimensions
      if (this.overlayCanvas && this.video.videoWidth > 0 && this.overlayCanvas.width !== this.video.videoWidth) {
        this.overlayCanvas.width = this.video.videoWidth;
        this.overlayCanvas.height = this.video.videoHeight;
      }

      // Offscreen canvas for frame extraction
      const offscreen = document.createElement('canvas');
      offscreen.width = this.video.videoWidth || 640;
      offscreen.height = this.video.videoHeight || 480;
      const ctx = offscreen.getContext('2d');
      ctx.drawImage(this.video, 0, 0, offscreen.width, offscreen.height);

      const dataUrl = offscreen.toDataURL('image/jpeg', 0.80);

      const response = await fetch('/api/scan/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: dataUrl,
          direction: this.direction,
        }),
      });

      const elapsed = Math.round(performance.now() - t0);
      if (this.latencyEl) {
        this.latencyEl.textContent = `${elapsed} ms`;
      }

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
    if (!this.overlayCanvas) return;
    const ctx = this.overlayCanvas.getContext('2d');
    ctx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);

    if (res.outcome === 'MATCH') {
      this.lastBoxFound = true;
      if (this.radar) {
        this.radar.classList.add('opacity-0', 'scale-90');
        this.radar.classList.remove('opacity-100', 'scale-100');
      }

      const b = res.box;
      if (b) {
        this.drawTargetBox(ctx, b, '#10b981', res.employee.name, `${res.confidence}%`, 'VERIFIED PERSONNEL');
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
      this.lastBoxFound = true;
      if (this.radar) {
        this.radar.classList.add('opacity-0', 'scale-90');
        this.radar.classList.remove('opacity-100', 'scale-100');
      }

      const b = res.box;
      if (b) {
        this.drawTargetBox(ctx, b, '#f43f5e', 'Unknown Person', '', 'UNREGISTERED');
      }
      this.setStatus('Unregistered face detected', 'rose');

    } else if (res.outcome === 'NO_FACE') {
      this.lastBoxFound = false;
      if (this.radar) {
        this.radar.classList.remove('opacity-0', 'scale-90');
        this.radar.classList.add('opacity-100', 'scale-100');
      }
      this.setStatus('Scanning actively...', 'cyan');
      if (this.loadingText) {
        this.loadingText.textContent = 'AI NEURAL SCANNING...';
      }
    }
  }

  drawTargetBox(ctx, box, color, title, score, badgeText = '') {
    const isVideoMirrored = this.video && (
      this.video.classList.contains('scale-x-[-1]') ||
      (this.video.className && this.video.className.indexOf('scale-x-[-1]') !== -1)
    );
    const x = isVideoMirrored ? (this.overlayCanvas.width - (box.x + box.width)) : box.x;
    const y = box.y;
    const width = box.width;
    const height = box.height;

    // 1. Semi-transparent glowing biometric target fill
    ctx.fillStyle = color === '#10b981' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)';
    ctx.fillRect(x, y, width, height);

    // 2. Corner targeting bracket lines with glow
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.shadowColor = color;
    ctx.shadowBlur = 10;

    const lineLen = Math.min(28, width * 0.28);

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

    // Reset shadow for clean text & landmarks
    ctx.shadowBlur = 0;

    // 3. Render facial feature landmark points (eyes, nose, mouth corners)
    if (box.landmarks && box.landmarks.length > 0) {
      box.landmarks.forEach(([lx, ly]) => {
        const mappedLx = isVideoMirrored ? (this.overlayCanvas.width - lx) : lx;
        ctx.fillStyle = '#38bdf8';
        ctx.beginPath();
        ctx.arc(mappedLx, ly, 3.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#0284c7';
        ctx.beginPath();
        ctx.arc(mappedLx, ly, 1.5, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    // 4. Name / Confidence Header Tag
    if (title) {
      ctx.fillStyle = color;
      ctx.font = 'bold 14px Inter, sans-serif';
      const label = score ? `${title} [${score}]` : title;
      const textWidth = ctx.measureText(label).width;

      const tagY = Math.max(26, y - 10);
      ctx.fillStyle = color;
      ctx.fillRect(x, tagY - 22, textWidth + 18, 24);

      ctx.fillStyle = '#0b0f19';
      ctx.fillText(label, x + 9, tagY - 6);
    }

    // 5. Bottom Status Sub-badge
    if (badgeText) {
      ctx.font = 'bold 10px JetBrains Mono, monospace';
      const subWidth = ctx.measureText(badgeText).width;
      const subY = y + height + 18;

      ctx.fillStyle = 'rgba(11, 15, 25, 0.85)';
      ctx.fillRect(x, y + height + 4, subWidth + 14, 18);

      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y + height + 4, subWidth + 14, 18);

      ctx.fillStyle = color;
      ctx.fillText(badgeText, x + 7, subY - 1);
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
    if (confidenceEl) {
      confidenceEl.textContent = `(${res.confidence}%)`;
    }

    this.resultCard.classList.remove('opacity-0', 'translate-y-4', 'pointer-events-none');
    this.resultCard.classList.add('opacity-100', 'translate-y-0');

    // Auto fade after 6 seconds
    clearTimeout(this.fadeTimer);
    this.fadeTimer = setTimeout(() => {
      this.resultCard.classList.add('opacity-0', 'translate-y-4', 'pointer-events-none');
      this.resultCard.classList.remove('opacity-100', 'translate-y-0');
    }, 6000);
  }

  triggerFlashEffect() {
    const flashEl = document.getElementById('scanner-flash');
    if (flashEl) {
      flashEl.classList.add('flash-success');
      setTimeout(() => flashEl.classList.remove('flash-success'), 800);
    }
  }
}

// Auto-initialize when scanner feed is present
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('webcam-feed')) {
    window.faceScanner = new LiveFaceScanner();
  }
});
