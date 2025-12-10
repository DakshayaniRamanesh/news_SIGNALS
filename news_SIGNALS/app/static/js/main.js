document.addEventListener('DOMContentLoaded', () => {
    fetchStats();
    fetchData();
    setupModalHandlers();
    setupMarketData(); // Initialize market data
    setupExportHandler(); // Initialize export feature
    updateClock();
    setupNotifications();
    setInterval(updateClock, 1000);

    // Refresh every 15 seconds
    // Refresh every 15 seconds, unless history is enabled
    setInterval(() => {
        const historyToggle = document.getElementById('history-toggle');
        if (historyToggle && historyToggle.checked) {
            return;
        }
        fetchStats();
        fetchData();
        updateNotifications();
        if (typeof fetchMarketData === 'function' && currentMarketType) {
            fetchMarketData(currentMarketType);
        }
    }, 15000);

    // History Toggle Handler
    const historyToggle = document.getElementById('history-toggle');
    if (historyToggle) {
        historyToggle.addEventListener('change', () => {
            const liveView = document.getElementById('live-dashboard');
            const histView = document.getElementById('historical-dashboard');

            if (historyToggle.checked) {
                // Swith to History
                if (liveView) liveView.style.display = 'none';
                if (histView) histView.style.display = 'block';
                fetchHistoryData();
            } else {
                // Switch to Live
                if (liveView) liveView.style.display = 'block';
                if (histView) histView.style.display = 'none';
                fetchData();
                fetchStats();
                document.getElementById('last-updated').textContent = 'Last Updated: Just now';
            }
        });
    }

    // Initialize Historical View Handlers
    setupHistoricalView();

    // Modal Close Handler
    document.querySelector('.close-modal').addEventListener('click', () => {
        document.getElementById('detail-modal').style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        const modal = document.getElementById('detail-modal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }

        const notifDropdown = document.getElementById('notif-dropdown');
        const notifBtn = document.getElementById('notif-btn');
        if (notifDropdown && notifBtn && !notifDropdown.contains(event.target) && !notifBtn.contains(event.target)) {
            notifDropdown.classList.remove('show');
        }
    });

    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            const icon = refreshBtn.querySelector('i');
            icon.classList.add('fa-spin');
            refreshBtn.disabled = true;
            refreshBtn.style.opacity = '0.7';

            try {
                const response = await fetch('/api/refresh', { method: 'POST' });
                const res = await response.json();
                if (res.status === 'success') {
                    setTimeout(() => {
                        fetchStats();
                        fetchData();
                        updateNotifications();
                        icon.classList.remove('fa-spin');
                        refreshBtn.disabled = false;
                        refreshBtn.style.opacity = '1';
                    }, 2000);
                } else {
                    alert('Refresh failed: ' + res.message);
                    icon.classList.remove('fa-spin');
                    refreshBtn.disabled = false;
                    refreshBtn.style.opacity = '1';
                }
            } catch (error) {
                console.error('Error refreshing:', error);
                icon.classList.remove('fa-spin');
                refreshBtn.disabled = false;
                refreshBtn.style.opacity = '1';
            }
        });
    }
});

function setupNotifications() {
    const notifBtn = document.getElementById('notif-btn');
    const notifDropdown = document.getElementById('notif-dropdown');

    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent immediate close
            notifDropdown.classList.toggle('show');
        });
        // Initial check
        updateNotifications();
    }
}

async function updateNotifications() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();

        // Filter for "High Risk" only as per user request for the red light
        const alerts = data.filter(item => item.impact_level === 'High Risk');

        // Check for > 40% High Risk Alert
        if (data.length > 0) {
            const highRiskRatio = alerts.length / data.length;
            if (highRiskRatio > 0.4 && !sessionStorage.getItem('riskAlertShown')) {
                alert(`⚠️ CRITICAL WARNING: High Risk Volume is ${Math.round(highRiskRatio * 100)}%!\n\nMore than 40% of current news items are flagged as High Risk.`);
                sessionStorage.setItem('riskAlertShown', 'true');
            }
        }

        const notifList = document.getElementById('notif-list');
        const notifDot = document.getElementById('notif-dot');

        if (notifList) {
            if (alerts.length === 0) {
                notifList.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">No new alerts</div>';
                if (notifDot) notifDot.style.display = 'none';
            } else {
                notifList.innerHTML = '';
                alerts.slice(0, 5).forEach(alert => {
                    const div = document.createElement('div');
                    div.className = 'notif-item';
                    div.innerHTML = `
                        <div class="notif-title">${alert.Title}</div>
                        <div class="notif-meta">
                            <span>${alert.Source}</span>
                            <span class="notif-badge">${alert.impact_level}</span>
                        </div>
                    `;
                    div.addEventListener('click', () => {
                        if (alert.Link) window.open(alert.Link, '_blank');
                    });
                    notifList.appendChild(div);
                });

                if (notifDot) {
                    notifDot.style.display = 'block';
                    notifDot.classList.add('pulse');
                }
            }
        }
    } catch (e) {
        console.error("Notifications update failed", e);
    }
}

function updateClock() {
    const now = new Date();
    const timeElem = document.getElementById('clock-time');
    const dateElem = document.getElementById('clock-date');

    if (timeElem && dateElem) {
        timeElem.textContent = now.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });

        dateElem.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'short',
            day: 'numeric'
        });
    }
}

let currentData = [];

function setupExportHandler() {
    const exportBtn = document.getElementById('btn-export');
    if (!exportBtn) return;

    exportBtn.addEventListener('click', () => {
        // Trigger PDF download in new tab
        window.open('/api/export-pdf', '_blank');
    });
}

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('stat-risk').textContent = data.high_risk;
        document.getElementById('stat-opportunity').textContent = data.opportunity;
        document.getElementById('stat-events').textContent = data.major_events;
        document.getElementById('stat-total').textContent = data.total_articles;
        if (data.last_updated) {
            document.getElementById('last-updated').textContent = 'Last Updated: ' + data.last_updated;
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

let impactChart = null;
let opsChart = null;

async function fetchData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        currentData = data; // Store globally

        updateDashboardStats(data);
        updateCharts(data);
        updateSignals(data);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

async function fetchHistoryData() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        currentData = data; // Store globally

        // Don't update live dashboard stats/charts automatically
        // Just load the data ready for analysis
        document.getElementById('last-updated').textContent = 'Mode: Historical Archive';

        // Initial render of empty state or full list
        renderHistoricalFeed(data.slice(0, 20)); // Show recent 20 initially

    } catch (error) {
        console.error('Error fetching history data:', error);
    }
}

function setupHistoricalView() {
    const btnAnalyze = document.getElementById('btn-analyze-history');
    if (btnAnalyze) {
        btnAnalyze.addEventListener('click', handleHistoryAnalyze);
    }
}

function handleHistoryAnalyze() {
    const startStr = document.getElementById('hist-start-date').value;
    const endStr = document.getElementById('hist-end-date').value;
    const statusDiv = document.getElementById('hist-fetch-status');
    const feed = document.getElementById('historical-feed-list');

    if (!startStr || !endStr) {
        alert('Please select a valid date range.');
        return;
    }

    const startDate = new Date(startStr);
    const endDate = new Date(endStr);
    endDate.setHours(23, 59, 59);

    if (statusDiv) {
        statusDiv.style.display = 'none';
        statusDiv.textContent = '';
    }

    // 1. Filter Local Data
    const filtered = currentData.filter(d => {
        if (!d.Published) return false;
        const pubDate = new Date(d.Published);
        return pubDate >= startDate && pubDate <= endDate;
    });

    // 2. Show local data eagerly if available
    if (filtered.length > 0) {
        updateHistoricalStats(filtered);
        renderHistoricalFeed(filtered);
        calculateTrend(filtered);
    }

    // 3. Always attempt to scrape more data for better coverage
    fetchExternalHistory(startStr, endStr, filtered.length > 0);
}

async function fetchExternalHistory(start, end, hasLocalData) {
    const statusDiv = document.getElementById('hist-fetch-status');
    const feed = document.getElementById('historical-feed-list');

    // UI Loading State
    if (statusDiv) {
        statusDiv.style.display = 'block';
        statusDiv.innerHTML = hasLocalData
            ? `<i class="fa-solid fa-sync fa-spin"></i> Updating archive with latest data from ${start} to ${end}...`
            : `<i class="fa-solid fa-satellite-dish fa-beat"></i> Scraping external archives from ${start} to ${end}...`;
    }

    // Only clear feed if we have no local data to show
    if (feed && !hasLocalData) {
        feed.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);"><div class="loading-sm"></div> Accessing Global News Nodes...</div>';
    }

    try {
        const response = await fetch('/api/scrape_history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start: start, end: end, query: "ALL" })
        });

        if (!response.ok) throw new Error('Scraping failed');

        const newData = await response.json();

        if (newData.length > 0) {
            // Success
            if (statusDiv) {
                statusDiv.innerHTML = `<i class="fa-solid fa-check-circle" style="color: var(--success);"></i> Sync Complete. Found ${newData.length} records.`;
                setTimeout(() => { statusDiv.style.display = 'none'; }, 3000);
            }

            // Merge Data: Add only new items to currentData
            // Use Link as unique key logic check
            const existingLinks = new Set(currentData.map(d => d.Link));
            let addedCount = 0;
            newData.forEach(item => {
                if (!existingLinks.has(item.Link)) {
                    currentData.push(item);
                    addedCount++;
                }
            });

            // Re-Filter to show the full combined dataset for this range
            const startDate = new Date(start);
            const endDate = new Date(end);
            endDate.setHours(23, 59, 59);

            const combinedFiltered = currentData.filter(d => {
                if (!d.Published) return false;
                const pubDate = new Date(d.Published);
                return pubDate >= startDate && pubDate <= endDate;
            });

            // Render
            updateHistoricalStats(combinedFiltered);
            renderHistoricalFeed(combinedFiltered);
            calculateTrend(combinedFiltered);

        } else {
            // No new data found
            if (statusDiv) {
                statusDiv.innerHTML = hasLocalData
                    ? `<i class="fa-solid fa-check"></i> Archive is up to date.`
                    : `<i class="fa-solid fa-triangle-exclamation" style="color: var(--risk);"></i> No external records found for this period.`;
                setTimeout(() => { statusDiv.style.display = 'none'; }, 3000);
            }
            if (feed && !hasLocalData) {
                feed.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No data found in global archives.</div>';
                clearTrendChart();
                updateHistoricalStats([]);
            }
        }

    } catch (error) {
        console.error('External fetch error:', error);
        if (statusDiv) {
            statusDiv.innerHTML = `<i class="fa-solid fa-circle-xmark" style="color: var(--risk);"></i> Connection failed.`;
        }
        if (feed && !hasLocalData) {
            feed.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">Failed to connect to external archives.</div>';
        }
    }
}

function updateHistoricalStats(data) {
    document.getElementById('hist-stat-days').textContent = new Set(data.map(d => new Date(d.Published).toDateString())).size;
    document.getElementById('hist-stat-risk').textContent = data.filter(d => d.impact_level === 'High Risk').length;
    document.getElementById('hist-stat-opp').textContent = data.filter(d => d.impact_level === 'Opportunity').length;
}

function renderHistoricalFeed(data) {
    const list = document.getElementById('historical-feed-list');
    if (!list) return;
    list.innerHTML = '';

    if (data.length === 0) {
        list.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No data loaded</div>';
        return;
    }

    data.slice(0, 50).forEach(item => {
        const div = document.createElement('div');
        div.style.cssText = 'padding: 1rem; border-bottom: 1px solid var(--border);';

        let badgeColor = '#64748b';
        if (item.impact_level === 'High Risk') badgeColor = '#ef4444';
        if (item.impact_level === 'Opportunity') badgeColor = '#22c55e';

        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-size: 0.8rem; color: var(--text-secondary);">${item.Published || 'Unknown Date'}</span>
                <span style="font-size: 0.75rem; background: ${badgeColor}20; color: ${badgeColor}; padding: 2px 8px; border-radius: 10px;">${item.impact_level}</span>
            </div>
            <div style="font-weight: 500; margin-bottom: 0.5rem;">${item.Title}</div>
            <div style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.4;">${item.Summary}</div>
        `;
        list.appendChild(div);
    });
}

let trendChart = null;

function calculateTrend(data) {
    // 1. Group by Date
    const dailyCounts = {};
    const topicCounts = {};

    data.forEach(d => {
        const dateKey = new Date(d.Published).toLocaleDateString();
        // Risk Score: High Risk = 1, else 0
        const isRisk = d.impact_level === 'High Risk' ? 1 : 0;

        if (!dailyCounts[dateKey]) dailyCounts[dateKey] = { risk: 0, count: 0 };
        dailyCounts[dateKey].risk += isRisk;
        dailyCounts[dateKey].count += 1;

        // Topics
        if (d.operational_tag) {
            d.operational_tag.split(',').forEach(tag => {
                const t = tag.trim();
                if (t && t !== 'general') topicCounts[t] = (topicCounts[t] || 0) + 1;
            });
        }
    });

    const dates = Object.keys(dailyCounts).sort((a, b) => new Date(a) - new Date(b));
    const riskValues = dates.map(d => dailyCounts[d].risk);

    // 2. Linear Regression for Slope
    let slope = 0;
    if (dates.length > 1) {
        const n = dates.length;
        const x = Array.from({ length: n }, (_, i) => i); // 0, 1, 2...
        const y = riskValues;

        const sumX = x.reduce((a, b) => a + b, 0);
        const sumY = y.reduce((a, b) => a + b, 0);
        const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
        const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);

        slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    }

    // 3. Update Text
    const predictionText = document.getElementById('prediction-risk-text');
    if (predictionText) {
        let outlook = "stable";
        let color = "#94a3b8";

        if (slope > 0.1) { outlook = "escalating rapidly"; color = "#ef4444"; }
        else if (slope > 0) { outlook = "increasing slightly"; color = "#fbbf24"; }
        else if (slope < -0.1) { outlook = "subsiding noticeably"; color = "#22c55e"; }
        else if (slope < 0) { outlook = "decreasing slightly"; color = "#34d399"; }

        predictionText.innerHTML = `
            Based on the analysis of <b>${data.length}</b> records over <b>${dates.length}</b> days, the risk velocity is <b style="color: ${color}">${outlook}</b>.
            <br>Model Confidence: High.
        `;
    }

    // 4. Update Topics
    const topTopics = Object.entries(topicCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    const topicContainer = document.getElementById('prediction-topics');
    if (topicContainer) {
        topicContainer.innerHTML = topTopics.map(([tag, count]) =>
            `<span style="background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 15px; font-size: 0.85rem;">${tag} (${count})</span>`
        ).join('');
    }

    // 5. Render Trend Chart
    const ctx = document.getElementById('trendChart').getContext('2d');

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Risk Events Frequency',
                data: riskValues,
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8' } }
            },
            scales: {
                y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                x: { display: false }
            }
        }
    });
}

function clearTrendChart() {
    if (trendChart) {
        trendChart.destroy();
        trendChart = null;
    }
    const predictionText = document.getElementById('prediction-risk-text');
    if (predictionText) predictionText.textContent = 'No data available for prediction.';
    document.getElementById('prediction-topics').innerHTML = '';
}

function updateDashboardStats(data) {
    if (!data) return;

    const total = data.length;
    const highRisk = data.filter(d => d.impact_level === 'High Risk').length;
    const opportunity = data.filter(d => d.impact_level === 'Opportunity').length;
    const majorEvents = data.filter(d => d.event_flag === 'Major Event').length;

    const elRisk = document.getElementById('stat-risk');
    const elOpp = document.getElementById('stat-opportunity');
    const elEvents = document.getElementById('stat-events');
    const elTotal = document.getElementById('stat-total');

    if (elRisk) elRisk.textContent = highRisk;
    if (elOpp) elOpp.textContent = opportunity;
    if (elEvents) elEvents.textContent = majorEvents;
    if (elTotal) elTotal.textContent = total;
}

function setupModalHandlers() {
    // National Activity Card
    const nationalCard = document.getElementById('list-national').closest('.card');
    nationalCard.addEventListener('click', () => openDetailModal('national'));

    // Operational Environment Card
    const operationalCard = document.getElementById('list-operational').closest('.card');
    operationalCard.addEventListener('click', () => openDetailModal('operational'));

    // Risk & Opportunity Card
    const riskCard = document.getElementById('list-risk').closest('.card');
    riskCard.addEventListener('click', () => openDetailModal('risk'));

    // Transport & Mobility Card
    const transportCard = document.getElementById('list-transport').closest('.card');
    transportCard.addEventListener('click', () => openDetailModal('transport'));

    // Weather & Hazards Card
    const weatherCard = document.getElementById('list-weather').closest('.card');
    weatherCard.addEventListener('click', () => openDetailModal('weather'));

    // Economic Indicators Card
    const economyCard = document.getElementById('list-economy').closest('.card');
    economyCard.addEventListener('click', () => openDetailModal('economy'));

    // Public Sentiment Card
    const sentimentCard = document.getElementById('list-sentiment').closest('.card');
    sentimentCard.addEventListener('click', () => openDetailModal('sentiment'));

    // Energy & Utilities Card
    const energyCard = document.getElementById('list-energy').closest('.card');
    energyCard.addEventListener('click', () => openDetailModal('energy'));
}

function openDetailModal(type) {
    const modal = document.getElementById('detail-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');

    modal.style.display = 'block';

    // Reset scroll position
    const content = modal.querySelector('.modal-content');
    if (content) content.scrollTop = 0;

    body.innerHTML = '';

    let items = [];

    if (type === 'national') {
        title.textContent = 'National Activity Indicators';
        items = currentData.filter(d => d.event_flag && d.event_flag !== 'Normal' && d.event_flag !== 'nan');
        // Group by Event Flag
        renderGroupedItems(body, items, 'event_flag');
    } else if (type === 'operational') {
        title.textContent = 'Operational Environment Indicators';
        items = currentData.filter(d => d.operational_tag && d.operational_tag !== 'general');
        // Group by Operational Tag
        renderGroupedItems(body, items, 'operational_tag');
    } else if (type === 'risk') {
        title.textContent = 'Risk & Opportunity Insights';
        items = currentData.filter(d => {
            const imp = (d.impact_level || '').toLowerCase();
            return imp.includes('risk') || imp.includes('opportunity');
        });
        // Group by Impact Level
        renderGroupedItems(body, items, 'impact_level');
    } else if (type === 'transport') {
        title.textContent = 'Transport & Mobility Indicators';
        items = currentData.filter(d => d.operational_tag && d.operational_tag.includes('transport'));
        renderGroupedItems(body, items, 'operational_tag');
    } else if (type === 'weather') {
        title.textContent = 'Weather & Natural Hazards';
        items = currentData.filter(d => d.operational_tag && d.operational_tag.includes('weather'));
        renderGroupedItems(body, items, 'operational_tag');
    } else if (type === 'economy') {
        title.textContent = 'Economic Indicators';
        items = currentData.filter(d => d.operational_tag && d.operational_tag.includes('economic'));
        renderGroupedItems(body, items, 'operational_tag');
    } else if (type === 'sentiment') {
        title.textContent = 'Public Sentiment & Social Media Trends';
        items = currentData.filter(d => d.operational_tag && d.operational_tag.includes('sentiment'));
        renderGroupedItems(body, items, 'operational_tag');
    } else if (type === 'energy') {
        title.textContent = 'Energy & Utilities (Power, Fuel)';
        items = currentData.filter(d => d.operational_tag && (d.operational_tag.includes('energy') || d.operational_tag.includes('utilities')));
        renderGroupedItems(body, items, 'operational_tag');
    }
}

function renderGroupedItems(container, items, groupField) {
    if (items.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">No indicators found for this category.</p>';
        return;
    }

    // Grouping logic
    const groups = {};
    items.forEach(item => {
        // Handle comma-separated tags if necessary, but keep simple for now
        const key = item[groupField] || 'Uncategorized';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
    });

    Object.keys(groups).sort().forEach(groupName => {
        const section = document.createElement('div');
        section.className = 'modal-section';

        const h3 = document.createElement('h3');
        h3.innerHTML = `<i class="fa-solid fa-layer-group" style="font-size: 0.9em; opacity: 0.7;"></i> ${groupName}`;
        section.appendChild(h3);

        groups[groupName].forEach(item => {
            const div = document.createElement('div');
            div.style.cssText = 'padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 0.5rem; border: 1px solid var(--border);';
            div.innerHTML = `
                <div style="font-weight: 500; margin-bottom: 0.25rem;">${item.Title}</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${item.Summary}</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted);">
                    <span>${item.Source}</span>
                    <a href="${item.Link}" target="_blank" style="color: var(--accent);">Read Source <i class="fa-solid fa-external-link-alt"></i></a>
                </div>
            `;
            section.appendChild(div);
        });

        container.appendChild(section);
    });
}

function updateSignals(data) {
    if (!data) return;

    // 1. National Activity (Major Events / Emerging)
    const nationalItems = data.filter(d => d.event_flag && d.event_flag !== 'Normal' && d.event_flag !== 'nan');
    renderSignalList('list-national', nationalItems.slice(0, 5), 'event_flag');

    // 2. Operational Environment (Tags != general)
    const operationalItems = data.filter(d => d.operational_tag && d.operational_tag !== 'general');
    renderSignalList('list-operational', operationalItems.slice(0, 5), 'operational_tag');

    // 3. Risk & Opportunity (Impact contains Risk or Opportunity)
    // Sort by absolute impact score to get most significant
    const riskOppItems = data.filter(d => {
        const imp = (d.impact_level || '').toLowerCase();
        return imp.includes('risk') || imp.includes('opportunity');
    }).sort((a, b) => Math.abs(b.impact_score) - Math.abs(a.impact_score));
    renderSignalList('list-risk', riskOppItems.slice(0, 5), 'impact_level');

    // 4. Transport & Mobility
    const transportItems = data.filter(d => d.operational_tag && d.operational_tag.includes('transport'));
    renderSignalList('list-transport', transportItems.slice(0, 5), 'operational_tag');

    // 5. Weather & Hazards
    const weatherItems = data.filter(d => d.operational_tag && d.operational_tag.includes('weather'));
    renderSignalList('list-weather', weatherItems.slice(0, 5), 'operational_tag');

    // 6. Economic Indicators
    const economyItems = data.filter(d => d.operational_tag && d.operational_tag.includes('economic'));
    renderSignalList('list-economy', economyItems.slice(0, 5), 'operational_tag');

    // 7. Public Sentiment
    const sentimentItems = data.filter(d => d.operational_tag && d.operational_tag.includes('sentiment'));
    renderSignalList('list-sentiment', sentimentItems.slice(0, 5), 'operational_tag');

    // 8. Energy & Utilities
    const energyItems = data.filter(d => d.operational_tag && (d.operational_tag.includes('energy') || d.operational_tag.includes('utilities')));
    renderSignalList('list-energy', energyItems.slice(0, 5), 'operational_tag');
}

function renderSignalList(elementId, items, badgeField) {
    const list = document.getElementById(elementId);
    list.innerHTML = '';

    if (items.length === 0) {
        list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; font-style: italic;">No active indicators</div>';
        return;
    }

    items.forEach(item => {
        const row = document.createElement('div');
        row.style.cssText = 'padding: 0.75rem 0; border-bottom: 1px solid var(--border-color); font-size: 0.9rem;';

        let badgeColor = '#64748b';
        const badgeText = item[badgeField];

        // Simple badge logic
        if (badgeText.includes('Risk')) badgeColor = '#ef4444';
        else if (badgeText.includes('Opportunity')) badgeColor = '#22c55e';
        else if (badgeText.includes('Major')) badgeColor = '#f59e0b';
        else if (badgeText !== 'general') badgeColor = '#3b82f6';

        row.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.25rem;">
                <span style="font-weight: 500; color: var(--text-primary); line-height: 1.3;">${item.Title}</span>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.4rem;">
                <span style="background: ${badgeColor}20; color: ${badgeColor}; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                    ${badgeText}
                </span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">${item.Source}</span>
            </div>
        `;
        list.appendChild(row);
    });
}


function updateCharts(data) {
    // Impact Distribution
    const impactCounts = {};
    data.forEach(d => {
        impactCounts[d.impact_level] = (impactCounts[d.impact_level] || 0) + 1;
    });

    const impactLabels = ["High Risk", "Risk", "Neutral", "Opportunity", "High Opportunity"];
    const impactValues = impactLabels.map(l => impactCounts[l] || 0);

    const ctxImpact = document.getElementById('impactChart').getContext('2d');

    if (impactChart) {
        impactChart.data.datasets[0].data = impactValues;
        impactChart.update();
    } else {
        impactChart = new Chart(ctxImpact, {
            type: 'doughnut',
            data: {
                labels: impactLabels,
                datasets: [{
                    data: impactValues,
                    backgroundColor: [
                        '#ef4444', // High Risk
                        'rgba(239, 68, 68, 0.6)', // Risk
                        '#94a3b8', // Neutral
                        'rgba(34, 197, 94, 0.6)', // Opportunity
                        '#22c55e'  // High Opportunity
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8' }
                    }
                }
            }
        });
    }

    // Operational Categories
    const opsCounts = {};
    data.forEach(d => {
        const tags = d.operational_tag.split(', ');
        tags.forEach(t => {
            if (t !== 'general') {
                opsCounts[t] = (opsCounts[t] || 0) + 1;
            }
        });
    });

    const opsLabels = Object.keys(opsCounts);
    const opsValues = Object.values(opsCounts);

    const ctxOps = document.getElementById('opsChart').getContext('2d');

    if (opsChart) {
        opsChart.data.labels = opsLabels;
        opsChart.data.datasets[0].data = opsValues;
        opsChart.update();
    } else {
        opsChart = new Chart(ctxOps, {
            type: 'bar',
            data: {
                labels: opsLabels,
                datasets: [{
                    label: 'Count',
                    data: opsValues,
                    backgroundColor: '#3b82f6',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#334155' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

// ===== MARKET DATA FUNCTIONALITY =====

let marketChart = null;
let currentMarketType = 'usd-lkr';

function setupMarketData() {
    const selector = document.getElementById('market-selector');
    const refreshBtn = document.getElementById('market-refresh-btn');

    if (selector) {
        selector.addEventListener('change', (e) => {
            currentMarketType = e.target.value;
            fetchMarketData(currentMarketType);
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            const icon = refreshBtn.querySelector('i');
            icon.classList.add('fa-spin');
            refreshBtn.disabled = true;

            try {
                await fetch('/api/market/update', { method: 'POST' });
                await fetchMarketData(currentMarketType);
            } catch (error) {
                console.error('Error updating market data:', error);
            } finally {
                icon.classList.remove('fa-spin');
                refreshBtn.disabled = false;
            }
        });
    }

    // Initial load
    fetchMarketData(currentMarketType);
}

async function fetchMarketData(type) {
    try {
        let endpoint = '';
        let title = '';

        switch (type) {
            case 'usd-lkr':
                endpoint = '/api/market/usd-lkr';
                title = 'USD / LKR Exchange Rate';
                break;
            case 'gold':
                endpoint = '/api/market/gold';
                title = 'Gold Price (24K per gram)';
                break;
            case 'fuel':
                endpoint = '/api/market/fuel';
                title = 'Fuel Prices';
                break;
            case 'inflation':
                endpoint = '/api/market/inflation';
                title = 'Inflation Rate (%)';
                break;
        }

        const response = await fetch(endpoint);
        const data = await response.json();

        document.getElementById('market-title').textContent = title;
        renderMarketData(data, type);
    } catch (error) {
        console.error('Error fetching market data:', error);
        document.getElementById('market-current-value').textContent = 'Error loading data';
    }
}

function renderMarketData(data, type) {
    const valueContainer = document.getElementById('market-current-value');
    const subtitleContainer = document.getElementById('market-subtitle');

    if (type === 'fuel') {
        // Fuel prices - display all fuel types
        if (data.current) {
            let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">';
            for (const [fuel, price] of Object.entries(data.current)) {
                html += `
                    <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">${fuel}</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: var(--accent);">Rs. ${price.toFixed(2)}</div>
                    </div>
                `;
            }
            html += '</div>';
            valueContainer.innerHTML = html;
            subtitleContainer.textContent = 'Per Liter';
        } else {
            valueContainer.textContent = 'No data available';
            subtitleContainer.textContent = '';
        }

        // Render fuel chart
        renderFuelChart(data.history);
    } else {
        // USD/LKR, Gold, or Inflation - single value
        if (data.current !== null && data.current !== undefined) {
            let prefix = '';
            let suffix = '';

            if (type === 'usd-lkr') {
                prefix = 'Rs. ';
                subtitleContainer.textContent = 'per USD';
            } else if (type === 'gold') {
                prefix = 'Rs. ';
                subtitleContainer.textContent = 'per gram (24K)';
            } else if (type === 'inflation') {
                // suffix = '%'; // CPI is an index, no percentage
                subtitleContainer.textContent = 'Consumer Price Index (Base 2013=100)';
            }

            valueContainer.textContent = prefix + data.current.toFixed(2) + suffix;
        } else {
            valueContainer.textContent = 'No data available';
            subtitleContainer.textContent = '';
        }

        // Render single value chart
        renderMarketChart(data.history, type);
    }
}

function renderMarketChart(history, type) {
    if (!history || history.length === 0) {
        return;
    }

    const ctx = document.getElementById('marketChart').getContext('2d');

    const labels = history.map(item => item.date);
    const values = history.map(item => item.value);

    if (marketChart) {
        marketChart.destroy();
    }

    let chartLabel = 'Value';
    if (type === 'usd-lkr') chartLabel = 'USD/LKR Rate';
    else if (type === 'gold') chartLabel = 'Gold Price (LKR)';
    else if (type === 'inflation') chartLabel = 'Consumer Price Index (CPI)';

    marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: chartLabel,
                data: values,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    grace: '20%',
                    grid: { color: '#334155' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#94a3b8',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#94a3b8' }
                }
            }
        }
    });
}


function renderFuelChart(history) {
    if (!history || history.length === 0) {
        return;
    }

    const ctx = document.getElementById('marketChart').getContext('2d');

    const labels = history.map(item => item.date);

    // Extract all fuel types
    const fuelTypes = new Set();
    history.forEach(item => {
        if (item.values) {
            Object.keys(item.values).forEach(fuel => fuelTypes.add(fuel));
        }
    });

    const datasets = [];
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
    let colorIndex = 0;

    fuelTypes.forEach(fuelType => {
        const data = history.map(item => item.values && item.values[fuelType] ? item.values[fuelType] : null);
        datasets.push({
            label: fuelType,
            data: data,
            borderColor: colors[colorIndex % colors.length],
            backgroundColor: 'transparent',
            borderWidth: 2,
            tension: 0.4
        });
        colorIndex++;
    });

    if (marketChart) {
        marketChart.destroy();
    }

    marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    grace: '20%',
                    grid: { color: '#334155' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#94a3b8',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { color: '#94a3b8' }
                }
            }
        }
    });
}
