// Dashboard JavaScript
let currentPage = 1;
const itemsPerPage = 50;
let priceChart = null;
let distributionChart = null;
let tokenChart = null;
let currentFilters = {
    filter: '',
    search: '',
    min_price_change: null,
    max_price_change: null
};
let currentSort = { key: 'none', dir: 'desc' };
let lastTokensPage = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadStatistics();
    loadTokens();
    loadPumpedTokens();
    loadDumpedTokens();
    setupEventListeners();
    setupCharts();
    
    // Auto refresh every 30 seconds
    setInterval(() => {
        loadStatistics();
        loadTokens();
        loadPumpedTokens();
        loadDumpedTokens();
    }, 30000);
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    document.getElementById('reset-filters').addEventListener('click', resetFilters);
    document.getElementById('prev-page').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page').addEventListener('click', () => changePage(1));
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
    // Debounce search typing
    let searchTimer = null;
    document.getElementById('search-input').addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => applyFilters(), 400);
    });
    // Sort select
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            currentSort = parseSortValue(sortSelect.value);
            currentFilters.sort_by = currentSort.key === 'price' ? 'price'
                : currentSort.key === 'price_change_24h' ? 'price_change_24h'
                : currentSort.key === 'volume_24h' ? 'volume_24h'
                : currentSort.key;
            currentFilters.sort_dir = currentSort.dir.toUpperCase();
            currentPage = 1;
            loadTokens();
        });
    }
    // Clickable headers sorting
    document.querySelectorAll('.tokens-table thead th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const keyMap = {
                'symbol': 'symbol',
                'name': 'name',
                'price': 'price',
                'change': 'price_change_24h',
                'volume': 'volume_24h',
                'liquidity': 'liquidity'
            };
            const k = keyMap[th.dataset.sort] || 'none';
            // toggle direction
            if (currentSort.key === k) {
                currentSort.dir = currentSort.dir === 'desc' ? 'asc' : 'desc';
            } else {
                currentSort = { key: k, dir: 'desc' };
            }
            // reflect to select if possible
            if (k === 'price') sortSelect.value = currentSort.dir === 'desc' ? 'price_desc' : 'price_asc';
            else if (k === 'price_change_24h') sortSelect.value = currentSort.dir === 'desc' ? 'change_desc' : 'change_asc';
            else if (k === 'volume_24h') sortSelect.value = currentSort.dir === 'desc' ? 'volume_desc' : 'volume_asc';
            else sortSelect.value = 'none';
            currentFilters.sort_by = currentSort.key;
            currentFilters.sort_dir = currentSort.dir.toUpperCase();
            currentPage = 1;
            loadTokens();
        });
    });
    // Sync CoinGecko
    const syncBtn = document.getElementById('btn-sync-coingecko');
    if (syncBtn) {
        syncBtn.addEventListener('click', syncCoinGecko);
    }
    
    // Modal
    const modal = document.getElementById('chart-modal');
    const closeModal = document.querySelector('.close-modal');
    closeModal.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const data = await response.json();
        
        document.getElementById('stat-total-tokens').textContent = formatNumber(data.total_tokens);
        document.getElementById('stat-pumped').textContent = formatNumber(data.pumped_tokens);
        document.getElementById('stat-dumped').textContent = formatNumber(data.dumped_tokens);
        document.getElementById('stat-signals').textContent = formatNumber(data.total_signals);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load tokens
async function loadTokens() {
    try {
        const offset = (currentPage - 1) * itemsPerPage;
        const params = new URLSearchParams({
            limit: itemsPerPage,
            offset: offset,
            ...currentFilters
        });
        
        // Remove null values
        Object.keys(params).forEach(key => {
            if (params.get(key) === 'null' || params.get(key) === '') {
                params.delete(key);
            }
        });
        
        const response = await fetch(`/api/tokens?${params.toString()}`);
        const data = await response.json();
        
        lastTokensPage = data.tokens || [];
        displayTokens(lastTokensPage);
        updatePagination(data.total, data.offset, data.limit);
        updateCharts(data.tokens);
    } catch (error) {
        console.error('Error loading tokens:', error);
        document.getElementById('tokens-table-body').innerHTML = 
            '<tr><td colspan="8" class="loading">خطا در بارگذاری داده‌ها</td></tr>';
    }
}

// Display tokens in table
function displayTokens(tokens) {
    const tbody = document.getElementById('tokens-table-body');
    
    if (tokens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">هیچ ارزی یافت نشد</td></tr>';
        return;
    }

    // Server-side sorting already applied; just render
    const sorted = tokens;
    
    tbody.innerHTML = sorted.map(token => {
        const priceChange = token.price_change_24h || 0;
        const priceChangeClass = priceChange >= 0 ? 'positive' : 'negative';
        const priceChangeSign = priceChange >= 0 ? '+' : '';
        const typeClass = token.type || 'normal';
        const typeText = typeClass === 'pump' ? 'پامپ' : typeClass === 'dump' ? 'دامپ' : 'عادی';
        
        return `
            <tr>
                <td><strong>${token.symbol || '-'}</strong></td>
                <td>${token.name || '-'}</td>
                <td>$${formatNumber((token.price_usd ?? token.price ?? 0), 6)}</td>
                <td>
                    <span class="token-change ${priceChangeClass}">
                        ${priceChangeSign}${priceChange.toFixed(2)}%
                    </span>
                </td>
                <td>$${formatNumber((token.volume_24h ?? 0))}</td>
                <td>$${formatNumber(token.liquidity || 0)}</td>
                <td><span class="token-type ${typeClass}">${typeText}</span></td>
                <td>
                    <button class="btn-chart" onclick="showTokenChart('${token.address}', '${token.symbol}')">
                        نمایش چارت
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// Update pagination
function updatePagination(total, offset, limit) {
    const start = offset + 1;
    const end = Math.min(offset + limit, total);
    document.getElementById('pagination-info').textContent = `نمایش ${start}-${end} از ${total}`;
    document.getElementById('page-info').textContent = `صفحه ${currentPage}`;
    
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = end >= total;
}

// Change page
function changePage(direction) {
    const newPage = currentPage + direction;
    if (newPage >= 1) {
        currentPage = newPage;
        loadTokens();
    }
}

// Apply filters
function applyFilters() {
    currentFilters = {
        filter: document.getElementById('filter-type').value,
        search: document.getElementById('search-input').value,
        min_price_change: document.getElementById('min-price-change').value || null,
        max_price_change: document.getElementById('max-price-change').value || null,
        min_price: document.getElementById('min-price').value || null,
        max_price: document.getElementById('max-price').value || null,
        min_volume: document.getElementById('min-volume').value || null,
        max_volume: document.getElementById('max-volume').value || null,
        sort_by: currentSort.key,
        sort_dir: currentSort.dir.toUpperCase()
    };
    
    currentPage = 1;
    loadTokens();
}

// Reset filters
function resetFilters() {
    document.getElementById('filter-type').value = '';
    document.getElementById('search-input').value = '';
    document.getElementById('min-price-change').value = '';
    document.getElementById('max-price-change').value = '';
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) sortSelect.value = 'none';
    const ids = ['min-price','max-price','min-volume','max-volume'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    
    currentFilters = {
        filter: '',
        search: '',
        min_price_change: null,
        max_price_change: null,
        min_price: null,
        max_price: null,
        min_volume: null,
        max_volume: null,
        sort_by: null,
        sort_dir: null
    };
    currentSort = { key: 'none', dir: 'desc' };
    
    currentPage = 1;
    loadTokens();
}

// Load pumped tokens
async function loadPumpedTokens() {
    try {
        const response = await fetch('/api/pumped?limit=10');
        const data = await response.json();
        displayPumpedTokens(data.tokens);
    } catch (error) {
        console.error('Error loading pumped tokens:', error);
    }
}

// Display pumped tokens
function displayPumpedTokens(tokens) {
    const container = document.getElementById('pumped-tokens-list');
    
    if (tokens.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">هیچ ارز پامپی یافت نشد</p>';
        return;
    }
    
    container.innerHTML = tokens.map(token => {
        const priceChange = token.price_change_24h || 0;
        return `
            <div class="token-item">
                <div class="token-info">
                    <span class="token-symbol">${token.symbol || '-'}</span>
                    <span class="token-price">$${formatNumber(token.price_usd || 0, 6)}</span>
                </div>
                <span class="token-change positive">+${priceChange.toFixed(2)}%</span>
            </div>
        `;
    }).join('');
}

// Load dumped tokens
async function loadDumpedTokens() {
    try {
        const response = await fetch('/api/dumped?limit=10');
        const data = await response.json();
        displayDumpedTokens(data.tokens);
    } catch (error) {
        console.error('Error loading dumped tokens:', error);
    }
}

// Display dumped tokens
function displayDumpedTokens(tokens) {
    const container = document.getElementById('dumped-tokens-list');
    
    if (tokens.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">هیچ ارز دامپی یافت نشد</p>';
        return;
    }
    
    container.innerHTML = tokens.map(token => {
        const priceChange = token.price_change_24h || 0;
        return `
            <div class="token-item">
                <div class="token-info">
                    <span class="token-symbol">${token.symbol || '-'}</span>
                    <span class="token-price">$${formatNumber(token.price_usd || 0, 6)}</span>
                </div>
                <span class="token-change negative">${priceChange.toFixed(2)}%</span>
            </div>
        `;
    }).join('');
}

// Setup charts
function setupCharts() {
    // Price chart
    const priceCtx = document.getElementById('price-chart').getContext('2d');
    priceChart = new Chart(priceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'تغییرات قیمت (%)',
                data: [],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    },
                    ticks: {
                        color: '#cbd5e1'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    },
                    ticks: {
                        color: '#cbd5e1'
                    }
                }
            }
        }
    });
    
    // Distribution chart
    const distCtx = document.getElementById('distribution-chart').getContext('2d');
    distributionChart = new Chart(distCtx, {
        type: 'bar',
        data: {
            labels: ['دامپ شدید', 'دامپ', 'عادی', 'پامپ', 'پامپ شدید'],
            datasets: [{
                label: 'تعداد ارزها',
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(239, 68, 68, 0.5)',
                    'rgba(148, 163, 184, 0.5)',
                    'rgba(16, 185, 129, 0.5)',
                    'rgba(16, 185, 129, 0.8)'
                ],
                borderColor: [
                    '#ef4444',
                    '#ef4444',
                    '#94a3b8',
                    '#10b981',
                    '#10b981'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    },
                    ticks: {
                        color: '#cbd5e1'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#cbd5e1'
                    }
                }
            }
        }
    });
}

// Update charts with token data
function updateCharts(tokens) {
    if (tokens.length === 0) return;
    
    // Update distribution chart
    const distribution = {
        'dumped_severe': 0,  // < -20%
        'dumped': 0,         // -20% to -15%
        'normal': 0,         // -15% to 15%
        'pump': 0,           // 15% to 20%
        'pumped_severe': 0   // > 20%
    };
    
    tokens.forEach(token => {
        const change = token.price_change_24h || 0;
        if (change < -20) {
            distribution.dumped_severe++;
        } else if (change < -15) {
            distribution.dumped++;
        } else if (change > 20) {
            distribution.pumped_severe++;
        } else if (change > 15) {
            distribution.pump++;
        } else {
            distribution.normal++;
        }
    });
    
    distributionChart.data.datasets[0].data = [
        distribution.dumped_severe,
        distribution.dumped,
        distribution.normal,
        distribution.pump,
        distribution.pumped_severe
    ];
    distributionChart.update();
    
    // Update price chart (sample data for visualization)
    const topTokens = tokens.slice(0, 10);
    priceChart.data.labels = topTokens.map(t => t.symbol || 'N/A');
    priceChart.data.datasets[0].data = topTokens.map(t => t.price_change_24h || 0);
    priceChart.update();
}

function parseSortValue(v) {
    switch (v) {
        case 'price_desc': return { key: 'price', dir: 'desc' };
        case 'price_asc': return { key: 'price', dir: 'asc' };
        case 'change_desc': return { key: 'price_change_24h', dir: 'desc' };
        case 'change_asc': return { key: 'price_change_24h', dir: 'asc' };
        case 'volume_desc': return { key: 'volume_24h', dir: 'desc' };
        case 'volume_asc': return { key: 'volume_24h', dir: 'asc' };
        default: return { key: 'none', dir: 'desc' };
    }
}

async function syncCoinGecko() {
    const btn = document.getElementById('btn-sync-coingecko');
    const status = document.getElementById('sync-status');
    try {
        btn.disabled = true;
        status.textContent = 'در حال همگام‌سازی...';
        const res = await fetch('/api/coingecko/sync?pages=3&vs_currency=usd', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            status.textContent = `همگام‌سازی انجام شد: ${data.synced} رکورد`;
            loadStatistics();
            loadTokens();
            loadPumpedTokens();
            loadDumpedTokens();
        } else {
            status.textContent = `خطا: ${data.error || 'نامشخص'}`;
        }
    } catch (e) {
        console.error('sync error', e);
        status.textContent = 'خطا در همگام‌سازی';
    } finally {
        btn.disabled = false;
        setTimeout(() => status.textContent = '', 5000);
    }
}

// Show token chart in modal
async function showTokenChart(tokenAddress, tokenSymbol) {
    try {
        const modal = document.getElementById('chart-modal');
        const modalTitle = document.getElementById('modal-token-name');
        modalTitle.textContent = `نمودار قیمت ${tokenSymbol}`;
        
        // Load price history
        const response = await fetch(`/api/price-history/${tokenAddress}?hours=24`);
        const data = await response.json();
        
        // Create or update chart
        const chartCtx = document.getElementById('token-chart').getContext('2d');
        
        if (tokenChart) {
            tokenChart.destroy();
        }
        
        const labels = data.history.map(item => {
            const date = new Date(item.timestamp);
            return date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
        });
        
        const prices = data.history.map(item => item.price);
        
        tokenChart = new Chart(chartCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'قیمت (USD)',
                    data: prices,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 2,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#cbd5e1'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        },
                        ticks: {
                            color: '#cbd5e1',
                            callback: function(value) {
                                return '$' + value.toFixed(6);
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        },
                        ticks: {
                            color: '#cbd5e1',
                            maxTicksLimit: 10
                        }
                    }
                }
            }
        });
        
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error loading token chart:', error);
        alert('خطا در بارگذاری نمودار');
    }
}

// Format number
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return '0';
    
    if (num >= 1e9) {
        return (num / 1e9).toFixed(decimals) + 'B';
    } else if (num >= 1e6) {
        return (num / 1e6).toFixed(decimals) + 'M';
    } else if (num >= 1e3) {
        return (num / 1e3).toFixed(decimals) + 'K';
    } else {
        return num.toFixed(decimals);
    }
}

