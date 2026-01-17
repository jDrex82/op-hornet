const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Remove the wrongly placed campaigns panel (it's inside the sidebar map)
const wrongPanel = `
        {/* Campaigns Panel */}
        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden p-4 md:p-6 \${mobileTab !== 'campaigns' ? 'hidden' : ''} \${desktopTab === 'campaigns' ? 'md:block' : 'md:hidden'}\`}>
          <h2 className="text-lg font-semibold mb-4">Campaign Correlation</h2>
          <CampaignView apiKey={apiKey} onIncidentClick={(id) => fetchIncidentDetails(id)} />
        </div>
`;

content = content.replace(wrongPanel, '');
console.log('Removed wrongly placed panel');

// Now insert it correctly - after incident panel closing tag, before sidebar
const incidentPanelEnd = `          )}
        </div>

        {/* Sidebar */}`;

const correctPlacement = `          )}
        </div>

        {/* Campaigns Panel */}
        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden p-4 md:p-6 \${mobileTab !== 'campaigns' ? 'hidden' : ''} \${desktopTab === 'campaigns' ? 'md:block' : 'md:hidden'}\`}>
          <h2 className="text-lg font-semibold mb-4">Campaign Correlation</h2>
          <CampaignView apiKey={apiKey} onIncidentClick={(id) => fetchIncidentDetails(id)} />
        </div>

        {/* Sidebar */}`;

if (content.includes(incidentPanelEnd)) {
  content = content.replace(incidentPanelEnd, correctPlacement);
  console.log('Inserted panel in correct position');
} else {
  console.log('Could not find insertion point');
}

fs.writeFileSync(path, content);
console.log('Done!');
