/**
 * Market Profile JavaScript
 * Handles dynamic symbol/expiry selection, data fetching, and chart rendering
 */

// Global state
let currentSymbol = null;
let currentExpiry = null;
let currentATM = null;
let marketProfileData = null;
let futuresChart = null;
let futuresSeries = null;
let volumeSeries = null;
let autoRefreshInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Market Profile initialized');
    loadFOSymbols();
    initFuturesChart();
    setupEventListeners();
});

/**
 * Load F&O symbols from API
 */
async function loadFOSymbols() {
    try {
        const response = await fetch('/api/fo-symbols');
        const data = await response.json();

        if (data.status === 'success') {
            const selector = document.getElementById('symbol-selector');
            selector.innerHTML = '';

            // Add indices
            if (data.symbols.indices && data.symbols.indices.length > 0) {
                const indicesGroup = document.createElement('optgroup');
                indicesGroup.label = 'Indices';
                data.symbols.indices.forEach(symbol => {
                    const option = document.createElement('option');
                    option.value = symbol;
                    option.textContent = symbol;
                    indicesGroup.appendChild(option);
                });
                selector.appendChild(indicesGroup);
            }

            // Add stocks
            if (data.symbols.stocks && data.symbols.stocks.length > 0) {
                const stocksGroup = document.createElement('optgroup');
                stocksGroup.label = 'Stocks';
                data.symbols.stocks.forEach(symbol => {
                    const option = document.createElement('option');
                    option.value = symbol;
                    option.textContent = symbol;
                    stocksGroup.appendChild(option);
                });
                selector.appendChild(stocksGroup);
            }

            // Select first symbol by default (NIFTY)
            if (data.symbols.indices && data.symbols.indices.length > 0) {
                selector.value = data.symbols.indices[0];
                currentSymbol = data.symbols.indices[0];
                await loadExpiries(currentSymbol);
            }
        }
    } catch (error) {
        console.error('Error loading F&O symbols:', error);
        showError('Failed to load symbols');
    }
}

/**
 * Load expiry dates for selected symbol
 */
async function loadExpiries(symbol) {
    try {
        document.getElementById('expiry-selector').disabled = true;
        document.getElementById('fetch-btn').disabled = true;

        const response = await fetch(`/api/expiry/${symbol}`);
        const data = await response.json();

        if (data.status === 'success') {
            const selector = document.getElementById('expiry-selector');
            selector.innerHTML = '';

            data.expiries.forEach(expiry => {
                const option = document.createElement('option');
                option.value = expiry;
                option.textContent = expiry;
                selector.appendChild(option);
            });

            // Select first expiry by default
            if (data.expiries.length > 0) {
                selector.value = data.expiries[0];
                currentExpiry = data.expiries[0];
            }

            selector.disabled = false;
            document.getElementById('fetch-btn').disabled = false;
        } else {
            showError(data.message || 'Failed to load expiries');
        }
    } catch (error) {
        console.error('Error loading expiries:', error);
        showError('Failed to load expiries');
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Symbol selector
    document.getElementById('symbol-selector').addEventListener('change', async (e) => {
        currentSymbol = e.target.value;
        await loadExpiries(currentSymbol);
    });

    // Expiry selector
    document.getElementById('expiry-selector').addEventListener('change', (e) => {
        currentExpiry = e.target.value;
    });

    // Fetch button
    document.getElementById('fetch-btn').addEventListener('click', async () => {
        if (currentSymbol && currentExpiry) {
            await fetchMarketProfile();
        }
    });

    // Auto-refresh toggle
    document.getElementById('auto-refresh').addEventListener('change', (e) => {
        if (e.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
}

/**
 * Fetch complete market profile data
 */
async function fetchMarketProfile() {
    if (!currentSymbol || !currentExpiry) {
        showError('Please select symbol and expiry');
        return;
    }

    try {
        showFetchStatus('Fetching data...', 'loading');
        document.getElementById('fetch-btn').disabled = true;

        // First, trigger OI fetch from OpenAlgo
        const fetchResponse = await fetch(`/api/fetch-oi/${currentSymbol}?expiry=${currentExpiry}`);
        const fetchData = await fetchResponse.json();

        if (fetchData.status === 'success') {
            console.log(`Fetched ${fetchData.strikes_fetched} strikes for ${currentSymbol} ${currentExpiry}`);
        }

        // Now get the complete market profile
        const response = await fetch(`/api/market-profile/${currentSymbol}?expiry=${currentExpiry}`);
        const data = await response.json();

        if (data.status === 'success') {
            marketProfileData = data;
            renderMarketProfile(data);
            showFetchStatus('Data loaded', 'success');
            updateLastUpdate();
        } else {
            showError(data.message || 'Failed to load market profile');
        }
    } catch (error) {
        console.error('Error fetching market profile:', error);
        showError('Failed to fetch data: ' + error.message);
    } finally {
        document.getElementById('fetch-btn').disabled = false;
    }
}

/**
 * Render complete market profile
 */
function renderMarketProfile(data) {
    // Update stats
    document.getElementById('spot-price').textContent = data.underlying_price.toFixed(2);
    document.getElementById('atm-strike').textContent = data.atm_strike;
    document.getElementById('pcr-value').textContent = data.pcr.toFixed(2);
    document.getElementById('total-ce-oi').textContent = formatNumber(data.total_ce_oi);
    document.getElementById('total-pe-oi').textContent = formatNumber(data.total_pe_oi);

    currentATM = data.atm_strike;

    // Render futures chart
    renderFuturesChart(data.futures_candles);

    // Render OI charts
    renderOILevels(data.oi_levels, data.atm_strike);
    renderOIChanges(data.oi_changes, data.atm_strike);
}

/**
 * Initialize futures chart
 */
function initFuturesChart() {
    const container = document.getElementById('futures-chart');

    futuresChart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        layout: {
            background: { color: '#000000' },
            textColor: '#10b981',
            fontSize: 11
        },
        grid: {
            vertLines: { color: '#0a0a0a' },
            horzLines: { color: '#0a0a0a' }
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                color: '#10b981',
                width: 1,
                style: LightweightCharts.LineStyle.Dotted
            },
            horzLine: {
                color: '#10b981',
                width: 1,
                style: LightweightCharts.LineStyle.Dotted
            }
        },
        rightPriceScale: {
            borderColor: '#141414',
            autoScale: true
        },
        timeScale: {
            borderColor: '#141414',
            timeVisible: true,
            secondsVisible: false
        }
    });

    // Create candlestick series
    futuresSeries = futuresChart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444'
    });

    // Create volume series
    volumeSeries = futuresChart.addHistogramSeries({
        color: 'rgba(16, 185, 129, 0.3)',
        priceScaleId: 'volume',
        priceFormat: {
            type: 'volume'
        }
    });

    futuresChart.priceScale('volume').applyOptions({
        scaleMargins: {
            top: 0.8,
            bottom: 0
        }
    });

    // Handle resize
    window.addEventListener('resize', () => {
        futuresChart.resize(container.clientWidth, container.clientHeight);
    });
}

/**
 * Render futures chart data
 */
function renderFuturesChart(candles) {
    if (!futuresSeries || !volumeSeries || !candles || candles.length === 0) {
        return;
    }

    const chartData = candles.map(candle => ({
        time: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
    }));

    const volumeData = candles.map(candle => ({
        time: candle.time,
        value: candle.volume || 0,
        color: candle.close >= candle.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'
    }));

    futuresSeries.setData(chartData);
    volumeSeries.setData(volumeData);

    futuresChart.timeScale().fitContent();
}

/**
 * Render OI levels (Current OI)
 */
function renderOILevels(oiData, atmStrike) {
    const container = document.getElementById('oi-levels');
    container.innerHTML = '';

    if (!oiData || (!oiData.CE && !oiData.PE)) {
        container.innerHTML = '<p class="text-center text-sm p-4">No OI data available</p>';
        return;
    }

    // Get all strikes
    const ceStrikes = Object.keys(oiData.CE || {}).map(Number);
    const peStrikes = Object.keys(oiData.PE || {}).map(Number);
    const allStrikes = [...new Set([...ceStrikes, ...peStrikes])].sort((a, b) => b - a);

    // Find max OI for scaling
    const maxCEOI = Math.max(...Object.values(oiData.CE || {}).map(d => d.oi || 0), 1);
    const maxPEOI = Math.max(...Object.values(oiData.PE || {}).map(d => d.oi || 0), 1);
    const maxOI = Math.max(maxCEOI, maxPEOI);

    // Render each strike
    allStrikes.forEach(strike => {
        const row = document.createElement('div');
        row.className = 'strike-row' + (strike === atmStrike ? ' atm-row' : '');

        const peOI = oiData.PE?.[strike]?.oi || 0;
        const ceOI = oiData.CE?.[strike]?.oi || 0;

        const peWidth = (peOI / maxOI) * 100;
        const ceWidth = (ceOI / maxOI) * 100;

        row.innerHTML = `
            <div style="display: flex; width: 45%; justify-content: flex-end;">
                <div class="oi-bar-pe" style="width: ${peWidth}%; text-align: right; padding-right: 4px; font-size: 10px;">
                    ${peOI > 0 ? formatNumber(peOI) : ''}
                </div>
            </div>
            <div class="strike-label">${strike}</div>
            <div style="display: flex; width: 45%;">
                <div class="oi-bar-ce" style="width: ${ceWidth}%; padding-left: 4px; font-size: 10px;">
                    ${ceOI > 0 ? formatNumber(ceOI) : ''}
                </div>
            </div>
        `;

        row.title = `Strike ${strike}: CE ${formatNumber(ceOI)} | PE ${formatNumber(peOI)}`;
        container.appendChild(row);
    });
}

/**
 * Render OI changes (Daily changes)
 */
function renderOIChanges(oiChanges, atmStrike) {
    const container = document.getElementById('oi-changes');
    container.innerHTML = '';

    if (!oiChanges || (!oiChanges.CE && !oiChanges.PE)) {
        container.innerHTML = '<p class="text-center text-sm p-4">No OI change data available</p>';
        return;
    }

    // Get all strikes
    const ceStrikes = Object.keys(oiChanges.CE || {}).map(Number);
    const peStrikes = Object.keys(oiChanges.PE || {}).map(Number);
    const allStrikes = [...new Set([...ceStrikes, ...peStrikes])].sort((a, b) => b - a);

    // Find max change for scaling
    const maxChange = Math.max(
        ...Object.values(oiChanges.CE || {}).map(d => Math.abs(d.change || 0)),
        ...Object.values(oiChanges.PE || {}).map(d => Math.abs(d.change || 0)),
        1
    );

    // Render each strike
    allStrikes.forEach(strike => {
        const row = document.createElement('div');
        row.className = 'strike-row' + (strike === atmStrike ? ' atm-row' : '');

        const peChange = oiChanges.PE?.[strike]?.change || 0;
        const ceChange = oiChanges.CE?.[strike]?.change || 0;

        const peWidth = (Math.abs(peChange) / maxChange) * 100;
        const ceWidth = (Math.abs(ceChange) / maxChange) * 100;

        const peClass = peChange >= 0 ? 'oi-change-positive' : 'oi-change-negative';
        const ceClass = ceChange >= 0 ? 'oi-change-positive' : 'oi-change-negative';

        row.innerHTML = `
            <div style="display: flex; width: 45%; justify-content: flex-end;">
                <div class="oi-bar-pe ${peClass}" style="width: ${peWidth}%; text-align: right; padding-right: 4px; font-size: 10px;">
                    ${peChange !== 0 ? (peChange > 0 ? '+' : '') + formatNumber(peChange) : ''}
                </div>
            </div>
            <div class="strike-label">${strike}</div>
            <div style="display: flex; width: 45%;">
                <div class="oi-bar-ce ${ceClass}" style="width: ${ceWidth}%; padding-left: 4px; font-size: 10px;">
                    ${ceChange !== 0 ? (ceChange > 0 ? '+' : '') + formatNumber(ceChange) : ''}
                </div>
            </div>
        `;

        row.title = `Strike ${strike}: CE ${ceChange > 0 ? '+' : ''}${formatNumber(ceChange)} | PE ${peChange > 0 ? '+' : ''}${formatNumber(peChange)}`;
        container.appendChild(row);
    });
}

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }

    // Refresh every 5 minutes
    autoRefreshInterval = setInterval(() => {
        if (currentSymbol && currentExpiry) {
            console.log('Auto-refreshing market profile...');
            fetchMarketProfile();
        }
    }, 5 * 60 * 1000);

    console.log('Auto-refresh enabled (5 minutes)');
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('Auto-refresh disabled');
    }
}

/**
 * Show fetch status
 */
function showFetchStatus(message, type) {
    const statusEl = document.getElementById('fetch-status');
    statusEl.textContent = message;

    statusEl.className = 'badge ';
    if (type === 'loading') {
        statusEl.className += 'badge-warning';
    } else if (type === 'success') {
        statusEl.className += 'badge-success';
    } else if (type === 'error') {
        statusEl.className += 'badge-error';
    } else {
        statusEl.className += 'badge-ghost';
    }
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    showFetchStatus(message, 'error');
}

/**
 * Update last update timestamp
 */
function updateLastUpdate() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: true
    });
    document.getElementById('last-update').textContent = `Updated: ${timeStr}`;
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    if (num >= 10000000) {
        return (num / 10000000).toFixed(2) + 'Cr';
    } else if (num >= 100000) {
        return (num / 100000).toFixed(2) + 'L';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}
