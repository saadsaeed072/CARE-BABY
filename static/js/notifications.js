/**
 * Real-time Notifications with Socket.IO
 * BabyCare Platform
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO
    const socket = io();

    // Listen for new notifications
    socket.on('new_notification', function(data) {
        showToast(data.title, data.message, data.type || 'info');
        updateNotificationBadge();
    });

    // Listen for new messages
    socket.on('new_message', function(data) {
        // If we are not on the chat page with this user, show a toast
        const currentChatUser = document.getElementById('chat-with-user-id');
        if (!currentChatUser || currentChatUser.value != data.sender_id) {
            showToast('New Message from ' + data.sender_name, data.message_text, 'message');
        }
        updateMessageBadge();
        
        // If we ARE on the chat page, play a sound or append message (optional enhancement)
        if (typeof appendIncomingMessage === 'function') {
            appendIncomingMessage(data);
        }
    });

    /**
     * Show a premium toast notification
     */
    function showToast(title, message, type) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toastId = 'toast-' + Date.now();
        const iconClass = getIconForType(type);
        const colorClass = getColorForType(type);

        const toastHtml = `
            <div id="${toastId}" class="toast show animate-slide-in" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header border-0 pb-0">
                    <div class="toast-icon-wrapper ${colorClass} me-2">
                        <i class="bi ${iconClass}"></i>
                    </div>
                    <strong class="me-auto">${title}</strong>
                    <small class="text-muted">Just now</small>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body pt-2">
                    ${message}
                </div>
                <div class="toast-progress ${colorClass}"></div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (toastElement) {
                toastElement.classList.add('animate-slide-out');
                setTimeout(() => toastElement.remove(), 500);
            }
        }, 5000);
    }

    function getIconForType(type) {
        switch(type) {
            case 'booking': return 'bi-calendar-check';
            case 'message': return 'bi-chat-dots';
            case 'success': return 'bi-check-circle';
            case 'warning': return 'bi-exclamation-triangle';
            case 'danger': return 'bi-x-circle';
            default: return 'bi-info-circle';
        }
    }

    function getColorForType(type) {
        switch(type) {
            case 'booking': return 'bg-primary-subtle text-primary';
            case 'message': return 'bg-info-subtle text-info';
            case 'success': return 'bg-success-subtle text-success';
            case 'warning': return 'bg-warning-subtle text-warning';
            case 'danger': return 'bg-danger-subtle text-danger';
            default: return 'bg-secondary-subtle text-secondary';
        }
    }

    /**
     * Update notification badge count in navbar
     */
    function updateNotificationBadge() {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            let count = parseInt(badge.textContent) || 0;
            badge.textContent = count + 1;
            badge.classList.remove('d-none');
            badge.classList.add('pulse-animation');
        }
    }

    /**
     * Update message badge count in navbar
     */
    function updateMessageBadge() {
        const badge = document.querySelector('.message-badge');
        if (badge) {
            let count = parseInt(badge.textContent) || 0;
            badge.textContent = count + 1;
            badge.classList.remove('d-none');
            badge.classList.add('pulse-animation');
        }
    }
});
