import re

with open('/app/hornet/dashboard/index.html', 'r') as f:
    html = f.read()

# Replace the loadRecentFindings function with expandable version
old_func = '''function loadRecentFindings() {
    fetch('/api/v1/incidents/findings/recent?limit=5', {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(list) {
            var html = '';
            for (var i = 0; i < list.length; i++) {
                var f = list[i];
                html += '<div class="findings-panel p-2 rounded text-xs">';
                html += '<div class="flex justify-between mb-1"><span class="text-amber-400 font-medium">' + f.agent + '</span><span class="text-gray-500">' + (f.tokens_consumed || 0) + ' tok</span></div>';
                html += '<div class="text-gray-400 truncate">' + (f.reasoning ? f.reasoning.substring(0,80) : 'No reasoning') + '...</div>';
                html += '</div>';
            }
            document.getElementById('recentFindings').innerHTML = html || '<div class="text-gray-600">No findings yet</div>';
        })
        .catch(function() { document.getElementById('recentFindings').innerHTML = '<div class="text-gray-600 text-xs">No findings yet</div>'; });
}'''

new_func = '''function loadRecentFindings() {
    fetch('/api/v1/incidents/findings/recent?limit=5', {headers: {'X-API-Key': apiKey}})
        .then(function(r) { return r.json(); })
        .then(function(list) {
            var html = '';
            for (var i = 0; i < list.length; i++) {
                var f = list[i];
                var reasoning = f.reasoning || 'No reasoning';
                var preview = reasoning.length > 60 ? reasoning.substring(0,60) + '...' : reasoning;
                html += '<div class="findings-panel p-2 rounded text-xs">';
                html += '<div class="flex justify-between mb-1 cursor-pointer finding-header" data-idx="' + i + '">';
                html += '<span class="text-amber-400 font-medium">' + f.agent + '</span>';
                html += '<span class="text-gray-500">' + (f.tokens_consumed || 0) + ' tok <span class="expand-icon">+</span></span>';
                html += '</div>';
                html += '<div class="text-gray-400 finding-preview" data-idx="' + i + '">' + preview + '</div>';
                html += '<div class="text-gray-300 finding-full hidden mt-2 p-2 bg-black/40 rounded whitespace-pre-wrap" data-idx="' + i + '">' + reasoning + '</div>';
                html += '</div>';
            }
            document.getElementById('recentFindings').innerHTML = html || '<div class="text-gray-600">No findings yet</div>';
            // Add click handlers
            var headers = document.querySelectorAll('.finding-header');
            for (var j = 0; j < headers.length; j++) {
                headers[j].onclick = function() {
                    var idx = this.getAttribute('data-idx');
                    var preview = document.querySelector('.finding-preview[data-idx="' + idx + '"]');
                    var full = document.querySelector('.finding-full[data-idx="' + idx + '"]');
                    var icon = this.querySelector('.expand-icon');
                    if (full.classList.contains('hidden')) {
                        full.classList.remove('hidden');
                        preview.classList.add('hidden');
                        icon.textContent = '-';
                    } else {
                        full.classList.add('hidden');
                        preview.classList.remove('hidden');
                        icon.textContent = '+';
                    }
                };
            }
        })
        .catch(function() { document.getElementById('recentFindings').innerHTML = '<div class="text-gray-600 text-xs">No findings yet</div>'; });
}'''

html = html.replace(old_func, new_func)

with open('/app/hornet/dashboard/index.html', 'w') as f:
    f.write(html)

print('Expandable findings added!')
