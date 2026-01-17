const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Match with the blank line that exists
const oldPattern = "        </div>\r\n\r\n        {/* Sidebar */}";

const newPattern = `        </div>\r\n\r\n        {/* Campaigns Panel */}\r\n        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden p-4 md:p-6 \${mobileTab !== 'campaigns' ? 'hidden' : ''} \${desktopTab === 'campaigns' ? 'md:block' : 'md:hidden'}\`}>\r\n          <h2 className="text-lg font-semibold mb-4">Campaign Correlation</h2>\r\n          <CampaignView apiKey={apiKey} onIncidentClick={(id) => fetchIncidentDetails(id)} />\r\n        </div>\r\n\r\n        {/* Sidebar */}`;

if (content.includes(oldPattern)) {
  content = content.replace(oldPattern, newPattern);
  fs.writeFileSync(path, content);
  console.log('Fixed! Campaigns panel inserted correctly.');
} else {
  console.log('Still not found');
}
