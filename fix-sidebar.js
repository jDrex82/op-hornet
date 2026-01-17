const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Update sidebar to hide on desktop when campaigns is selected
const oldSidebar = "${mobileTab !== 'health' ? 'hidden md:flex' : 'flex'}";
const newSidebar = "${mobileTab !== 'health' ? 'hidden' : 'flex'} ${desktopTab === 'incidents' ? 'md:flex' : 'md:hidden'}";

if (content.includes(oldSidebar)) {
  content = content.replace(oldSidebar, newSidebar);
  fs.writeFileSync(path, content);
  console.log('Fixed sidebar visibility!');
} else {
  console.log('Checking for pattern...');
  const idx = content.indexOf("mobileTab !== 'health'");
  if (idx > 0) {
    console.log('Found at:', idx);
    console.log('Context:', content.substring(idx - 10, idx + 80));
  }
}
