const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Replace the static Export Report button with a functional one
const oldButton = `<button className="border border-white/15 text-slate-400 hover:text-white px-5 py-2 rounded-lg text-sm font-medium transition-all">Export Report</button>`;

const newButton = `<button 
                onClick={() => {
                  const url = \`\${API_BASE}/api/v1/reports/\${selectedIncident.id}/pdf\`;
                  const link = document.createElement('a');
                  link.href = url;
                  link.setAttribute('download', \`HORNET_Incident_\${selectedIncident.id.substring(0,8)}.pdf\`);
                  
                  // Add API key header via fetch and blob
                  fetch(url, {
                    headers: { 'X-API-Key': apiKey || localStorage.getItem('hornet_api_key') }
                  })
                  .then(res => res.blob())
                  .then(blob => {
                    const blobUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = blobUrl;
                    a.download = \`HORNET_Incident_\${selectedIncident.id.substring(0,8)}_\${new Date().toISOString().split('T')[0]}.pdf\`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(blobUrl);
                  })
                  .catch(err => console.error('PDF export failed:', err));
                }}
                className="border border-amber-500/50 text-amber-400 hover:bg-amber-500 hover:text-slate-950 px-5 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="12" y2="18"/><line x1="15" y1="15" x2="12" y2="18"/>
                </svg>
                Export PDF
              </button>`;

if (content.includes(oldButton)) {
  content = content.replace(oldButton, newButton);
  fs.writeFileSync(path, content);
  console.log('Export PDF button updated!');
} else {
  console.log('Button not found, searching...');
  const idx = content.indexOf('Export Report');
  console.log('Found at index:', idx);
  if (idx > 0) {
    console.log('Context:', content.substring(idx - 50, idx + 100));
  }
}
