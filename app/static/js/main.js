/**
 * FaceTrack AI — Global UI Utilities & Face Enrollment Modal Engine
 */

// Lucide Icons initialization
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

// Modal Utilities
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

// Face Enrollment Modal Engine
let enrollmentStream = null;
let currentEnrollEmpId = null;

async function openFaceEnrollModal(empId, empName) {
  currentEnrollEmpId = empId;
  const nameLabel = document.getElementById('enroll-emp-name');
  if (nameLabel) nameLabel.textContent = empName;

  const video = document.getElementById('enroll-video');
  const snapCanvas = document.getElementById('enroll-canvas');
  const statusEl = document.getElementById('enroll-status');
  const previewImg = document.getElementById('enroll-preview');

  if (previewImg) previewImg.classList.add('hidden');
  if (video) video.classList.remove('hidden');
  if (statusEl) {
    statusEl.textContent = 'Align face in the center of the camera.';
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
      statusEl.textContent = 'Camera access error: ' + err.message;
      statusEl.className = 'text-xs text-rose-400 text-center';
    }
  }
}

function closeFaceEnrollModal() {
  if (enrollmentStream) {
    enrollmentStream.getTracks().forEach((t) => t.stop());
    enrollmentStream = null;
  }
  closeModal('face-enroll-modal');
}

async function captureAndEnrollFace() {
  const video = document.getElementById('enroll-video');
  const statusEl = document.getElementById('enroll-status');
  if (!video || !currentEnrollEmpId) return;

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const base64Data = canvas.toDataURL('image/jpeg', 0.9);

  if (statusEl) {
    statusEl.textContent = 'Processing face scan & extracting 128-d vector...';
    statusEl.className = 'text-xs text-cyan-400 text-center animate-pulse';
  }

  try {
    const res = await fetch(`/api/employees/${currentEnrollEmpId}/register-face`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64Data }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      statusEl.textContent = data.message;
      statusEl.className = 'text-xs text-emerald-400 font-semibold text-center';
      setTimeout(() => {
        closeFaceEnrollModal();
        window.location.reload();
      }, 1200);
    } else {
      statusEl.textContent = data.message || 'Face enrollment failed.';
      statusEl.className = 'text-xs text-rose-400 font-medium text-center';
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = 'Network or server error during enrollment.';
      statusEl.className = 'text-xs text-rose-400 text-center';
    }
  }
}

