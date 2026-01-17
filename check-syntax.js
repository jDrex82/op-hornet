const fs = require('fs');
const content = fs.readFileSync('C:/Projects/hornet/hornet-dashboard/src/App.jsx', 'utf8');

// Check campaigns panel has correct className={
const campaignLine = content.split('\n').find(l => l.includes('Campaigns Panel'));
const nextLine = content.split('\n')[content.split('\n').findIndex(l => l.includes('Campaigns Panel')) + 1];

console.log('Line after Campaigns Panel comment:');
console.log(nextLine);
console.log('\nHas className={`:', nextLine.includes('className={`'));
