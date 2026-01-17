const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Find the incident panel line with mobileTab condition and add desktopTab
const oldPattern = "${mobileTab !== 'incidents' ? 'hidden md:block' : ''}";
const newPattern = "${mobileTab !== 'incidents' ? 'hidden' : ''} ${desktopTab === 'incidents' ? 'md:block' : 'md:hidden'}";

if (content.includes(oldPattern)) {
  content = content.replace(oldPattern, newPattern);
  fs.writeFileSync(path, content);
  console.log('Fixed incident panel visibility!');
} else {
  console.log('Pattern not found. Searching...');
  const idx = content.indexOf("mobileTab !== 'incidents'");
  console.log('Found mobileTab check at index:', idx);
  if (idx > 0) {
    console.log('Context:', content.substring(idx - 20, idx + 80));
  }
}
