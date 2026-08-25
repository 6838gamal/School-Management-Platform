/* ============================================================
   School Management System — Global JavaScript
   ============================================================ */

(function () {
    const saved = document.cookie.match(/theme=(dark|light)/);
    if (saved && saved[1] === 'dark') document.documentElement.classList.add('dark');
})();

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    document.cookie = `theme=${isDark ? 'dark' : 'light'};path=/;max-age=31536000`;
}
document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    let overlay = document.getElementById('sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'sidebar-overlay';
        overlay.addEventListener('click', () => {
            sidebar?.classList.remove('open');
            overlay.classList.remove('active');
        });
        document.body.appendChild(overlay);
    }
    sidebar?.classList.toggle('open');
    overlay.classList.toggle('active');
}
document.getElementById('sidebar-toggle')?.addEventListener('click', toggleSidebar);

function showModal(id) { document.getElementById(id)?.classList.add('active'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('active'); }
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('modal-backdrop')) e.target.classList.remove('active');
});
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') document.querySelectorAll('.modal-backdrop.active').forEach(m => m.classList.remove('active'));
});

function showToast(message, type) {
    type = type || 'info';
    let container = document.getElementById('toast-container');
    if (!container) { container = document.createElement('div'); container.id = 'toast-container'; document.body.appendChild(container); }
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () { toast.style.opacity = '0'; toast.style.transform = 'translateY(-10px)'; setTimeout(function () { toast.remove(); }, 200); }, 3000);
}

async function apiFetch(url, options) {
    options = options || {};
    const defaults = { headers: { 'Content-Type': 'application/json' } };
    const merged = Object.assign({}, defaults, options);
    merged.headers = Object.assign({}, defaults.headers, options.headers || {});
    if (merged.body && typeof merged.body === 'object' && !(merged.body instanceof FormData)) merged.body = JSON.stringify(merged.body);
    const res = await fetch(url, merged);
    if (res.status === 204) return null;
    const data = await res.json().catch(function () { return null; });
    if (!res.ok) { const msg = (data && data.detail) || ('HTTP ' + res.status); showToast(msg, 'error'); throw new Error(msg); }
    return data;
}

function confirmAction(message) { return window.confirm(message); }
function todayStr() { return new Date().toISOString().split('T')[0]; }
function formatDate(dateStr) { if (!dateStr) return '—'; const d = new Date(dateStr); return d.toLocaleDateString('ar-SA', { year: 'numeric', month: 'short', day: 'numeric' }); }

document.querySelectorAll('[data-auto-dismiss]').forEach(function (el) {
    setTimeout(function () { el.style.opacity = '0'; setTimeout(function () { el.remove(); }, 300); }, parseInt(el.dataset.autoDismiss) || 4000);
});
