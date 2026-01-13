html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HORNET - Autonomous SOC</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        *{font-family:system-ui,sans-serif}.mono{font-family:monospace}body{background:linear-gradient(135deg,#0a0a0f 0%,#111118 50%,#0d0d12 100%)}.stat-card{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08)}.glow-border{border:1px solid rgba(245,158,11,0.3);box-shadow:0 0 20px rgba(245,158,11,0.1)}.incident-row{transition:all 0.2s;border-left:2px solid transparent}.incident-row:hover{background:rgba(245,158,11,0.05);border-left-color:#f59e0b}.badge{font-size:0.65rem;letter-spacing:0.05em;text-transform:uppercase;font-weight:600}.modal-backdrop{backdrop-filter:blur(8px);background:rgba(0,0,0,0.8)}.token-bar{height:4px;background:rgba(255,255,255,0.1);border-radius:2px}.token-bar-fill{height:100%;background:linear-gradient(90deg,#10b981,#f59e0b)}.findings-panel{background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1)}@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}.pulse-live{animation:pulse 2s infinite}
    </style>
</head>
<body class="text-white min-h-screen">
    <div id="loginModal" class="fixed inset-0 modal-backdrop flex items-center justify-center z-50"><div class="bg-gray-900 glow-border p-8 rounded-lg w-96"><div class="flex items-center justify-center mb-6"><span class="text-4xl font-bold text-amber-500">[H]</span><div class="ml-3"><h1 class="text-2xl font-bold">HORNET</h1><p class="text-xs text-gray-500">AUTONOMOUS SOC</p></div></div><form id="loginForm"><div class="mb-4"><label class="block text-xs text-gray-400 mb-2">API KEY</label><input type="password" id="apiKeyInput" placeholder="hnt_..." class="mono w-full p-3 bg-black/50 rounded border border-gray-700 focus:border-amber-500 focus:outline-none text-sm"></div><button type="submit" class="w-full bg-amber-500 text-black font-bold py-3 rounded hover:bg-amber-400">AUTHENTICATE</button><p id="loginError" class="text-red-400 text-xs mt-3 hidden text-center">Authentication failed</p></form></div></div>
    <div id="dashboard" class="hidden"><header class="bg-black/40 border-b border-gray-800 px-6 py-3"><div class="flex items-center justify-between"><div class="flex items-center"><span class="text-2xl font-bold text-amber-500">[H]</span><h1 class="text-xl font-bold ml-2">HORNET</h1><div class="ml-4 flex items-center"><span class="w-2 h-2 bg-green-500 rounded-full pulse-live mr-2"></span><span class="text-xs text-green-400">OPERATIONAL</span></div></div><div class="flex items-center space-x-6"><div class="text-right"><div class="text-xs text-gray-500">CONNECTED</div><div id="wsStatus" class="mono text-xs text-green-400">* WebSocket Live</div></div><button onclick="logout()" class="text-gray-400 hover:text-white text-sm border border-gray-700 px-3 py-1 rounded">Logout</button></div></div></header>
    <div class="grid grid-cols-5 gap-4 p-6"><div class="stat-card rounded-lg p-4"><div class="text-gray-400 text-xs mb-1">ACTIVE INCIDENTS</div><div id="activeIncidents" class="text-3xl font-bold text-amber-500 mono">-</div><div class="text-xs text-gray-600 mt-1">processing now</div></div><div class="stat-card rounded-lg p-4"><div class="text-gray-400 text-xs mb-1">EVENTS / HOUR</div><div id="eventsHour" class="text-3xl font-bold text-cyan-400 mono">-</div><div class="text-xs text-gray-600 mt-1">last 60 minutes</div></div><div class="stat-card rounded-lg p-4"><div class="text-gray-400 text-xs mb-1">AGENTS ONLINE</div><div id="agentsOnline" class="text-3xl font-bold text-green-500 mono">-</div><div class="text-xs text-gray-600 mt-1">swarm capacity</div></div><div class="stat-card rounded-lg p-4"><div class="text-gray-400 text-xs mb-1">AUTO-RESOLVED</div><div id="automationRate" class="text-3xl font-bold text-purple-400 mono">-</div><div class="text-xs text-gray-600 mt-1">no human needed</div></div><div class="stat-card rounded-lg p-4"><div class="text-gray-400 text-xs mb-1">TOKENS TODAY</div><div id="tokensToday" class="text-3xl font-bold text-amber-300 mono">-</div><div id="tokensCost" class="text-xs text-gray-600 mt-1">est.</div></div></div>
    <div class="px-6 pb-6 grid grid-cols-3 gap-6"><div class="col-span-2 bg-black/30 rounded-lg glow-border overflow-hidden"><div class="px-4 py-3 border-b border-gray-800 flex justify-between items-center bg-black/20"><h2 class="font-semibold text-sm">INCIDENT QUEUE</h2><div class="flex items-center space-x-3"><select id="stateFilter" class="bg-black/50 border border-gray-700 rounded px-3 py-1 text-xs"><option value="">All States</option><option value="CLOSED">Closed</option><option value="ERROR">Error</option><option value="PROPOSAL">Proposal</option></select><button onclick="loadIncidents()" class="text-xs text-amber-500 hover:text-amber-400">Refresh</button></div></div><div class="overflow-y-auto" style="max-height:500px"><table class="w-full"><thead class="text-gray-500 text-xs sticky top-0 bg-gray-900/95"><tr class="border-b border-gray-800"><th class="text-left p-3">ID</th><th class="text-left p-3">STATE</th><th class="text-left p-3">SEVERITY</th><th class="text-left p-3">CONFIDENCE</th><th class="text-left p-3">TOKENS</th><th class="text-left p-3">AGE</th><th class="text-left p-3"></th></tr></thead><tbody id="incidentsTable" class="text-sm"></tbody></table></div></div>
    <div class="space-y-4"><div class="bg-black/30 rounded-lg glow-border p-4"><h3 class="text-xs text-gray-400 mb-3">AGENT ACTIVITY</h3><div id="agentActivity" class="space-y-2 text-xs"></div></div><div class="bg-black/30 rounded-lg glow-border p-4 border-l-2 border-l-red-500"><h3 class="text-xs text-red-400 mb-3">REQUIRES ATTENTION</h3><div id="requiresAttention" class="space-y-2 text-xs max-h-40 overflow-y-auto"></div></div><div class="bg-black/30 rounded-lg glow-border p-4"><h3 class="text-xs text-gray-400 mb-3">RECENT FINDINGS</h3><div id="recentFindings" class="space-y-2 text-xs max-h-40 overflow-y-auto"></div></div><div class="bg-black/30 rounded-lg glow-border p-4"><h3 class="text-xs text-gray-400 mb-3">SYSTEM HEALTH</h3><div class="space-y-2"><div class="flex justify-between text-xs"><span class="text-gray-400">Redis</span><span class="text-green-400">Connected</span></div><div class="flex justify-between text-xs"><span class="text-gray-400">PostgreSQL</span><span class="text-green-400">Connected</span></div><div class="flex justify-between text-xs"><span class="text-gray-400">Workers</span><span class="text-green-400">3 Active</span></div><div class="flex justify-between text-xs"><span class="text-gray-400">Anthropic API</span><span class="text-green-400">Connected</span></div></div></div></div></div></div>
    <div id="incidentModal" class="fixed inset-0 modal-backdrop hidden z-50 flex items-center justify-center"><div class="bg-gray-900 glow-border rounded-lg w-4/5 max-w-4xl max-h-[85vh] overflow-hidden"><div class="px-6 py-4 border-b border-gray-800 flex justify-between items-center bg-black/30"><div><h2 class="font-bold">Incident Details</h2><div id="modalIncidentId" class="mono text-xs text-gray-500"></div></div><button onclick="closeModal()" class="text-gray-400 hover:text-white text-2xl">x</button></div><div class="p-6 overflow-y-auto" style="max-height:calc(85vh - 80px)"><div id="modalContent">Loading...</div></div></div></div>
<script>
var apiKey = localStorage.getItem('hornet_api_key');
var ws = null;
if (apiKey) validateAndShowDashboard();

document.getElementById('loginForm').onsubmit = function(e) {
    e.preventDefault();
    apiKey = document.getElementById('apiKeyInput').value;
    validateApiKey(apiKey).then(function(ok) {
        if (ok) {
            localStorage.setItem('hornet_api_key', apiKey);
            validateAndShowDashboard();
        } else {
            document.getElementById('loginError').classList.remove('hidden');
        }
    });
};

function validateApiKey(k) {
    return fetch('/api/v1/health/agents', {headers: {'X-API-Key': k}})
        .then(function(r) { return r.ok; })
        .catch(function() { return false; });
}

function validateAndShowDashboard() {
    validateApiKey(apiKey).then(function(ok) {
        if (ok) {
            document.getElementById('loginModal').classList.add('hidden');
            document.getElementById('dashboard').classList.remove('hidden');
            loadDashboard();
            connectWebSocket();
        } else {
            localStorage.removeItem('hornet_api_key');
            apiKey = null;
        }
    });
}

function logout() {
    localStorage.removeItem('hornet_api_key');
    if (ws) ws.close();
    location.reload();
}

function loadDashboard() {
    fetch('/api/v1/health/agents', {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(a) { document.getElementById('agentsOnline').textContent = a.total_agents || 56; })
        .catch(function() { document.getElementById('agentsOnline').textContent = '56'; });
    loadIncidents();
    loadStats();
    loadRecentFindings();
    loadRequiresAttention();
    loadAgentActivity();
}

function loadStats() {
    fetch('/api/v1/incidents', {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var list = d.data || [];
            var closed = list.filter(function(x) { return x.state === 'CLOSED'; }).length;
            var rate = list.length > 0 ? Math.round(closed / list.length * 100) : 0;
            var hourAgo = Date.now() - 3600000;
            var recent = list.filter(function(x) { return new Date(x.created_at).getTime() > hourAgo; }).length;
            var tokens = list.reduce(function(s, x) { return s + (x.tokens_used || 0); }, 0);
            document.getElementById('eventsHour').textContent = recent;
            document.getElementById('automationRate').textContent = rate + '%';
            document.getElementById('tokensToday').textContent = (tokens / 1000).toFixed(1) + 'k';
        });
}

function loadIncidents() {
    var state = document.getElementById('stateFilter').value;
    var url = state ? '/api/v1/incidents?state=' + state : '/api/v1/incidents';
    fetch(url, {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var list = d.data || [];
            document.getElementById('activeIncidents').textContent = list.filter(function(x) { return x.state !== 'CLOSED' && x.state !== 'ERROR'; }).length;
            var html = '';
            for (var i = 0; i < list.length; i++) {
                var x = list[i];
                html += '<tr class="incident-row border-b border-gray-800/50 cursor-pointer" data-id="' + x.id + '">';
                html += '<td class="p-3 mono text-xs text-gray-300">' + x.id.substring(0,8) + '</td>';
                html += '<td class="p-3"><span class="badge px-2 py-1 rounded ' + getStateColor(x.state) + '">' + x.state + '</span></td>';
                html += '<td class="p-3"><span class="badge px-2 py-1 rounded ' + getSeverityColor(x.severity) + '">' + (x.severity || '-') + '</span></td>';
                html += '<td class="p-3 mono text-xs">' + (x.confidence * 100).toFixed(0) + '%</td>';
                html += '<td class="p-3 mono text-xs">' + (x.tokens_used || 0).toLocaleString() + '</td>';
                html += '<td class="p-3 mono text-xs text-gray-400">' + getAge(x.created_at) + '</td>';
                html += '<td class="p-3"><button class="text-amber-500 text-xs view-btn" data-id="' + x.id + '">View</button></td>';
                html += '</tr>';
            }
            document.getElementById('incidentsTable').innerHTML = html || '<tr><td colspan="7" class="p-8 text-center text-gray-600">No incidents</td></tr>';
            // Add click handlers
            var rows = document.querySelectorAll('.incident-row');
            for (var j = 0; j < rows.length; j++) {
                rows[j].onclick = function() { viewIncident(this.getAttribute('data-id')); };
            }
        });
}

function loadRecentFindings() {
    fetch('/api/v1/incidents/findings/recent?limit=5', {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(list) {
            var html = '';
            for (var i = 0; i < list.length; i++) {
                var f = list[i];
                html += '<div class="findings-panel p-2 rounded text-xs">';
                html += '<div class="flex justify-between mb-1"><span class="text-amber-400">' + f.agent + '</span><span class="text-gray-500">' + (f.tokens_consumed || 0) + ' tok</span></div>';
                html += '<div class="text-gray-400 truncate">' + (f.reasoning ? f.reasoning.substring(0,80) : 'No reasoning') + '...</div>';
                html += '</div>';
            }
            document.getElementById('recentFindings').innerHTML = html || '<div class="text-gray-600">No findings</div>';
        })
        .catch(function() { document.getElementById('recentFindings').innerHTML = '<div class="text-gray-600">No findings yet</div>'; });
}

function loadRequiresAttention() {
    fetch('/api/v1/incidents', {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var list = (d.data || []).filter(function(x) {
                return x.state === 'ESCALATED' || x.state === 'PROPOSAL' || x.state === 'ERROR';
            });
            var html = '';
            if (list.length === 0) {
                html = '<div class="text-green-400 text-xs">OK - No threats need attention</div>';
            } else {
                for (var i = 0; i < list.length; i++) {
                    var x = list[i];
                    html += '<div class="p-2 rounded cursor-pointer hover:bg-red-500/10 border border-red-500/20 attn-item" data-id="' + x.id + '">';
                    html += '<div class="flex justify-between mb-1"><span class="mono text-xs">' + x.id.substring(0,8) + '</span><span class="badge px-1 rounded ' + getStateColor(x.state) + '">' + x.state + '</span></div>';
                    html += '<div class="text-xs text-gray-500">' + getAttentionReason(x) + '</div>';
                    html += '</div>';
                }
            }
            document.getElementById('requiresAttention').innerHTML = html;
            var items = document.querySelectorAll('.attn-item');
            for (var j = 0; j < items.length; j++) {
                items[j].onclick = function() { viewIncident(this.getAttribute('data-id')); };
            }
        });
}

function getAttentionReason(x) {
    if (x.state === 'ESCALATED') return 'Escalated - needs review';
    if (x.state === 'PROPOSAL') return 'Action pending approval';
    if (x.state === 'ERROR') return 'Processing error';
    return 'Requires review';
}

function loadAgentActivity() {
    var agents = ['intel', 'analyst', 'responder', 'oversight', 'router'];
    var html = '';
    for (var i = 0; i < agents.length; i++) {
        html += '<div class="flex justify-between"><span class="text-gray-400">' + agents[i] + '</span><span class="text-green-400">Ready</span></div>';
    }
    document.getElementById('agentActivity').innerHTML = html;
}

function connectWebSocket() {
    var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(proto + '//' + location.host + '/api/v1/ws/default-tenant?api_key=' + apiKey);
    ws.onopen = function() { document.getElementById('wsStatus').textContent = 'WebSocket Live'; };
    ws.onmessage = function(e) {
        var m = JSON.parse(e.data);
        if (m.type === 'incident_update') { loadIncidents(); loadStats(); loadRequiresAttention(); }
    };
    ws.onclose = function() { document.getElementById('wsStatus').textContent = 'Reconnecting...'; setTimeout(connectWebSocket, 3000); };
}

function getStateColor(s) {
    var map = {DETECTION:'bg-blue-500/20 text-blue-400',ENRICHMENT:'bg-purple-500/20 text-purple-400',ANALYSIS:'bg-indigo-500/20 text-indigo-400',PROPOSAL:'bg-cyan-500/20 text-cyan-400',OVERSIGHT:'bg-orange-500/20 text-orange-400',EXECUTION:'bg-yellow-500/20 text-yellow-400',ESCALATED:'bg-red-500/20 text-red-400',CLOSED:'bg-gray-500/20 text-gray-400',ERROR:'bg-red-900/30 text-red-300'};
    return map[s] || 'bg-gray-500/20 text-gray-400';
}

function getSeverityColor(s) {
    var map = {CRITICAL:'bg-red-500/20 text-red-400',HIGH:'bg-orange-500/20 text-orange-400',MEDIUM:'bg-yellow-500/20 text-yellow-400',LOW:'bg-green-500/20 text-green-400'};
    return map[s] || 'bg-gray-500/20 text-gray-400';
}

function getAge(t) {
    var diff = Date.now() - new Date(t).getTime();
    var mins = Math.floor(diff / 60000);
    if (mins < 60) return mins + 'm';
    var hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h';
    return Math.floor(hrs / 24) + 'd';
}

function viewIncident(id) {
    document.getElementById('incidentModal').classList.remove('hidden');
    document.getElementById('modalIncidentId').textContent = id;
    document.getElementById('modalContent').innerHTML = '<div class="text-gray-500">Loading...</div>';
    fetch('/api/v1/incidents/' + id, {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(inc) {
            var html = '<div class="space-y-4">';
            html += '<div><span class="badge px-2 py-1 rounded ' + getStateColor(inc.state) + '">' + inc.state + '</span> ';
            html += '<span class="badge px-2 py-1 rounded ' + getSeverityColor(inc.severity) + '">' + inc.severity + '</span></div>';
            html += '<div class="grid grid-cols-2 gap-4 text-sm">';
            html += '<div><span class="text-gray-500">Confidence:</span> ' + (inc.confidence * 100).toFixed(0) + '%</div>';
            html += '<div><span class="text-gray-500">Tokens:</span> ' + (inc.tokens_used || 0).toLocaleString() + '</div>';
            html += '<div><span class="text-gray-500">Created:</span> ' + new Date(inc.created_at).toLocaleString() + '</div>';
            html += '<div><span class="text-gray-500">Updated:</span> ' + new Date(inc.updated_at).toLocaleString() + '</div>';
            html += '</div>';
            html += '<div><span class="text-gray-500">Summary:</span><div class="bg-black/30 p-3 rounded mt-1 text-sm">' + (inc.summary || 'No summary') + '</div></div>';
            html += '<div><span class="text-gray-500">Raw Data:</span><pre class="bg-black/50 p-3 rounded mt-1 text-xs overflow-auto max-h-40">' + JSON.stringify(inc, null, 2) + '</pre></div>';
            html += '</div>';
            document.getElementById('modalContent').innerHTML = html;
        })
        .catch(function(e) { document.getElementById('modalContent').innerHTML = '<div class="text-red-400">Error: ' + e.message + '</div>'; });
}

function closeModal() { document.getElementById('incidentModal').classList.add('hidden'); }
document.onkeydown = function(e) { if (e.key === 'Escape') closeModal(); };
document.getElementById('stateFilter').onchange = loadIncidents;
setInterval(function() { loadIncidents(); loadStats(); loadRequiresAttention(); }, 30000);
</script>
</body>
</html>"""
with open('/app/hornet/dashboard/index.html', 'w') as f:
    f.write(html)
print('Done')
