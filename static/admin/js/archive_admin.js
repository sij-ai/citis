// Archive Admin JavaScript
function retryArchive(shortcode) {
    if (confirm(`Retry archiving for ${shortcode}?`)) {
        fetch(`/admin/archive/shortcode/${shortcode}/retry-archive/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Archive task queued for ${shortcode}!\nTask ID: ${data.task_id}`);
                // Refresh the page after a delay to show updated status
                setTimeout(() => window.location.reload(), 2000);
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to retry archive');
        });
    }
}

// Auto-refresh functionality for task status
function startAutoRefresh() {
    // Refresh task status every 30 seconds
    setInterval(() => {
        // Only refresh if on shortcode changelist or detail page
        if (window.location.href.includes('/admin/archive/shortcode/')) {
            location.reload();
        }
    }, 30000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add refresh button to admin pages
    const breadcrumb = document.querySelector('.breadcrumbs');
    if (breadcrumb && window.location.href.includes('/admin/archive/shortcode/')) {
        const refreshBtn = document.createElement('button');
        refreshBtn.innerHTML = '🔄 Refresh Status';
        refreshBtn.className = 'button';
        refreshBtn.style.marginLeft = '10px';
        refreshBtn.onclick = () => location.reload();
        breadcrumb.appendChild(refreshBtn);
    }
}); 