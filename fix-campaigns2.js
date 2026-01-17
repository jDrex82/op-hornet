const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let lines = fs.readFileSync(path, 'utf8').split('\n');

// Find line numbers
let mobileTabLine = -1;
let incidentPanelLine = -1;
let sidebarLine = -1;

for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('{/* Mobile Tab Switcher */}')) mobileTabLine = i;
  if (lines[i].includes('{/* Incident Panel */}')) incidentPanelLine = i;
  if (lines[i].includes('{/* Sidebar */}')) sidebarLine = i;
}

console.log('Found lines:', { mobileTabLine, incidentPanelLine, sidebarLine });

// Insert desktop tab bar before mobile tab switcher
if (mobileTabLine > 0) {
  const desktopTabs = `      {/* Desktop Tab Bar */}
      <div className="hidden md:flex gap-2 px-6 mb-4">
        {['incidents', 'campaigns'].map((tab) => (
          <button key={tab} onClick={() => setDesktopTab(tab)}
            className={\`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all \${desktopTab === tab ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'}\`}>
            {tab}
          </button>
        ))}
      </div>
`;
  lines.splice(mobileTabLine, 0, desktopTabs);
  console.log('Inserted desktop tabs at line', mobileTabLine);
  // Adjust other line numbers
  incidentPanelLine += desktopTabs.split('\n').length;
  sidebarLine += desktopTabs.split('\n').length;
}

// Fix incident panel line (add desktop tab condition)
if (incidentPanelLine > 0) {
  const nextLine = lines[incidentPanelLine + 1];
  if (nextLine && nextLine.includes('mobileTab')) {
    lines[incidentPanelLine + 1] = nextLine
      .replace("mobileTab !== 'incidents' ? 'hidden md:block' : ''", "mobileTab !== 'incidents' ? 'hidden' : ''} \${desktopTab === 'incidents' ? 'md:block' : 'md:hidden'");
    console.log('Fixed incident panel visibility');
  }
}

// Insert campaigns panel before sidebar
if (sidebarLine > 0) {
  const campaignsPanel = `
        {/* Campaigns Panel */}
        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden p-4 md:p-6 \${mobileTab !== 'campaigns' ? 'hidden' : ''} \${desktopTab === 'campaigns' ? 'md:block' : 'md:hidden'}\`}>
          <h2 className="text-lg font-semibold mb-4">Campaign Correlation</h2>
          <CampaignView apiKey={apiKey} onIncidentClick={(id) => fetchIncidentDetails(id)} />
        </div>
`;
  lines.splice(sidebarLine, 0, campaignsPanel);
  console.log('Inserted campaigns panel at line', sidebarLine);
}

fs.writeFileSync(path, lines.join('\n'));
console.log('Done!');
