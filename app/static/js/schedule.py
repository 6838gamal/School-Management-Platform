// ============= دوال القائمة المنسدلة =============

function toggleDropdown(btn) {
    const container = btn.closest('.dropdown-container');
    const menu = container.querySelector('.dropdown-menu');
    
    document.querySelectorAll('.dropdown-menu.show').forEach(function(m) {
        if (m !== menu) {
            m.classList.remove('show');
            m.classList.add('hidden');
        }
    });
    
    menu.classList.toggle('hidden');
    menu.classList.toggle('show');
}

// إغلاق القوائم عند الضغط في أي مكان خارجها
document.addEventListener('click', function(event) {
    const isDropdownButton = event.target.closest('.dropdown-btn');
    const isDropdownMenu = event.target.closest('.dropdown-menu');
    
    if (!isDropdownButton && !isDropdownMenu) {
        document.querySelectorAll('.dropdown-menu.show').forEach(function(menu) {
            menu.classList.remove('show');
            menu.classList.add('hidden');
        });
    }
});

// ============= دوال الحذف =============

function confirmDelete(url, message = 'هل أنت متأكد من الحذف؟') {
    if (confirm(message)) {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => btn.disabled = true);
        fetch(url, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage('✅ ' + data.message, 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showMessage('❌ ' + (data.message || 'حدث خطأ أثناء الحذف'), 'error');
                buttons.forEach(btn => btn.disabled = false);
            }
        })
        .catch(error => {
            showMessage('❌ حدث خطأ في الاتصال بالخادم', 'error');
            buttons.forEach(btn => btn.disabled = false);
            console.error(error);
        });
    }
}

// ============= دوال الرسائل =============

function showMessage(message, type = 'success') {
    const colors = {
        success: 'bg-green-50 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800',
        error: 'bg-red-50 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800',
        warning: 'bg-yellow-50 text-yellow-800 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-800'
    };
    document.querySelectorAll('.toast-message').forEach(el => el.remove());
    const div = document.createElement('div');
    div.className = `toast-message fixed top-4 right-4 p-4 rounded-lg border ${colors[type]} shadow-lg z-50 max-w-md animate-slide-in`;
    div.innerHTML = message;
    document.body.appendChild(div);
    setTimeout(() => { div.remove(); }, 5000);
}
