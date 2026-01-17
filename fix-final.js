const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Fix 1: Desktop tab bar className (line ~798)
content = content.replace(
  /className=`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all \$\{desktopTab === tab/g,
  "className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all ${desktopTab === tab"
);

// Fix 2: Incident panel visibility - add desktop tab condition
content = content.replace(
  /className=`bg-slate-900\/50 border border-white\/5 rounded-xl overflow-hidden \$\{mobileTab !== 'incidents' \? 'hidden md:block' : ''\}`>/,
  "className={`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden ${mobileTab !== 'incidents' ? 'hidden' : ''} ${desktopTab === 'incidents' ? 'md:block' : 'md:hidden'}`}>"
);

fs.writeFileSync(path, content);
console.log('Fixed!');
