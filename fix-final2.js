const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Fix 1: Add { after className= for desktop tab button
content = content.replace(
  "className=`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all ${desktopTab === tab ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'}`>",
  "className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all ${desktopTab === tab ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>"
);

// Fix 2: Incident panel - add { and desktop condition
content = content.replace(
  "className=`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden ${mobileTab !== 'incidents' ? 'hidden md:block' : ''}`>",
  "className={`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden ${mobileTab !== 'incidents' ? 'hidden' : ''} ${desktopTab === 'incidents' ? 'md:block' : 'md:hidden'}`}>"
);

console.log('Replacements made');
fs.writeFileSync(path, content);
