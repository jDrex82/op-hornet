const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

// Find the exact line
const lines = content.split('\n');
const line799 = lines[798];
const line818 = lines[817];

console.log('Line 799 raw:');
console.log(JSON.stringify(line799));
console.log('\nLine 818 raw:');
console.log(JSON.stringify(line818));

// Check if patterns exist
console.log('\nSearching for className=`px-4...');
console.log('Found at index:', content.indexOf("className=`px-4"));
