// WebSocket and Chart Management
let ws;
let log = document.getElementById("log");
let charts = {};
let currentRunData = {};
let allRunsData = {};
let connectionRetries = 0;
let maxRetries = 5;

// Initialize connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log(`Connecting to WebSocket at: ${wsUrl}`);
    ws = new WebSocket(wsUrl);

    ws.onopen = function() {
        console.log('WebSocket connection opened');
        updateConnectionStatus('Connected', 'success');
        logMessage('🔗 Connected to benchmark server');
        connectionRetries = 0;
    };

    ws.onclose = function(event) {
        console.log('WebSocket connection closed:', event.code, event.reason);
        updateConnectionStatus('Disconnected', 'danger');
        logMessage('❌ Disconnected from benchmark server');
        
        // Auto-reconnect
        if (connectionRetries < maxRetries) {
            connectionRetries++;
            console.log(`Attempting to reconnect... (${connectionRetries}/${maxRetries})`);
            logMessage(`🔄 Reconnecting... (${connectionRetries}/${maxRetries})`);
            setTimeout(connectWebSocket, 3000);
        } else {
            logMessage('❌ Max reconnection attempts reached. Please refresh the page.');
        }
    };

    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        updateConnectionStatus('Error', 'danger');
        logMessage('⚠️ Connection error');
    };

    ws.onmessage = function(event) {
        const data = event.data;
        console.log('📨 WebSocket message received:', data.substring(0, 100));
        
        // Always display the message
        logMessage(data);
        
        try {
            // Parse benchmark results and update charts
            parseBenchmarkResult(data);
        } catch (error) {
            console.error('❌ Error parsing message:', error, 'Data:', data);
        }
    };
}

// Initialize charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded, initializing...');
    logMessage('🖥️ Dashboard initialized');
    
    // Initialize WebSocket first
    connectWebSocket();
    
    // Then initialize other components
    initializeCharts();
    loadHistoricalRuns();
    
    console.log('Initialization complete');
});

ws.onmessage = function(event) {
    const data = event.data;
    logMessage(data);
    
    // Parse benchmark results and update charts
    parseBenchmarkResult(data);
};

function logMessage(message) {
    if (!log) {
        log = document.getElementById("log");
        if (!log) {
            console.error('Log element not found!');
            return;
        }
    }
    
    const timestamp = new Date().toLocaleTimeString();
    const logLine = `[${timestamp}] ${message}\n`;
    log.textContent += logLine;
    log.scrollTop = log.scrollHeight;
    
    // Also log to console for debugging
    console.log('Dashboard Log:', logLine.trim());
}

function updateConnectionStatus(status, type) {
    const statusBadge = document.getElementById('connectionStatus');
    statusBadge.textContent = status;
    statusBadge.className = `badge bg-${type}`;
}

function startBenchmark() {
    const label = document.getElementById("label").value.trim();
    if(!label) {
        alert('Please enter a run label');
        return;
    }
    
    // Check WebSocket connection
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not connected. Attempting to reconnect...');
        logMessage('⚠️ Reconnecting to server...');
        
        // Try to reconnect
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('✅ WebSocket reconnected');
            logMessage('🔗 Reconnected to benchmark server');
            // Retry the benchmark
            sendBenchmarkCommand(label);
        };
        
        ws.onerror = function(error) {
            console.error('WebSocket reconnection error:', error);
            logMessage('❌ Connection failed. Please refresh the page.');
        };
        
        return;
    }
    
    sendBenchmarkCommand(label);
}

function sendBenchmarkCommand(label) {
    // Show loading spinner
    const spinner = document.getElementById('benchmarkSpinner');
    spinner.classList.remove('d-none');
    
    // Get benchmark options
    const gpuEnabled = document.getElementById('gpuBenchmark')?.checked || false;
    const ollamaEnabled = document.getElementById('ollamaBenchmark')?.checked || false;
    
    // Send benchmark start command
    const command = `run:${label}:gpu=${gpuEnabled}:ollama=${ollamaEnabled}`;
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(command);
        console.log(`📨 Sent command: ${command}`);
        logMessage(`🚀 Starting benchmark: ${label}`);
        logMessage(`   GPU: ${gpuEnabled}, Ollama: ${ollamaEnabled}`);
    } else {
        console.error('WebSocket not open. State:', ws?.readyState);
        logMessage('❌ WebSocket not connected. Please refresh the page.');
        alert('WebSocket not connected. Please refresh the page and try again.');
    }
}
    
    // Show loading spinner
    const spinner = document.getElementById('benchmarkSpinner');
    spinner.classList.remove('d-none');
    
    // Get benchmark options
    const gpuEnabled = document.getElementById('gpuBenchmark').checked;
    const ollamaEnabled = document.getElementById('ollamaBenchmark').checked;
    
    // Send benchmark start command
    const command = `run:${label}:gpu=${gpuEnabled}:ollama=${ollamaEnabled}`;
    ws.send(command);
    
    logMessage(`🚀 Starting benchmark: ${label}`);
    
    // Switch to overview tab
    const overviewTab = new bootstrap.Tab(document.getElementById('overview-tab'));
    overviewTab.show();
    
    // Hide spinner after delay
    setTimeout(() => {
        spinner.classList.add('d-none');
    }, 2000);
}

function clearLogs() {
    log.textContent = '';
    logMessage('📝 Logs cleared');
}

// Chart initialization
function initializeCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top'
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    };

    // CPU Chart
    charts.cpu = new Chart(document.getElementById('cpuChart'), {
        type: 'bar',
        data: {
            labels: ['1 Thread', 'All Threads'],
            datasets: [{
                label: 'Events/sec',
                data: [0, 0],
                backgroundColor: ['#007bff', '#0056b3'],
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'CPU Performance'
                }
            }
        }
    });

    // Memory Chart
    charts.memory = new Chart(document.getElementById('memoryChart'), {
        type: 'line',
        data: {
            labels: ['Read MB/s', 'Write MB/s'],
            datasets: [{
                label: 'Memory Bandwidth',
                data: [0, 0],
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                fill: true
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'Memory Bandwidth'
                }
            }
        }
    });

    // Disk Chart
    charts.disk = new Chart(document.getElementById('diskChart'), {
        type: 'bar',
        data: {
            labels: ['Read MB/s', 'Write MB/s'],
            datasets: [{
                label: 'Disk I/O',
                data: [0, 0],
                backgroundColor: ['#ffc107', '#fd7e14'],
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'Disk Performance'
                }
            }
        }
    });

    // GPU Chart
    charts.gpu = new Chart(document.getElementById('gpuChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'GPU Temperature (°C)',
                data: [],
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                fill: false
            }, {
                label: 'GPU Utilization (%)',
                data: [],
                borderColor: '#6f42c1',
                backgroundColor: 'rgba(111, 66, 193, 0.1)',
                fill: false
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'GPU Metrics'
                }
            },
            scales: {
                ...chartOptions.scales,
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    // Ollama LLM Charts
    charts.llmTokens = new Chart(document.getElementById('llmTokensChart'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Tokens/sec',
                data: [],
                backgroundColor: '#17a2b8',
                borderColor: '#117a65',
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'LLM Tokens/sec Performance'
                }
            }
        }
    });

    charts.llmLatency = new Chart(document.getElementById('llmLatencyChart'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Latency (ms)',
                data: [],
                backgroundColor: '#ffc107',
                borderColor: '#fd7e14',
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'LLM Latency Performance'
                }
            }
        }
    });

    charts.llmMemory = new Chart(document.getElementById('llmMemoryChart'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Memory (MB)',
                data: [],
                backgroundColor: '#6f42c1',
                borderColor: '#4c1d95',
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'LLM Memory Usage'
                }
            }
        }
    });
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    display: true,
                    text: 'GPU Metrics'
                }
            },
            scales: {
                ...chartOptions.scales,
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    // Comparison Chart
    charts.comparison = new Chart(document.getElementById('comparisonChart'), {
        type: 'radar',
        data: {
            labels: ['CPU 1T', 'CPU All', 'Memory', 'Disk Read', 'Disk Write', 'LLM Tokens/s', 'LLM Latency', 'LLM Memory'],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Performance Comparison'
                }
            },
            scales: {
                r: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Parse benchmark results from log messages
function parseBenchmarkResult(message) {
    console.log('🔍 Parsing benchmark result:', message.substring(0, 50));
    
    // Extract run name from message
    const runMatch = message.match(/\[(.*?)\]/);
    if (!runMatch) {
        console.log('⚠️ No run name found in message');
        return;
    }
    
    const runName = runMatch[1];
    console.log(`📊 Run: ${runName}`);
    
    // Parse CPU results
    if (message.includes('CPU 1 thread') && message.includes('events per second')) {
        const cpuMatch = message.match(/(\d+\.\d+)\s+events per second/);
        if (cpuMatch) {
            currentRunData.cpu1Thread = parseFloat(cpuMatch[1]);
            updateChart('cpu', [currentRunData.cpu1Thread, currentRunData.cpuAllThreads || 0]);
        }
    }
    
    if (message.includes('CPU all threads') && message.includes('events per second')) {
        const cpuMatch = message.match(/(\d+\.\d+)\s+events per second/);
        if (cpuMatch) {
            currentRunData.cpuAllThreads = parseFloat(cpuMatch[1]);
            updateChart('cpu', [currentRunData.cpu1Thread || 0, currentRunData.cpuAllThreads]);
        }
    }
    
    // Parse Memory results
    if (message.includes('Memory test') && message.includes('MiB/sec')) {
        const memMatches = message.match(/(\d+\.\d+)\s+MiB\/sec/g);
        if (memMatches && memMatches.length >= 2) {
            const readSpeed = parseFloat(memMatches[0]);
            const writeSpeed = parseFloat(memMatches[1]);
            currentRunData.memory = { read: readSpeed, write: writeSpeed };
            updateChart('memory', [readSpeed, writeSpeed]);
        }
    }
    
    // Parse Disk results
    if (message.includes('Disk test') && message.includes('MiB/sec')) {
        const diskMatches = message.match(/(\d+\.\d+)\s+MiB\/sec/g);
        if (diskMatches && diskMatches.length >= 2) {
            const readSpeed = parseFloat(diskMatches[0]);
            const writeSpeed = parseFloat(diskMatches[1]);
            currentRunData.disk = { read: readSpeed, write: writeSpeed };
            updateChart('disk', [readSpeed, writeSpeed]);
        }
    }
    
    // Parse GPU metrics (placeholder for now)
    if (message.includes('GPU Temperature')) {
        const tempMatch = message.match(/(\d+)°C/);
        if (tempMatch) {
            addGPUMetric('temperature', parseInt(tempMatch[1]));
        }
    }
    
    if (message.includes('GPU Utilization')) {
        const utilMatch = message.match(/(\d+)%/);
        if (utilMatch) {
            addGPUMetric('utilization', parseInt(utilMatch[1]));
        }
    }
    
    // Parse Ollama LLM results
    if (message.includes('Tokens/sec:')) {
        const tokenMatch = message.match(/Tokens\/sec:\s*(\d+\.?\d*)/);
        if (tokenMatch) {
            currentRunData.ollama.tokens_per_sec = parseFloat(tokenMatch.group(1));
            updateChart('llmTokens', [currentRunData.ollama.tokens_per_sec]);
            updateMetricsSummary();
        }
    }
    
    if (message.includes('Latency:')) {
        const latencyMatch = message.match(/Latency:\s*(\d+\.?\d*)s/);
        if (latencyMatch) {
            currentRunData.ollama.latency = parseFloat(latencyMatch.group(1));
            updateChart('llmLatency', [currentRunData.ollama.latency]);
            updateMetricsSummary();
        }
    }
    
    if (message.includes('Memory:') && message.includes('MB')) {
        const memoryMatch = message.match(/Memory:\s*(\d+)\s*MB/);
        if (memoryMatch) {
            currentRunData.ollama.memory_mb = parseInt(memoryMatch.group(1));
            updateChart('llmMemory', [currentRunData.ollama.memory_mb]);
            updateMetricsSummary();
        }
    }
    
    // Update metrics summary
    if (Object.keys(currentRunData).length > 0) {
        updateMetricsSummary();
    }
}

function updateChart(chartName, data) {
    if (charts[chartName]) {
        console.log(`📊 Updating ${chartName} chart with data:`, data);
        
        if (chartName === 'cpu' && Array.isArray(data) && data.length === 2) {
            charts[chartName].data.datasets[0].data = data;
        } else if (chartName === 'memory' && Array.isArray(data) && data.length === 2) {
            charts[chartName].data.datasets[0].data = data;
        } else if (chartName === 'disk' && Array.isArray(data) && data.length === 2) {
            charts[chartName].data.datasets[0].data = data;
        } else if (chartName === 'llmTokens' || chartName === 'llmLatency' || chartName === 'llmMemory') {
            charts[chartName].data.datasets[0].data = data;
        } else if (chartName === 'gpu') {
            // Handle multiple GPU datasets
            if (data.length >= 2) {
                charts[chartName].data.datasets[0].data = data.temperature || [];
                charts[chartName].data.datasets[1].data = data.utilization || [];
            } else {
                charts[chartName].data.datasets[0].data = data;
            }
        } else {
            charts[chartName].data.datasets[0].data = data;
        }
        
        charts[chartName].update('none'); // Use 'none' mode for smooth updates
    }
}
        
        charts[chartName].update('none'); // Use 'none' mode for smooth updates without animation
    }
}

function addGPUMetric(type, value) {
    const chart = charts.gpu;
    const timestamp = new Date().toLocaleTimeString();
    
    if (!chart.data.labels.includes(timestamp)) {
        chart.data.labels.push(timestamp);
        
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[1].data.shift();
        }
    }
    
    const datasetIndex = type === 'temperature' ? 0 : 1;
    chart.data.datasets[datasetIndex].data.push(value);
    chart.update();
}

function updateMetricsSummary() {
    const summaryDiv = document.getElementById('metricsSummary');
    
    let html = '<div class="metrics-summary fade-in">';
    
    if (currentRunData.cpuAllThreads) {
        html += `
            <div class="metric-card">
                <h6>CPU Score</h6>
                <div class="metric-value">${currentRunData.cpuAllThreads.toFixed(0)}</div>
                <small>events/sec</small>
            </div>
        `;
    }
    
    if (currentRunData.memory) {
        html += `
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h6>Memory</h6>
                <div class="metric-value">${(currentRunData.memory.read + currentRunData.memory.write).toFixed(0)}</div>
                <small>MB/s total</small>
            </div>
        `;
    }
    
    if (currentRunData.disk) {
        html += `
            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <h6>Disk I/O</h6>
                <div class="metric-value">${(currentRunData.disk.read + currentRunData.disk.write).toFixed(0)}</div>
                <small>MB/s total</small>
            </div>
        `;
    }
    
    if (currentRunData.ollama) {
        html += `
            <div class="metric-card" style="background: linear-gradient(135deg, #6f42c1 0%, #20a8d8 100%);">
                <h6>LLM Tokens/sec</h6>
                <div class="metric-value">${currentRunData.ollama.tokens_per_sec.toFixed(1)}</div>
                <small>tokens/sec</small>
            </div>
        `;
        
        html += `
            <div class="metric-card" style="background: linear-gradient(135deg, #6f42c1 0%, #20a8d8 100%);">
                <h6>LLM Latency</h6>
                <div class="metric-value">${(currentRunData.ollama.latency * 1000).toFixed(0)}</div>
                <small>ms</small>
            </div>
        `;
        
        html += `
            <div class="metric-card" style="background: linear-gradient(135deg, #e83e8c 0%, #38a169 100%);">
                <h6>LLM Memory</h6>
                <div class="metric-value">${currentRunData.ollama.memory_mb} MB</div>
                <small>VRAM usage</small>
            </div>
        `;
    }
    
    html += '</div>';
    summaryDiv.innerHTML = html;
}

// Load historical runs
async function loadHistoricalRuns() {
    try {
        const response = await fetch('/api/runs');
        const runs = await response.json();
        
        const tableBody = document.getElementById('runsTableBody');
        const compareCheckboxes = document.getElementById('compareCheckboxes');
        
        if (!compareCheckboxes) {
            console.error('compareCheckboxes element not found');
            return;
        }
        
        tableBody.innerHTML = '';
        compareCheckboxes.innerHTML = '';
        
        runs.forEach((run, index) => {
            // Add to table
            const row = document.createElement('tr');
            row.innerHTML = `
                    <td>${run.name}</td>
                    <td>${new Date(run.date).toLocaleDateString()}</td>
                    <td>${run.cpuAllThreads ? run.cpuAllThreads.toFixed(0) : 'N/A'}</td>
                    <td>${run.memory ? (run.memory.read + run.memory.write).toFixed(0) : 'N/A'}</td>
                    <td>${run.disk ? (run.disk.read + run.disk.write).toFixed(0) : 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary">View</button>
                        <button class="btn btn-sm btn-outline-info">Compare</button>
                        <button class="btn btn-sm btn-outline-danger">Delete</button>
                    </td>
                `;
            
            // Add event listeners to buttons
            const buttons = row.querySelectorAll('button');
            buttons[0].onclick = () => viewRun(run.name);
            buttons[1].onclick = () => addToComparison(run.name);
            buttons[2].onclick = () => deleteRun(run.name);
            
            tableBody.appendChild(row);
            
            // Add to comparison checkboxes
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check';
            checkboxDiv.innerHTML = `
                    <input class="form-check-input comparison-checkbox" type="checkbox" value="${run.name}" id="compare_${index}">
                    <label class="form-check-label" for="compare_${index}">
                        <strong>${run.name}</strong>
                        <small class="text-muted d-block">CPU: ${run.cpuAllThreads ? run.cpuAllThreads.toFixed(0) : 'N/A'} | Memory: ${run.memory ? (run.memory.read + run.memory.write).toFixed(0) : 'N/A'} MB/s</small>
                    </label>
                `;
            
            compareCheckboxes.appendChild(checkboxDiv);
        });
        
        allRunsData = runs.reduce((acc, run) => {
            acc[run.name] = run;
            return acc;
        }, {});
        
    } catch (error) {
        console.error('Error loading historical runs:', error);
        logMessage('❌ Error loading historical runs');
    }
    
    // Add change listener to checkboxes (max 3 selections)
    setTimeout(() => {
        document.querySelectorAll('.comparison-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const selected = document.querySelectorAll('.comparison-checkbox:checked');
                if (selected.length > 3) {
                    this.checked = false;
                    alert('Maximum 3 runs can be compared at once');
                }
            });
        });
    }, 100);
}

function addToComparison(runName) {
    const checkbox = document.querySelector(`.comparison-checkbox[value="${runName}"]`);
    if (checkbox) {
        checkbox.checked = true;
        const selected = document.querySelectorAll('.comparison-checkbox:checked');
        if (selected.length > 3) {
            checkbox.checked = false;
            alert('Maximum 3 runs can be compared at once');
        } else {
            updateComparisonChart();
        }
    }
}

function updateComparisonChart() {
    const selectedCheckboxes = document.querySelectorAll('.comparison-checkbox:checked');
    const selectedRuns = Array.from(selectedCheckboxes).map(cb => cb.value);
    
    if (selectedRuns.length < 2) {
        console.log('⚠️ Need at least 2 runs to compare');
        return;
    }
    
    console.log('📊 Comparing runs:', selectedRuns);
    
    const datasets = selectedRuns.map((runName, index) => {
        const run = allRunsData[runName];
        if (!run) return null;
        
        const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'];
        const color = colors[index % colors.length];
        
        return {
            label: runName,
            data: [
                run.cpu1Thread || 0,
                run.cpuAllThreads || 0,
                run.memory ? (run.memory.read + run.memory.write) / 2 : 0,
                run.disk ? run.disk.read : 0,
                run.disk ? run.disk.write : 0
            ],
            borderColor: color,
            backgroundColor: color + '33',
            fill: true
        };
    }).filter(dataset => dataset !== null);
    
    if (charts.comparison && datasets.length > 0) {
        charts.comparison.data.datasets = datasets;
        charts.comparison.update();
        logMessage(`📊 Comparing ${selectedRuns.length} runs: ${selectedRuns.join(', ')}`);
    }
}

function clearComparison() {
    document.querySelectorAll('.comparison-checkbox').forEach(cb => cb.checked = false);
    if (charts.comparison) {
        charts.comparison.data.datasets = [];
        charts.comparison.update();
    }
    logMessage('🧹 Comparison cleared');
}

async function resetAllRuns() {
    if (!confirm('⚠️ This will delete ALL benchmark runs and reset the system. Continue?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/runs', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            logMessage(`🗑️ ${result.message}`);
            
            // Clear current data and reload
            currentRunData = {};
            allRunsData = {};
            
            // Clear charts
            Object.keys(charts).forEach(chartName => {
                if (charts[chartName]) {
                    if (chartName === 'comparison') {
                        charts[chartName].data.datasets = [];
                    } else if (charts[chartName].data.datasets[0]) {
                        charts[chartName].data.datasets[0].data = [0, 0, 0, 0, 0];
                    }
                    charts[chartName].update();
                }
            });
            
            // Reload historical runs (should be empty now)
            await loadHistoricalRuns();
            
            // Clear comparison checkboxes
            clearComparison();
            
            alert('✅ All benchmark runs deleted successfully!');
        } else {
            const error = await response.json();
            logMessage(`❌ Failed to reset: ${error.error}`);
        }
    } catch (error) {
        console.error('Error resetting runs:', error);
        logMessage('❌ Error resetting runs - check console');
    }
}

async function deleteRun(runName) {
    if (!runName || runName === 'undefined' || runName === '') {
        logMessage('❌ Invalid run name');
        return;
    }
    
    if (!confirm(`⚠️ This will delete the benchmark run '${runName}'. Continue?`)) {
        return;
    }
    
    try {
        console.log(`🗑️ Attempting to delete run: "${runName}"`);
        
        // Validate runName
        if (!runName || runName === 'undefined' || runName === '') {
            logMessage('❌ Invalid run name for deletion');
            return;
        }
        
        const response = await fetch(`/api/run/${encodeURIComponent(runName)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log(`🔍 Delete response status: ${response.status}`);
        
        if (response.ok) {
            const result = await response.json();
            logMessage(`🗑️ ${result.message}`);
            
            // Remove from allRunsData
            delete allRunsData[runName];
            
            // Reload historical runs to refresh table
            await loadHistoricalRuns();
            
            // Clear from comparison if selected
            const checkbox = document.querySelector(`.comparison-checkbox[value="${runName}"]`);
            if (checkbox) {
                checkbox.remove();
                updateComparisonChart();
            }
            
            alert('✅ Run deleted successfully!');
        } else {
            const error = await response.json();
            logMessage(`❌ Failed to delete: ${error.error}`);
        }
    } catch (error) {
        console.error('Error deleting run:', error);
        logMessage('❌ Error deleting run - check console');
    }
}

function viewRun(runName) {
    const run = allRunsData[runName];
    if (!run) return;
    
    currentRunData = run;
    updateChartsFromRunData(run);
    
    // Switch to overview tab
    const overviewTab = new bootstrap.Tab(document.getElementById('overview-tab'));
    overviewTab.show();
}

function updateChartsFromRunData(runData) {
    if (runData.cpu1Thread && runData.cpuAllThreads) {
        updateChart('cpu', [runData.cpu1Thread, runData.cpuAllThreads]);
    }
    
    if (runData.memory) {
        updateChart('memory', [runData.memory.read, runData.memory.write]);
    }
    
    if (runData.disk) {
        updateChart('disk', [runData.disk.read, runData.disk.write]);
    }
    
    updateMetricsSummary();
}

function addToComparison(runName) {
    const select = document.getElementById('compareRuns');
    const options = select.options;
    
    for (let i = 0; i < options.length; i++) {
        if (options[i].value === runName) {
            options[i].selected = true;
            updateComparisonChart();
            break;
        }
    }
}

document.getElementById('compareRuns').addEventListener('change', updateComparisonChart);

function updateComparisonChart() {
    const select = document.getElementById('compareRuns');
    const selectedRuns = Array.from(select.selectedOptions).map(option => option.value);
    
    const datasets = selectedRuns.map((runName, index) => {
        const run = allRunsData[runName];
        if (!run) return null;
        
        const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'];
        const color = colors[index % colors.length];
        
        return {
            label: runName,
            data: [
                run.cpu1Thread || 0,
                run.cpuAllThreads || 0,
                run.memory ? (run.memory.read + run.memory.write) / 2 : 0,
                run.disk ? run.disk.read : 0,
                run.disk ? run.disk.write : 0
            ],
            borderColor: color,
            backgroundColor: color + '33',
            fill: true
        };
    }).filter(dataset => dataset !== null);
    
    charts.comparison.data.datasets = datasets;
    charts.comparison.update();
}
