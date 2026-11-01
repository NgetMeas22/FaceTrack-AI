/**
 * FaceTrack AI — Global UI Utilities, Toast Alerts, Button Loading States & Biometric Enrollment
 */

// Lucide Icons initialization
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }
  initToastFromUrl();
  initFormLoadingHandlers();
});

// ==========================================================================
// TOAST NOTIFICATION & ALERTS SYSTEM
// ==========================================================================

function playChime(type) {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;

    if (type === 'success') {
      // Harmonic major chime
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.type = 'sine';
      osc2.type = 'sine';
      osc1.frequency.setValueAtTime(523.25, now);       // C5
      osc1.frequency.setValueAtTime(659.25, now + 0.08); // E5
      osc2.frequency.setValueAtTime(783.99, now + 0.16); // G5

      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(now);
      osc2.start(now + 0.08);
      osc1.stop(now + 0.4);
      osc2.stop(now + 0.4);
    } else if (type === 'error') {
      // Alert low buzz
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(180, now);
      osc.frequency.setValueAtTime(140, now + 0.1);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.35);
    }
  } catch (e) {
    // Audio autoplay restrictions ignored
  }
}

window.showToast = function(message, type = 'success', title = '') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = {
    success: 'check-circle-2',
    error: 'alert-circle',
    warning: 'alert-triangle',
    info: 'info',
  };

  const titles = {
    success: title || 'Action Completed',
    error: title || 'Operation Error',
    warning: title || 'Security Warning',
    info: title || 'System Telemetry',
  };

  const item = document.createElement('div');
  item.className = `toast-item toast-${type}`;
  item.innerHTML = `
    <i data-lucide="${icons[type] || 'info'}" class="w-5 h-5 shrink-0 mt-0.5"></i>
    <div class="flex-1 min-w-0 pr-2">
      <h5 class="text-xs font-bold leading-tight tracking-tight">${titles[type]}</h5>
      <p class="text-xs font-medium opacity-95 mt-0.5 break-words">${message}</p>
    </div>
    <button onclick="dismissToast(this.parentElement)" class="text-white/70 hover:text-white p-1 -mr-1 rounded-lg transition-colors">
      <i data-lucide="x" class="w-3.5 h-3.5"></i>
    </button>
    <div class="toast-progress"></div>
  `;

  container.appendChild(item);
  if (window.lucide) window.lucide.createIcons();
  playChime(type);

  // Auto remove after 4.2 seconds
  const timer = setTimeout(() => {
    dismissToast(item);
  }, 4200);

  item._timer = timer;
};

window.dismissToast = function(item) {
  if (!item) return;
  if (item._timer) clearTimeout(item._timer);
  item.classList.add('toast-leave');
  setTimeout(() => {
    if (item.parentElement) item.remove();
  }, 300);
};

function initToastFromUrl() {
  const params = new URLSearchParams(window.location.search);
  
  if (params.has('success')) {
    const val = params.get('success');
    const messages = {
      created: 'New corporate personnel record created & stored successfully.',
      updated: 'Employee credentials and position updated.',
      enrolled: 'Face embedding extracted and saved to gallery.',
      role_updated: 'Operator clearance level successfully updated.',
      provisioned: 'New system operator provisioned with credentials.',
      settings_saved: 'System & sensor parameters synchronized.',
    };
    showToast(messages[val] || val, 'success', 'Success');
  } else if (params.has('error')) {
    showToast(params.get('error'), 'error', 'Error Notice');
  } else if (params.has('message')) {
    showToast(params.get('message'), 'info', 'Notice');
  }

  // Clean URL query without page reload
  if (params.has('success') || params.has('error') || params.has('message')) {
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);
  }
}

// ==========================================================================
// BUTTON LOADING STATE UTILITIES
// ==========================================================================

window.setButtonLoading = function(btn, loadingText = 'Processing...') {
  if (!btn) return;
  btn.dataset.origHtml = btn.innerHTML;
  btn.disabled = true;
  btn.classList.add('btn-loading');

  btn.innerHTML = `
    <span class="btn-spinner"></span>
    <span>${loadingText}</span>
  `;
};

window.resetButtonLoading = function(btn) {
  if (!btn || !btn.dataset.origHtml) return;
  btn.disabled = false;
  btn.classList.remove('btn-loading');
  btn.innerHTML = btn.dataset.origHtml;
  if (window.lucide) window.lucide.createIcons();
};

function initFormLoadingHandlers() {
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', function (e) {
      const submitBtn = this.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        // Determine loading message based on button contents
        let msg = 'Processing...';
        const txt = submitBtn.textContent.trim().toLowerCase();
        if (txt.includes('save') || txt.includes('profile')) msg = 'Saving Profile...';
        else if (txt.includes('sign in') || txt.includes('authenticate')) msg = 'Authenticating...';
        else if (txt.includes('enroll') || txt.includes('face')) msg = 'Extracting Biometrics...';
        else if (txt.includes('export')) msg = 'Generating Dossier...';
        else if (txt.includes('upload')) msg = 'Uploading Image...';
        else if (txt.includes('operator')) msg = 'Provisioning...';

        setButtonLoading(submitBtn, msg);
      }
    });
  });
}

// Client-side image upload preview helper
window.previewImage = function(input, previewImgId, placeholderId) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function(e) {
      const img = document.getElementById(previewImgId);
      if (img) {
        img.src = e.target.result;
        img.classList.remove('hidden');
      }
      if (placeholderId) {
        const ph = document.getElementById(placeholderId);
        if (ph) ph.classList.add('hidden');
      }
    };
    reader.readAsDataURL(input.files[0]);
  }
};

// ==========================================================================
// MODAL CONTROLLERS & FACE ENROLLMENT
// ==========================================================================

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

let enrollmentStream = null;
let currentEnrollEmpId = null;

async function openFaceEnrollModal(empId, empName) {
  currentEnrollEmpId = empId;
  const nameLabel = document.getElementById('enroll-emp-name');
  if (nameLabel) nameLabel.textContent = empName;

  const video = document.getElementById('enroll-video');
  const statusEl = document.getElementById('enroll-status');
  const progressBar = document.getElementById('enroll-progress');
  if (progressBar) progressBar.classList.add('hidden');

  if (video) video.classList.remove('hidden');
  if (statusEl) {
    statusEl.textContent = 'Align face steadily in the center of the optical view.';
    statusEl.className = 'text-xs text-slate-400 text-center';
  }

  openModal('face-enroll-modal');

  try {
    enrollmentStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      audio: false,
    });
    if (video) {
      video.srcObject = enrollmentStream;
      video.play();
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = 'Optical sensor access error: ' + err.message;
      statusEl.className = 'text-xs text-rose-400 text-center';
    }
    showToast('Failed to access camera: ' + err.message, 'error', 'Hardware Sensor');
  }
}

function closeFaceEnrollModal() {
  if (enrollmentStream) {
    enrollmentStream.getTracks().forEach((t) => t.stop());
    enrollmentStream = null;
  }
  closeModal('face-enroll-modal');
}

async function captureAndEnrollFace(btn) {
  const video = document.getElementById('enroll-video');
  const statusEl = document.getElementById('enroll-status');
  const progressBar = document.getElementById('enroll-progress');
  const progressFill = document.getElementById('enroll-progress-fill');
  if (!video || !currentEnrollEmpId) return;

  const captureBtn = btn || document.getElementById('btn-capture-enroll');
  if (captureBtn) setButtonLoading(captureBtn, 'Analyzing Landmarks...');

  if (progressBar) {
    progressBar.classList.remove('hidden');
    if (progressFill) progressFill.style.width = '25%';
  }

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const base64Data = canvas.toDataURL('image/jpeg', 0.92);

  if (statusEl) {
    statusEl.textContent = 'Extracting 128-d SFace vector & storing face cropped image...';
    statusEl.className = 'text-xs text-cyan-400 text-center animate-pulse';
  }
  if (progressFill) progressFill.style.width = '65%';

  try {
    const res = await fetch(`/api/employees/${currentEnrollEmpId}/register-face`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64Data }),
    });

    const data = await res.json();
    if (progressFill) progressFill.style.width = '100%';

    if (res.ok && data.success) {
      statusEl.textContent = data.message;
      statusEl.className = 'text-xs text-emerald-400 font-semibold text-center';
      showToast(data.message, 'success', 'Face Enrolled');

      setTimeout(() => {
        closeFaceEnrollModal();
        window.location.reload();
      }, 1000);
    } else {
      statusEl.textContent = data.message || 'Face enrollment failed.';
      statusEl.className = 'text-xs text-rose-400 font-medium text-center';
      showToast(data.message || 'Enrollment failed', 'error', 'Biometric Error');
      if (captureBtn) resetButtonLoading(captureBtn);
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = 'Network or server error during enrollment.';
      statusEl.className = 'text-xs text-rose-400 text-center';
    }
    showToast('Failed to connect to enrollment server', 'error', 'Network Error');
    if (captureBtn) resetButtonLoading(captureBtn);
  }
}
