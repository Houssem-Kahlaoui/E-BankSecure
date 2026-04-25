// main.js — Secure e-Bank shared JavaScript

// ── Sidebar toggle ──
const sidebar      = document.getElementById('sidebar');
const sidebarToggle= document.getElementById('sidebarToggle');
const mainContent  = document.querySelector('.main-content');
const menuBtn      = document.getElementById('menuBtn');

if (sidebarToggle) {
  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    mainContent && mainContent.classList.toggle('expanded');
    const icon = sidebarToggle.querySelector('i');
    icon.className = sidebar.classList.contains('collapsed')
      ? 'bi bi-chevron-right'
      : 'bi bi-chevron-left';
  });
}

if (menuBtn) {
  menuBtn.addEventListener('click', () => {
    sidebar.classList.toggle('mobile-open');
  });
  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', e => {
    if (window.innerWidth <= 900 &&
        sidebar && sidebar.classList.contains('mobile-open') &&
        !sidebar.contains(e.target) && e.target !== menuBtn) {
      sidebar.classList.remove('mobile-open');
    }
  });
}

// ── Notification panel ──
const notifPanel = document.getElementById('notifPanel');

function toggleNotifications() {
  if (!notifPanel) return;
  notifPanel.classList.toggle('open');
  if (notifPanel.classList.contains('open')) {
    // Mark as read after 1 second
    setTimeout(() => {
      fetch('/customer/notifications/read', { method: 'POST' })
        .then(() => {
          const badge = document.querySelector('.notif-badge');
          if (badge) badge.remove();
        });
    }, 1000);
  }
}

// Close panel on outside click
document.addEventListener('click', e => {
  const notifBtn = document.getElementById('notifBtn');
  if (notifPanel && notifPanel.classList.contains('open') &&
      !notifPanel.contains(e.target) && e.target !== notifBtn &&
      !notifBtn?.contains(e.target)) {
    notifPanel.classList.remove('open');
  }
});

// ── Flash auto-dismiss ──
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => {
    el.style.animation = 'slideDown 0.3s reverse';
    setTimeout(() => el.remove(), 280);
  }, 5000);
});

// ── Modal helpers ──
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('open');
}
function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
}
// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});
// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
    if (notifPanel) notifPanel.classList.remove('open');
  }
});

// ── Active nav link ──
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-link').forEach(link => {
  if (link.getAttribute('href') &&
      currentPath.startsWith(link.getAttribute('href'))) {
    link.classList.add('active');
  }
});

// ── Copy to clipboard ──
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copié dans le presse-papiers !', 'success');
  });
}

// ── Toast helper ──
function showToast(message, type = 'info') {
  const container = document.querySelector('.flash-container') ||
                    (() => {
                      const c = document.createElement('div');
                      c.className = 'flash-container flash-fixed';
                      document.body.appendChild(c);
                      return c;
                    })();
  const icons = { success: 'check-circle', danger: 'exclamation-circle',
                  warning: 'exclamation-triangle', info: 'info-circle' };
  const toast = document.createElement('div');
  toast.className = `flash flash-${type}`;
  toast.innerHTML = `<i class="bi bi-${icons[type] || 'info-circle'}"></i>${message}
                     <button class="flash-close" onclick="this.parentElement.remove()">
                       <i class="bi bi-x"></i></button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

// ── Format currency (DNT) ──
function formatDNT(amount) {
  return new Intl.NumberFormat('fr-TN', {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  }).format(amount) + ' DNT';
}

// ── Animate counter numbers ──
function animateCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target  = parseFloat(el.dataset.count);
    const isFloat = el.dataset.count.includes('.');
    const duration = 1200;
    const start    = performance.now();
    const from     = 0;
    const update   = now => {
      const elapsed = now - start;
      const progress= Math.min(elapsed / duration, 1);
      const ease    = 1 - Math.pow(1 - progress, 3);
      const value   = from + (target - from) * ease;
      el.textContent = isFloat
        ? value.toLocaleString('fr-TN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : Math.round(value).toLocaleString('fr-TN');
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  });
}
// Trigger when visible
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) { animateCounters(); observer.disconnect(); } });
});
const statsGrid = document.querySelector('.stats-grid');
if (statsGrid) observer.observe(statsGrid);

// ── Confirm dialog wrapper ──
function confirmAction(message, formId) {
  if (confirm(message)) {
    document.getElementById(formId)?.submit();
    return true;
  }
  return false;
}
