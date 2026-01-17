const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Edit 1: Add desktop tab bar before mobile tab switcher
const oldMobile = '      {/* Mobile Tab Switcher */}\n      <div className="md:hidden flex border-b border-white/5">';
const newMobile = `      {/* Desktop Tab Bar */}
      <div className="hidden md:flex gap-2 px-6 mb-4">
        {['incidents', 'campaigns'].map((tab) => (
          <button key={tab} onClick={() => setDesktopTab(tab)}
            className={\`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all \${desktopTab === tab ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'}\`}>
            {tab}
          </button>
        ))}
      </div>

      {/* Mobile Tab Switcher */}
      <div className="md:hidden flex border-b border-white/5">`;

content = content.replace(oldMobile, newMobile);

// Edit 2: Fix incident panel visibility
const oldIncident = `{/* Incident Panel */}
        <div className=\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden \${mobileTab !== 'incidents' ? 'hidden md:block' : ''}\`>`;
const newIncident = `{/* Incident Panel */}
        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden \${mobileTab !== 'incidents' ? 'hidden' : ''} \${desktopTab === 'incidents' ? 'md:block' : 'md:hidden'}\`}>`;

content = content.replace(oldIncident, newIncident);

// Edit 3: Add campaigns panel before sidebar
const oldSidebar = `        </div>
        {/* Sidebar */}`;
const newSidebar = `        </div>

        {/* Campaigns Panel */}
        <div className={\`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden p-4 md:p-6 \${mobileTab !== 'campaigns' ? 'hidden' : ''} \${desktopTab === 'campaigns' ? 'md:block' : 'md:hidden'}\`}>
          <h2 className="text-lg font-semibold mb-4">Campaign Correlation</h2>
          <CampaignView apiKey={apiKey} onIncidentClick={(id) => fetchIncidentDetails(id)} />
        </div>

        {/* Sidebar */}`;

content = content.replace(oldSidebar, newSidebar);

fs.writeFileSync(path, content);
console.log('Done!');
