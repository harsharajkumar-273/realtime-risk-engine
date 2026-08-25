let ws = null;
let chart = null;
let latencyHistory = [];
const MAX_ROWS = 50;

// DOM Elements
const elTpsSlider = document.getElementById("tps-slider");
const elTpsVal = document.getElementById("tps-val");
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const tbody = document.getElementById("telemetry-tbody");

// KPI Elements
const kpiTotal = document.getElementById("kpi-total");
const kpiAllow = document.getElementById("kpi-allow");
const kpiReview = document.getElementById("kpi-review");
const kpiDecline = document.getElementById("kpi-decline");
const kpiAllowPct = document.getElementById("kpi-allow-pct");
const kpiReviewPct = document.getElementById("kpi-review-pct");
const kpiDeclinePct = document.getElementById("kpi-decline-pct");
const kpiLatency = document.getElementById("kpi-latency");
const kpiP95 = document.getElementById("kpi-p95");
const circuitStateEl = document.getElementById("circuit-state");

let totals = { total: 0, allow: 0, review: 0, decline: 0 };

function initChart() {
    const ctx = document.getElementById("latencyChart").getContext("2d");
    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Pipeline Latency (ms)",
                data: [],
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                fill: true,
                tension: 0.3,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: { display: false },
                y: {
                    beginAtZero: true,
                    grid: { color: "#1f2d4d" },
                    ticks: { color: "#94a3b8" }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    const wsStatusEl = document.getElementById("ws-status");
    
    ws.onopen = () => {
        wsStatusEl.innerText = "CONNECTED";
        wsStatusEl.className = "green";
    };
    
    ws.onclose = () => {
        wsStatusEl.innerText = "DISCONNECTED";
        wsStatusEl.className = "red";
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "TRANSACTION_PROCESSED") {
            handleTransactionProcessed(msg.data);
        }
    };
}

function handleTransactionProcessed(data) {
    const tx = data.transaction;
    const dec = data.decision;
    
    // Update Totals
    totals.total += 1;
    if (dec.decision === "ALLOW") totals.allow += 1;
    else if (dec.decision === "REVIEW") totals.review += 1;
    else totals.decline += 1;
    
    kpiTotal.innerText = totals.total.toLocaleString();
    kpiAllow.innerText = totals.allow.toLocaleString();
    kpiReview.innerText = totals.review.toLocaleString();
    kpiDecline.innerText = totals.decline.toLocaleString();
    
    kpiAllowPct.innerText = `${((totals.allow / totals.total) * 100).toFixed(1)}%`;
    kpiReviewPct.innerText = `${((totals.review / totals.total) * 100).toFixed(1)}%`;
    kpiDeclinePct.innerText = `${((totals.decline / totals.total) * 100).toFixed(1)}%`;
    
    // Latencies
    const lat = dec.latencies.total_ms;
    latencyHistory.push(lat);
    if (latencyHistory.length > 50) latencyHistory.shift();
    
    const avgLat = (latencyHistory.reduce((a, b) => a + b, 0) / latencyHistory.length).toFixed(2);
    kpiLatency.innerText = `${avgLat} ms`;
    
    circuitStateEl.innerText = dec.circuit_state;
    
    // Update Chart
    if (chart) {
        chart.data.labels.push("");
        chart.data.datasets[0].data.push(lat);
        if (chart.data.labels.length > 30) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        chart.update("none");
    }
    
    // Append Table Row
    const tr = document.createElement("tr");
    const reasonsHtml = dec.reason_codes.map(r => `<span class="reason-tag">${r}</span>`).join(" ");
    
    tr.innerHTML = `
        <td style="font-family: monospace;">${tx.transaction_id.substring(0, 10)}</td>
        <td style="font-family: monospace;">${tx.account_id}</td>
        <td><strong>$${tx.amount.toFixed(2)}</strong></td>
        <td>${tx.country}</td>
        <td><span class="pill ${dec.decision}">${dec.decision}</span></td>
        <td><strong>${dec.risk_score.toFixed(3)}</strong></td>
        <td style="color: #38bdf8;">${lat.toFixed(2)}ms</td>
        <td>${reasonsHtml || '<span style="color: #64748b;">Clear</span>'}</td>
    `;
    
    tbody.insertBefore(tr, tbody.firstChild);
    if (tbody.children.length > MAX_ROWS) {
        tbody.removeChild(tbody.lastChild);
    }
}

// Controls
elTpsSlider.addEventListener("input", (e) => {
    elTpsVal.innerText = e.target.value;
});

btnStart.addEventListener("click", async () => {
    const tps = parseFloat(elTpsSlider.value);
    await fetch("/api/v1/stream/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tps: tps })
    });
    btnStart.disabled = true;
    btnStop.disabled = false;
});

btnStop.addEventListener("click", async () => {
    await fetch("/api/v1/stream/stop", { method: "POST" });
    btnStart.disabled = false;
    btnStop.disabled = true;
});

document.querySelectorAll(".btn-anomaly").forEach(btn => {
    btn.addEventListener("click", async () => {
        const fraudType = btn.getAttribute("data-type");
        await fetch("/api/v1/simulate/anomaly", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fraud_type: fraudType })
        });
    });
});

window.onload = () => {
    initChart();
    connectWebSocket();
};
