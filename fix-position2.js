const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Find the exact pattern - incident panel end followed immediately by sidebar
const oldPattern = `        </div>
        {/* Sidebar */}`;

const newPattern = `        </div>

        {/* Campaigns Panel */}
        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden p-4 md:p-6 \${mobileTab !== 'campaigns' ? 'hidden' : ''} \${desktopTab === 'campaigns' ? 'md:block' : 'md:hidden'}\`}>
          <h2 className="text-lg font-semibold mb-4">Campaign Correlation</h2>
          <CampaignView apiKey={apiKey} onIncidentClick={(id) => fetchIncidentDetails(id)} />
        </div>

        {/* Sidebar */}`;

if (content.includes(oldPattern)) {
  content = content.replace(oldPattern, newPattern);
  fs.writeFileSync(path, content);
  console.log('Fixed! Campaigns panel inserted correctly.');
} else {
  console.log('Pattern not found. Let me search...');
  const idx = content.indexOf('{/* Sidebar */}');
  console.log('Sidebar comment at index:', idx);
  if (idx > 0) {
    console.log('Context before Sidebar:', JSON.stringify(content.substring(idx - 30, idx)));
  }
}
