// Optimization Dashboard JavaScript

// Load stats on page load
document.addEventListener('DOMContentLoaded', function() {
    loadPerformanceStats();
    loadCacheStats();
    
    // Refresh button
    document.getElementById('refresh-stats').addEventListener('click', () => {
        loadPerformanceStats();
        loadCacheStats();
    });
    
    // Clear cache button
    document.getElementById('clear-cache').addEventListener('click', clearCache);
    
    // Auto refresh every 30 seconds
    setInterval(() => {
        loadPerformanceStats();
        loadCacheStats();
    }, 30000);
});

// Load performance stats
async function loadPerformanceStats() {
    try {
        const response = await fetch('/api/performance/stats');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        displayOperationsStats(data.operations || {});
        displayRequestsStats(data.requests || {});
    } catch (error) {
        console.error('Error loading performance stats:', error);
        document.getElementById('operations-stats').innerHTML = 
            '<div class="error-state">خطا در بارگذاری آمار عملکرد</div>';
    }
}

// Display operations stats
function displayOperationsStats(operations) {
    const container = document.getElementById('operations-stats');
    
    if (Object.keys(operations).length === 0) {
        container.innerHTML = '<div class="empty-state">هیچ داده‌ای یافت نشد</div>';
        return;
    }
    
    let html = '<table class="stats-table"><thead><tr><th>عملیات</th><th>تعداد</th><th>میانگین (ms)</th><th>حداقل</th><th>حداکثر</th></tr></thead><tbody>';
    
    for (const [op, stats] of Object.entries(operations)) {
        html += `
            <tr>
                <td><strong>${op}</strong></td>
                <td>${stats.count || 0}</td>
                <td>${((stats.avg || 0) * 1000).toFixed(2)}</td>
                <td>${((stats.min || 0) * 1000).toFixed(2)}</td>
                <td>${((stats.max || 0) * 1000).toFixed(2)}</td>
            </tr>
        `;
    }
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Display requests stats
function displayRequestsStats(requests) {
    const container = document.getElementById('requests-stats');
    
    if (Object.keys(requests).length === 0) {
        container.innerHTML = '<div class="empty-state">هیچ داده‌ای یافت نشد</div>';
        return;
    }
    
    let html = '<table class="stats-table"><thead><tr><th>Endpoint</th><th>کل</th><th>خطا</th><th>نرخ موفقیت</th></tr></thead><tbody>';
    
    for (const [endpoint, stats] of Object.entries(requests)) {
        const successRate = stats.success_rate || 0;
        const successClass = successRate > 95 ? 'success' : successRate > 80 ? 'warning' : 'error';
        
        html += `
            <tr>
                <td><strong>${endpoint}</strong></td>
                <td>${stats.total || 0}</td>
                <td>${stats.errors || 0}</td>
                <td><span class="rate-${successClass}">${successRate.toFixed(2)}%</span></td>
            </tr>
        `;
    }
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Load cache stats
async function loadCacheStats() {
    try {
        const response = await fetch('/api/cache/stats');
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        displayCacheStats(data);
    } catch (error) {
        console.error('Error loading cache stats:', error);
        document.getElementById('cache-stats').innerHTML = 
            '<div class="error-state">خطا در بارگذاری آمار cache</div>';
    }
}

// Display cache stats
function displayCacheStats(stats) {
    const container = document.getElementById('cache-stats');
    
    const hitRate = stats.total_entries > 0 
        ? ((stats.active_entries / stats.total_entries) * 100).toFixed(2) 
        : 0;
    
    container.innerHTML = `
        <div class="cache-grid">
            <div class="cache-stat-item">
                <div class="cache-stat-label">کل ورودی‌ها</div>
                <div class="cache-stat-value">${stats.total_entries || 0}</div>
            </div>
            <div class="cache-stat-item">
                <div class="cache-stat-label">ورودی‌های فعال</div>
                <div class="cache-stat-value">${stats.active_entries || 0}</div>
            </div>
            <div class="cache-stat-item">
                <div class="cache-stat-label">ورودی‌های منقضی</div>
                <div class="cache-stat-value">${stats.expired_entries || 0}</div>
            </div>
            <div class="cache-stat-item">
                <div class="cache-stat-label">نرخ Hit</div>
                <div class="cache-stat-value">${hitRate}%</div>
            </div>
        </div>
    `;
}

// Clear cache
async function clearCache() {
    if (!confirm('آیا مطمئن هستید که می‌خواهید cache را پاک کنید؟')) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            Toast.success('Cache با موفقیت پاک شد');
            loadCacheStats();
        } else {
            Toast.error('خطا در پاک کردن cache');
        }
    } catch (error) {
        console.error('Error clearing cache:', error);
        Toast.error('خطا در پاک کردن cache');
    }
}

