const fs = require('fs');
const content = fs.readFileSync('C:/Projects/hornet/hornet-dashboard/src/App.jsx', 'utf8');

// Check for correct JSX syntax
const hasCorrectDesktopTab = content.includes("className={`px-4 py-2 rounded-lg");
const hasCorrectIncidentPanel = content.includes("${desktopTab === 'incidents' ? 'md:block' : 'md:hidden'}");
const hasCampaignView = content.includes("<CampaignView apiKey={apiKey}");

console.log('Desktop tab className correct:', hasCorrectDesktopTab);
console.log('Incident panel has desktop condition:', hasCorrectIncidentPanel);
console.log('CampaignView component present:', hasCampaignView);
