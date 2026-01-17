const fs = require('fs');
const path = 'C:/Projects/hornet/hornet-dashboard/src/App.jsx';
let content = fs.readFileSync(path, 'utf8');

const line799 = content.split('\n')[798];

// Find the character after className=
const idx = line799.indexOf('className=');
if (idx >= 0) {
  const char = line799[idx + 10];
  console.log('Character after className=:', char);
  console.log('Char code:', char.charCodeAt(0));
  console.log('Is backtick (96)?:', char.charCodeAt(0) === 96);
}

// Try to find and replace using the actual content
const searchStr = line799.trim();
console.log('\nSearch string exists in file:', content.includes(searchStr));
