// Futures Analysis JavaScript
let analysisData = [];
let currentFilters = {
    timeframe: 'all',
    signal: 'all',
    search: ''
};
let currentParams = {};
let tradingChart = null;
let currentTradingSymbol = null;
let currentTradingPrice = 0;
let priceUpdateInterval = null;
let lastCloses = [];
let lastVolumes = [];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadParams();
    setupEventListeners();
    loadAnalysis();
    
    // Auto refresh every 60 seconds
    setInterval(() => {
        loadAnalysis();
    }, 60000);
});

// Setup event listeners
function setupEventListeners() {
    // Settings toggle
    document.getElementById('toggle-settings').addEventListener('click', toggleSettings);
    
    // Form submit
    document.getElementById('params-form').addEventListener('submit', saveParams);
    document.getElementById('reset-params').addEventListener('click', resetParams);
    
    // Filters
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    document.getElementById('refresh-btn').addEventListener('click', loadAnalysis);
    
    // Sort
    document.getElementById('sort-by').addEventListener('change', sortResults);
    
    // Modal
    const modal = document.getElementById('symbol-modal');
    const closeModal = document.querySelector('.close-modal');
    closeModal.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Trading Modal
    const tradingModal = document.getElementById('trading-modal');
    const closeTradingModal = document.getElementById('close-trading-modal');
    closeTradingModal.addEventListener('click', () => {
        closeTradingModalFunc();
    });
    window.addEventListener('click', (e) => {
        if (e.target === tradingModal) {
            closeTradingModalFunc();
        }
    });
    
    // Trading form
    document.getElementById('trading-form').addEventListener('submit', placeOrder);
    document.getElementById('calculate-btn').addEventListener('click', calculatePrices);
    document.getElementById('entry-percent').addEventListener('input', calculatePrices);
    document.getElementById('stop-loss-percent').addEventListener('input', calculatePrices);
    document.getElementById('take-profit-percent').addEventListener('input', calculatePrices);

    // Overlay toggles
    const toggles = ['toggle-tech', 'toggle-vp', 'toggle-ut', 'toggle-bs', 'toggle-bb', 'toggle-ema'];
    toggles.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => rebuildTradingChart());
    });
}

// Toggle settings panel
function toggleSettings() {
    const content = document.getElementById('settings-content');
    const toggle = document.getElementById('toggle-settings');
    content.classList.toggle('collapsed');
    toggle.classList.toggle('collapsed');
}

// Load parameters
async function loadParams() {
    try {
        const response = await fetch('/api/futures/params');
        const params = await response.json();
        currentParams = params;
        
        // Populate form
        Object.keys(params).forEach(key => {
            const input = document.getElementById(key);
            if (input) {
                input.value = params[key];
            }
        });
        
        updateStatus('فعال', true);
    } catch (error) {
        console.error('Error loading params:', error);
        updateStatus('خطا در بارگذاری تنظیمات', false);
    }
}

// Save parameters
async function saveParams(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const params = {};
    
    formData.forEach((value, key) => {
        // Convert to number if applicable
        const numValue = parseFloat(value);
        params[key] = isNaN(numValue) ? value : numValue;
    });
    
    try {
        const response = await fetch('/api/futures/params', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
        
        const result = await response.json();
        if (result.success) {
            currentParams = result.params;
            alert('تنظیمات با موفقیت ذخیره شد');
            loadAnalysis(); // Reload analysis with new params
        } else {
            alert('خطا در ذخیره تنظیمات');
        }
    } catch (error) {
        console.error('Error saving params:', error);
        alert('خطا در ذخیره تنظیمات');
    }
}

// Reset parameters
function resetParams() {
    if (confirm('آیا مطمئن هستید که می‌خواهید تنظیمات را به حالت پیش‌فرض بازگردانید؟')) {
        loadParams();
    }
}

// Load analysis
async function loadAnalysis() {
    try {
        updateStatus('در حال تحلیل...', false);
        
        const params = {
            timeframes: '15m,1m,1d',
            min_volume: currentParams.min_volume || 1000000,
            limit: currentParams.limit || 50,
            min_score: currentParams.min_score || 0
        };
        
        const queryString = new URLSearchParams(params).toString();
        let response = await fetch(`/api/futures/analyze?${queryString}`);
        let data = await response.json();
        if (data.error || !Array.isArray(data.symbols) || data.symbols.length === 0) {
            response = await fetch(`/api/bitunix/futures/analyze?${queryString}`);
            data = await response.json();
            if (data.error) throw new Error(data.error);
        }
        analysisData = data.symbols || [];
        displayResults(analysisData);
        
        document.getElementById('symbols-count').textContent = data.total || 0;
        document.getElementById('last-update').textContent = new Date().toLocaleTimeString('fa-IR');
        updateStatus('فعال', true);
    } catch (error) {
        console.error('Error loading analysis:', error);
        updateStatus('خطا در بارگذاری داده‌ها', false);
        document.getElementById('analysis-table-body').innerHTML = 
            '<tr><td colspan="10" class="loading">خطا در بارگذاری داده‌ها: ' + error.message + '</td></tr>';
    }
}

// Display results
function displayResults(symbols) {
    const tbody = document.getElementById('analysis-table-body');
    
    if (symbols.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading">هیچ داده‌ای یافت نشد</td></tr>';
        return;
    }
    
    // Apply filters
    let filtered = symbols;
    
    if (currentFilters.search) {
        filtered = filtered.filter(s => 
            s.symbol.toLowerCase().includes(currentFilters.search.toLowerCase())
        );
    }
    
    tbody.innerHTML = filtered.map((symbolData, index) => {
        const symbol = symbolData.symbol;
        const timeframes = symbolData.timeframes;
        
        // Get default timeframe data (15m)
        const defaultTF = timeframes['15m'] || timeframes['1m'] || timeframes['1d'] || Object.values(timeframes)[0];
        
        if (!defaultTF) return '';
        
        const rsi = defaultTF.rsi || 50;
        const macd = defaultTF.macd || { histogram: 0 };
        const ma = defaultTF.ma || 0;
        const price = defaultTF.current_price || 0;
        const score = symbolData.avg_score || 0;
        const signal = defaultTF.signal || 'NEUTRAL';
        const volume = symbolData.volume_24h || 0;
        
        // Apply signal filter
        if (currentFilters.signal !== 'all' && signal !== currentFilters.signal) {
            return '';
        }
        
        // Apply timeframe filter
        if (currentFilters.timeframe !== 'all' && !timeframes[currentFilters.timeframe]) {
            return '';
        }
        
        // Determine RSI badge class
        let rsiClass = 'neutral';
        if (rsi < 30) rsiClass = 'oversold';
        else if (rsi > 70) rsiClass = 'overbought';
        
        // Determine MACD badge class
        let macdClass = 'neutral';
        if (macd.histogram > 0) macdClass = 'positive';
        else if (macd.histogram < 0) macdClass = 'negative';
        
        // Determine MA badge class
        let maClass = 'neutral';
        const maSignal = defaultTF.ma_signal || 0;
        if (maSignal > 0) maClass = 'above';
        else if (maSignal < 0) maClass = 'below';
        
        // Score class
        let scoreClass = 'neutral';
        if (score > 10) scoreClass = 'positive';
        else if (score < -10) scoreClass = 'negative';
        
        // Timeframes badges
        const timeframeBadges = Object.keys(timeframes).map(tf => {
            const tfData = timeframes[tf];
            const tfSignal = tfData.signal || 'NEUTRAL';
            const isActive = currentFilters.timeframe === tf;
            return `<span class="timeframe-badge ${isActive ? 'active' : ''}" onclick="filterByTimeframe('${tf}')">${tf}: ${tfSignal}</span>`;
        }).join('');
        
        return `
            <tr onclick="showSymbolDetail('${symbol}')" ondblclick="openTradingModal('${symbol}', ${price})" style="cursor: pointer;">
                <td>${index + 1}</td>
                <td><strong>${symbol}</strong></td>
                <td>$${formatNumber(price, 6)}</td>
                <td>
                    <span class="score-display ${scoreClass}">${score.toFixed(2)}</span>
                </td>
                <td>
                    <span class="indicator-badge rsi-badge ${rsiClass}">${rsi.toFixed(2)}</span>
                </td>
                <td>
                    <span class="indicator-badge macd-badge ${macdClass}">${macd.histogram.toFixed(4)}</span>
                </td>
                <td>
                    <span class="indicator-badge ma-badge ${maClass}">${maSignal > 0 ? 'بالا' : maSignal < 0 ? 'پایین' : 'خنثی'}</span>
                </td>
                <td>$${formatNumber(volume)}</td>
                <td>
                    <div class="timeframes-display">${timeframeBadges}</div>
                </td>
                <td>
                    <span class="signal-badge ${signal}">${getSignalText(signal)}</span>
                </td>
            </tr>
        `;
    }).filter(row => row !== '').join('');
}

// Filter by timeframe
function filterByTimeframe(timeframe) {
    currentFilters.timeframe = timeframe === currentFilters.timeframe ? 'all' : timeframe;
    applyFilters();
}

// Apply filters
function applyFilters() {
    currentFilters.timeframe = document.getElementById('timeframe-filter').value;
    currentFilters.signal = document.getElementById('signal-filter').value;
    currentFilters.search = document.getElementById('search-symbol').value;
    
    displayResults(analysisData);
}

// Sort results
function sortResults() {
    const sortBy = document.getElementById('sort-by').value;
    
    analysisData.sort((a, b) => {
        switch (sortBy) {
            case 'score':
                return b.avg_score - a.avg_score;
            case 'volume':
                return b.volume_24h - a.volume_24h;
            case 'price_change':
                const aChange = Object.values(a.timeframes)[0]?.price_change || 0;
                const bChange = Object.values(b.timeframes)[0]?.price_change || 0;
                return bChange - aChange;
            default:
                return 0;
        }
    });
    
    displayResults(analysisData);
}

// Show symbol detail
async function showSymbolDetail(symbol) {
    try {
        const modal = document.getElementById('symbol-modal');
        const modalContent = document.getElementById('modal-content');
        const modalTitle = document.getElementById('modal-symbol-name');
        
        modalTitle.textContent = `جزئیات تحلیل ${symbol}`;
        modalContent.innerHTML = '<div class="loading">در حال بارگذاری...</div>';
        modal.style.display = 'block';
        
        // Get analysis for all timeframes
        const timeframes = ['1m', '15m', '1d'];
        const analyses = {};
        
        for (const tf of timeframes) {
            try {
                const response = await fetch(`/api/futures/analyze-symbol?symbol=${symbol}&timeframe=${tf}`);
                const analysis = await response.json();
                if (analysis && !analysis.error) {
                    analyses[tf] = analysis;
                }
            } catch (error) {
                console.error(`Error loading ${tf} analysis:`, error);
            }
        }
        
        // Display analysis
        let html = '';
        
        for (const [tf, analysis] of Object.entries(analyses)) {
            html += `
                <div class="modal-detail-section">
                    <h3>تایم فریم ${tf}</h3>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">قیمت فعلی:</span>
                            <span class="detail-value">$${formatNumber(analysis.current_price, 6)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">تغییر قیمت:</span>
                            <span class="detail-value ${analysis.price_change >= 0 ? 'positive' : 'negative'}">${analysis.price_change >= 0 ? '+' : ''}${analysis.price_change.toFixed(2)}%</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">RSI:</span>
                            <span class="detail-value">${analysis.rsi.toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">MACD:</span>
                            <span class="detail-value">${analysis.macd.macd.toFixed(4)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">MACD Signal:</span>
                            <span class="detail-value">${analysis.macd.signal.toFixed(4)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">MACD Histogram:</span>
                            <span class="detail-value ${analysis.macd.histogram >= 0 ? 'positive' : 'negative'}">${analysis.macd.histogram.toFixed(4)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">MA (${currentParams.ma_period || 20}):</span>
                            <span class="detail-value">$${formatNumber(analysis.ma, 6)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">سیگنال MA:</span>
                            <span class="detail-value">${analysis.ma_signal > 0 ? 'بالا' : analysis.ma_signal < 0 ? 'پایین' : 'خنثی'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">حجم:</span>
                            <span class="detail-value">$${formatNumber(analysis.volume)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">نسبت حجم:</span>
                            <span class="detail-value">${analysis.volume_ratio.toFixed(2)}x</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">امتیاز کل:</span>
                            <span class="detail-value ${analysis.score.total_score >= 0 ? 'positive' : 'negative'}">${analysis.score.total_score.toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">سیگنال:</span>
                            <span class="signal-badge ${analysis.signal}">${getSignalText(analysis.signal)}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (html === '') {
            html = '<div class="loading">هیچ داده‌ای یافت نشد</div>';
        }
        
        modalContent.innerHTML = html;
    } catch (error) {
        console.error('Error showing symbol detail:', error);
        document.getElementById('modal-content').innerHTML = 
            '<div class="loading">خطا در بارگذاری جزئیات</div>';
    }
}

// Get signal text in Persian
function getSignalText(signal) {
    const signals = {
        'STRONG_BUY': 'خرید قوی',
        'BUY': 'خرید',
        'NEUTRAL': 'خنثی',
        'SELL': 'فروش',
        'STRONG_SELL': 'فروش قوی'
    };
    return signals[signal] || signal;
}

// Update status
function updateStatus(text, isActive) {
    const indicator = document.getElementById('status-indicator');
    indicator.textContent = text;
    if (isActive) {
        indicator.classList.add('active');
    } else {
        indicator.classList.remove('active');
    }
}

// Close trading modal
function closeTradingModalFunc() {
    const tradingModal = document.getElementById('trading-modal');
    tradingModal.style.display = 'none';
    
    if (tradingChart) {
        tradingChart.destroy();
        tradingChart = null;
    }
    
    if (priceUpdateInterval) {
        clearInterval(priceUpdateInterval);
        priceUpdateInterval = null;
    }
}

// Open trading modal
async function openTradingModal(symbol, price) {
    try {
        // Close any existing modal
        if (priceUpdateInterval) {
            clearInterval(priceUpdateInterval);
        }
        
        currentTradingSymbol = symbol;
        currentTradingPrice = price;
        
        const modal = document.getElementById('trading-modal');
        document.getElementById('trading-symbol-name').textContent = `معامله ${symbol}`;
        document.getElementById('trading-symbol').value = symbol;
        document.getElementById('current-price').textContent = `$${formatNumber(price, 6)}`;
        
        modal.style.display = 'block';
        
        // Load chart
        await loadTradingChart(symbol);
        
        // Calculate initial prices
        await calculatePrices();
        
        // Update price periodically (every 5 seconds)
        priceUpdateInterval = setInterval(async () => {
            await updateTradingPrice(symbol);
        }, 5000);
    } catch (error) {
        console.error('Error opening trading modal:', error);
        alert('خطا در باز کردن مودال معامله');
    }
}

// Load trading chart
async function loadTradingChart(symbol) {
    try {
        let response = await fetch(`/api/bybit/klines?symbol=${symbol}&interval=1&limit=200`);
        let data = await response.json();
        if (data.error) {
            response = await fetch(`/api/bitunix/klines?symbol=${symbol}&interval=1&limit=200`);
            data = await response.json();
            if (data.error) throw new Error(data.error);
        }
        const klines = data.klines || [];
        
        // Parse data for chart
        const labels = klines.map(k => {
            const date = new Date(k.time);
            return date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
        });
        
        const prices = klines.map(k => k.close);
        const volumes = klines.map(k => k.volume);
        lastCloses = prices;
        lastVolumes = volumes;
        
        // Destroy existing chart
        const ctx = document.getElementById('trading-chart').getContext('2d');
        if (tradingChart) {
            tradingChart.destroy();
        }
        
        // Create new chart base datasets
        tradingChart = new Chart(ctx, makeChartConfig(labels, prices, volumes));
        await loadServerSignals(symbol);
        applyOverlays();
    } catch (error) {
        console.error('Error loading trading chart:', error);
    }
}

function rebuildTradingChart() {
    if (!tradingChart || lastCloses.length === 0) return;
    applyOverlays();
}

function makeChartConfig(labels, prices, volumes) {
    return {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'قیمت',
                data: prices,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                tension: 0.4,
                fill: true,
                yAxisID: 'y'
            }, {
                label: 'حجم',
                data: volumes,
                type: 'bar',
                backgroundColor: 'rgba(148, 163, 184, 0.3)',
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
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
                    type: 'linear',
                    display: true,
                    position: 'left',
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return '$' + Number(value).toFixed(2);
                        }
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    ticks: {
                        color: '#cbd5e1'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    ticks: {
                        color: '#cbd5e1',
                        maxTicksLimit: 20
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                }
            }
        }
    };
}

function applyOverlays() {
    const showTech = document.getElementById('toggle-tech')?.checked;
    const showVP = document.getElementById('toggle-vp')?.checked;
    const showUT = document.getElementById('toggle-ut')?.checked;
    const showBS = document.getElementById('toggle-bs')?.checked;
    const showBB = document.getElementById('toggle-bb')?.checked;
    const showEMA = document.getElementById('toggle-ema')?.checked;

    // Reset to base datasets (first 2 datasets kept)
    tradingChart.data.datasets = tradingChart.data.datasets.slice(0, 2);

    // Compute SMA(20), RSI(14), MACD hist
    const sma = calcSMA(lastCloses, 20);
    const rsiArr = calcRSI(lastCloses, 14);
    const macdHist = calcMACDHist(lastCloses, 12, 26, 9);

    // UT Bot Alerts (cross markers)
    if (showUT) {
        const points = [];
        for (let i = 1; i < lastCloses.length; i++) {
            const c = lastCloses[i];
            const p = lastCloses[i - 1];
            const ma = sma[i] ?? null;
            const prevMa = sma[i - 1] ?? null;
            const hist = macdHist[i] ?? null;
            const prevHist = macdHist[i - 1] ?? null;
            const rsi = rsiArr[i] ?? 50;
            // Buy/Sell signal when MACD hist crosses zero and price crosses MA
            const macdCross = hist !== null && prevHist !== null && ((hist > 0 && prevHist <= 0) || (hist < 0 && prevHist >= 0));
            const maCross = ma !== null && prevMa !== null && ((c > ma && p <= prevMa) || (c < ma && p >= prevMa));
            if (macdCross && maCross && rsi > 45 && rsi < 55) {
                points.push({ x: i, y: c });
            }
        }
        tradingChart.data.datasets.push({
            label: 'UT Alerts',
            type: 'scatter',
            data: points,
            yAxisID: 'y',
            pointStyle: 'crossRot',
            pointRadius: 6,
            borderColor: '#f59e0b',
            backgroundColor: '#f59e0b'
        });
    }

    // Volume Profile (POC line)
    if (showVP) {
        const vp = calcVolumeProfile(lastCloses, lastVolumes, 20);
        if (vp.pocPrice) {
            const pocLine = Array.from({ length: lastCloses.length }, () => vp.pocPrice);
            tradingChart.data.datasets.push({
                label: 'POC',
                data: pocLine,
                borderColor: '#ef4444',
                borderDash: [6, 6],
                pointRadius: 0,
                fill: false,
                yAxisID: 'y'
            });
        }
    }

    // Server Buy/Sell signals overlay
    if (showBS && window._serverSignals) {
        const buys = (window._serverSignals.buy || []).map(p => ({ x: p.idx, y: p.price }));
        const sells = (window._serverSignals.sell || []).map(p => ({ x: p.idx, y: p.price }));
        tradingChart.data.datasets.push({
            label: 'Buy',
            type: 'scatter',
            data: buys,
            yAxisID: 'y',
            pointStyle: 'triangle',
            pointRadius: 6,
            borderColor: '#22c55e',
            backgroundColor: '#22c55e'
        });
        tradingChart.data.datasets.push({
            label: 'Sell',
            type: 'scatter',
            data: sells,
            yAxisID: 'y',
            pointStyle: 'triangle',
            rotation: 180,
            pointRadius: 6,
            borderColor: '#ef4444',
            backgroundColor: '#ef4444'
        });
    }

    if (showEMA) addEMACross();
    if (showBB) addBBands();
    // Technical Ratings badge
    const badge = document.getElementById('tech-rating-badge');
    if (showTech && badge) {
        const last = lastCloses.length - 1;
        const rsi = rsiArr[last] ?? 50;
        const hist = macdHist[last] ?? 0;
        const price = lastCloses[last];
        const ma = sma[last] ?? price;
        let rating = 'Neutral';
        let color = '#f59e0b';
        const bullish = (rsi < 35) || (hist > 0 && price > ma);
        const bearish = (rsi > 65) || (hist < 0 && price < ma);
        if (bullish && !bearish) {
            rating = 'Buy';
            color = '#22c55e';
        } else if (bearish && !bullish) {
            rating = 'Sell';
            color = '#ef4444';
        }
        badge.textContent = `Technical Ratings: ${rating}`;
        badge.style.color = color;
    } else if (badge) {
        badge.textContent = '';
    }

    tradingChart.update();
}

// ---------- Lightweight indicator helpers (client-side) ----------
function calcSMA(values, period) {
    const out = new Array(values.length).fill(null);
    let sum = 0;
    for (let i = 0; i < values.length; i++) {
        sum += values[i];
        if (i >= period) sum -= values[i - period];
        if (i >= period - 1) out[i] = sum / period;
    }
    return out;
}

function calcRSI(values, period) {
    const out = new Array(values.length).fill(null);
    let gain = 0, loss = 0;
    for (let i = 1; i <= period; i++) {
        const diff = values[i] - values[i - 1];
        if (diff > 0) gain += diff; else loss -= diff;
    }
    let avgGain = gain / period;
    let avgLoss = loss / period;
    out[period] = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));
    for (let i = period + 1; i < values.length; i++) {
        const diff = values[i] - values[i - 1];
        const up = diff > 0 ? diff : 0;
        const down = diff < 0 ? -diff : 0;
        avgGain = (avgGain * (period - 1) + up) / period;
        avgLoss = (avgLoss * (period - 1) + down) / period;
        out[i] = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));
    }
    return out;
}

function calcEMA(values, period) {
    const k = 2 / (period + 1);
    const out = new Array(values.length).fill(null);
    let ema = 0;
    for (let i = 0; i < values.length; i++) {
        if (i < period - 1) continue;
        if (i === period - 1) {
            let sum = 0; for (let j = 0; j < period; j++) sum += values[j];
            ema = sum / period;
        } else {
            ema = values[i] * k + ema * (1 - k);
        }
        out[i] = ema;
    }
    return out;
}

function calcMACDHist(values, fast=12, slow=26, signal=9) {
    const emaFast = calcEMA(values, fast);
    const emaSlow = calcEMA(values, slow);
    const macd = values.map((_, i) => (emaFast[i] != null && emaSlow[i] != null) ? (emaFast[i] - emaSlow[i]) : null);
    const macdForSignal = macd.map(v => v == null ? 0 : v);
    const signalArr = calcEMA(macdForSignal, signal);
    return macd.map((v, i) => (v != null && signalArr[i] != null) ? (v - signalArr[i]) : null);
}

function calcVolumeProfile(closes, volumes, bins = 20) {
    if (!closes.length) return { pocPrice: null };
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const step = (max - min) / bins || 1;
    const buckets = new Array(bins).fill(0);
    for (let i = 0; i < closes.length; i++) {
        const idx = Math.min(bins - 1, Math.max(0, Math.floor((closes[i] - min) / step)));
        buckets[idx] += volumes[i] || 0;
    }
    let pocIdx = 0;
    for (let i = 1; i < bins; i++) if (buckets[i] > buckets[pocIdx]) pocIdx = i;
    const pocPrice = min + pocIdx * step;
    return { pocPrice };
}
// Update trading price
async function updateTradingPrice(symbol) {
    try {
        const response = await fetch(`/api/bitunix/price?symbol=${symbol}`);
        const data = await response.json();
        
        if (data.price) {
            currentTradingPrice = data.price;
            document.getElementById('current-price').textContent = `$${formatNumber(data.price, 6)}`;
            await calculatePrices();
        }
    } catch (error) {
        console.error('Error updating price:', error);
    }
}

// Calculate prices
async function calculatePrices() {
    try {
        const symbol = document.getElementById('trading-symbol').value;
        const entryPercent = parseFloat(document.getElementById('entry-percent').value) || 0;
        const stopLossPercent = parseFloat(document.getElementById('stop-loss-percent').value) || 2;
        const takeProfitPercent = parseFloat(document.getElementById('take-profit-percent').value) || 4;
        const side = document.getElementById('trading-side').value || 'Buy';
        
        if (!symbol || currentTradingPrice === 0) {
            return;
        }
        
        const response = await fetch('/api/bitunix/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                current_price: currentTradingPrice,
                entry_percent: entryPercent,
                stop_loss_percent: stopLossPercent,
                take_profit_percent: takeProfitPercent,
                side: side
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Update display
        document.getElementById('entry-price-display').textContent = `$${formatNumber(data.entry_price, 6)}`;
        document.getElementById('entry-percent-display').textContent = `${entryPercent >= 0 ? '+' : ''}${entryPercent.toFixed(2)}%`;
        
        document.getElementById('stop-loss-display').textContent = `$${formatNumber(data.stop_loss, 6)}`;
        document.getElementById('stop-loss-percent-display').textContent = `-${stopLossPercent.toFixed(2)}%`;
        
        document.getElementById('take-profit-display').textContent = `$${formatNumber(data.take_profit, 6)}`;
        document.getElementById('take-profit-percent-display').textContent = `+${takeProfitPercent.toFixed(2)}%`;
        
    } catch (error) {
        console.error('Error calculating prices:', error);
        alert('خطا در محاسبه قیمت‌ها: ' + error.message);
    }
}

// Place order
async function placeOrder(e) {
    e.preventDefault();
    
    try {
        const symbol = document.getElementById('trading-symbol').value;
        const entryPercent = parseFloat(document.getElementById('entry-percent').value) || 0;
        const stopLossPercent = parseFloat(document.getElementById('stop-loss-percent').value) || 2;
        const takeProfitPercent = parseFloat(document.getElementById('take-profit-percent').value) || 4;
        const usdAmount = parseFloat(document.getElementById('usd-amount').value);
        const orderType = document.getElementById('order-type').value;
        const side = document.getElementById('trading-side').value || 'Buy';
        
        if (!symbol || usdAmount === 0) {
            alert('لطفا مبلغ معامله را وارد کنید');
            return;
        }
        
        if (!confirm(`آیا مطمئن هستید که می‌خواهید معامله ${symbol} با مبلغ $${usdAmount} را ارسال کنید؟`)) {
            return;
        }
        
        const btn = document.getElementById('place-order-btn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'در حال ارسال...';
        
        const response = await fetch('/api/bitunix/place-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                side: side,
                order_type: orderType,
                usd_amount: usdAmount,
                entry_percent: entryPercent,
                stop_loss_percent: stopLossPercent,
                take_profit_percent: takeProfitPercent
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ معامله با موفقیت ارسال شد!\n\nOrder ID: ' + data.order_id);
            // Close modal
            closeTradingModalFunc();
        } else {
            alert('❌ خطا در ارسال معامله: ' + (data.error || 'خطای ناشناخته'));
        }
        
        btn.disabled = false;
        btn.textContent = originalText;
        
    } catch (error) {
        console.error('Error placing order:', error);
        alert('خطا در ارسال معامله: ' + error.message);
        document.getElementById('place-order-btn').disabled = false;
        document.getElementById('place-order-btn').textContent = 'ارسال به Bitunix';
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

    // moved into applyOverlays
async function loadServerSignals(symbol) {
    try {
        const res = await fetch(`/api/futures/signals?symbol=${symbol}&interval=1&source=bybit`)
        const json = await res.json()
        if (!json.error) {
            window._serverSignals = json
        } else {
            window._serverSignals = null
        }
    } catch {
        window._serverSignals = null
    }
}
function calcSTD(values, period) {
    const out = new Array(values.length).fill(null);
    for (let i = 0; i < values.length; i++) {
        if (i < period - 1) continue;
        const slice = values.slice(i - period + 1, i + 1);
        const mean = slice.reduce((a, b) => a + b, 0) / period;
        const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / period;
        out[i] = Math.sqrt(variance);
    }
    return out;
}

function addBBands() {
    const period = 20;
    const mult = 2;
    const ma = calcSMA(lastCloses, period);
    const std = calcSTD(lastCloses, period);
    const upper = lastCloses.map((_, i) => (ma[i] != null && std[i] != null) ? ma[i] + mult * std[i] : null);
    const lower = lastCloses.map((_, i) => (ma[i] != null && std[i] != null) ? ma[i] - mult * std[i] : null);
    tradingChart.data.datasets.push({ label: 'BB Upper', data: upper, borderColor: '#14b8a6', pointRadius: 0, fill: false, yAxisID: 'y' });
    tradingChart.data.datasets.push({ label: 'BB Lower', data: lower, borderColor: '#14b8a6', borderDash: [4,4], pointRadius: 0, fill: false, yAxisID: 'y' });
}

function addEMACross() {
    const emaFast = calcEMA(lastCloses, 12);
    const emaSlow = calcEMA(lastCloses, 26);
    tradingChart.data.datasets.push({ label: 'EMA(12)', data: emaFast, borderColor: '#f97316', pointRadius: 0, fill: false, yAxisID: 'y' });
    tradingChart.data.datasets.push({ label: 'EMA(26)', data: emaSlow, borderColor: '#fb7185', pointRadius: 0, fill: false, yAxisID: 'y' });
}
