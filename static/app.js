const COLORS = {
    exponential: '#e74c3c',
    hyperbolic: '#2ecc71',
    harmonic: '#3498db',
};

let charts = {};
let rateUnit = 'BOPD';
let cumulativeUnit = 'Mbbl';
let cumulativeUnitSmall = 'bbl';

function deriveUnits(rateColumn) {
    if (!rateColumn) return;
    const col = rateColumn.toLowerCase();
    if (col.includes('bopd') || col.includes('oil')) {
        rateUnit = 'BOPD'; cumulativeUnit = 'Mbbl'; cumulativeUnitSmall = 'bbl';
    } else if (col.includes('bwpd') || col.includes('water')) {
        rateUnit = 'BWPD'; cumulativeUnit = 'Mbbl'; cumulativeUnitSmall = 'bbl';
    } else if (col.includes('mcfd') || col.includes('gas')) {
        rateUnit = 'MCFD'; cumulativeUnit = 'MMcf'; cumulativeUnitSmall = 'Mcf';
    } else {
        // Fallback: try to extract unit from column name suffix after last underscore
        const parts = rateColumn.split('_');
        rateUnit = parts[parts.length - 1].toUpperCase();
        cumulativeUnit = 'M' + rateUnit.toLowerCase();
        cumulativeUnitSmall = rateUnit.toLowerCase();
    }
}

// File upload label
document.getElementById('csvFile').addEventListener('change', function () {
    const label = document.getElementById('fileLabel');
    if (this.files.length > 0) {
        label.textContent = this.files[0].name;
        label.style.color = 'var(--text)';
        label.style.borderColor = 'var(--accent)';

        // Read columns from CSV header
        const reader = new FileReader();
        reader.onload = function (e) {
            const header = e.target.result.split('\n')[0].split(',').map(s => s.trim());
            const select = document.getElementById('rateColumn');
            select.innerHTML = '';
            header.filter(c => c !== 'date').forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.textContent = col;
                select.appendChild(opt);
            });
        };
        reader.readAsText(this.files[0]);
    }
});

function runAnalysis() {
    const btn = document.getElementById('analyzeBtn');
    btn.disabled = true;
    btn.textContent = 'Running...';

    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('results').style.display = 'none';
    document.getElementById('loading').classList.add('active');
    document.getElementById('errorMsg').style.display = 'none';

    const formData = new FormData();
    const fileInput = document.getElementById('csvFile');
    if (fileInput.files.length > 0) {
        formData.append('file', fileInput.files[0]);
    }
    formData.append('rate_column', document.getElementById('rateColumn').value);
    formData.append('forecast_years', document.getElementById('forecastYears').value);
    formData.append('economic_limit', document.getElementById('econLimit').value);

    fetch('/api/analyze', { method: 'POST', body: formData })
        .then(r => r.json().then(data => ({ ok: r.ok, data })))
        .then(({ ok, data }) => {
            document.getElementById('loading').classList.remove('active');
            btn.disabled = false;
            btn.textContent = 'Analyze';

            if (!ok) {
                document.getElementById('errorMsg').textContent = data.error;
                document.getElementById('errorMsg').style.display = 'block';
                return;
            }

            // Update rate column options if returned
            if (data.available_columns) {
                const select = document.getElementById('rateColumn');
                const current = select.value;
                select.innerHTML = '';
                data.available_columns.forEach(col => {
                    const opt = document.createElement('option');
                    opt.value = col;
                    opt.textContent = col;
                    if (col === current) opt.selected = true;
                    select.appendChild(opt);
                });
            }

            deriveUnits(data.rate_column);
            renderResults(data);
        })
        .catch(err => {
            document.getElementById('loading').classList.remove('active');
            btn.disabled = false;
            btn.textContent = 'Analyze';
            document.getElementById('errorMsg').textContent = 'Network error: ' + err.message;
            document.getElementById('errorMsg').style.display = 'block';
        });
}

function renderResults(data) {
    document.getElementById('results').style.display = 'block';

    // Model cards
    const cardsDiv = document.getElementById('modelCards');
    let cardsHTML = '';

    const modelOrder = ['exponential', 'hyperbolic', 'harmonic'];
    modelOrder.forEach(name => {
        if (!data.models[name]) return;
        const m = data.models[name];
        const eur = data.eur[name];
        const isBest = name === data.best_model;

        cardsHTML += `
            <div class="card ${isBest ? 'best' : ''}">
                <div class="model-name">
                    ${name}${isBest ? '<span class="badge">Best Fit</span>' : ''}
                </div>
                <div class="r2" style="color: ${COLORS[name]}">R\u00B2 = ${m.r_squared.toFixed(4)}</div>
                <div class="params">
                    qi = <span>${m.qi.toFixed(1)}</span> ${rateUnit}<br>
                    Di = <span>${m.di_annual.toFixed(4)}</span> /yr
                    ${m.b !== undefined ? `<br>b = <span>${m.b.toFixed(4)}</span>` : ''}
                </div>
            </div>
        `;
    });

    // EUR card for best model
    const bestEur = data.eur[data.best_model];
    cardsHTML += `
        <div class="card eur-card best">
            <div class="model-name">EUR (${data.best_model})</div>
            <div class="eur-value">${bestEur.eur_mbbl.toFixed(1)} ${cumulativeUnit}</div>
            <div class="eur-detail">
                ${Number(bestEur.eur_bbl).toLocaleString()} ${cumulativeUnitSmall}<br>
                Econ Life: <span>${bestEur.time_to_econ_limit_years.toFixed(1)}</span> years<br>
                Aband. Rate: <span>${bestEur.abandonment_rate_bopd.toFixed(1)}</span> ${rateUnit}
            </div>
        </div>
    `;

    cardsDiv.innerHTML = cardsHTML;

    // Destroy old charts
    Object.values(charts).forEach(c => c.destroy());
    charts = {};

    renderFitsChart(data);
    renderComparisonChart(data);
    renderForecastChart(data);
    renderCumulativeChart(data);
}

const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { labels: { color: '#8b8fa8', font: { size: 12 } } },
    },
    scales: {
        x: {
            ticks: { color: '#8b8fa8', maxTicksLimit: 10 },
            grid: { color: 'rgba(46,51,72,0.5)' },
        },
        y: {
            ticks: { color: '#8b8fa8' },
            grid: { color: 'rgba(46,51,72,0.5)' },
        },
    },
};

function renderFitsChart(data) {
    const datasets = [{
        label: 'Actual',
        data: data.rates,
        borderColor: '#fff',
        backgroundColor: '#fff',
        pointRadius: 3,
        pointStyle: 'circle',
        showLine: false,
        order: 0,
    }];

    ['exponential', 'hyperbolic', 'harmonic'].forEach(name => {
        if (!data.fits[name]) return;
        datasets.push({
            label: name.charAt(0).toUpperCase() + name.slice(1),
            data: data.fits[name],
            borderColor: COLORS[name],
            borderWidth: 2,
            pointRadius: 0,
            pointStyle: 'line',
            tension: 0.3,
            order: 1,
        });
    });

    charts.fits = new Chart(document.getElementById('fitsChart'), {
        type: 'line',
        data: { labels: data.dates, datasets },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { labels: { color: '#8b8fa8', font: { size: 12 }, usePointStyle: true, boxWidth: 4, boxHeight: 4 } },
            },
            scales: {
                ...CHART_DEFAULTS.scales,
                x: { ...CHART_DEFAULTS.scales.x, type: 'category' },
                y: { ...CHART_DEFAULTS.scales.y, title: { display: true, text: `Rate (${rateUnit})`, color: '#8b8fa8' } },
            },
        },
    });
}

function renderComparisonChart(data) {
    const models = Object.keys(data.models);
    const r2 = models.map(m => data.models[m].r_squared);
    const eurs = models.map(m => data.eur[m].eur_mbbl);
    const colors = models.map(m => COLORS[m]);

    charts.comparison = new Chart(document.getElementById('comparisonChart'), {
        type: 'bar',
        data: {
            labels: models.map(m => m.charAt(0).toUpperCase() + m.slice(1)),
            datasets: [
                {
                    label: 'R-squared',
                    data: r2,
                    backgroundColor: colors.map(c => c + '99'),
                    borderColor: colors,
                    borderWidth: 1,
                    yAxisID: 'y',
                },
                {
                    label: `EUR (${cumulativeUnit})`,
                    data: eurs,
                    backgroundColor: colors.map(c => c + '44'),
                    borderColor: colors,
                    borderWidth: 1,
                    borderDash: [4, 4],
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            ...CHART_DEFAULTS,
            scales: {
                x: CHART_DEFAULTS.scales.x,
                y: {
                    ...CHART_DEFAULTS.scales.y,
                    position: 'left',
                    title: { display: true, text: 'R-squared', color: '#8b8fa8' },
                    min: Math.min(...r2) - 0.005,
                    max: 1,
                },
                y1: {
                    ...CHART_DEFAULTS.scales.y,
                    position: 'right',
                    title: { display: true, text: `EUR (${cumulativeUnit})`, color: '#8b8fa8' },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}

function renderForecastChart(data) {
    const allDates = [...data.dates, ...data.forecast_dates];
    const histRates = [...data.rates, ...new Array(data.forecast_dates.length).fill(null)];
    const fcastRates = [...new Array(data.dates.length).fill(null), ...data.forecast_rates];
    // Connect forecast to last historical point
    fcastRates[data.dates.length - 1] = data.rates[data.rates.length - 1];

    const econLine = new Array(allDates.length).fill(data.economic_limit);

    charts.forecast = new Chart(document.getElementById('forecastChart'), {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'Historical',
                    data: histRates,
                    borderColor: '#fff',
                    backgroundColor: '#fff',
                    pointRadius: 2,
                    borderWidth: 2,
                    spanGaps: false,
                },
                {
                    label: 'Forecast (' + data.best_model + ')',
                    data: fcastRates,
                    borderColor: COLORS[data.best_model],
                    borderDash: [6, 3],
                    borderWidth: 2,
                    pointRadius: 0,
                    spanGaps: false,
                },
                {
                    label: 'Economic Limit',
                    data: econLine,
                    borderColor: '#666',
                    borderDash: [2, 2],
                    borderWidth: 1,
                    pointRadius: 0,
                },
            ],
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                legend: { labels: { color: '#8b8fa8', font: { size: 12 }, usePointStyle: true, pointStyle: 'line' } },
            },
            scales: {
                x: { ...CHART_DEFAULTS.scales.x, type: 'category', ticks: { ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit: 15 } },
                y: { ...CHART_DEFAULTS.scales.y, title: { display: true, text: `Rate (${rateUnit})`, color: '#8b8fa8' }, min: 0 },
            },
        },
    });
}

function renderCumulativeChart(data) {
    const allDates = data.cumulative_dates;
    const n = data.cumulative_hist.length;
    const histCum = [...data.cumulative_hist.map(v => v / 1000), ...new Array(data.cumulative_forecast.length).fill(null)];
    const fcastCum = [...new Array(n).fill(null), ...data.cumulative_forecast.map(v => v / 1000)];
    // Connect
    fcastCum[n - 1] = data.cumulative_hist[n - 1] / 1000;

    charts.cumulative = new Chart(document.getElementById('cumulativeChart'), {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'Historical',
                    data: histCum,
                    borderColor: '#4f8cff',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: 'rgba(79,140,255,0.1)',
                    spanGaps: false,
                },
                {
                    label: 'Forecast',
                    data: fcastCum,
                    borderColor: COLORS[data.best_model],
                    borderDash: [6, 3],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: COLORS[data.best_model] + '15',
                    spanGaps: false,
                },
            ],
        },
        options: {
            ...CHART_DEFAULTS,
            scales: {
                x: { ...CHART_DEFAULTS.scales.x, type: 'category', ticks: { ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit: 15 } },
                y: { ...CHART_DEFAULTS.scales.y, title: { display: true, text: `Cumulative (${cumulativeUnit})`, color: '#8b8fa8' } },
            },
        },
    });
}
